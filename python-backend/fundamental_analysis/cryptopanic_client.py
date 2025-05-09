import httpx
import logging
from typing import List, Dict, Optional

from .base_client import BaseFundamentalClient

logger = logging.getLogger(__name__)

class CryptoPanicClient(BaseFundamentalClient):
    """
    Client for fetching news data from the CryptoPanic API.
    API Documentation: https://cryptopanic.com/developers/api/
    """
    BASE_URL = "https://cryptopanic.com/api/v1/posts/"

    def __init__(self, api_key: str):
        super().__init__(api_key)
        if not api_key:
            raise ValueError("CryptoPanic API key is required.")

    async def get_data(self, symbol: str, limit: int = 5, **kwargs) -> Optional[str]:
        """
        Fetches news for a given cryptocurrency symbol from CryptoPanic.

        Args:
            symbol (str): The cryptocurrency symbol (e.g., BTC, ETH). 
                          Note: CryptoPanic uses currency codes, not pairs like BTCUSDT.
            limit (int): Maximum number of news items to return.
            **kwargs: Other optional parameters for the API like 'filter', 'kind', 'region', 'public'.

        Returns:
            Optional[str]: A formatted string containing the news, or None if an error occurs.
        """
        # CryptoPanic uses currency codes (e.g., BTC), not pairs (e.g., BTCUSDT).
        # We need to strip "USDT" or other pair suffixes if present.
        currency_code = symbol.replace("USDT", "").replace("BUSD", "").upper()
        if not currency_code:
            logger.warning(f"Could not derive a valid currency code from symbol: {symbol}")
            return "İlgili sembol için haber bulunamadı (geçersiz kod)."

        params = {
            "auth_token": self.api_key,
            "currencies": currency_code,
            "public": "true", # Ensure we only get publicly available posts
        }
        params.update(kwargs) # Allow overriding defaults or adding more params

        logger.info(f"Fetching news for {currency_code} from CryptoPanic with params: { {k:v for k,v in params.items() if k != 'auth_token'} }")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status() # Raises an exception for 4XX/5XX errors
                data = response.json()

            if not data.get("results"):
                logger.info(f"No news found for {currency_code} on CryptoPanic.")
                return f"{currency_code} için CryptoPanic üzerinde güncel haber bulunamadı."

            news_items = data["results"][:limit]
            formatted_news = f"\n--- {currency_code} İçin Son Haberler (CryptoPanic) ---\n"
            for i, item in enumerate(news_items):
                title = item.get("title", "N/A")
                published_at = item.get("published_at", "N/A")
                source_title = item.get("source", {}).get("title", "N/A")
                url = item.get("url", "#")
                
                # Sentiment (if available and 'votes' has the data)
                votes = item.get("votes", {})
                positive_votes = votes.get("positive", 0)
                negative_votes = votes.get("negative", 0)
                sentiment_str = f" (Sentiment: +{positive_votes}/-{negative_votes})" if positive_votes or negative_votes else ""

                formatted_news += f"{i+1}. {title} ({source_title} - {published_at}){sentiment_str}\n   Link: {url}\n"
            
            logger.debug(f"Formatted news for {currency_code}:\n{formatted_news}")
            return formatted_news.strip()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching news for {currency_code} from CryptoPanic: {e}")
            logger.error(f"Response content: {e.response.text}")
            return f"{currency_code} için CryptoPanic haberleri alınırken HTTP hatası oluştu: {e.response.status_code}"
        except httpx.RequestError as e:
            logger.error(f"Request error fetching news for {currency_code} from CryptoPanic: {e}")
            return f"{currency_code} için CryptoPanic haberleri alınırken bağlantı hatası oluştu."
        except Exception as e:
            logger.error(f"Error processing news for {currency_code} from CryptoPanic: {e}")
            logger.exception(f"CryptoPanic istemcisinde {currency_code} için beklenmedik bir hata oluştu:")
            return f"{currency_code} için CryptoPanic haberleri işlenirken bir hata oluştu." 