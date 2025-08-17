#!/usr/bin/env python3
"""
Simplified Web API that directly uses the AI Assistant without MCP.
This is for testing the frontend while we debug the MCP issues.
"""

import asyncio
import sys
import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
import uvicorn
import logging

from src.ai_assistant import AIAssistant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# todo: move to src/models.py
class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    use_functions: bool = True
    temperature: float = 0.7
    translate_queries: bool = True

class KnowledgeRequest(BaseModel):
    texts: list[str]

# Global AI Assistant instance
assistant = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the AI Assistant on startup."""
    global assistant
    try:
        assistant = AIAssistant()
        logger.info("✅ AI Assistant initialized")
        yield
    except Exception as e:
        logger.error(f"❌ Failed to initialize AI Assistant: {e}")

app = FastAPI(title="MCP Era-AI-Assistant API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MCP Era-AI-Assistant API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "assistant_initialized": assistant is not None
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint."""
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

@app.post("/add_knowledge")
async def add_knowledge(request: KnowledgeRequest):
    """Add knowledge to RAG system."""
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
    try:
        result = await assistant.add_knowledge(texts=request.texts)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Status: {result['status']}\n{result.get('message', '')}"
                    }
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_knowledge(query: str, k: int = 5):
    """Search knowledge base."""
    if assistant is None:
        raise HTTPException(status_code=500, detail="AI Assistant not initialized")
    
    try:
        result = await assistant.search_knowledge(query=query, k=k)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        content_text = f"Found {result['count']} results for '{result['query']}':\n\n"
        for i, doc in enumerate(result['results'], 1):
            content_text += f"{i}. {doc['content'][:200]}...\n\n"
        
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

@app.get("/system_info")
async def get_system_info():
    """Get system information."""
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
    """Get conversation history."""
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
    """Clear conversation history."""
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

if __name__ == "__main__":
    logging.info("🌐 Starting MCP AI Assistant Web API (Direct)...")
    logging.info("📖 API Documentation: http://localhost:8000/docs")
    logging.info("🔗 Health Check: http://localhost:8000/health")
    logging.info("⚠️  Note: This version bypasses MCP for direct testing")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
