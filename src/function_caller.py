import logging
import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Callable

from src.config import config
from src.api_clients.lunarcrush import LunarCrushClient

logger = logging.getLogger(__name__)

class FunctionCaller:
    """Handles function calling and external API interactions."""
    
    def __init__(self):
        self.session = None
        self.lunarcrush_client = None
        self.registered_functions: Dict[str, Callable] = {}
        self._setup_default_functions()
    
    def _setup_api_clients(self):
        """Initialize API clients with async context."""
        if not self.lunarcrush_client:
            self.lunarcrush_client = LunarCrushClient()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        self._setup_api_clients()
        # Initialize the LunarCrush client with async context
        if self.lunarcrush_client:
            await self.lunarcrush_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        # Close the LunarCrush client
        if self.lunarcrush_client:
            await self.lunarcrush_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _setup_default_functions(self):
        """Register default functions that can be called."""
        self.register_function("get_coin_metrics", self._get_coin_metrics)
        self.register_function("get_coin_metrics_by_id", self._get_coin_metrics_by_id)
        self.register_function("get_coin_meta", self._get_coin_meta)
        self.register_function("get_topic_creators", self._get_topic_creators)
        self.register_function("get_cryptocurrency_news", self._get_cryptocurrency_news)

    def register_function(self, name: str, func: Callable):
        """Register a new function that can be called."""
        self.registered_functions[name] = func
        logger.info(f"Registered function: {name}")
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get all registered function definitions in OpenAI format."""
        definitions = [
            {
                "name": "get_coin_metrics",
                "description": "Получить текущие метрики всех криптовалют, включая цены, рыночную капитализацию, объем торгов и социальные метрики",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_coin_metrics_by_id",
                "description": "Получить детальные метрики конкретной криптовалюты по ID, включая цену, рыночные данные, предложение и метрики производительности",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coin_id": {
                            "type": "string",
                            "description": "Уникальный ID криптовалюты (например, '1' для Bitcoin, '2' для Ethereum)"
                        }
                    },
                    "required": ["coin_id"]
                }
            },
            {
                "name": "get_coin_meta",
                "description": "Получить комплексную метаинформацию о криптовалюте, включая описание, ссылки, блокчейн-сети и ресурсы разработки",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coin_id": {
                            "type": "string",
                            "description": "Уникальный ID криптовалюты"
                        }
                    },
                    "required": ["coin_id"]
                }
            },

            {
                "name": "get_topic_creators",
                "description": "Получить топ-инфлюенсеров и создателей контента для конкретной криптовалюты с количеством подписчиков и метриками вовлеченности",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Тема криптовалюты (например, 'bitcoin', 'ethereum')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Количество создателей для возврата (по умолчанию: 3, максимум рекомендуется: 10)",
                            "default": 3
                        }
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "get_cryptocurrency_news",
                "description": "Получить последние новости о криптовалютах с анализом настроений, метриками вовлеченности и информацией о создателях",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Количество новостных статей для возврата (по умолчанию: 3, максимум рекомендуется: 10)",
                            "default": 3
                        }
                    }
                }
            }
        ]
        
        return definitions
    
    async def _get_coin_metrics(self) -> Dict[str, Any]:
        """Wrapper for get_coin_metrics function."""
        if not self.lunarcrush_client:
            raise RuntimeError("LunarCrush client not initialized. Use async context manager.")
        return await self.lunarcrush_client.get_coin_metrics()
    
    async def _get_coin_metrics_by_id(self, coin_id: str) -> Dict[str, Any]:
        """Wrapper for get_coin_metrics_by_id function."""
        if not self.lunarcrush_client:
            raise RuntimeError("LunarCrush client not initialized. Use async context manager.")
        return await self.lunarcrush_client.get_coin_metrics_by_id(coin_id)
    
    async def _get_coin_meta(self, coin_id: str) -> Dict[str, Any]:
        """Wrapper for get_coin_meta function."""
        if not self.lunarcrush_client:
            raise RuntimeError("LunarCrush client not initialized. Use async context manager.")
        return await self.lunarcrush_client.get_coin_meta(coin_id)
    
    async def _get_topic_creators(self, topic: str, limit: int = 3) -> Dict[str, Any]:
        """Wrapper for get_topic_creators function."""
        if not self.lunarcrush_client:
            raise RuntimeError("LunarCrush client not initialized. Use async context manager.")
        return await self.lunarcrush_client.get_topic_creators(topic, limit)
    
    async def _get_cryptocurrency_news(self, limit: int = 3) -> Dict[str, Any]:
        """Wrapper for get_cryptocurrency_news function."""
        if not self.lunarcrush_client:
            raise RuntimeError("LunarCrush client not initialized. Use async context manager.")
        return await self.lunarcrush_client.get_cryptocurrency_news(limit)
    
    async def execute_function_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function call based on LLM decision.
        
        Args:
            function_call: Function call object from OpenAI API
            
        Returns:
            Function execution result
        """
        try:
            # Handle both old and new function call formats
            if hasattr(function_call, 'name'):
                function_name = function_call.name
                arguments = function_call.arguments
            else:
                function_name = function_call.get("name")
                arguments = function_call.get("arguments", "{}")
            
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            
            logger.info(f"Executing function: {function_name} with args: {arguments}")
            
            if function_name in self.registered_functions:
                func = self.registered_functions[function_name]
                
                if hasattr(func, '__call__'):
                    # Handle async functions
                    if asyncio.iscoroutinefunction(func):
                        result = await func(**arguments)
                    else:
                        result = func(**arguments)
                    
                    return {
                        "function_name": function_name,
                        "result": result,
                        "status": "success"
                    }
                else:
                    raise ValueError(f"Function {function_name} is not callable")
            else:
                # Try external API call
                return await self._call_external_api(function_name, arguments)
                
        except Exception as e:
            logger.error(f"Error executing function {function_call.get('name')}: {str(e)}")
            return {
                "function_name": function_call.get("name"),
                "result": f"Error: {str(e)}",
                "status": "error"
            }
    
    async def _call_external_api(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call external API for function execution.
        
        Args:
            function_name: Name of the function to call
            arguments: Function arguments
            
        Returns:
            API response
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Construct API URL
            api_url = f"{config.EXTERNAL_API_BASE_URL}/{function_name}"
            
            headers = {
                "Authorization": f"Bearer {config.EXTERNAL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            async with self.session.post(
                api_url,
                json=arguments,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "function_name": function_name,
                        "result": result,
                        "status": "success"
                    }
                else:
                    error_text = await response.text()
                    return {
                        "function_name": function_name,
                        "result": f"API Error {response.status}: {error_text}",
                        "status": "error"
                    }
                    
        except Exception as e:
            logger.error(f"Error calling external API for {function_name}: {str(e)}")
            return {
                "function_name": function_name,
                "result": f"External API Error: {str(e)}",
                "status": "error"
            }
    
    # Default function implementations
    async def _get_weather(self, location: str, unit: str = "celsius") -> Dict[str, Any]:
        """Get weather information for a location."""
        # This is a mock implementation - replace with actual weather API
        return {
            "location": location,
            "temperature": 22,
            "unit": unit,
            "condition": "sunny",
            "humidity": 65
        }
    
    async def _search_web(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web for information."""
        # This is a mock implementation - replace with actual search API
        return {
            "query": query,
            "results": [
                {"title": f"Result 1 for {query}", "url": "https://example.com/1"},
                {"title": f"Result 2 for {query}", "url": "https://example.com/2"}
            ],
            "total_results": max_results
        }
    
    async def _calculate(self, expression: str) -> Dict[str, Any]:
        """Perform mathematical calculations."""
        try:
            # Safe evaluation of mathematical expressions
            allowed_names = {
                k: v for k, v in __builtins__.items()
                if k in ['abs', 'round', 'min', 'max', 'sum']
            }
            allowed_names.update({
                'abs': abs, 'round': round, 'min': min, 'max': max, 'sum': sum
            })
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            return {
                "expression": expression,
                "result": result,
                "type": type(result).__name__
            }
        except Exception as e:
            return {
                "expression": expression,
                "result": f"Calculation error: {str(e)}",
                "type": "error"
            }
    
    async def _get_current_time(self, timezone: str = "UTC") -> Dict[str, Any]:
        """Get current date and time."""
        from datetime import datetime
        import pytz
        
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            
            return {
                "timezone": timezone,
                "datetime": current_time.isoformat(),
                "date": current_time.strftime("%Y-%m-%d"),
                "time": current_time.strftime("%H:%M:%S")
            }
        except Exception as e:
            return {
                "timezone": timezone,
                "error": f"Invalid timezone: {str(e)}"
            }
