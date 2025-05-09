import aiohttp
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class MarketSentimentClient:
    def __init__(self):
        self.fear_greed_url = "https://api.alternative.me/fng/"
        self.market_trend_url = "https://api.coingecko.com/api/v3/global"
        
    async def get_fear_greed_index(self) -> Optional[Dict]:
        """Fetches the current Fear & Greed Index."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.fear_greed_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'data' in data and len(data['data']) > 0:
                            latest = data['data'][0]
                            return {
                                'value': int(latest['value']),
                                'value_classification': latest['value_classification'],
                                'timestamp': latest['timestamp'],
                                'time_until_update': latest['time_until_update']
                            }
                    logger.warning(f"Fear & Greed Index alınamadı. Status: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Fear & Greed Index alınırken hata: {e}")
            return None

    async def get_market_trend(self) -> Optional[Dict]:
        """Fetches the current market trend data from CoinGecko."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.market_trend_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'data' in data:
                            market_data = data['data']
                            return {
                                'total_market_cap': market_data['total_market_cap']['usd'],
                                'total_volume': market_data['total_volume']['usd'],
                                'market_cap_change_percentage_24h': market_data['market_cap_change_percentage_24h_usd'],
                                'market_cap_dominance': {
                                    'btc': market_data['market_cap_percentage']['btc'],
                                    'eth': market_data['market_cap_percentage']['eth']
                                },
                                'active_cryptocurrencies': market_data['active_cryptocurrencies'],
                                'upcoming_icos': market_data['upcoming_icos'],
                                'ongoing_icos': market_data['ongoing_icos'],
                                'ended_icos': market_data['ended_icos']
                            }
                    logger.warning(f"Market trend verisi alınamadı. Status: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Market trend verisi alınırken hata: {e}")
            return None

    def format_market_sentiment_for_llm(self, fear_greed_data: Optional[Dict], market_trend_data: Optional[Dict]) -> str:
        """Formats market sentiment data for LLM context."""
        sentiment_str = "## Piyasa Duyarlılık Verileri\n\n"
        
        # Fear & Greed Index
        if fear_greed_data:
            sentiment_str += "### Korku & Açgözlülük Endeksi\n"
            sentiment_str += f"- Değer: {fear_greed_data['value']} ({fear_greed_data['value_classification']})\n"
            sentiment_str += f"- Son Güncelleme: {fear_greed_data['timestamp']}\n\n"
        else:
            sentiment_str += "### Korku & Açgözlülük Endeksi\n"
            sentiment_str += "- Veri alınamadı\n\n"
        
        # Market Trend
        if market_trend_data:
            sentiment_str += "### Piyasa Trendi\n"
            sentiment_str += f"- Toplam Piyasa Değeri: ${market_trend_data['total_market_cap']:,.2f}\n"
            sentiment_str += f"- 24s Değişim: %{market_trend_data['market_cap_change_percentage_24h']:.2f}\n"
            sentiment_str += f"- Toplam Hacim: ${market_trend_data['total_volume']:,.2f}\n"
            sentiment_str += f"- BTC Dominansı: %{market_trend_data['market_cap_dominance']['btc']:.2f}\n"
            sentiment_str += f"- ETH Dominansı: %{market_trend_data['market_cap_dominance']['eth']:.2f}\n"
            sentiment_str += f"- Aktif Kripto Para Sayısı: {market_trend_data['active_cryptocurrencies']}\n"
        else:
            sentiment_str += "### Piyasa Trendi\n"
            sentiment_str += "- Veri alınamadı\n"
        
        return sentiment_str 