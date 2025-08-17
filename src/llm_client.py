import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.callbacks.manager import get_openai_callback

from src.config import config

logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with OpenAI LLM APIs."""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.chat_model = ChatOpenAI(
            model=config.OPENAI_MODEL,
            temperature=0.7,
            api_key=config.OPENAI_API_KEY
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1000,
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
        try:
            params = {
                "model": config.OPENAI_MODEL,
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            if functions:
                params["functions"] = functions
                
            response = self.client.chat.completions.create(**params)
            
            logger.info(f"Chat completion successful: {len(response.choices)} choices")
            
            return {
                "content": response.choices[0].message.content,
                "function_call": response.choices[0].message.function_call,
                "usage": response.usage.dict() if response.usage else None,
                "model": response.model,
                "id": response.id
            }
            
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise
    
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
            stream = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            raise
