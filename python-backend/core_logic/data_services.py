import logging

# Functions in this module are primarily for fetching and doing initial broad-level processing
# of data from external exchange/market APIs.

def get_all_usdt_tickers_data(binance_cli):
    """Binance'den tüm USDT çiftleri için 24 saatlik ticker verilerini alır."""
    logging.info("\n--- Tüm USDT Çiftleri İçin Ticker Verileri Alınıyor ---")
    try:
        all_tickers = binance_cli.get_all_tickers() # Bu exchange_client içinde tanımlı olmalı
        if not all_tickers:
            logging.error("Hata: Binance API'den ticker verileri alınamadı.")
            return None

        usdt_tickers = []
        for ticker in all_tickers:
            if isinstance(ticker, dict) and 'symbol' in ticker and ticker['symbol'].endswith("USDT"):
                try:
                    # Gerekli alanları sayısal değere çevirelim, hata durumunda None yapalım
                    ticker_data = {
                        'symbol': ticker['symbol'],
                        'lastPrice': float(ticker.get('lastPrice', 0)),
                        'priceChangePercent': float(ticker.get('priceChangePercent', 0)),
                        'quoteVolume': float(ticker.get('quoteVolume', 0)) # USDT cinsinden hacim
                    }
                    usdt_tickers.append(ticker_data)
                except ValueError as ve:
                    logging.warning(f"Uyarı: {ticker.get('symbol')} için veri dönüştürme hatası: {ve}. Bu sembol atlanıyor.")
                except Exception as ex:
                    logging.warning(f"Uyarı: {ticker.get('symbol')} işlenirken beklenmedik hata: {ex}. Bu sembol atlanıyor.")
        
        logging.info(f"Toplam {len(usdt_tickers)} adet USDT çifti için ticker verisi başarıyla işlendi.")
        return usdt_tickers

    except Exception as e:
        logging.error(f"Tüm USDT ticker verilerini alırken genel bir hata oluştu: {e}")
        logging.exception("Tüm USDT ticker verileri alınırken bir istisna oluştu:")
        return None

def fetch_and_format_cmc_top_coins(cmc_cli, num_coins):
    """Fetches and formats top N coins by market cap from CoinMarketCap."""
    if not cmc_cli or not cmc_cli.cmc:
        logging.warning("CoinMarketCap istemcisi mevcut değil, piyasa değeri listesi atlanıyor.")
        return []
    cmc_top_coins_data = cmc_cli.get_listings_by_market_cap(limit=num_coins)
    if not cmc_top_coins_data:
        logging.warning("CoinMarketCap'ten piyasa değeri verisi alınamadı.")
        return []
    
    formatted_coins = []
    for coin_data_cmc in cmc_top_coins_data:
        formatted_coins.append({
            'symbol': coin_data_cmc['symbol'],
            'market_cap': coin_data_cmc['market_cap'],
            'lastPrice': coin_data_cmc['price'],
            'priceChangePercent': coin_data_cmc['percent_change_24h'],
            'quoteVolume': None # CMC listings/latest doesn't provide this directly
        })
    logging.info(f"CoinMarketCap'ten {len(formatted_coins)} adet piyasa değeri verisi işlendi.")
    return formatted_coins 