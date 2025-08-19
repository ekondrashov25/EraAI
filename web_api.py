import logging
import asyncio
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
import aiohttp
import xml.etree.ElementTree as ET
from fastapi.middleware.cors import CORSMiddleware

from src.ai_assistant import AIAssistant
from src.models import ChatRequest, KnowledgeRequest
from src.api_clients.lunarcrush import LunarCrushClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

assistant = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global assistant
    try:
        assistant = AIAssistant()
        logger.info("AI Assistant initialized")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize AI Assistant: {e}")

app = FastAPI(title="EraAI API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# uncomment for production
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://88.218.68.76"],
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE"],
#     allow_headers=["Authorization", "Content-Type"],
# )

@app.get("/")
async def root():
    return {
        "message": "EraAI API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "assistant_initialized": assistant is not None
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
    try:
        result = await assistant.chat(
            user_message=request.message,
            use_rag=request.use_rag,
            use_functions=request.use_functions,
            temperature=request.temperature,
            translate_queries=request.translate_queries
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result["response"]
                    }
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quick_actions")
async def get_quick_actions():
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    try:
        # 1) Gather real-time context (non-fatal best-effort)
        market_lines = []
        try:
            # Reuse assistant's FunctionCaller/LunarCrush if configured is complex; use direct client here
            from src.config import config as app_config
            if app_config.LUNARCRUSH_API_BASE_URL and app_config.LUNARCRUSH_API_KEY:
                async with LunarCrushClient() as lc:
                    coins_resp = await lc.get_coin_metrics()
                coins = coins_resp.get("data", []) if isinstance(coins_resp, dict) else []
                def rank_key(c):
                    r = c.get("market_cap_rank")
                    return r if isinstance(r, (int, float)) else float("inf")
                top = sorted(coins, key=rank_key)[:6]
                for c in top:
                    sym = c.get("symbol") or "?"
                    ch24 = c.get("percent_change_24h")
                    ch7 = c.get("percent_change_7d")
                    price = c.get("price")
                    market_lines.append(f"{sym}: price={price}, 24h={ch24}%, 7d={ch7}%")
        except Exception:
            pass

        async def fetch_rss_titles(session: aiohttp.ClientSession, url: str, limit: int = 5):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    text = await resp.text()
                    root = ET.fromstring(text)
                    # Try RSS 2.0 structure
                    items = root.findall('.//item')
                    titles = [it.findtext('title') for it in items if it.findtext('title')]
                    if not titles:
                        # Try Atom
                        entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                        titles = [e.findtext('{http://www.w3.org/2005/Atom}title') for e in entries if e.findtext('{http://www.w3.org/2005/Atom}title')]
                    return [t.strip() for t in titles[:limit]]
            except Exception:
                return []

        news_titles: list[str] = []  # type: ignore
        rss_urls = [
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cointelegraph.com/rss"
        ]
        try:
            async with aiohttp.ClientSession() as session:
                results = await asyncio.gather(*[fetch_rss_titles(session, u, 3) for u in rss_urls], return_exceptions=True)
                for r in results:
                    if isinstance(r, list):
                        news_titles.extend(r)
        except Exception:
            pass

        # 2) Prompt the LLM with enriched context to produce 4 starters
        context_sections = []
        if market_lines:
            context_sections.append("Рынок:\n" + "\n".join(market_lines))
        if news_titles:
            context_sections.append("Заголовки новостей:\n" + "\n".join(news_titles[:8]))
        context_blob = "\n\n".join(context_sections)

        prompt = f"""
        Сгенерируй 4 короткие подсказки (quick actions) для стартового экрана крипто-ассистента на русском языке, основываясь на текущих событиях и рынке.
        Требования:
        - Одна подсказка — про обзор рынка/бирж сегодня
        - Одна — про макро/политику/регуляторов и влияние на рынок
        - Две — про конкретные активы/темы (учи тыкеры из данных, если есть)
        - Не длиннее 40 символов каждая
        - Только список из 4 строк, без нумерации и пояснений
        - Не используй смайлики!
        
        Данные (если пусто — игнорируй):
        {context_blob}
        """

        result = await assistant.chat(
            user_message=prompt,
            use_rag=False,
            use_functions=False,
            temperature=0.5,
            translate_queries=False
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        response_text = result.get("response") or ""
        lines = [l.strip("-• \t").strip() for l in response_text.strip().split("\n") if l.strip()]
        questions = []
        for line in lines:
            if len(line) > 2 and line[0].isdigit() and line[1] in ".)":
                line = line[2:].strip()
            if line and line not in questions:
                questions.append(line)
        default_questions = [
            "Анализ BTC",
            "Обзор рынка",
            "Торговые идеи",
            "Что такое DeFi"
        ]
        while len(questions) < 4:
            questions.append(default_questions[len(questions)])
        questions = questions[:4]

        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "quick_actions",
                        "questions": questions
                    }
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/add_knowledge")
# async def add_knowledge(request: KnowledgeRequest):
#     if assistant is None:
#         raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
#     try:
#         result = await assistant.add_knowledge(texts=request.texts)
        
#         if result["status"] == "error":
#             raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
#         return {
#             "result": {
#                 "content": [
#                     {
#                         "type": "text",
#                         "text": f"Status: {result['status']}\n{result.get('message', '')}"
#                     }
#                 ]
#             }
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/search")
# async def search_knowledge(query: str, k: int = 5):
#     if assistant is None:
#         raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
#     try:
#         result = await assistant.search_knowledge(query=query, k=k)
        
#         if result["status"] == "error":
#             raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
#         content_text = f"Found {result['count']} results for '{result['query']}':\n\n"
#         for i, doc in enumerate(result['results'], 1):
#             content_text += f"{i}. {doc['content'][:200]}...\n\n"
        
#         return {
#             "result": {
#                 "content": [
#                     {
#                         "type": "text",
#                         "text": content_text
#                     }
#                 ]
#             }
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/system_info")
async def get_system_info():
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
    try:
        info = await assistant.get_system_info()
        
        if "error" in info:
            raise HTTPException(status_code=500, detail=info["error"])
        
        content_text = f"""
        System Information:
        Model: {info['model']}
        RAG System: {info['rag_system']['total_documents']} documents in collection '{info['rag_system']['collection_name']}'
        Functions: {info['functions']['available']} available, {len(info['functions']['registered'])} registered
        Conversation: {info['conversation']['history_length']} messages in history
        """
        
        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": content_text
                    }
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation_history")
async def get_conversation_history():
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
    try:
        history = assistant.get_conversation_history()
        
        # get_conversation_history returns a list directly, not a dict with status
        
        content_text = "Conversation History:\n\n"
        for i, message in enumerate(history, 1):
            role = message['role']
            content = message['content'][:200] + "..." if len(message['content']) > 200 else message['content']
            content_text += f"{i}. {role}: {content}\n\n"
        
        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": content_text
                    }
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_history")
async def clear_conversation_history():
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
    try:
        result = assistant.clear_conversation_history()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result["message"]
                    }
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/related_questions")
async def get_related_questions():
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
    try:
        # Get conversation history to analyze context
        history = assistant.get_conversation_history()
        
        if len(history) < 2:  # Need at least one user message and one assistant response
            # Return default questions if no conversation yet
            default_questions = [
                "Анализ BTC",
                "Обзор рынка",
                "Торговые идеи",
                "Что такое DeFi"
            ]
            return {
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "default_questions",
                            "questions": default_questions
                        }
                    ]
                }
            }
        
        # Generate related questions based on conversation context
        # Use the last few messages to understand the context
        recent_messages = history[-4:]  # Last 4 messages (2 exchanges)
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        
        # Create a prompt to generate related questions
        prompt = f"""
        Based on this conversation context, generate 4 short related questions that the user might want to ask next.
        Focus on crypto, trading, and economic topics. Keep each question under 40 characters for mobile display.
        Make questions specific and actionable but concise. Do not give the same question twice. Do not give anything except questions.
        
        Context:
        {context}
        
        Generate exactly 4 SHORT questions, one per line, in Russian:
        """
        
        # Use the assistant to generate related questions
        result = await assistant.chat(
            user_message=prompt,
            use_rag=False,  # Don't use RAG for this
            use_functions=False,  # Don't use functions for this
            temperature=0.7,
            translate_queries=False
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        # Parse the response to extract questions
        response_text = result["response"]
        questions = []
        
        # Split by lines and clean up
        lines = response_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            # Remove numbering if present (1., 2., etc.)
            if line and any(char.isdigit() for char in line[:3]):
                line = line.split('.', 1)[-1].strip()
            if line and line not in questions:
                questions.append(line)
        
        # Ensure we have exactly 4 questions, pad with defaults if needed
        default_questions = [
            "Анализ BTC",
            "Обзор рынка", 
            "Торговые идеи",
            "Что такое DeFi"
        ]
        
        while len(questions) < 4:
            questions.append(default_questions[len(questions)])
        
        questions = questions[:4]  # Limit to 4 questions
        
        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "related_questions",
                        "questions": questions
                    }
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logging.info("Starting EraAI API...")
    logging.info("API Documentation: http://localhost:8000/docs")
    logging.info("Health Check: http://localhost:8000/health")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
