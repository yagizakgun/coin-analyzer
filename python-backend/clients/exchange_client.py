import asyncio
from binance.async_client import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
import config
from config import logger
from core_logic.constants import KLINE_HISTORY_PERIOD, KLINE_INTERVAL

class BinanceClient:
    def __init__(self):
        if not config.EXCHANGE_API_KEY or not config.EXCHANGE_API_SECRET:
            logger.error("BinanceClient başlatılamadı: Borsa API anahtarı veya gizli anahtar eksik.")
            raise ValueError("Binance API anahtarı ve gizli anahtar config.py üzerinden ayarlanmalı (.env dosyasını kontrol edin).")
        self.client = AsyncClient(config.EXCHANGE_API_KEY, config.EXCHANGE_API_SECRET)
        logger.info("Binance AsyncClient başarıyla başlatıldı (python-binance).")
        self.default_kline_interval = config.DEFAULT_KLINE_INTERVAL
        self.default_kline_limit = config.DEFAULT_KLINE_LIMIT
        self.default_kline_history_period = KLINE_HISTORY_PERIOD
        self._all_symbols_cache = None
        self._last_cache_time = 0

    async def get_server_time(self):
        try:
            server_time_data = await self.client.get_server_time()
            logger.info(f"Binance sunucu saati: {server_time_data}")
            return server_time_data
        except BinanceAPIException as e_api:
            logger.error(f"Binance API Exception (get_server_time): {e_api}")
            return None
        except BinanceRequestException as e_req:
            logger.error(f"Binance Request Exception (get_server_time): {e_req}")
            return None
        except Exception as e_main:
            logger.error(f"Binance sunucu saatini alırken genel hata: {e_main}")
            return None

    async def get_all_tickers(self):
        """Tüm semboller için 24 saatlik ticker verilerini alır."""
        try:
            tickers = await self.client.get_ticker()
            logger.info(f"Toplam {len(tickers)} adet 24hr ticker bilgisi (AsyncClient.get_ticker) alındı.")
            if tickers and len(tickers) > 0:
                logger.debug("DEBUG (AsyncClient.get_ticker): İlk 3 ticker:")
                for i, ticker_item in enumerate(tickers[:3]):
                    logger.debug(f"  {i+1}. {ticker_item}")
                
                # Update symbols cache while we have the data
                self._all_symbols_cache = [ticker['symbol'] for ticker in tickers]
                import time
                self._last_cache_time = time.time()
            return tickers
        except BinanceAPIException as e_api:
            logger.error(f"Binance API Exception (get_all_tickers): {e_api}")
            return None
        except BinanceRequestException as e_req:
            logger.error(f"Binance Request Exception (get_all_tickers): {e_req}")
            return None
        except Exception as e_main:
            logger.error(f"Tüm ticker bilgilerini alırken genel hata: {e_main}")
            return None

    async def get_klines(self, symbol, interval, limit=500):
        try:
            klines = await self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            logger.info(f"{symbol} için {limit} adet {interval} K-line verisi (AsyncClient.get_klines) alındı.")
            return klines
        except BinanceAPIException as e_api:
            logger.error(f"Binance API Exception for {symbol} ({interval}, {limit}): {e_api}")
            return None
        except BinanceRequestException as e_req:
            logger.error(f"Binance Request Exception for {symbol} ({interval}, {limit}): {e_req}")
            return None
        except Exception as e_main:
            logger.error(f"{symbol} için K-line verileri alınırken genel hata ({interval}, {limit}): {e_main}")
            return None

    async def validate_symbol(self, symbol):
        """
        Verilen sembolün Binance'de mevcut olup olmadığını doğrular.
        
        Args:
            symbol: Doğrulanacak sembol
            
        Returns:
            bool: Sembol geçerliyse True, değilse False
            str: Geçerli sembol varsa (alternatif form olabilir) sembol, yoksa None
        """
        try:
            # Önce direk kontrol et
            ticker = await self.client.get_ticker(symbol=symbol)
            if ticker:
                return True, symbol
            
            # Direk ticker alınamadıysa, alternatif formları dene
            # Örneğin BTC -> BTCUSDT, BTCBTC, BTCETH vb.
            base_symbol = symbol.replace("USDT", "").replace("BTC", "").replace("ETH", "").replace("BUSD", "")
            
            # Eğer baş sembolü çok kısaysa veya boşsa doğrulamaya gerek yok
            if len(base_symbol) < 2:
                return False, None
                
            # Cache'den tüm sembolleri al (performans için)
            all_symbols = self._all_symbols_cache
            
            # Cache boşsa veya 30 dakikadan eskiyse güncelle
            if not all_symbols:
                import time
                current_time = time.time()
                
                if not self._last_cache_time or (current_time - self._last_cache_time) > 1800:  # 30 dakika
                    exchange_info = await self.client.get_exchange_info()
                    if exchange_info and 'symbols' in exchange_info:
                        all_symbols = [symbol_info['symbol'] for symbol_info in exchange_info['symbols']]
                        self._all_symbols_cache = all_symbols
                        self._last_cache_time = current_time
            
            # Sembolleri kontrol et
            if all_symbols:
                # Alternatif para birimleri listesi
                quote_currencies = ["USDT", "BTC", "ETH", "BUSD", "USD", "USDC"]
                
                # Başka semboller veya alternatif formlar var mı kontrol et
                for quote in quote_currencies:
                    alt_symbol = f"{base_symbol}{quote}"
                    if alt_symbol in all_symbols:
                        return True, alt_symbol
            
            # Hiçbir alternatif form bulunamadı
            return False, None
            
        except Exception as e:
            logger.error(f"Sembol doğrulanırken hata oluştu ({symbol}): {e}")
            return False, None

    def get_spot_usdt_pairs(self, quote_asset="USDT"):
        logger.info("get_spot_usdt_pairs geçici olarak devre dışı.")
        return []

    async def close(self):
        """İstemci oturumunu kapatır."""
        try:
            if self.client:
                await self.client.close_connection()
                logger.info("Binance AsyncClient oturumu başarıyla kapatıldı.")
        except Exception as e:
            logger.error(f"Binance AsyncClient oturumu kapatılırken hata: {e}")

async def main_test():
    try:
        binance_client = BinanceClient()
    except ValueError as e:
        logger.error(f"Test istemcisi oluşturulurken hata: {e}")
        return

    try:
        server_time = await binance_client.get_server_time()
        if server_time:
            logger.info(f"Sunucu Zamanı (main test): {server_time}")

        tickers = await binance_client.get_all_tickers()
        if tickers:
            logger.info(f"Toplam {len(tickers)} ticker bulundu (main test).")
            for ticker_item in tickers[:3]:
                logger.info(ticker_item)

        symbol_to_test = "BTCUSDT"
        interval_to_test = KLINE_INTERVAL
        limit_to_test = 5
        klines = await binance_client.get_klines(symbol_to_test, interval_to_test, limit_to_test)
        if klines:
            logger.info(f"'{symbol_to_test}' için K-line verileri ({interval_to_test} interval, son {limit_to_test} adet) (main test):")
            for kline_data in klines:
                logger.info(kline_data)
                
        # Sembol doğrulama testleri
        valid_symbols = ["BTC", "BTCUSDT", "ETH", "ETHUSDT"]
        invalid_symbols = ["XYZ123", "ABCDEFUSDT"]
        
        for symbol in valid_symbols + invalid_symbols:
            is_valid, valid_form = await binance_client.validate_symbol(symbol)
            if is_valid:
                logger.info(f"✅ {symbol} -> {valid_form} (Geçerli sembol)")
            else:
                logger.info(f"❌ {symbol} (Geçersiz sembol)")
    finally:
        if binance_client:
            await binance_client.close()

if __name__ == "__main__":
    asyncio.run(main_test()) 