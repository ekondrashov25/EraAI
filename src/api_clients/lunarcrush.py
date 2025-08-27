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
    

    async def get_coin_meta(self, coin_id: str) -> Dict[str, Any]:
        """Get formatted coin meta data."""
        # Rate limiting
        await asyncio.sleep(1)
        response = await self.request("GET", f"/public/coins/{coin_id}/meta/v1")
        
        data = response.get("data", {})
        config = response.get("config", {})
        
        # Extract blockchain networks with addresses
        blockchain_networks = []
        for network in data.get("blockchain", []):
            if network.get("address") and network.get("address") != "0":
                blockchain_networks.append({
                    "network": network.get("network"),
                    "address": network.get("address"),
                    "decimals": network.get("decimals"),
                    "type": network.get("type")
                })
        
        # Format the meta data
        meta_info = {
            # Basic Information
            "id": data.get("id"),
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "market_categories": data.get("market_categories"),
            "last_updated": config.get("generated"),
            
            # Description
            "short_summary": data.get("short_summary"),
            "description": data.get("description"),
            
            # Links
            "github_link": data.get("github_link"),
            "website_link": data.get("website_link"),
            "whitepaper_link": data.get("whitepaper_link"),
            "twitter_link": data.get("twitter_link"),
            "reddit_link": data.get("reddit_link"),
            "coingecko_link": data.get("coingecko_link"),
            "coinmarketcap_link": data.get("coinmarketcap_link"),
            
            # Blockchain Information
            "blockchain_networks": blockchain_networks,
            "total_networks": len(blockchain_networks),
            
            # Raw data for additional processing
            "raw_blockchain": data.get("blockchain", []),
            "raw_updated": data.get("updated")
        }
        
        return meta_info



    async def get_topic_creators(self, topic: str, limit: int = 3) -> Dict[str, Any]:
        """Get top creators/influencers for a specific topic/cryptocurrency."""
        # Rate limiting
        await asyncio.sleep(1)
        response = await self.request("GET", f"/public/topic/{topic}/creators/v1")
        
        creators_data = response.get("data", [])
        
        # Limit the number of creators to avoid large responses
        creators_data = creators_data[:limit]
        
        # Format the creators data
        formatted_creators = []
        for creator in creators_data:
            formatted_creator = {
                # Basic Information
                "creator_id": creator.get("creator_id"),
                "creator_name": creator.get("creator_name"),
                
                # Network Information
                "network": creator.get("creator_id", "").split("::")[0] if "::" in creator.get("creator_id", "") else "unknown",
                "unique_id": creator.get("creator_id", "").split("::")[1] if "::" in creator.get("creator_id", "") else creator.get("creator_id"),
                
                # Metrics
                "creator_followers": creator.get("creator_followers"),
                "creator_rank": creator.get("creator_rank"),
                "interactions_24h": creator.get("interactions_24h"),
                
                # Formatted metrics for display
                "followers_formatted": self.format_followers(creator.get("creator_followers")),
                "interactions_formatted": self.format_interactions(creator.get("interactions_24h")),
            }
            formatted_creators.append(formatted_creator)
        
        # Sort by rank to ensure proper ordering
        formatted_creators.sort(key=lambda x: x.get("creator_rank", 999))
        
        # Calculate totals from full dataset for accurate statistics
        def safe_int(value):
            """Safely convert value to int, handling strings with commas."""
            if value is None:
                return 0
            try:
                if isinstance(value, str):
                    return int(value.replace(',', ''))
                return int(value)
            except (ValueError, TypeError):
                return 0
        
        total_interactions = sum(safe_int(creator.get("interactions_24h", 0)) for creator in response.get("data", []))
        total_followers = sum(safe_int(creator.get("creator_followers", 0)) for creator in response.get("data", []))
        total_creators = len(response.get("data", []))
        
        return {
            "creators": formatted_creators,
            "count": len(formatted_creators),
            "total_available": total_creators,
            "top_creator": formatted_creators[0] if formatted_creators else None,
            "total_interactions": total_interactions,
            "avg_followers": total_followers // total_creators if total_creators > 0 else 0,
            "limit_applied": limit
        }

    async def get_cryptocurrency_news(self, limit: int = 3) -> Dict[str, Any]:
        """Get cryptocurrency news articles."""
        # Rate limiting
        await asyncio.sleep(1)
        response = await self.request("GET", "/public/category/cryptocurrencies/news/v1")
        
        config = response.get("config", {})
        news_data = response.get("data", [])
        
        # Limit the number of news articles to avoid large responses
        news_data = news_data[:limit]
        
        # Format the news data
        formatted_news = []
        for article in news_data:
            formatted_article = {
                # Basic Information
                "id": article.get("id"),
                "post_type": article.get("post_type"),
                "post_title": article.get("post_title"),
                "post_link": article.get("post_link"),
                "post_image": article.get("post_image"),
                
                # Timestamps
                "post_created": article.get("post_created"),
                "created_formatted": self.format_timestamp(article.get("post_created")),
                
                # Sentiment Analysis
                "post_sentiment": article.get("post_sentiment"),
                "sentiment_label": self.get_sentiment_label(article.get("post_sentiment")),
                
                # Creator Information
                "creator_id": article.get("creator_id"),
                "creator_name": article.get("creator_name"),
                "creator_display_name": article.get("creator_display_name"),
                "creator_followers": article.get("creator_followers"),
                "creator_avatar": article.get("creator_avatar"),
                "creator_network": article.get("creator_id", "").split("::")[0] if "::" in article.get("creator_id", "") else "unknown",
                
                # Engagement Metrics
                "interactions_24h": article.get("interactions_24h"),
                "interactions_total": article.get("interactions_total"),
                "interactions_24h_formatted": self.format_interactions(article.get("interactions_24h")),
                "interactions_total_formatted": self.format_interactions(article.get("interactions_total")),
            }
            formatted_news.append(formatted_article)
        
        # Calculate totals from full dataset for accurate statistics
        def safe_int(value):
            """Safely convert value to int, handling strings with commas."""
            if value is None:
                return 0
            try:
                if isinstance(value, str):
                    return int(value.replace(',', ''))
                return int(value)
            except (ValueError, TypeError):
                return 0
        
        total_articles = len(response.get("data", []))
        total_interactions = sum(safe_int(article.get("interactions_24h", 0)) for article in response.get("data", []))
        avg_sentiment = sum(article.get("post_sentiment", 3) for article in response.get("data", [])) / total_articles if total_articles > 0 else 3
        
        return {
            # Configuration
            "category": config.get("category"),
            "type": config.get("type"),
            "last_updated": config.get("generated"),
            
            # News Articles
            "articles": formatted_news,
            "count": len(formatted_news),
            "total_available": total_articles,
            "limit_applied": limit,
            
            # Aggregated Metrics
            "total_interactions": total_interactions,
            "total_interactions_formatted": self.format_interactions(total_interactions),
            "avg_sentiment": round(avg_sentiment, 2),
            "avg_sentiment_label": self.get_sentiment_label(avg_sentiment)
        }

    
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

    @staticmethod
    def format_followers(value) -> str:
        """Format follower count for display."""
        if value is None:
            return "N/A"
        try:
            # Convert to int if it's a string
            if isinstance(value, str):
                # Remove commas and convert to int
                value = int(value.replace(',', ''))
            else:
                value = int(value)
            
            if value >= 1e6:
                return f"{value/1e6:.1f}M"
            elif value >= 1e3:
                return f"{value/1e3:.1f}K"
            else:
                return f"{value:,}"
        except (ValueError, TypeError):
            return "N/A"

    @staticmethod
    def format_interactions(value) -> str:
        """Format interaction count for display."""
        if value is None:
            return "N/A"
        try:
            # Convert to int if it's a string
            if isinstance(value, str):
                # Remove commas and convert to int
                value = int(value.replace(',', ''))
            else:
                value = int(value)
            
            if value >= 1e6:
                return f"{value/1e6:.1f}M"
            elif value >= 1e3:
                return f"{value/1e3:.1f}K"
            else:
                return f"{value:,}"
        except (ValueError, TypeError):
            return "N/A"

    @staticmethod
    def format_timestamp(timestamp: int) -> str:
        """Format unix timestamp to readable date."""
        if timestamp is None:
            return "N/A"
        try:
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Invalid timestamp"

    @staticmethod
    def get_sentiment_label(sentiment: float) -> str:
        """Convert sentiment score to label."""
        if sentiment is None:
            return "Unknown"
        if sentiment >= 4.0:
            return "Very Positive"
        elif sentiment >= 3.5:
            return "Positive"
        elif sentiment >= 3.0:
            return "Neutral"
        elif sentiment >= 2.5:
            return "Negative"
        else:
            return "Very Negative"



