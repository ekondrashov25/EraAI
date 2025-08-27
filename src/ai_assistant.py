import io
import logging
import json
from typing import List, Dict, Any, Optional

from src.llm_client import LLMClient
from src.rag_system import RAGSystem
from src.function_caller import FunctionCaller
from src.config import config


logger = logging.getLogger(__name__)

class AIAssistant:
    def __init__(self):
        self.llm_client = LLMClient()
        self.rag_system = RAGSystem()
        self.function_caller = None  # Will be initialized in async context
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = config.SYSTEM_PROMPT
        self._summary: str = ""
    
    async def _ensure_function_caller(self):
        """Ensure function caller is initialized with async context."""
        if self.function_caller is None:
            self.function_caller = FunctionCaller()
            await self.function_caller.__aenter__()
    
    async def cleanup(self):
        """Clean up resources."""
        if self.function_caller:
            await self.function_caller.__aexit__(None, None, None)
            self.function_caller = None
    
    async def chat(self, user_message: str, use_rag: bool = True, use_functions: bool = True, temperature: float = 0.7, translate_queries: bool = True) -> Dict[str, Any]:
        try:
            # Ensure function caller is initialized
            if use_functions:
                await self._ensure_function_caller()
            
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            messages = self.conversation_history.copy()
            
            system_content = self._build_system_prompt()
            if not messages or messages[0]["role"] != "system":
                messages.insert(0, {
                    "role": "system",
                    "content": system_content
                })
            else:
                messages[0]["content"] = system_content
            
            context = ""
            if use_rag:
                search_query = user_message
                if translate_queries and self._is_russian_text(user_message):
                    translated_query = await self._translate_to_english(user_message)
                    if translated_query:
                        search_query = translated_query
                        logger.info(f"Translated query: '{user_message}' → '{translated_query}'")
                
                context = await self.rag_system.get_relevant_context(search_query)
                if context:
                    # Truncate context to avoid exceeding prompt limits
                    if len(context) > config.RAG_CONTEXT_MAX_CHARS:
                        context = context[:config.RAG_CONTEXT_MAX_CHARS]
                    enhanced_message = f"Context:\n{context}\n\nUser question: {user_message}"
                    messages[-1]["content"] = enhanced_message

            # Optional: inject concise summary as context carrier if we have one
            if self._summary:
                messages.insert(1, {"role": "system", "content": f"Running summary of prior conversation (for context preservation):\n{self._summary}"})

            # Trim conversation history to stay within limits (prefers newest + context)
            messages = self._trim_messages(messages)
            
            functions = None
            if use_functions:
                functions = self.function_caller.get_function_definitions()
            
            if functions:
                response = await self.llm_client.function_call(
                    messages=messages,
                    functions=functions,
                    temperature=temperature
                )
            else:
                response = await self.llm_client.chat_completion(
                    messages=messages,
                    temperature=temperature
                )
            
            function_results = []
            if response.get("function_call"):
                function_call = response["function_call"]
                if hasattr(function_call, 'name'):
                    function_call_dict = {
                        "name": function_call.name,
                        "arguments": function_call.arguments
                    }
                else:
                    function_call_dict = function_call
                
                function_result = await self.function_caller.execute_function_call(
                    function_call_dict
                )
                function_results.append(function_result)
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "function_call": function_call_dict
                })
                
                messages.append({
                    "role": "function",
                    "name": function_result["function_name"],
                    "content": json.dumps(function_result["result"])
                })
                
                # Re-trim messages after adding function result
                messages = self._trim_messages(messages)
                final_response = await self.llm_client.chat_completion(
                    messages=messages,
                    temperature=temperature
                )
                
                assistant_message = final_response["content"]
            else:
                assistant_message = response["content"]
            
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            # Update rolling summary to preserve long-term context
            self._update_summary(user_message, assistant_message)
            
            return {
                "response": assistant_message,
                "function_calls": function_results,
                "context_used": bool(context),
                "usage": response.get("usage"),
                "model": response.get("model")
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "error": str(e)
            }

    def _is_russian_text(self, text: str) -> bool:
        russian_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
        return any(char in russian_chars for char in text)

    def _trim_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Trim messages preferring the most recent turns; keep system and latest user/context fully when possible."""
        if not messages:
            return messages
        max_history = max(1, config.MAX_HISTORY_MESSAGES)
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
        history = messages[1:] if system_msg else messages[:]
        # First, cap by number of messages (keep most recent)
        recent_history = history[-max_history:]
        # Now enforce soft char budget preferring newest messages
        budget = config.MAX_PROMPT_CHARS
        kept_reversed: List[Dict[str, Any]] = []
        used = 0
        for msg in reversed(recent_history):
            content_text = msg.get("content") or ""
            content_len = len(content_text)
            if used + content_len <= budget:
                kept_reversed.append(msg)
                used += content_len
            else:
                # Always keep at least part of the newest message if nothing kept yet
                if not kept_reversed and content_len > 0:
                    part = max(0, budget)
                    new_msg = dict(msg)
                    new_msg["content"] = content_text[:part]
                    kept_reversed.append(new_msg)
                    used += len(new_msg["content"]) 
                # Otherwise stop; older messages are dropped first
                break
        kept_history = list(reversed(kept_reversed))
        # Prepend system message, truncated if needed
        if system_msg:
            remaining = max(0, budget - sum(len((m.get("content") or "")) for m in kept_history))
            sys_content = system_msg.get("content") or ""
            if len(sys_content) > remaining and remaining > 0:
                sys_copy = dict(system_msg)
                sys_copy["content"] = sys_content[:remaining]
                return [sys_copy] + kept_history
            elif remaining <= 0:
                # No room; still include a very short system prefix to keep role context
                sys_copy = dict(system_msg)
                sys_copy["content"] = sys_content[:128]
                return [sys_copy] + kept_history
            else:
                return [system_msg] + kept_history
        return kept_history

    async def _translate_to_english(self, text: str) -> str:
        try:
            translation_prompt = f"""
            Imagine that you are one of the best professional translators in the world of economics, finance, and cryptocurrencies, working with the world's top corporations and publications. Translate the following text from Russian to English, maintaining the original accuracy and professionalism of the information.

            Russian: {text}
            English:
            """
        
            response = await self.llm_client.chat_completion([{"role": "user", "content": translation_prompt}], temperature=0.1)
            
            if response and "content" in response:
                return response["content"].strip()
            else:
                return text
                
        except Exception as e:
            logger.warning(f"Translation failed: {str(e)}")
            return text
    
    async def add_knowledge(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:

        try:
            await self.rag_system.add_texts(texts, metadatas)
            return {
                "status": "success",
                "documents_added": len(texts),
                "message": f"Successfully added {len(texts)} documents to knowledge base"
            }
        except Exception as e:
            logger.error(f"Error adding knowledge: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Error: {str(e)}"
            }

    async def add_pdf_content(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:

        try:
            try:
                import PyPDF2
            except ImportError:
                logger.error("PyPDF2 not installed. Please install it with: pip install PyPDF2")
                return {
                    "status": "error",
                    "error": "PyPDF2 not installed",
                    "message": "Please install PyPDF2: pip install PyPDF2"
                }
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            pages_processed = len(pdf_reader.pages)
            
            texts = []
            metadatas = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():  # Only add non-empty pages
                        # Split large pages into smaller chunks
                        page_chunks = self._split_large_text(text, max_chunk_size=8000)
                        
                        for chunk_num, chunk in enumerate(page_chunks, 1):
                            texts.append(chunk)
                            metadatas.append({
                                "source": filename,
                                "page": page_num,
                                "chunk": chunk_num,
                                "total_chunks": len(page_chunks),
                                "type": "pdf"
                            })
                            
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                    continue
            
            if not texts:
                return {
                    "status": "error",
                    "error": "No text could be extracted from PDF",
                    "message": "The PDF appears to be empty or unreadable"
                }
            
            # Process texts in batches to avoid token limits
            batch_size = 50  # Process 50 chunks at a time
            total_chunks_added = 0
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                
                try:
                    await self.rag_system.add_texts(batch_texts, batch_metadatas)
                    total_chunks_added += len(batch_texts)
                    logger.info(f"Added batch {i//batch_size + 1}: {len(batch_texts)} chunks")
                except Exception as e:
                    logger.error(f"Error adding batch {i//batch_size + 1}: {str(e)}")
                    continue
            
            return {
                "status": "success",
                "pages_processed": pages_processed,
                "chunks_added": total_chunks_added,
                "message": f"Successfully processed {filename}: {pages_processed} pages, {total_chunks_added} text chunks added"
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Error processing PDF: {str(e)}"
            }

    def _split_large_text(self, text: str, max_chunk_size: int = 8000) -> List[str]:
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        sentences = text.split('. ')
        
        for sentence in sentences:
            # If adding this sentence would exceed the limit, save current chunk and start new one
            if len(current_chunk) + len(sentence) + 2 > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If we still have chunks that are too large, split them further
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > max_chunk_size:
                # Split by paragraphs
                paragraphs = chunk.split('\n\n')
                current_para_chunk = ""
                
                for paragraph in paragraphs:
                    if len(current_para_chunk) + len(paragraph) + 2 > max_chunk_size and current_para_chunk:
                        final_chunks.append(current_para_chunk.strip())
                        current_para_chunk = paragraph
                    else:
                        if current_para_chunk:
                            current_para_chunk += "\n\n" + paragraph
                        else:
                            current_para_chunk = paragraph
                
                if current_para_chunk.strip():
                    final_chunks.append(current_para_chunk.strip())
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    async def search_knowledge(self, query: str, k: int = 5) -> Dict[str, Any]:
        try:
            results = await self.rag_system.search_similar(query, k=k)
            
            return {
                "status": "success",
                "query": query,
                "results": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in results
                ],
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Error searching knowledge: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Error: {str(e)}"
            }
    
    async def register_custom_function(self, name: str, description: str, func: callable, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

        try:
            self.function_caller.register_function(name, func)
            
            return {
                "status": "success",
                "function_name": name,
                "message": f"Successfully registered function: {name}"
            }
        except Exception as e:
            logger.error(f"Error registering function: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Error: {str(e)}"
            }
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        return self.conversation_history.copy()
    
    def clear_conversation_history(self) -> Dict[str, str]:
        self.conversation_history = []
        return {"status": "success", "message": "Conversation history cleared"}

    def _build_system_prompt(self) -> str:
        base = self.system_prompt or ""
        
        # Add Russian language enforcement
        russian_instruction = """
        ВАЖНО: ВСЕГДА отвечай на РУССКОМ ЯЗЫКЕ. Никогда не отвечай на английском языке.
        Всегда используй русский язык для всех ответов, независимо от языка запроса пользователя.
        
        У ТЕБЯ ЕСТЬ ДОСТУП К ФУНКЦИЯМ ДЛЯ ПОЛУЧЕНИЯ АКТУАЛЬНЫХ ДАННЫХ О КРИПТОВАЛЮТАХ:
        - get_coin_metrics() - получить метрики всех криптовалют
        - get_coin_metrics_by_id(coin_id) - получить детальные данные конкретной криптовалюты
        - get_coin_meta(coin_id) - получить информацию о проекте и ссылки
        - get_topic_creators(topic) - получить топ-инфлюенсеров
        - get_cryptocurrency_news() - получить последние новости
        
        ВСЕГДА ИСПОЛЬЗУЙ ЭТИ ФУНКЦИИ для получения актуальных данных о криптовалютах.
        НЕ ГОВОРИ, что у тебя нет доступа к данным - у тебя есть функции для их получения!
        """
        
        # Suppress repetitive greetings on continued turns
        if len(self.conversation_history) >= 2:
            suppress = "Не приветствуй и не представляйся снова; продолжай разговор кратко."
            return f"{russian_instruction}\n{base}\n\n{suppress}" if base else f"{russian_instruction}\n{suppress}"
        
        return f"{russian_instruction}\n{base}" if base else russian_instruction

    def _update_summary(self, user: str, assistant: str) -> None:
        """Maintain a very concise rolling summary to carry context without large history."""
        # If we already have a summary, just append minimally; otherwise, start it
        # Keep summary short
        max_len = 1200
        addition = f"User: {user}\nAssistant: {assistant}\n"
        if not self._summary:
            self._summary = addition[:max_len]
        else:
            self._summary = (self._summary + addition)[-max_len:]
    
    async def get_system_info(self) -> Dict[str, Any]:
        try:
            rag_stats = await self.rag_system.get_collection_stats()
            
            return {
                "model": config.OPENAI_MODEL,
                "rag_system": {
                    "total_documents": rag_stats.get("total_documents", 0),
                    "collection_name": rag_stats.get("collection_name", "documents")
                },
                "functions": {
                    "available": len(self.function_caller.get_function_definitions()),
                    "registered": list(self.function_caller.registered_functions.keys())
                },
                "conversation": {
                    "history_length": len(self.conversation_history)
                }
            }
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {"error": str(e)}
    
    async def stream_chat(self, user_message: str, use_rag: bool = True, temperature: float = 0.7):

        try:
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            messages = self.conversation_history.copy()
            
            if not messages or messages[0]["role"] != "system":
                messages.insert(0, {
                    "role": "system",
                    "content": self.system_prompt
                })
            
            # Get relevant context if RAG is enabled
            if use_rag:
                context = await self.rag_system.get_relevant_context(user_message)
                if context:
                    enhanced_message = f"Context:\n{context}\n\nUser question: {user_message}"
                    messages[-1]["content"] = enhanced_message
            
            full_response = ""
            async for chunk in self.llm_client.stream_chat(messages, temperature):
                full_response += chunk
                yield chunk
            
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response
            })
            
        except Exception as e:
            logger.error(f"Error in stream chat: {str(e)}")
            yield f"Error: {str(e)}"
