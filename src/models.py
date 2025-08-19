from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    use_functions: bool = True
    temperature: float = 0.7
    translate_queries: bool = True

class KnowledgeRequest(BaseModel):
    texts: list[str]