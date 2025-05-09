# Adjust import path for config
import config 
from coinmarketcapapi import CoinMarketCapAPI, CoinMarketCapAPIError
import logging # logging eklendi
import traceback # exception loglama için

# Logger oluştur
logger = logging.getLogger(__name__)

class CoinMarketCapClient:
    def __init__(self):
        if not config.COINMARKETCAP_API_KEY:
            logger.error("CoinMarketCapClient başlatılamadı: API anahtarı eksik.")
            raise ValueError("CoinMarketCap API anahtarı config.py üzerinden ayarlanmalı (.env dosyasını kontrol edin).")
        try:
            self.cmc = CoinMarketCapAPI(config.COINMARKETCAP_API_KEY)
            # Test the connection / API key validity by fetching key info
            key_info_response = self.cmc.key_info()
            
            credits_left_message = "Kredi bilgisi alınamadı."
            if key_info_response and key_info_response.data:
                usage_data = key_info_response.data.get('usage')
                if usage_data:
                    current_day_usage = usage_data.get('current_day')
                    if current_day_usage:
                        credits_left = current_day_usage.get('credits_left')
                        if credits_left is not None:
                            credits_left_message = f"Kalan günlük kredi: {credits_left}"
            
            logger.info(f"CoinMarketCap istemcisi başarıyla başlatıldı. {credits_left_message}")

        except CoinMarketCapAPIError as e:
            error_message = "Bilinmeyen CMC API Hatası"
            if e.rep and hasattr(e.rep, 'status') and isinstance(e.rep.status, dict) and 'error_message' in e.rep.status:
                error_message = e.rep.status['error_message']
            else:
                error_message = str(e)
            logger.error(f"CoinMarketCap API Hatası (Başlatma): {error_message}")
            logger.debug(f"CoinMarketCap API Error details (init): {e.rep}")
            self.cmc = None # Indicate client is not usable
        except Exception as e:
            logger.error(f"CoinMarketCap istemcisi başlatılırken beklenmedik hata: {e}")
            logger.exception("CoinMarketCap istemcisi başlatılırken bir istisna oluştu:")
            self.cmc = None

    def get_listings_by_market_cap(self, limit=50, convert_to='USD', sort_by='market_cap'):
        """ 
        CoinMarketCap'ten piyasa değerine göre sıralanmış coin listesini alır.
        Returns: List of dicts, e.g., [
            {'symbol': 'BTC', 'market_cap': 1.2e12, 'price': 60000.0, 'percent_change_24h': 1.5},
            ...
        ]
        veya hata durumunda None.
        """
        if not self.cmc:
            logger.warning("CoinMarketCap istemcisi düzgün başlatılamadığı için veri alınamıyor.")
            return None
        
        try:
            logger.info(f"CoinMarketCap API'den piyasa değerine göre ilk {limit} coin isteniyor ({convert_to} cinsinden)...")
            listings = self.cmc.cryptocurrency_listings_latest(
                limit=limit, 
                convert=convert_to, 
                sort=sort_by,
                sort_dir='desc' # En yüksek market cap en başta
            )
            
            processed_listings = []
            if listings and listings.data:
                for coin in listings.data:
                    symbol = coin.get('symbol')
                    quote_data = coin.get('quote', {}).get(convert_to, {})
                    
                    market_cap = quote_data.get('market_cap')
                    price = quote_data.get('price')
                    percent_change_24h = quote_data.get('percent_change_24h')

                    if symbol and market_cap is not None and price is not None:
                        processed_listings.append({
                            'symbol': symbol,
                            'market_cap': market_cap,
                            'price': price,
                            'percent_change_24h': percent_change_24h # Bu None olabilir, listelemede kontrol edilecek
                        })
                logger.info(f"CoinMarketCap'ten {len(processed_listings)} adet coin başarıyla işlendi.")
                return processed_listings
            else:
                logger.warning("CoinMarketCap'ten veri alınamadı veya veri formatı beklenildiği gibi değil.")
                logger.debug(f"CMC listings_latest raw response: {listings}")
                return None

        except CoinMarketCapAPIError as e:
            error_msg = "Bilinmeyen CMC API Hatası"
            if e.rep and hasattr(e.rep, 'status') and isinstance(e.rep.status, dict) and 'error_message' in e.rep.status:
                 error_msg = e.rep.status['error_message']
            else:
                error_msg = str(e) # Fallback to string representation of the error
            logger.error(f"CoinMarketCap API Hatası (get_listings_by_market_cap): {error_msg}")
            logger.debug(f"CoinMarketCap API Error details (get_listings): {e.rep}")
            return None
        except Exception as e:
            logger.error(f"CoinMarketCap listelerini alırken beklenmedik hata: {e}")
            logger.exception("CoinMarketCap listeleri alınırken bir istisna oluştu:")
            return None

# Test amaçlı - Bu kısım modül yapısı değişince çalışmayabilir.
# if __name__ == '__main__':
#     try:
#         cmc_client = CoinMarketCapClient()
#         # ... (test kodları)
#     except Exception as e:
#         logger.error(f"Test sırasında hata: {e}") 