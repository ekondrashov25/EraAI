import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.callbacks.manager import get_openai_callback
import asyncio
import time

from src.config import config

logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with OpenAI LLM APIs."""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.chat_model = ChatOpenAI(
            model=config.OPENAI_MODEL,
            temperature=0.7,
            api_key=config.OPENAI_API_KEY,
        )
        # Simple RPM limiter state
        self._request_timestamps: list[float] = []
        # Simple TPM limiter state: list of (timestamp, tokens)
        self._token_timestamps: list[tuple[float, int]] = []
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenAI.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            functions: List of function definitions for function calling
            
        Returns:
            OpenAI API response
        """
        # Default response token cap from config
        if max_tokens is None:
            max_tokens = config.RESPONSE_MAX_TOKENS

        attempt = 0
        last_error: Optional[Exception] = None
        while attempt < config.OPENAI_RETRY_MAX_ATTEMPTS:
            try:
                # Pre-trim messages to stay within prompt budget
                messages = self._shrink_messages(messages)
                # Throttle based on RPM/TPM before making the call
                await self._throttle_if_needed()
                await self._throttle_tokens_if_needed(
                    self._estimate_message_tokens(messages) + (max_tokens or 0)
                )
                params = {
                    "model": config.OPENAI_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if functions:
                    # Convert functions to tools format for newer API
                    tools = []
                    for func in functions:
                        tools.append({
                            "type": "function",
                            "function": func
                        })
                    params["tools"] = tools

                response = self.client.chat.completions.create(**params)
                logger.info(f"Chat completion successful: {len(response.choices)} choices")
                self._record_request()
                # Record token usage for TPM limiter when available
                try:
                    if response.usage and hasattr(response.usage, "total_tokens"):
                        total_tokens_used = int(response.usage.total_tokens)
                    else:
                        total_tokens_used = self._estimate_message_tokens(messages) + (max_tokens or 0)
                    self._record_tokens(total_tokens_used)
                except Exception:
                    pass
                # Handle both old function_call and new tool_calls format
                function_call = None
                if hasattr(response.choices[0].message, 'function_call') and response.choices[0].message.function_call:
                    function_call = response.choices[0].message.function_call
                elif hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                    # Convert tool_calls to function_call format for compatibility
                    tool_call = response.choices[0].message.tool_calls[0]
                    function_call = type('FunctionCall', (), {
                        'name': tool_call.function.name,
                        'arguments': tool_call.function.arguments
                    })()
                
                return {
                    "content": response.choices[0].message.content,
                    "function_call": function_call,
                    "usage": response.usage.dict() if response.usage else None,
                    "model": response.model,
                    "id": response.id
                }
            except Exception as e:
                message = str(e)
                # On rate limit or token errors, backoff and try to reduce size
                if "rate_limit" in message or "429" in message or "tokens per min" in message or "Request too large" in message:
                    attempt += 1
                    last_error = e
                    backoff = config.OPENAI_RETRY_BASE_DELAY_SEC * (2 ** (attempt - 1))
                    logger.warning(f"Retrying after rate/token error (attempt {attempt}/{config.OPENAI_RETRY_MAX_ATTEMPTS}) in {backoff:.1f}s: {message}")
                    # Reduce max_tokens and shrink prompt roughly by dropping oldest messages
                    max_tokens = max(128, int(max_tokens * 0.8))
                    messages = self._shrink_messages(messages)
                    # Add a small extra delay to respect TPM soft limits
                    await self._throttle_tokens_if_needed(
                        self._estimate_message_tokens(messages) + (max_tokens or 0)
                    )
                    await asyncio.sleep(backoff)
                    continue
                logger.error(f"Error in chat completion: {message}")
                raise
        # If we exit loop without returning, raise last error
        logger.error(f"Exceeded retry attempts for chat completion: {last_error}")
        raise last_error if last_error else RuntimeError("Chat completion failed")
    
    async def chat_with_langchain(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Use LangChain for chat completion with better message handling.
        
        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt
            
        Returns:
            AI response content
        """
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            
            if system_prompt:
                langchain_messages.append(SystemMessage(content=system_prompt))
            
            for msg in messages:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
            
            with get_openai_callback() as cb:
                response = self.chat_model.invoke(langchain_messages)
                logger.info(f"LangChain chat successful. Tokens used: {cb.total_tokens}")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error in LangChain chat: {str(e)}")
            raise
    
    async def function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict],
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Execute function calling with the LLM.
        
        Args:
            messages: List of message dictionaries
            functions: List of function definitions
            temperature: Sampling temperature (lower for function calling)
            
        Returns:
            Function call response
        """
        try:
            response = await self.chat_completion(
                messages=messages,
                functions=functions,
                temperature=temperature
            )
            
            if response.get("function_call"):
                logger.info(f"Function call detected: {response['function_call'].name}")
                return response
            else:
                logger.warning("No function call detected in response")
                return response
                
        except Exception as e:
            logger.error(f"Error in function calling: {str(e)}")
            raise
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ):
        """
        Stream chat completion responses.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            
        Yields:
            Streaming response chunks
        """
        try:
            # Ensure prompt is within limits before streaming
            trimmed = self._shrink_messages(messages)
            await self._throttle_if_needed()
            await self._throttle_tokens_if_needed(
                self._estimate_message_tokens(trimmed) + config.RESPONSE_MAX_TOKENS
            )
            stream = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=trimmed,
                temperature=temperature,
                stream=True
            )
            self._record_request()
            # Best-effort token accounting for stream: count input + expected output cap
            try:
                self._record_tokens(self._estimate_message_tokens(trimmed) + config.RESPONSE_MAX_TOKENS)
            except Exception:
                pass
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            raise

    def _shrink_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prefer newest messages and RAG-augmented user turn; keep system, drop oldest first, truncate last if needed."""
        if not messages:
            return messages
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
        history = messages[1:] if system_msg else messages[:]
        # Prefer the newest turns
        history = history[-max(1, config.MAX_HISTORY_MESSAGES):]
        budget = config.MAX_PROMPT_CHARS
        kept_reversed: List[Dict[str, Any]] = []
        used = 0
        for msg in reversed(history):
            content = msg.get("content") or ""
            length = len(content)
            if used + length <= budget:
                kept_reversed.append(msg)
                used += length
            else:
                if not kept_reversed and length > 0:
                    # Include partial newest message
                    part = max(0, budget)
                    new_msg = dict(msg)
                    new_msg["content"] = content[:part]
                    kept_reversed.append(new_msg)
                    used += len(new_msg["content"]) 
                break
        kept_history = list(reversed(kept_reversed))
        if system_msg:
            remaining = max(0, budget - sum(len((m.get("content") or "")) for m in kept_history))
            sys_content = system_msg.get("content") or ""
            if len(sys_content) > remaining and remaining > 0:
                sys_copy = dict(system_msg)
                sys_copy["content"] = sys_content[:remaining]
                return [sys_copy] + kept_history
            elif remaining <= 0:
                sys_copy = dict(system_msg)
                sys_copy["content"] = sys_content[:128]
                return [sys_copy] + kept_history
            else:
                return [system_msg] + kept_history
        return kept_history

    async def _throttle_if_needed(self) -> None:
        """Throttle requests to stay under an RPM ceiling if configured."""
        rpm = config.OPENAI_RPM_LIMIT
        if not rpm or rpm <= 0:
            return
        now = time.time()
        window_start = now - config.RPM_WINDOW_SEC
        # Drop timestamps outside window
        self._request_timestamps = [t for t in self._request_timestamps if t >= window_start]
        if len(self._request_timestamps) >= rpm:
            # Sleep until the oldest request rolls out of the window
            oldest = self._request_timestamps[0]
            sleep_for = max(0.0, oldest + config.RPM_WINDOW_SEC - now)
            if sleep_for > 0:
                logger.info(f"Throttling to respect RPM limit; sleeping {sleep_for:.2f}s")
                await asyncio.sleep(sleep_for)

    def _record_request(self) -> None:
        self._request_timestamps.append(time.time())

    async def _throttle_tokens_if_needed(self, requested_tokens: int) -> None:
        """Throttle to stay under a soft TPM ceiling if configured."""
        tpm = config.OPENAI_TPM_LIMIT
        if not tpm or tpm <= 0:
            return
        now = time.time()
        window = config.TPM_WINDOW_SEC
        window_start = now - window
        # Drop entries outside window
        self._token_timestamps = [(t, tok) for (t, tok) in self._token_timestamps if t >= window_start]
        used = sum(tok for (_t, tok) in self._token_timestamps)
        if used + requested_tokens > tpm:
            # Need to sleep until enough tokens roll out
            # Compute when enough tokens will expire
            cumulative = used
            # Sort by oldest first
            sorted_entries = sorted(self._token_timestamps, key=lambda x: x[0])
            sleep_for = 0.0
            for ts, tok in sorted_entries:
                cumulative -= tok
                # Time when this entry exits the window
                exit_time = ts + window
                if cumulative + requested_tokens <= tpm:
                    sleep_for = max(0.0, exit_time - now)
                    break
            if sleep_for > 0:
                logger.info(f"Throttling to respect TPM limit; sleeping {sleep_for:.2f}s")
                await asyncio.sleep(sleep_for)

    def _record_tokens(self, tokens_used: int) -> None:
        self._token_timestamps.append((time.time(), int(tokens_used)))

    def _estimate_message_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Very rough token estimate: ~4 chars per token including role markers."""
        if not messages:
            return 0
        total_chars = 0
        for msg in messages:
            content = msg.get("content") or ""
            total_chars += len(content)
            # Add small overhead for role and structure
            total_chars += 20
        # 1 token per 4 chars heuristic
        return max(1, total_chars // 4)
