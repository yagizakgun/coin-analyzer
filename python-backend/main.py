import logging
import time
import pandas as pd
from binance.exceptions import BinanceAPIException
import asyncio
import os
from typing import Optional, List, Dict, Any
import json
from datetime import datetime
import sys

from config import EXCHANGE_API_KEY, EXCHANGE_API_SECRET, LLM_API_KEY, DEFAULT_KLINE_LIMIT, CRYPTOPANIC_API_KEY
# Updated imports from new directory structure
from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from clients.market_data_client import CoinMarketCapClient
from clients.market_sentiment_client import MarketSentimentClient
from fundamental_analysis.cryptopanic_client import CryptoPanicClient
# from binance.client import Client # No longer directly used in main.py after refactor
# import pandas_ta as ta # No longer directly used in main.py after refactor
import traceback

# Import from new and existing local modules
from core_logic.constants import (
    DEFAULT_TOP_N, CMC_TOP_N_MARKET_CAP, 
    LLM_ANALYSIS_PROMPT_TEMPLATE, LLM_ANALYSIS_PROMPT_TEMPLATE_NO_BTC_CONTEXT,
    LLM_HISTORICAL_ANALYSIS_PROMPT_TEMPLATE, LLM_HISTORICAL_ANALYSIS_PROMPT_TEMPLATE_NO_BTC_CONTEXT,
    FEW_SHOT_EXAMPLE, # Add the new example for few-shot learning
    TARGET_KLINE_INTERVALS, KLINE_INTERVAL_MAP, KLINE_HISTORY_PERIOD, KLINE_INTERVAL, # KLINE_INTERVAL is still used by get_bitcoin_trend_summary
    SMA_SHORT_PERIOD, SMA_LONG_PERIOD, # HATAYI DÜZELTMEK İÇİN EKLENDİ
    EMA_SHORT_PERIOD, EMA_LONG_PERIOD, ATR_PERIOD, # Added for prompt formatting
    RSI_PERIOD, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD, BBANDS_LENGTH, BBANDS_STD, # Added for prompt formatting
    ANALYSIS_MEMORY_DIR, MAX_SUMMARIES_TO_LOAD, SUMMARY_START_MARKER, SUMMARY_END_MARKER # Added memory constants
)
from utils.general_utils import (
    get_top_n_by_volume, get_top_n_gainers, get_top_n_decliners,
    format_indicator_value, preprocess_klines_df, calculate_technical_indicators,
    extract_latest_indicators, extract_price_summary_data
) # format_indicator_value, preprocess_klines_df etc. are used by analysis_logic now
from core_logic.data_services import get_all_usdt_tickers_data, fetch_and_format_cmc_top_coins
from core_logic.analysis_logic import (
    get_bitcoin_trend_summary, format_price_data_for_llm
)
from handlers.console_handlers import display_coin_selection_lists, get_and_validate_user_coin_choice

# Import the new modular analysis system
try:
    from core_logic.analysis_facade import initialize_analysis_system, get_analysis_system
    print("Successfully imported analysis_facade")
except ImportError as e:
    print(f"Error importing analysis_facade: {e}")
    # Add the parent directory to sys.path if needed
    sys.path.append(os.path.abspath('.'))
    try:
        from core_logic.analysis_facade import initialize_analysis_system, get_analysis_system
        print("Successfully imported analysis_facade after path adjustment")
    except ImportError as e:
        print(f"Still cannot import analysis_facade: {e}")
from core_logic.analysis_modules import (
    CryptoAnalysisModule,
    SpotTradingAnalysisModule,
    FuturesTradingAnalysisModule
)

# Logging yapılandırması
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                    handlers=[
                        logging.FileHandler("bot.log", mode='w', encoding='utf-8'),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# TARGET_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"] # Analiz edilecek coinler - ARTIK DİNAMİK OLACAK
# KLINE_INTERVAL = Client.KLINE_INTERVAL_1HOUR # Moved to constants.py
# KLINE_HISTORY_PERIOD = "72 hour ago UTC" # Moved to constants.py

# DEFAULT_TOP_N = 15 # Moved to constants.py
# CMC_TOP_N_MARKET_CAP = 40 # Moved to constants.py

# def format_indicator_value(value, precision=2): # Moved to utils.py
#     if isinstance(value, float):
#         return f"{value:.{precision}f}"
#     return str(value)

# --- MEMORY SYSTEM CONSTANTS ---
# ANALYSIS_MEMORY_DIR = "analysis_memory"
# MAX_SUMMARIES_TO_LOAD = 5 # Max number of past summaries to feed to LLM
# SUMMARY_START_MARKER = "---YENI_Ozet_BASLANGIC---"
# SUMMARY_END_MARKER = "---YENI_Ozet_BITIS---"


# --- MEMORY SYSTEM HELPER FUNCTIONS ---
async def load_analysis_summaries(symbol: str) -> list:
    """Loads past analysis summaries for a given symbol from its JSON file."""
    memory_file_path = os.path.join(ANALYSIS_MEMORY_DIR, f"{symbol}_memory.json")
    if not os.path.exists(ANALYSIS_MEMORY_DIR):
        try:
            os.makedirs(ANALYSIS_MEMORY_DIR)
            logging.info(f"'{ANALYSIS_MEMORY_DIR}' directory created.")
        except OSError as e:
            logging.error(f"Error creating directory '{ANALYSIS_MEMORY_DIR}': {e}")
            return []

    if os.path.exists(memory_file_path):
        try:
            with open(memory_file_path, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
            logging.info(f"Loaded {len(summaries)} past summaries for {symbol} from {memory_file_path}")
            return summaries
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {memory_file_path}. Returning empty list.")
            return []
        except Exception as e:
            logging.error(f"Error reading summaries for {symbol} from {memory_file_path}: {e}")
            return []
    else:
        logging.info(f"No past summary file found for {symbol} at {memory_file_path}.")
        return []

async def save_analysis_summary(symbol: str, summary_text: str, analysis_date_iso: Optional[str] = None):
    """Saves a new analysis summary for a given symbol to its JSON file.
    Optionally uses a specific ISO date for the summary's timestamp."""
    if not summary_text or not summary_text.strip():
        logging.warning(f"Attempted to save an empty or whitespace-only summary for {symbol}. Skipping.")
        return

    memory_file_path = os.path.join(ANALYSIS_MEMORY_DIR, f"{symbol}_memory.json")
    if not os.path.exists(ANALYSIS_MEMORY_DIR):
        try:
            os.makedirs(ANALYSIS_MEMORY_DIR)
            logging.info(f"'{ANALYSIS_MEMORY_DIR}' directory created for saving summary.")
        except OSError as e:
            logging.error(f"Error creating directory '{ANALYSIS_MEMORY_DIR}' for saving summary: {e}")
            return

    summaries = await load_analysis_summaries(symbol) # Load existing to append

    timestamp_to_save = analysis_date_iso if analysis_date_iso else datetime.now().isoformat()

    new_summary_entry = {
        "timestamp": timestamp_to_save,
        "summary": summary_text.strip()
    }
    summaries.append(new_summary_entry)

    # Keep summaries sorted by timestamp, newest first for easier slicing later if needed.
    # Though reversed iteration is used in analyze_coin, sorting here ensures consistency.
    summaries.sort(key=lambda x: x["timestamp"], reverse=True)


    try:
        with open(memory_file_path, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, ensure_ascii=False, indent=4)
        logging.info(f"Successfully saved new summary for {symbol} (Timestamp: {timestamp_to_save}) to {memory_file_path}")
    except Exception as e:
        logging.error(f"Error writing summaries for {symbol} to {memory_file_path}: {e}")


def _build_bitcoin_trend_summary_string(symbol, current_ticker_data, latest_indicators):
    """Builds the Bitcoin trend summary string using ticker data and latest indicators."""
    # get_ticker (sembol ile çağrıldığında) 'lastPrice' ve 'priceChangePercent' anahtarlarını döndürür
    current_price_str = current_ticker_data.get('lastPrice', 'N/A') 
    current_price_val = float(current_price_str) if current_price_str != 'N/A' else None
    price_change_percent_str = current_ticker_data.get('priceChangePercent', 'N/A')

    summary = f"Bitcoin (BTCUSDT) Güncel Durum Özeti:\\n"
    summary += f"  Mevcut Fiyat: {format_indicator_value(current_price_str, 2)} USDT (24s Değişim: %{format_indicator_value(price_change_percent_str, 2)})\\n"
    summary += f"  RSI(14): {format_indicator_value(latest_indicators.get('rsi'))}\\n"

    latest_sma20_val = latest_indicators.get('sma20')
    sma20_relation = "bilinmiyor"
    if current_price_val is not None and latest_sma20_val is not None and latest_sma20_val != 'N/A': # Check for 'N/A'
        if current_price_val > float(latest_sma20_val): sma20_relation = "üzerinde"
        elif current_price_val < float(latest_sma20_val): sma20_relation = "altında"
        else: sma20_relation = "eşit"
    summary += f"  Fiyat vs SMA20 ({format_indicator_value(latest_sma20_val)}): Fiyat {sma20_relation}\\n"

    latest_sma50_val = latest_indicators.get('sma50')
    sma50_relation = "bilinmiyor"
    if current_price_val is not None and latest_sma50_val is not None and latest_sma50_val != 'N/A': # Check for 'N/A'
        if current_price_val > float(latest_sma50_val): sma50_relation = "üzerinde"
        elif current_price_val < float(latest_sma50_val): sma50_relation = "altında"
        else: sma50_relation = "eşit"
    summary += f"  Fiyat vs SMA50 ({format_indicator_value(latest_sma50_val)}): Fiyat {sma50_relation}\\n"
    
    latest_macd_val = latest_indicators.get('macd')
    latest_macd_signal_val = latest_indicators.get('macd_signal')
    macd_relation = "bilinmiyor"
    if latest_macd_val is not None and latest_macd_signal_val is not None and latest_macd_val != 'N/A' and latest_macd_signal_val != 'N/A': # Check for 'N/A'
        if float(latest_macd_val) > float(latest_macd_signal_val): macd_relation = "üzerinde"
        elif float(latest_macd_val) < float(latest_macd_signal_val): macd_relation = "altında"
        else: macd_relation = "eşit"
    summary += f"  MACD Çizgisi ({format_indicator_value(latest_macd_val)}) vs Sinyal Çizgisi ({format_indicator_value(latest_macd_signal_val)}): MACD {macd_relation}\\n"
    return summary

async def get_bitcoin_trend_summary(binance_cli: BinanceClient):
    logging.info("--- Bitcoin (BTCUSDT) Trend Özeti Alınıyor ---")
    symbol = "BTCUSDT"
    # BTC summary will still use the single KLINE_INTERVAL for now.
    # This could be a future enhancement to make it multi-timeframe too.
    primary_btc_interval = KLINE_INTERVAL 
    try:
        klines = await binance_cli.get_klines(
            symbol,
            primary_btc_interval, 
            limit=DEFAULT_KLINE_LIMIT 
        )
        if not klines or len(klines) < 50:
            logging.warning(f"{symbol} için trend özeti oluşturacak yeterli mum verisi (en az 50) bulunamadı.")
            return "Bitcoin (BTCUSDT) trend verisi şu anda alınamıyor."

        # 24 saatlik tam ticker verisini almak için get_ticker(symbol=...) kullan
        current_ticker_data = await binance_cli.client.get_ticker(symbol=symbol)
        logger.debug(f"Bitcoin (BTCUSDT) anlık 24 saatlik ticker verisi: {current_ticker_data}")

        if not current_ticker_data:
            logging.warning(f"{symbol} için anlık 24 saatlik ticker verisi alınamadı.")
            return "Bitcoin (BTCUSDT) anlık fiyat ve değişim verisi şu anda alınamıyor."

        df = preprocess_klines_df(klines)
        df_with_indicators = calculate_technical_indicators(df)
        latest_indicators = extract_latest_indicators(df_with_indicators)
        
        summary = _build_bitcoin_trend_summary_string(symbol, current_ticker_data, latest_indicators)
        
        logging.info(f"Bitcoin Trend Özeti:\\n{summary}")
        return summary

    except Exception as e:
        logging.error(f"Bitcoin (BTCUSDT) trend özeti alınırken hata oluştu: {e}")
        logging.exception("Bitcoin trend özeti alınırken bir istisna oluştu:")
        return "Bitcoin (BTCUSDT) trend verisi alınırken bir hata oluştu."

async def get_all_usdt_tickers_data(binance_cli: BinanceClient):
    """Binance'den tüm USDT çiftleri için 24 saatlik ticker verilerini alır."""
    logging.info("\n--- Tüm USDT Çiftleri İçin Ticker Verileri Alınıyor ---")
    try:
        all_tickers = await binance_cli.get_all_tickers()
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

async def analyze_coin(binance_cli: BinanceClient, 
                       llm_cli: GeminiClient, 
                       fundamental_cli: Optional[CryptoPanicClient],
                       symbol: str, 
                       btc_trend_summary: str):
    """
    Analyzes a cryptocurrency using technical and fundamental data.
    """
    try:
        # Initialize market sentiment client
        market_sentiment_cli = MarketSentimentClient()
        
        # Fetch market sentiment data
        fear_greed_data = await market_sentiment_cli.get_fear_greed_index()
        market_trend_data = await market_sentiment_cli.get_market_trend()
        market_sentiment_str = market_sentiment_cli.format_market_sentiment_for_llm(fear_greed_data, market_trend_data)

        # 1. Load Historical Analysis Summaries
        historical_context_str = ""
        memory_file_path = os.path.join(ANALYSIS_MEMORY_DIR, f"{symbol}_memory.json")
        
        if os.path.exists(memory_file_path):
            try:
                with open(memory_file_path, 'r', encoding='utf-8') as f:
                    past_summaries = json.load(f)
                    
                if past_summaries:
                    # Sort by timestamp, newest first
                    past_summaries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                    
                    # Take the most recent summaries up to MAX_SUMMARIES_TO_LOAD
                    recent_summaries = past_summaries[:MAX_SUMMARIES_TO_LOAD]
                    
                    historical_context_str = "## Geçmiş Analiz Özetleri\n\n"
                    for summary in recent_summaries:
                        timestamp = summary.get('timestamp', '')
                        if timestamp:
                            try:
                                dt = datetime.fromisoformat(timestamp)
                                formatted_time = dt.strftime("%d.%m.%Y %H:%M")
                            except ValueError:
                                formatted_time = timestamp
                        else:
                            formatted_time = "Bilinmeyen Tarih"
                            
                        historical_context_str += f"### {formatted_time}\n"
                        historical_context_str += f"{summary.get('summary', 'Özet bulunamadı')}\n\n"
                    
                    # Extract trend information if multiple summaries exist
                    if len(past_summaries) >= 2:
                        # Compare sentiments over time
                        recent_sentiments = [s.get('sentiment', 'neutral') for s in past_summaries[-3:]]
                        positive_count = recent_sentiments.count('positive')
                        negative_count = recent_sentiments.count('negative')
                        neutral_count = recent_sentiments.count('neutral')
                        
                        sentiment_trend = "olumluya dönük" if positive_count > negative_count else "olumsuza dönük" if negative_count > positive_count else "kararsız/değişken"
                        
                        # Add trend summary
                        historical_context_str += f"\n## Özet Trend Analizi\n"
                        historical_context_str += f"Son {len(past_summaries[-3:])} analizdeki genel görünüm: {sentiment_trend}\n"
                        
                        # Add price trend if available
                        try:
                            if 'price' in past_summaries[-1] and 'price' in past_summaries[-2]:
                                last_price = float(past_summaries[-1]['price'].replace(',', ''))
                                previous_price = float(past_summaries[-2]['price'].replace(',', ''))
                                price_change_pct = ((last_price - previous_price) / previous_price) * 100
                                
                                price_trend = f"Son analiz ile bir önceki analiz arasında yaklaşık %{price_change_pct:.2f} "
                                price_trend += "artış" if price_change_pct > 0 else "düşüş" if price_change_pct < 0 else "değişim yok"
                                
                                historical_context_str += f"Fiyat trendi: {price_trend}\n"
                        except Exception as e:
                            logging.warning(f"Fiyat trend hesaplaması yapılamadı: {e}")
            
            except Exception as e:
                logging.error(f"Geçmiş analiz özetleri yüklenirken hata: {e}")
                logging.exception("Geçmiş analiz özetleri yüklenirken bir istisna oluştu:")
                historical_context_str = "Geçmiş analiz özetleri yüklenemedi."
        else:
            historical_context_str = "Bu coin için henüz geçmiş analiz özeti bulunmuyor."
        
        logging.debug(f"LLM için hazırlanan geçmiş özetler ({symbol}):\n{historical_context_str}")

        # 2. Fetch Current Market Data (Technical)
        klines_by_interval = {}
        all_klines_fetched_successfully = True
        for interval_code in TARGET_KLINE_INTERVALS:
            interval_str = KLINE_INTERVAL_MAP.get(interval_code, interval_code) # Get human-readable string
            logging.info(f"Fetching {interval_str} klines for {symbol}...")
            klines = await binance_cli.get_klines(
                symbol,
                interval_code,
                limit=DEFAULT_KLINE_LIMIT 
            )
            if not klines or len(klines) < 50: 
                logging.warning(f"{symbol} için {interval_str} zaman aralığında yeterli mum verisi (en az 50) alınamadı.")
                klines_by_interval[interval_code] = [] 
                all_klines_fetched_successfully = False 
            else:
                klines_by_interval[interval_code] = klines
        
        if not klines_by_interval or all(not k_list for k_list in klines_by_interval.values()):
             logging.warning(f"{symbol} için hiçbir zaman aralığında yeterli mum verisi alınamadı. Teknik analiz yapılamayacak.")
             # Temel analiz yine de yapılabilir, bu yüzden return demiyoruz hemen.
        
        current_ticker_24hr_data = await binance_cli.client.get_ticker(symbol=symbol)
        logger.debug(f"Anlık 24 saatlik ticker verisi ({symbol}): {current_ticker_24hr_data}")

        if not current_ticker_24hr_data: 
            logging.warning(f"{symbol} için 24 saatlik ticker verisi alınamadı. Fiyat bilgileri eksik olacak.")
            current_ticker_24hr_data = {} 

        formatted_technical_data = format_price_data_for_llm(symbol, klines_by_interval, current_ticker_24hr_data)

        # 3. Fetch Fundamental Data
        fundamental_data_str = ""
        if fundamental_cli:
            try:
                fundamental_data = await fundamental_cli.get_data(symbol)
                if fundamental_data:
                    fundamental_data_str = fundamental_data
                else:
                    fundamental_data_str = "Temel analiz verisi alınamadı."
            except Exception as e:
                logging.error(f"Temel analiz verisi alınırken hata: {e}")
                fundamental_data_str = "Temel analiz verisi alınırken bir hata oluştu."
        else:
            fundamental_data_str = "Temel analiz istemcisi mevcut değil."

        # 4. Prepare LLM Prompt
        prompt_to_llm_args = {
            "symbol": symbol,
            "formatted_data": formatted_technical_data,
            "fundamental_data": fundamental_data_str,
            "market_sentiment": market_sentiment_str,  # Add market sentiment data
            "SMA_SHORT_PERIOD": SMA_SHORT_PERIOD, 
            "SMA_LONG_PERIOD": SMA_LONG_PERIOD,
            "EMA_SHORT_PERIOD": EMA_SHORT_PERIOD,
            "EMA_LONG_PERIOD": EMA_LONG_PERIOD,
            "ATR_PERIOD": ATR_PERIOD,
            "RSI_PERIOD": RSI_PERIOD,
            "MACD_FAST_PERIOD": MACD_FAST_PERIOD,
            "MACD_SLOW_PERIOD": MACD_SLOW_PERIOD,
            "MACD_SIGNAL_PERIOD": MACD_SIGNAL_PERIOD,
            "BBANDS_LENGTH": BBANDS_LENGTH,
            "BBANDS_STD": BBANDS_STD,
            "historical_context": historical_context_str,
            "summary_start_marker": SUMMARY_START_MARKER,
            "summary_end_marker": SUMMARY_END_MARKER
        }

        if symbol != "BTCUSDT" and btc_trend_summary:
            prompt_to_llm_args["btc_trend_summary"] = btc_trend_summary
            # Add example for few-shot learning if we have sufficient tokens
            prompt_template = LLM_ANALYSIS_PROMPT_TEMPLATE + "\n\n# ÖRNEK YÜKSEK KALİTELİ ANALİZ\n" + FEW_SHOT_EXAMPLE
        else:
            # BTC analizi yapılıyorsa veya BTC özeti yoksa bu şablonu kullan
            prompt_template = LLM_ANALYSIS_PROMPT_TEMPLATE_NO_BTC_CONTEXT + "\n\n# ÖRNEK YÜKSEK KALİTELİ ANALİZ\n" + FEW_SHOT_EXAMPLE
        
        prompt_to_llm = prompt_template.format(**prompt_to_llm_args)
        
        logging.info("LLM'e gönderiliyor...")
        analysis_result_raw = llm_cli.generate_text(prompt_to_llm)

        # 5. Extract New Summary and Main Analysis from LLM Response
        new_summary_for_memory = ""
        main_analysis_content = analysis_result_raw
        
        if SUMMARY_START_MARKER in analysis_result_raw and SUMMARY_END_MARKER in analysis_result_raw:
            try:
                # Extract the summary part
                summary_start = analysis_result_raw.find(SUMMARY_START_MARKER) + len(SUMMARY_START_MARKER)
                summary_end = analysis_result_raw.find(SUMMARY_END_MARKER)
                new_summary_for_memory = analysis_result_raw[summary_start:summary_end].strip()
                
                # Remove the summary part from the main analysis
                main_analysis_content = (
                    analysis_result_raw[:summary_start - len(SUMMARY_START_MARKER)] +
                    analysis_result_raw[summary_end + len(SUMMARY_END_MARKER):]
                ).strip()
                
                logging.info(f"Özet başarıyla çıkarıldı ({symbol}):\n{new_summary_for_memory}")
            except Exception as e:
                logging.error(f"Özet çıkarılırken hata: {e}")
                logging.exception("Özet çıkarılırken bir istisna oluştu:")
                new_summary_for_memory = "Özet çıkarılamadı."
        else:
            logging.warning(f"LLM yanıtında özet işaretçileri bulunamadı ({symbol}).")
            new_summary_for_memory = "Özet işaretçileri bulunamadı."

        # 6. Save New Summary to Memory
        if new_summary_for_memory:
            try:
                # Create memory directory if it doesn't exist
                os.makedirs(ANALYSIS_MEMORY_DIR, exist_ok=True)
                
                # Load existing summaries
                existing_summaries = []
                if os.path.exists(memory_file_path):
                    try:
                        with open(memory_file_path, 'r', encoding='utf-8') as f:
                            existing_summaries = json.load(f)
                    except json.JSONDecodeError:
                        logging.warning(f"Geçersiz JSON formatı, yeni dosya oluşturuluyor: {memory_file_path}")
                        existing_summaries = []
                
                # Add new summary
                new_summary_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "summary": new_summary_for_memory
                }
                existing_summaries.append(new_summary_entry)
                
                # Save updated summaries
                with open(memory_file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_summaries, f, ensure_ascii=False, indent=4)
                
                logging.info(f"Yeni özet başarıyla kaydedildi ({symbol}).")
            except Exception as e:
                logging.error(f"Yeni özet kaydedilirken hata: {e}")
                logging.exception("Yeni özet kaydedilirken bir istisna oluştu:")

        return main_analysis_content

    except Exception as e:
        logging.error(f"Coin analizi sırasında hata: {e}")
        logging.exception("Coin analizi sırasında bir istisna oluştu:")
        return f"{symbol} analizi sırasında bir hata oluştu: {str(e)}"

async def analyze_coin_at_date(
    binance_cli: BinanceClient,
    llm_cli: GeminiClient,
    fundamental_cli: Optional[CryptoPanicClient],
    symbol: str,
    analysis_target_date_iso: str,
    btc_trend_summary_at_date: Optional[str] = None
):
    """
    Analyzes a single coin using data up to a specific historical date and saves it to memory.
    Note: Historical analysis does not include market sentiment data (fear/greed index, market trends)
    as these are only relevant for current analysis.
    """
    logging.info(f"--- {symbol} Geçmiş Tarih Analizi Başlatılıyor (Tarih: {analysis_target_date_iso}) ---")
    try:
        analysis_target_dt = datetime.fromisoformat(analysis_target_date_iso.replace("Z", "+00:00"))
        analysis_target_timestamp_ms = int(analysis_target_dt.timestamp() * 1000)
        # Use a more human readable format for the analysis date in the prompt
        human_readable_date = analysis_target_dt.strftime("%d %B %Y, %H:%M") 

        # 1. Load Past Summaries (before the analysis_target_date_iso)
        all_past_summaries = await load_analysis_summaries(symbol)
        relevant_past_summaries = [
            s for s in all_past_summaries
            if datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00")) < analysis_target_dt
        ]
        # Sort relevant summaries by timestamp, newest first, to pick the most recent ones for context
        relevant_past_summaries.sort(key=lambda x: x["timestamp"], reverse=True)

        historical_context_str = f"Bu coin için {human_readable_date} tarihinden öncesine ait analiz özeti bulunmamaktadır."
        
        if relevant_past_summaries:
            # Format historical context with more structured information
            historical_context_str = f"## {symbol} İçin {human_readable_date} Tarihinden Önceki Analiz Özetleri\n"
            historical_context_str += f"(En son {len(relevant_past_summaries[:MAX_SUMMARIES_TO_LOAD])} analiz gösteriliyor, en yeniden en eskiye doğru sıralanmıştır)\n\n"
            
            # Process summaries to extract additional context
            for i, summary_item in enumerate(relevant_past_summaries[:MAX_SUMMARIES_TO_LOAD]):
                # Calculate time between this summary and the target analysis date
                summary_dt = datetime.fromisoformat(summary_item['timestamp'].replace('Z', '+00:00'))
                time_diff = analysis_target_dt - summary_dt
                days_diff = time_diff.days
                hours_diff = time_diff.seconds // 3600
                
                time_before = f"{days_diff} gün" if days_diff > 0 else f"{hours_diff} saat" 
                
                # Get any extracted price and sentiment information
                price_info = f", Fiyat: {summary_item.get('price', 'belirtilmemiş')}" if 'price' in summary_item else ""
                sentiment = summary_item.get('sentiment', 'neutral')
                sentiment_emoji = "📈" if sentiment == "positive" else "📉" if sentiment == "negative" else "➡️"
                
                # Format the entry with all context
                historical_context_str += f"### Analiz: {summary_item.get('readable_date', summary_item['timestamp'])}\n"
                historical_context_str += f"(Analiz tarihinden {time_before} önce{price_info}) {sentiment_emoji}\n\n"
                historical_context_str += f"{summary_item['summary']}\n\n"
                
                # Add a separator between entries for clarity
                if i < len(relevant_past_summaries[:MAX_SUMMARIES_TO_LOAD]) - 1:
                    historical_context_str += "---\n\n"
            
            # Extract trend information if multiple summaries exist
            if len(relevant_past_summaries) >= 2:
                # Compare sentiments over time up to the analysis date
                recent_sentiments = [s.get('sentiment', 'neutral') for s in relevant_past_summaries[:3]]
                positive_count = recent_sentiments.count('positive')
                negative_count = recent_sentiments.count('negative')
                neutral_count = recent_sentiments.count('neutral')
                
                sentiment_trend = "olumluya dönük" if positive_count > negative_count else "olumsuza dönük" if negative_count > positive_count else "kararsız/değişken"
                
                # Add trend summary
                historical_context_str += f"\n## {human_readable_date} Öncesi Trend Analizi\n"
                historical_context_str += f"Son {len(relevant_past_summaries[:3])} analizdeki genel görünüm: {sentiment_trend}\n"
                
                # Add price trend if available
                try:
                    if 'price' in relevant_past_summaries[0] and 'price' in relevant_past_summaries[1]:
                        last_price = float(relevant_past_summaries[0]['price'].replace(',', ''))
                        previous_price = float(relevant_past_summaries[1]['price'].replace(',', ''))
                        price_change_pct = ((last_price - previous_price) / previous_price) * 100
                        
                        price_trend = f"Son analiz ile bir önceki analiz arasında yaklaşık %{price_change_pct:.2f} "
                        price_trend += "artış" if price_change_pct > 0 else "düşüş" if price_change_pct < 0 else "değişim yok"
                        
                        historical_context_str += f"Fiyat trendi: {price_trend}\n"
                except Exception as e:
                    logging.warning(f"Fiyat trend hesaplaması yapılamadı: {e}")
        
        logging.debug(f"LLM için hazırlanan geçmiş özetler ({symbol} @ {analysis_target_date_iso}):\n{historical_context_str}")

        # 2. Fetch Historical Market Data (Technical) up to analysis_target_timestamp_ms
        klines_by_interval = {}
        all_klines_fetched_successfully = True
        for interval_code in TARGET_KLINE_INTERVALS:
            interval_str = KLINE_INTERVAL_MAP.get(interval_code, interval_code)
            logging.info(f"Fetching {interval_str} klines for {symbol} up to {analysis_target_date_iso}...")
            # Fetch klines ending at or before the target date.
            # The `endTime` parameter in get_historical_klines is inclusive of the candle that *starts* at or before endTime.
            # We want klines *before* or *at* the target date.
            # For simplicity, we fetch a standard limit and the format_price_data_for_llm will use the latest available data from this set.
            # A more precise approach might involve iterating to get exactly N candles before the endTime.
            # For now, we use get_klines which typically gets recent data.
            # To get data truly *up to* a past date, we'd ideally use get_historical_klines.
            # Let's assume BinanceClient's get_klines can be adapted or a new method added for this.
            # For now, we'll use a placeholder and simulate this or accept current get_klines limitations.

            # --- MODIFICATION NEEDED for binance_cli.get_klines ---
            # It currently fetches the *latest* klines. We need klines *up to* analysis_target_timestamp_ms.
            # This requires using client.get_historical_klines with an endTime.
            # We'll assume binance_cli.get_historical_klines(symbol, interval, end_str=..., limit=...) exists.
            # For simplicity, let's modify the existing get_klines to accept an optional endTime_ms
            
            # Using a temporary direct call to illustrate, ideally integrated into BinanceClient
            raw_klines = await binance_cli.client.get_historical_klines(
                symbol,
                interval_code,
                start_str=None, # Fetch enough history
                end_str=str(analysis_target_timestamp_ms), # Data up to this timestamp
                limit=DEFAULT_KLINE_LIMIT
            )

            if not raw_klines or len(raw_klines) < 50:
                logging.warning(f"{symbol} için {interval_str} (hedef tarih: {analysis_target_date_iso}) zaman aralığında yeterli mum verisi (en az 50) alınamadı.")
                klines_by_interval[interval_code] = []
                all_klines_fetched_successfully = False
            else:
                klines_by_interval[interval_code] = raw_klines
        
        if not klines_by_interval or all(not k_list for k_list in klines_by_interval.values()):
            logging.error(f"{symbol} için {analysis_target_date_iso} tarihine kadar hiçbir zaman aralığında yeterli mum verisi alınamadı. Analiz yapılamayacak.")
            return f"{symbol} için {analysis_target_date_iso} tarihine kadar yeterli veri bulunamadı."

        # For historical analysis, current_ticker_24hr_data is not directly applicable in the same way.
        # We'll use the last kline's close price as the "current price" for that historical moment.
        # And we'll have to calculate 24hr change manually if needed, or omit it.
        # For now, format_price_data_for_llm should handle this if current_ticker_24hr_data is None or {}
        # Let's try to get the ticker data *as of* that historical point if possible, though many APIs don't support this.
        # Binance get_ticker is live. So we will pass an empty dict for current_ticker_24hr_data for historical.
        # The format_price_data_for_llm will need to be robust to this.
        # The last kline in our fetched data will represent the "current" state at analysis_target_date_iso.
        historical_ticker_data = {} # No direct way to get 24hr ticker for a past arbitrary time.
                                   # format_price_data_for_llm will use the latest kline data.

        formatted_technical_data = format_price_data_for_llm(
            symbol, 
            klines_by_interval, 
            historical_ticker_data, # Pass empty or None for historical
            is_historical=True,
            historical_timestamp_ms=analysis_target_timestamp_ms
        )
        
        if "yeterli geçmiş fiyat verisi bulunamadı" in formatted_technical_data or not formatted_technical_data.strip():
            logging.warning(f"{symbol} için ({analysis_target_date_iso}) formatlanmış teknik veri oluşturulamadı veya yetersiz veri: {formatted_technical_data}")
            formatted_technical_data = "Belirtilen tarih için teknik veri bulunamadı veya yetersiz."

        # Fundamental data for a specific past date is hard to get. CryptoPanic usually gives current news.
        fundamental_data_str = f"Belirtilen geçmiş tarih ({analysis_target_date_iso}) için temel analiz verisi/haber mevcut değil."
        if fundamental_cli:
            logging.info(f"Fetching fundamental data for {symbol} (current, as historical is hard)...")
            currency_code_for_news = symbol.replace("USDT", "").upper()
            # We might try to get news around that date if API supported, for now using current as a rough proxy or acknowledging limitation.
            # For this implementation, we'll state that historical news is not available.
            logging.warning(f"CryptoPanic historical news for {analysis_target_date_iso} is not supported directly. Current news might be fetched if logic allowed, but for training, assuming no specific past news.")
            # news_data = await fundamental_cli.get_data(currency_code_for_news, limit=5) 
            # if news_data:
            #     fundamental_data_str = f"Güncel haberler (geçmiş {analysis_target_date_iso} için direkt veri yok):\n{news_data}"
            
        logging.debug(f"LLM'e gönderilecek formatlanmış TEKNİK veri ({analysis_target_date_iso}):\n{formatted_technical_data}")
        logging.debug(f"LLM'e gönderilecek formatlanmış TEMEL veri ({analysis_target_date_iso}):\n{fundamental_data_str}")

        # Tarihi analizlerde market sentiment verileri kullanılmaz
        # Tarihi analiz şablonları market_sentiment parametresini içermez
        logging.info(f"Tarihi analizlerde market sentiment (korku/açgözlülük endeksi ve piyasa trendi) verileri kullanılmıyor.")
        
        prompt_to_llm_args = {
            "symbol": symbol,
            "formatted_data": formatted_technical_data,
            "fundamental_data": fundamental_data_str,
            "SMA_SHORT_PERIOD": SMA_SHORT_PERIOD,
            "SMA_LONG_PERIOD": SMA_LONG_PERIOD,
            "EMA_SHORT_PERIOD": EMA_SHORT_PERIOD,
            "EMA_LONG_PERIOD": EMA_LONG_PERIOD,
            "ATR_PERIOD": ATR_PERIOD,
            "RSI_PERIOD": RSI_PERIOD,
            "MACD_FAST_PERIOD": MACD_FAST_PERIOD,
            "MACD_SLOW_PERIOD": MACD_SLOW_PERIOD,
            "MACD_SIGNAL_PERIOD": MACD_SIGNAL_PERIOD,
            "BBANDS_LENGTH": BBANDS_LENGTH,
            "BBANDS_STD": BBANDS_STD,
            "historical_context": historical_context_str,
            "summary_start_marker": SUMMARY_START_MARKER,
            "summary_end_marker": SUMMARY_END_MARKER,
            "analysis_date": human_readable_date  # Add the formatted analysis date
        }
        
        # For historical analysis, use the specific historical templates
        if symbol != "BTCUSDT" and btc_trend_summary_at_date:
            prompt_to_llm_args["btc_trend_summary"] = btc_trend_summary_at_date
            # Use the historical analysis template with BTC context
            prompt_template = LLM_HISTORICAL_ANALYSIS_PROMPT_TEMPLATE
            logging.info(f"BTC trend özeti {analysis_target_date_iso} tarihi için kullanılıyor.")
        else:
            # Use the historical analysis template without BTC context
            prompt_template = LLM_HISTORICAL_ANALYSIS_PROMPT_TEMPLATE_NO_BTC_CONTEXT
            if symbol != "BTCUSDT":
                 logging.warning(f"BTC trend özeti {analysis_target_date_iso} için sağlanmadı, NO_BTC_CONTEXT şablonu kullanılıyor.")

        prompt_to_llm = prompt_template.format(**prompt_to_llm_args)
        
        logging.info(f"LLM'e gönderiliyor ({symbol} @ {analysis_target_date_iso})...")
        analysis_result_raw = llm_cli.generate_text(prompt_to_llm)

        new_summary_for_memory = ""
        main_analysis_content = analysis_result_raw

        if analysis_result_raw:
            try:
                start_idx = analysis_result_raw.rfind(SUMMARY_START_MARKER)
                end_idx = analysis_result_raw.rfind(SUMMARY_END_MARKER)
                if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                    new_summary_for_memory = analysis_result_raw[start_idx + len(SUMMARY_START_MARKER):end_idx].strip()
                    main_analysis_content = analysis_result_raw[:start_idx].strip()
                    if analysis_result_raw[end_idx + len(SUMMARY_END_MARKER):].strip():
                        main_analysis_content += "\n" + analysis_result_raw[end_idx + len(SUMMARY_END_MARKER):].strip()
                    logging.info(f"Yeni özet başarıyla çıkarıldı ({symbol} @ {analysis_target_date_iso}): '{new_summary_for_memory}'")
                else:
                    logging.warning(f"{symbol} ({analysis_target_date_iso}) için LLM yanıtında özet işaretçileri bulunamadı. Yanıtın tamamı ana analiz olarak kabul edilecek.")
                    new_summary_for_memory = f"LLM yanıtından otomatik özet çıkarılamadı. Analiz hedef tarihi: {analysis_target_date_iso}"
            except Exception as e:
                logging.error(f"{symbol} ({analysis_target_date_iso}) için LLM yanıtından özet çıkarılırken hata: {e}.")
                new_summary_for_memory = f"LLM yanıtından özet çıkarılırken hata oluştu. Analiz hedef tarihi: {analysis_target_date_iso}"
            
            if new_summary_for_memory:
                # Save summary with the historical date as its timestamp
                await save_analysis_summary(symbol, new_summary_for_memory, analysis_date_iso=analysis_target_date_iso)
            else:
                logging.warning(f"LLM'den {symbol} ({analysis_target_date_iso}) için geçerli bir yeni özet alınamadı, hafızaya kayıt yapılmayacak.")

            logging.info(f"\n{symbol} için LLM Geçmiş Tarih Analizi (Ana İçerik - {analysis_target_date_iso}):")
            logging.info(f"LLM Analiz Sonucu ({symbol} @ {analysis_target_date_iso}):\\n{str(main_analysis_content)}")
            return str(main_analysis_content)
        else:
            logging.warning(f"{symbol} ({analysis_target_date_iso}) için LLM'den analiz alınamadı.")
            return f"{symbol} ({analysis_target_date_iso}) için LLM'den analiz alınamadı."

    except ValueError as ve: # For datetime conversion errors
        logging.error(f"{symbol} analizi için geçersiz tarih formatı ({analysis_target_date_iso}): {ve}")
        return f"{symbol} analizi için geçersiz tarih formatı: {analysis_target_date_iso}. Lütfen YYYY-MM-DDTHH:MM:SS formatını kullanın."
    except BinanceAPIException as bae:
        logging.error(f"{symbol} ({analysis_target_date_iso}) geçmiş analizi sırasında Binance API hatası: {bae}")
        return f"{symbol} ({analysis_target_date_iso}) geçmiş analizi sırasında Binance API hatası: {bae}"
    except Exception as e:
        logging.error(f"{symbol} ({analysis_target_date_iso}) geçmiş analiz edilirken genel bir hata oluştu: {e}")
        logging.exception(f"{symbol} ({analysis_target_date_iso}) geçmiş analizi sırasında bir istisna oluştu:")
        return f"{symbol} ({analysis_target_date_iso}) geçmiş analiz edilirken genel bir hata oluştu: {e}"

def _fetch_and_format_cmc_top_coins(cmc_cli, num_coins):
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

def _get_top_n_by_volume(all_binance_usdt_tickers, n):
    """Returns top N coins by quoteVolume from Binance tickers."""
    if not all_binance_usdt_tickers:
        return []
    return sorted([t for t in all_binance_usdt_tickers if t['quoteVolume'] > 0], key=lambda x: x['quoteVolume'], reverse=True)[:n]

def _get_top_n_gainers(all_binance_usdt_tickers, n):
    """Returns top N gainer coins by priceChangePercent from Binance tickers."""
    if not all_binance_usdt_tickers:
        return []
    return sorted([t for t in all_binance_usdt_tickers if t['priceChangePercent'] > 0], key=lambda x: x['priceChangePercent'], reverse=True)[:n]

def _get_top_n_decliners(all_binance_usdt_tickers, n):
    """Returns top N decliner coins by priceChangePercent from Binance tickers."""
    if not all_binance_usdt_tickers:
        return []
    return sorted([t for t in all_binance_usdt_tickers if t['priceChangePercent'] < 0], key=lambda x: x['priceChangePercent'])[:n]

def _display_coin_selection_lists(top_market_cap, top_volume, top_gainers, top_decliners, default_top_n_display):
    """
    Display various top coin lists to help users select a coin for analysis.
    """
    print("\n--- 👇 Analiz Edilebilecek Bazı Kripto Para Önerileri (Herhangi bir Binance'deki coini analiz edebilirsiniz) ---")
    
    # Display top coins by market cap from CoinMarketCap if available
    if top_market_cap:
        print(f"\n🏆 Piyasa Değerine Göre İlk {len(top_market_cap)} Coin (CoinMarketCap):")
        for i, coin in enumerate(top_market_cap):
            symbol = coin.get('symbol', '')
            name = coin.get('name', '')
            price = coin.get('price', '')
            market_cap = coin.get('market_cap', '')
            price_change = coin.get('price_change_24h', '')
            price_change_sign = "🔴" if price_change and float(price_change) < 0 else "🟢"
            
            # Format with fixed width for better alignment
            print(f"{i+1:2d}. {symbol:9s} | {name:12s} | {price:10s} | {market_cap:14s} | {price_change_sign} {price_change:6s}%")

    # Display top volume coins
    if top_volume:
        print(f"\n📊 24s Hacme Göre İlk {len(top_volume)} Coin (Binance USDT):")
        for i, coin in enumerate(top_volume):
            symbol = coin.get('symbol', '')
            price = coin.get('lastPrice', '')
            price_change = coin.get('priceChangePercent', '')
            volume = coin.get('quoteVolume', '')
            price_change_sign = "🔴" if price_change and float(price_change) < 0 else "🟢"
            
            symbol_raw = symbol.replace("USDT", "")  # For cleaner display
            
            # Format with fixed width for better alignment
            price_str = f"{float(price):.8f}" if price else "N/A"
            # Truncate price string if too long but preserve significant digits
            if len(price_str) > 10:
                price_str = price_str[:10]
            
            volume_str = f"{float(volume):,.2f}" if volume else "N/A"
            price_change_str = f"{float(price_change):.2f}" if price_change else "N/A"
            
            print(f"{i+1:2d}. {symbol_raw:8s} | {price_str:12s} | {volume_str:14s} | {price_change_sign} {price_change_str:6s}%")

    # Display top gainers
    if top_gainers:
        print(f"\n📈 En Çok Yükselenler ({len(top_gainers)}) - 24s (Binance USDT):")
        for i, coin in enumerate(top_gainers):
            symbol = coin.get('symbol', '')
            price = coin.get('lastPrice', '')
            price_change = coin.get('priceChangePercent', '')
            
            symbol_raw = symbol.replace("USDT", "")  # For cleaner display
            
            # Format with fixed width for better alignment
            price_str = f"{float(price):.8f}" if price else "N/A"
            # Truncate price string if too long but preserve significant digits
            if len(price_str) > 10:
                price_str = price_str[:10]
            
            price_change_str = f"{float(price_change):.2f}" if price_change else "N/A"
            
            print(f"{i+1:2d}. {symbol_raw:8s} | {price_str:12s} | 🟢 {price_change_str:6s}%")

    # Display top decliners
    if top_decliners:
        print(f"\n📉 En Çok Düşenler ({len(top_decliners)}) - 24s (Binance USDT):")
        for i, coin in enumerate(top_decliners):
            symbol = coin.get('symbol', '')
            price = coin.get('lastPrice', '')
            price_change = coin.get('priceChangePercent', '')
            
            symbol_raw = symbol.replace("USDT", "")  # For cleaner display
            
            # Format with fixed width for better alignment
            price_str = f"{float(price):.8f}" if price else "N/A"
            # Truncate price string if too long but preserve significant digits
            if len(price_str) > 10:
                price_str = price_str[:10]
            
            price_change_str = f"{float(price_change):.2f}" if price_change else "N/A"
            
            print(f"{i+1:2d}. {symbol_raw:8s} | {price_str:12s} | 🔴 {price_change_str:6s}%")
    
    # Print a note about available options:
    print("\n⚠️ NOT: Yukarıdaki listeler sadece öneridir. Binance borsasında listelenen HERHANGİ bir coini analiz edebilirsiniz.")
    print("     Toplamda 1800+ farklı coin Binance'de USDT paritesi ile işlem görmektedir.")

async def get_and_validate_user_coin_choice(binance_client, all_binance_usdt_symbols, cmc_symbols):
    """
    Get and validate the user's choice of cryptocurrency symbol.
    
    Args:
        binance_client: BinanceClient instance
        all_binance_usdt_symbols: Set of all Binance USDT trading pairs 
        cmc_symbols: List of dictionaries containing CoinMarketCap symbols data
    
    Returns:
        str: Valid symbol for analysis, or None if user chooses to quit
    """
    available_symbols_for_input_check = set(all_binance_usdt_symbols)
    if cmc_symbols:
        available_symbols_for_input_check.update(c['symbol'] for c in cmc_symbols)

    while True:
        selected_symbol_input = input("\n👉 Analiz etmek istediğiniz coinin sembolünü girin (örn: BTC veya BTCUSDT) veya çıkmak için 'q' yazın: ").upper()

        if selected_symbol_input == 'Q':
            logging.info("Programdan çıkılıyor.")
            return None

        # İlk olarak basit bir yöntemle kontrol et (hızlı)
        selected_symbol_for_analysis = ""
        if not selected_symbol_input.endswith("USDT") and (selected_symbol_input + "USDT") in all_binance_usdt_symbols:
            selected_symbol_for_analysis = selected_symbol_input + "USDT"
        elif selected_symbol_input.endswith("USDT") and selected_symbol_input in all_binance_usdt_symbols:
            selected_symbol_for_analysis = selected_symbol_input
        elif cmc_symbols and selected_symbol_input in (c['symbol'] for c in cmc_symbols) and (selected_symbol_input + "USDT") in all_binance_usdt_symbols:
            selected_symbol_for_analysis = selected_symbol_input + "USDT"
        
        # Eğer basit kontrolden geçemediyse, daha kapsamlı kontrol yap
        if not selected_symbol_for_analysis:
            print(f"\n🔍 {selected_symbol_input} Binance'de kontrol ediliyor, lütfen bekleyin...")
            
            try:
                is_valid, valid_symbol = await binance_client.validate_symbol(selected_symbol_input)
                if is_valid:
                    selected_symbol_for_analysis = valid_symbol
                    print(f"✅ {selected_symbol_input} sembolü {valid_symbol} olarak bulundu ve analiz için kullanılacak.")
                else:
                    # Eğer direkt girildiği gibi bulunamadıysa, USDT ekleyerek tekrar dene
                    if not selected_symbol_input.endswith("USDT"):
                        is_valid, valid_symbol = await binance_client.validate_symbol(selected_symbol_input + "USDT")
                        if is_valid:
                            selected_symbol_for_analysis = valid_symbol
                            print(f"✅ {selected_symbol_input} sembolü {valid_symbol} olarak bulundu ve analiz için kullanılacak.")
            except Exception as e:
                logging.error(f"Sembol doğrulama sırasında hata: {e}")
        
        if selected_symbol_for_analysis:
            logging.info(f"Seçilen coin: {selected_symbol_input} -> Analiz edilecek: {selected_symbol_for_analysis}.")
            return selected_symbol_for_analysis
        else:
            print(f"\n⚠️ UYARI: {selected_symbol_input} sembolü Binance'de bulunamadı veya desteklenmiyor.")
            print("Birkaç olası neden:")
            print("1. Sembol adını yanlış yazdınız")
            print("2. Bu coin Binance'de listelenmemiş olabilir")
            print("3. Bu coin USDT paritesi ile değil, başka paritelerle işlem görüyor olabilir (örn: BTC, ETH, BUSD)")
            print("\nLütfen geçerli bir sembol girin veya çıkmak için 'q' yazın.")
            
            logging.warning(f"Geçersiz veya Binance'te bulunamayan sembol girdiniz: {selected_symbol_input}. Lütfen listelerden geçerli bir sembol girin veya 'q' ile çıkın.")

async def main():
    """
    Main function to run the coin scanner bot.
    Initializes clients, fetches market data, presents choices to the user,
    and triggers analysis for the selected coin.
    """

    binance_client = None # Initialize to None for finally block
    analysis_system = None
    try:
        logging.info("Coin Tarayıcı Bot Başlatılıyor...")
        binance_client = BinanceClient() 
        gemini_client = GeminiClient()     
        cmc_client = CoinMarketCapClient() 
        
        cryptopanic_client = None
        if CRYPTOPANIC_API_KEY:
            try:
                cryptopanic_client = CryptoPanicClient(api_key=CRYPTOPANIC_API_KEY)
                logging.info("CryptoPanic istemcisi başarıyla başlatıldı.")
            except ValueError as ve:
                logging.warning(f"CryptoPanic istemcisi başlatılamadı: {ve}. Temel analiz bu oturumda devre dışı kalacak.")
        else:
            logging.info("CRYPTOPANIC_API_KEY bulunamadı, CryptoPanic istemcisi başlatılmayacak.")

        logging.info("İstemciler başarıyla başlatıldı (Binance, Gemini, CMC).")

        # Initialize the modular analysis system
        print("Initializing modular analysis system...")
        try:
            analysis_system = initialize_analysis_system(binance_client, gemini_client, cryptopanic_client)
            print("Successfully initialized modular analysis system")
        except Exception as e:
            print(f"Error initializing analysis system: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            analysis_system = None

        try:
            server_time_data = await binance_client.get_server_time()
            if not server_time_data:
                logging.error("Binance sunucu zamanı alınamadı. Bağlantı testi başarısız.")
                # await binance_client.close() # Erken çıkış durumunda kapat
                return
            logging.info(f"Binance sunucu zamanı: {server_time_data}. Bağlantı başarılı.")
        except Exception as e:
            logging.error(f"Binance bağlantı testi sırasında genel hata: {e}")
            # await binance_client.close() # Erken çıkış durumunda kapat
            return

        while True: # Start of the new loop for continuous analysis
            all_binance_usdt_tickers = await get_all_usdt_tickers_data(binance_client)
            if not all_binance_usdt_tickers:
                logging.error("Binance USDT piyasa verileri alınamadığı için devam edilemiyor.")
                # Consider if we should break the loop or just skip this iteration
                await asyncio.sleep(60) # Wait a bit before retrying or exiting
                continue # Or break, depending on desired behavior for critical data failure

            top_market_cap_coins = fetch_and_format_cmc_top_coins(cmc_client, CMC_TOP_N_MARKET_CAP)
            
            top_volume_coins = get_top_n_by_volume(all_binance_usdt_tickers, DEFAULT_TOP_N)
            top_gainer_coins = get_top_n_gainers(all_binance_usdt_tickers, DEFAULT_TOP_N)
            top_decliner_coins = get_top_n_decliners(all_binance_usdt_tickers, DEFAULT_TOP_N)

            display_coin_selection_lists(
                top_market_cap_coins, 
                top_volume_coins, 
                top_gainer_coins, 
                top_decliner_coins,
                DEFAULT_TOP_N
            )
            
            all_binance_usdt_symbols_set = {t['symbol'] for t in all_binance_usdt_tickers}
            
            selected_symbol_for_analysis = await get_and_validate_user_coin_choice(
                binance_client,
                all_binance_usdt_symbols_set,
                top_market_cap_coins
            )

            if not selected_symbol_for_analysis:
                logging.info("Analiz için geçerli bir sembol seçilmedi veya kullanıcı çıkış yaptı. Program sonlandırılıyor.")
                break # Exit the while loop if user chose to quit or no valid symbol

            # Display available analysis modules and let user select one
            available_modules = analysis_system.list_available_modules()
            print("\n--- Analiz Modülleri ---")
            print(f"{'No.':<4} {'Modül Adı':<25} {'Açıklama':<50}")
            
            for i, module in enumerate(available_modules):
                print(f"{i+1:<3d}. {module['name']:<25} {module['description']:<50}")
            
            # Get user's module selection
            module_selection = input("\n👉 Kullanmak istediğiniz analiz modülünün numarasını girin (varsayılan: 1): ").strip()
            
            selected_module = "crypto_analysis"  # Default module
            if module_selection:
                try:
                    selection_index = int(module_selection) - 1
                    if 0 <= selection_index < len(available_modules):
                        selected_module = available_modules[selection_index]['name']
                    else:
                        logging.warning(f"Geçersiz modül numarası. Varsayılan modül kullanılacak: {selected_module}")
                except ValueError:
                    logging.warning(f"Geçersiz giriş. Varsayılan modül kullanılacak: {selected_module}")
            
            logging.info(f"Detaylı analiz başlatılıyor: {selected_symbol_for_analysis} (Modül: {selected_module})...")
            
            btc_trend_summary_text = await get_bitcoin_trend_summary(binance_client)
            
            # Perform analysis using the selected module
            if selected_module == "crypto_analysis":
                # Use existing analyze_coin function for backward compatibility
                analysis_result = await analyze_coin(
                    binance_client, 
                    gemini_client, 
                    cryptopanic_client,
                    selected_symbol_for_analysis, 
                    btc_trend_summary_text
                )
            else:
                # Use the new modular analysis system for other modules
                analysis_result = await analysis_system.analyze(
                    selected_module,
                    selected_symbol_for_analysis,
                    btc_trend_summary=btc_trend_summary_text
                )
            
            # Display analysis result
            print("\n" + "="*80)
            print(f"{selected_symbol_for_analysis} ANALİZ SONUCU (Modül: {selected_module})")
            print("="*80 + "\n")
            print(analysis_result)
            
            # Save analysis result to file
            output_dir = "analysis_results"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"{selected_symbol_for_analysis}_{selected_module}_{timestamp}.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(analysis_result)
            
            logging.info(f"{selected_symbol_for_analysis} analizi tamamlandı ve {output_file} dosyasına kaydedildi.")

            # Ask user if they want to analyze another coin
            user_choice = input("\nBaşka bir coin analiz etmek ister misiniz? (E/Evet veya H/Hayır): ").strip().upper()
            if user_choice in ['H', 'HAYIR', 'N', 'NO']:
                logging.info("Kullanıcı başka analiz istemedi. Program sonlandırılıyor.")
                break # Exit the while loop
            elif user_choice not in ['E', 'EVET', 'Y', 'YES']:
                logging.info("Geçersiz giriş. Varsayılan olarak devam ediliyor...") 
                # Optionally, you can be stricter and break or ask again.
                # For now, any input other than 'H' or 'N' (and their variants) will continue.
            else: # Added to explicitly handle 'E' or 'EVET' for clarity
                logging.info("Kullanıcı yeni bir analiz istedi. Döngü devam ediyor...")

    except ValueError as ve:
        logging.error(f"Program Kurulum Hatası: {ve}")
        logging.exception("Kurulum sırasında bir ValueError oluştu:")
    except BinanceAPIException as bae:
        logging.error(f"Binance API Hatası: {bae}")
        logging.exception("Ana akışta bir Binance API istisnası oluştu:")
    except Exception as e:
        logging.error(f"Ana programda genel bir hata oluştu: {e}")
        logging.error(f"Hata tipi: {type(e).__name__}")
        logging.error(traceback.format_exc())
        logging.exception("Ana programda beklenmedik bir istisna oluştu:")
    finally:
        if binance_client: # Ensure client exists before trying to close
            await binance_client.close()
            logging.info("Binance istemcisi ana program sonunda kapatıldı.")

if __name__ == "__main__":
    asyncio.run(main()) 