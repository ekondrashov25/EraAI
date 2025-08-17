import aiohttp
from typing import Dict, Any, Optional


class BaseAPIClient:
    """Base class for API clients with common functionality."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the API."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.setdefault("headers", {})
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        response = await self.session.request(method, url, **kwargs)
        return await response.json()
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return await self.request("POST", endpoint, **kwargs)
