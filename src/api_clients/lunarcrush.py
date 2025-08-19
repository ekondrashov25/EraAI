import asyncio
from typing import Dict, Any

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from api_clients.base_client import BaseAPIClient

class LunarCrushClient(BaseAPIClient):
    def __init__(self):
        super().__init__(config.LUNARCRUSH_API_BASE_URL, config.LUNARCRUSH_API_KEY)

    async def get_coin_metrics(self) -> Dict[str, Any]:
        """Get formatted coin metrics data."""
        # Rate limiting
        await asyncio.sleep(1)
        response = await self.request("GET", "/public/coins/list/v1")
        
        formatted_data = []
        for coin in response.get("data", []):
            formatted_coin = {
                "symbol": coin.get("symbol"),
                "name": coin.get("name"), 
                "price": coin.get("price"),
                "percent_change_1h": coin.get("percent_change_1h"),
                "percent_change_24h": coin.get("percent_change_24h"),
                "percent_change_7d": coin.get("percent_change_7d"),
                "volume_24h": coin.get("volume_24h"),
                "market_cap": coin.get("market_cap"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "sentiment": coin.get("sentiment"),
                "social_volume_24h": coin.get("social_volume_24h"),
                "social_dominance": coin.get("social_dominance"),
                "logo": coin.get("logo")
            }
            formatted_data.append(formatted_coin)
            
        return {
            "data": formatted_data,
            "count": len(formatted_data)
        }

    async def get_coin_metrics_by_id(self, coin_id: str) -> Dict[str, Any]:
        """Get coin metrics by ID."""
        # Rate limiting
        await asyncio.sleep(1)
        response = await self.request("GET", f"/public/coins/{coin_id}/v1")

        data = response["data"]
        config = response.get("config", {})

        coin_info = {
            # Basic Info
            "id": data.get("id"),
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "topic": config.get("topic"),
            "last_updated": config.get("generated"),
            
            # Price Information
            "price_usd": f"${data.get('price', 0):.2f}" if data.get('price') else "N/A",
            "price_btc": f"{data.get('price_btc', 0):.8f}" if data.get('price_btc') else "N/A",
            "close_price": f"${data.get('close', 0):.2f}" if data.get('close') else "N/A",
            
            # Market Data
            "market_cap": self.format_large_number(data.get("market_cap")),
            "market_cap_rank": data.get("market_cap_rank"),
            "volume_24h": self.format_large_number(data.get("volume_24h")),
            
            # Supply Information
            "circulating_supply": f"{data.get('circulating_supply', 0):,.0f}" if data.get('circulating_supply') else "N/A",
            "max_supply": f"{data.get('max_supply', 0):,.0f}" if data.get('max_supply') else "Unlimited",
            
            # Performance Metrics
            "change_24h": f"{data.get('percent_change_24h', 0):+.2f}%" if data.get('percent_change_24h') is not None else "N/A",
            "change_7d": f"{data.get('percent_change_7d', 0):+.2f}%" if data.get('percent_change_7d') is not None else "N/A",
            "change_30d": f"{data.get('percent_change_30d', 0):+.2f}%" if data.get('percent_change_30d') is not None else "N/A",
            
            # Additional Metrics
            "galaxy_score": f"{data.get('galaxy_score', 0):.1f}" if data.get('galaxy_score') else "N/A",
            "alt_rank": data.get("alt_rank"),
            "volatility": f"{data.get('volatility', 0):.4f}" if data.get('volatility') else "N/A",
            
            # Raw values for calculations
            "raw_price": data.get("price"),
            "raw_market_cap": data.get("market_cap"),
            "raw_volume_24h": data.get("volume_24h"),
            "raw_change_24h": data.get("percent_change_24h"),
            "raw_change_7d": data.get("percent_change_7d"),
            "raw_change_30d": data.get("percent_change_30d"),
        }

        return coin_info
    

    async def get_coin_time_series(self, coin_id: str, interval: str = "1h") -> Dict[str, Any]:
        """Get coin time series data."""
        # Rate limiting
        await asyncio.sleep(1)
        response = await self.request("GET", f"/public/coins/{coin_id}/time-series/v2?interval={interval}")
        return response

    
    @staticmethod
    def format_large_number(value: float) -> str:
        if value is None:
            return "N/A"
        if value >= 1e12:
            return f"${value/1e12:.2f}T"
        elif value >= 1e9:
            return f"${value/1e9:.2f}B"
        elif value >= 1e6:
            return f"${value/1e6:.2f}M"
        elif value >= 1e3:
            return f"${value/1e3:.2f}K"
        else:
            return f"${value:.2f}"
