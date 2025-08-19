import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    # Response token cap to avoid large generations
    RESPONSE_MAX_TOKENS: int = int(os.getenv("RESPONSE_MAX_TOKENS", "600"))

    # Soft prompt size limiter (approx chars; ~4 chars per token)
    MAX_PROMPT_CHARS: int = int(os.getenv("MAX_PROMPT_CHARS", "28000"))

    # RAG context size cap in characters
    RAG_CONTEXT_MAX_CHARS: int = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "6000"))

    # Conversation history cap (number of messages, excluding injected system)
    MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "16"))

    # Retry policy for rate limits
    OPENAI_RETRY_MAX_ATTEMPTS: int = int(os.getenv("OPENAI_RETRY_MAX_ATTEMPTS", "3"))
    OPENAI_RETRY_BASE_DELAY_SEC: float = float(os.getenv("OPENAI_RETRY_BASE_DELAY_SEC", "2.0"))

    # Requests-per-minute throttling (soft client-side limiter)
    OPENAI_RPM_LIMIT: int = int(os.getenv("OPENAI_RPM_LIMIT", "0"))  # 0 disables
    RPM_WINDOW_SEC: int = int(os.getenv("RPM_WINDOW_SEC", "60"))
    
    # Tokens-per-minute throttling (soft client-side limiter)
    OPENAI_TPM_LIMIT: int = int(os.getenv("OPENAI_TPM_LIMIT", "0"))  # 0 disables
    TPM_WINDOW_SEC: int = int(os.getenv("TPM_WINDOW_SEC", "60"))
    
    # MCP Server Configuration
    MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "localhost")
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "8000"))
    
    # External API Configuration
    LUNARCRUSH_API_BASE_URL: str = os.getenv("LUNARCRUSH_API_BASE_URL", "")
    LUNARCRUSH_API_KEY: str = os.getenv("LUNARCRUSH_API_KEY", "")
    
    # Vector Database Configuration
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # System Prompt Configuration
    SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", "")

    # Translation Prompt (for correct work of RAG) Configuration
    TRANSLATION_PROMPT: str = os.getenv("TRANSLATION_PROMPT", "")

    
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        return True

# Global config instance
config = Config()
