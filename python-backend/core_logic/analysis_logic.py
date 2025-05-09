import logging
import pandas as pd # Though not directly used, imported by utils that are called.
import pandas_ta as ta # Same as above
from datetime import datetime
from typing import Optional, Dict
import os
import json
import asyncio

# Adjust import paths for utils and constants
from utils.general_utils import (
    format_indicator_value, preprocess_klines_df, 
    calculate_technical_indicators, extract_latest_indicators, 
    extract_price_summary_data
)
from utils.volume_analysis import compare_volume_across_timeframes

from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from fundamental_analysis.cryptopanic_client import CryptoPanicClient
from config import EXCHANGE_API_KEY, EXCHANGE_API_SECRET, LLM_API_KEY, CRYPTOPANIC_API_KEY

from .constants import (
    KLINE_INTERVAL, KLINE_HISTORY_PERIOD, KLINE_INTERVAL_MAP, TARGET_KLINE_INTERVALS, 
    RSI_PERIOD, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD, 
    SMA_SHORT_PERIOD, SMA_LONG_PERIOD, DEFAULT_KLINE_LIMIT, RECENT_SR_CANDLE_COUNT, BBANDS_LENGTH, BBANDS_STD,
    EMA_SHORT_PERIOD, EMA_LONG_PERIOD, ATR_PERIOD, FIB_LOOKBACK_PERIOD
)

# Functions in this module are responsible for performing calculations, technical analysis,
# and formatting data specifically for the LLM.

def build_bitcoin_trend_summary_string(symbol, current_ticker_data, latest_indicators):
    """Builds the Bitcoin trend summary string using ticker data and latest indicators."""
    logging.debug(f"Building Bitcoin trend summary for {symbol}. Received latest_indicators: {latest_indicators}")
    current_price_str = current_ticker_data.get('lastPrice', 'N/A')
    current_price_val = float(current_price_str) if current_price_str != 'N/A' and current_price_str is not None else None
    price_change_percent_str = current_ticker_data.get('priceChangePercent', 'N/A')

    summary = f"Bitcoin ({symbol}) Güncel Durum Özeti:\\n"
    summary += f"  Mevcut Fiyat: {format_indicator_value(current_price_str, 2)} USDT (24s Değişim: %{format_indicator_value(price_change_percent_str, 2)})\\n"
    
    rsi_val = latest_indicators.get('rsi')
    summary += f"  RSI({RSI_PERIOD}): {format_indicator_value(rsi_val)}\\n"

    # SMA değerlerini f-string anahtarlarıyla al ve formatla
    latest_sma_short_key = f'sma_{SMA_SHORT_PERIOD}'
    latest_sma_long_key = f'sma_{SMA_LONG_PERIOD}'

    latest_sma_short_val_raw = latest_indicators.get(latest_sma_short_key)
    latest_sma_long_val_raw = latest_indicators.get(latest_sma_long_key)

    latest_sma_short_val_str = format_indicator_value(latest_sma_short_val_raw)
    latest_sma_long_val_str = format_indicator_value(latest_sma_long_val_raw)
    
    logging.debug(f"BTC Summary: current_price_val={current_price_val}, sma_short_val_raw ({latest_sma_short_key})={latest_sma_short_val_raw}, sma_long_val_raw ({latest_sma_long_key})={latest_sma_long_val_raw}")

    sma_short_relation = "bilinmiyor"
    if current_price_val is not None and latest_sma_short_val_raw is not None and not isinstance(latest_sma_short_val_raw, str):
        if current_price_val > latest_sma_short_val_raw: sma_short_relation = "üzerinde"
        elif current_price_val < latest_sma_short_val_raw: sma_short_relation = "altında"
        else: sma_short_relation = "eşit"
    summary += f"  Fiyat vs SMA{SMA_SHORT_PERIOD} ({latest_sma_short_val_str}): Fiyat {sma_short_relation}\\n"

    sma_long_relation = "bilinmiyor"
    if current_price_val is not None and latest_sma_long_val_raw is not None and not isinstance(latest_sma_long_val_raw, str):
        if current_price_val > latest_sma_long_val_raw: sma_long_relation = "üzerinde"
        elif current_price_val < latest_sma_long_val_raw: sma_long_relation = "altında"
        else: sma_long_relation = "eşit"
    summary += f"  Fiyat vs SMA{SMA_LONG_PERIOD} ({latest_sma_long_val_str}): Fiyat {sma_long_relation}\\n"
    
    latest_macd_val_raw = latest_indicators.get('macd')
    latest_macd_signal_val_raw = latest_indicators.get('macd_signal')

    latest_macd_val_str = format_indicator_value(latest_macd_val_raw)
    latest_macd_signal_val_str = format_indicator_value(latest_macd_signal_val_raw)

    macd_relation = "bilinmiyor"
    if latest_macd_val_raw is not None and latest_macd_signal_val_raw is not None and \
       not isinstance(latest_macd_val_raw, str) and not isinstance(latest_macd_signal_val_raw, str):
        if latest_macd_val_raw > latest_macd_signal_val_raw: macd_relation = "üzerinde"
        elif latest_macd_val_raw < latest_macd_signal_val_raw: macd_relation = "altında"
        else: macd_relation = "eşit"
    summary += f"  MACD Çizgisi ({latest_macd_val_str}) vs Sinyal Çizgisi ({latest_macd_signal_val_str}): MACD {macd_relation}\\n"
    return summary

async def get_bitcoin_trend_summary(binance_cli):
    logging.info("--- Bitcoin (BTCUSDT) Trend Özeti Alınıyor ---")
    symbol = "BTCUSDT"
    # For BTC summary, we use the primary KLINE_INTERVAL from constants for now.
    # This could be expanded to multi-timeframe in the future if needed.
    primary_btc_interval = KLINE_INTERVAL 
    try:
        # Use get_klines which is the async method in BinanceClient now
        klines = await binance_cli.get_klines(
            symbol,
            primary_btc_interval, # Using the single primary interval for BTC summary
            limit=500 # Explicitly request 500 candles for reliable indicator calculations
            # KLINE_HISTORY_PERIOD is not directly used by get_klines, limit is used.
            # Assuming DEFAULT_KLINE_LIMIT from config is used by get_klines by default if not specified
            # For consistency, if KLINE_HISTORY_PERIOD implied a certain number of klines, ensure limit reflects that.
            # However, the current get_klines takes `limit`. We should rely on a limit that ensures enough data (e.g., 500, or DEFAULT_KLINE_LIMIT from config)
        )
        if not klines or len(klines) < 50:
            logging.warning(f"{symbol} için trend özeti oluşturacak yeterli mum verisi (en az 50) bulunamadı.")
            return "Bitcoin (BTCUSDT) trend verisi şu anda alınamıyor."

        current_ticker_data = await binance_cli.client.get_ticker(symbol=symbol)

        df = preprocess_klines_df(klines)
        df_with_indicators = calculate_technical_indicators(df)
        latest_indicators = extract_latest_indicators(df_with_indicators)
        
        summary = build_bitcoin_trend_summary_string(symbol, current_ticker_data, latest_indicators)
        
        logging.info(f"Bitcoin Trend Özeti:\n{summary}")
        return summary

    except Exception as e:
        logging.error(f"Bitcoin (BTCUSDT) trend özeti alınırken hata oluştu: {e}")
        logging.exception("Bitcoin trend özeti alınırken bir istisna oluştu:")
        return "Bitcoin (BTCUSDT) trend verisi alınırken bir hata oluştu."

def format_price_data_for_llm(symbol, klines_by_interval, current_ticker_details, is_historical: bool = False, historical_timestamp_ms: Optional[int] = None):
    """Formats price data from multiple kline intervals for the LLM.
    Handles both live and historical data analysis."""
    
    processed_data_by_interval = {}
    has_any_valid_data = False
    header_price_info = {}
    timeframe_dfs = {} # Store processed DataFrames for cross-timeframe volume analysis

    if is_historical:
        logging.info(f"Geçmişe yönelik formatlama ({symbol} @ {historical_timestamp_ms})")
        # For historical, find the latest kline across all intervals to determine the "current price at that time"
        # This assumes klines are sorted oldest to newest, and we want the one closest to historical_timestamp_ms
        latest_close_price_historical = None
        latest_kline_time_historical = 0

        for interval_code, klines in klines_by_interval.items():
            if klines and len(klines) > 0:
                # Filter klines that are at or before the historical_timestamp_ms
                # kline[0] is open_time, kline[6] is close_time
                # We are interested in klines whose *open_time* is <= historical_timestamp_ms
                # And we want the *last* such kline.
                # Assuming klines are [open_time, open, high, low, close, ...]
                # And sorted by open_time ascendingly by the caller (e.g. get_historical_klines)
                valid_historical_klines = [k for k in klines if k[0] <= historical_timestamp_ms]
                if valid_historical_klines:
                    last_valid_kline = valid_historical_klines[-1] # Last kline at or before the target time
                    if last_valid_kline[0] > latest_kline_time_historical: # If this kline is later than others found so far
                        latest_kline_time_historical = last_valid_kline[0]
                        try:
                            latest_close_price_historical = float(last_valid_kline[4]) # Close price
                        except (ValueError, TypeError):
                            logging.warning(f"Geçmiş kline kapanış fiyatı ({last_valid_kline[4]}) float'a çevrilemedi.")
                            latest_close_price_historical = "N/A"
        
        header_price_info = {
            'current_price': latest_close_price_historical if latest_close_price_historical is not None else 'N/A',
            'price_change_percent': 'Geçmiş analiz için 24s değişim geçerli değil.',
            'data_timestamp_iso': datetime.fromtimestamp(historical_timestamp_ms / 1000).isoformat() if historical_timestamp_ms else 'N/A'
        }
        logging.info(f"Geçmiş analiz için başlık fiyat bilgisi: {header_price_info}")

    else: # Live analysis
        header_price_info = {
            'current_price': current_ticker_details.get('lastPrice', 'N/A'),
            'price_change_percent': current_ticker_details.get('priceChangePercent', 'N/A'),
            'data_timestamp_iso': datetime.now().isoformat() # For live data, it's current
        }

    for interval_code, klines in klines_by_interval.items():
        interval_str = KLINE_INTERVAL_MAP.get(interval_code, interval_code)
        
        # For historical, filter klines up to the historical_timestamp_ms for each interval before processing
        actual_klines_to_process = klines
        if is_historical and historical_timestamp_ms:
            actual_klines_to_process = [k for k in klines if k[0] <= historical_timestamp_ms]
            # Ensure we have enough klines *after* filtering for the historical date
            if len(actual_klines_to_process) > DEFAULT_KLINE_LIMIT:
                 # Take the last DEFAULT_KLINE_LIMIT klines ending at or before historical_timestamp_ms
                actual_klines_to_process = actual_klines_to_process[-DEFAULT_KLINE_LIMIT:]

        if not actual_klines_to_process or len(actual_klines_to_process) < 50:
            logging.warning(f"{symbol} için {interval_str} zaman aralığında (hedef tarih: {header_price_info.get('data_timestamp_iso', 'N/A')}) yeterli veri yok (en az 50 mum gerekli), atlanıyor.")
            processed_data_by_interval[interval_code] = {'error': f"{interval_str} için yeterli veri yok (en az 50 mum gerekli)."}
            continue

        try:
            df = preprocess_klines_df(actual_klines_to_process)
            df_with_indicators = calculate_technical_indicators(df)
            latest_indicators = extract_latest_indicators(df_with_indicators)
            price_summary = extract_price_summary_data(df_with_indicators, None) 
            
            processed_data_by_interval[interval_code] = {
                'price_summary': price_summary,
                'latest_indicators': latest_indicators
            }
            
            # Store processed DataFrame for cross-timeframe volume analysis
            timeframe_dfs[interval_str] = df_with_indicators
            
            has_any_valid_data = True
            logging.info(f"{symbol} için {interval_str} verisi ({('Geçmiş: ' + header_price_info.get('data_timestamp_iso','')) if is_historical else 'Canlı'}) başarıyla işlendi.")
        except Exception as e:
            logging.error(f"{symbol} için {interval_str} verisi işlenirken hata ({('Geçmiş: ' + header_price_info.get('data_timestamp_iso','')) if is_historical else 'Canlı'}): {e}")
            processed_data_by_interval[interval_code] = {'error': f"{interval_str} verisi işlenirken hata: {e}"}

    if not has_any_valid_data:
        return f"{symbol} için analiz edilebilir veri bulunamadı ({('Geçmiş: ' + header_price_info.get('data_timestamp_iso','')) if is_historical else 'Canlı'})."
    
    # Perform cross-timeframe volume analysis if we have data for multiple timeframes
    cross_timeframe_volume_data = None
    if len(timeframe_dfs) > 1:
        try:
            cross_timeframe_volume_data = compare_volume_across_timeframes(timeframe_dfs)
            logging.info(f"Cross-timeframe volume analysis completed: {cross_timeframe_volume_data}")
        except Exception as e:
            logging.error(f"Error performing cross-timeframe volume analysis: {e}")
    
    prompt_data_str = build_multi_timeframe_llm_prompt_data_string(
        symbol, 
        processed_data_by_interval, 
        header_price_info, # Use the determined header_price_info
        is_historical=is_historical,
        cross_timeframe_volume_data=cross_timeframe_volume_data
    )
    
    return prompt_data_str 

def build_multi_timeframe_llm_prompt_data_string(symbol, processed_data_by_interval, header_price_info, 
                                               is_historical: bool = False, cross_timeframe_volume_data: Optional[Dict] = None):
    """Builds the formatted string data for the LLM prompt from multiple timeframes."""
    prompt_data = f"Coin Sembolü: {symbol}\n"
    data_source_time_info = f"(Veri Zaman Damgası: {header_price_info.get('data_timestamp_iso')})" if is_historical else "(Canlı Veri)"
    
    prompt_data += f"Fiyat Bilgisi {data_source_time_info}: {format_indicator_value(header_price_info.get('current_price'), 2)} USDT\n"
    if not is_historical:
        prompt_data += f"Son 24 Saatlik Değişim: %{format_indicator_value(header_price_info.get('price_change_percent'), 2)}\n\n"
    else:
        prompt_data += f"Son 24 Saatlik Değişim: {header_price_info.get('price_change_percent')}\n\n" # This will be 'Geçmiş analiz için 24s değişim geçerli değil.'

    # Add cross-timeframe volume comparison if available
    if cross_timeframe_volume_data and len(cross_timeframe_volume_data) > 1:
        prompt_data += "## Farklı Zaman Dilimlerindeki Hacim Karşılaştırması:\n"
        
        # Create a table header for better readability
        prompt_data += "| Zaman Dilimi | Hacim Trendi | Trend Değişim (%) | Güncel Hacim | MA(20) | Güncel/MA(%) | Normalize |\n"
        prompt_data += "|--------------|--------------|-------------------|--------------|--------|--------------|----------|\n"
        
        # Sort timeframes from shortest to longest
        sorted_timeframes = sorted(cross_timeframe_volume_data.keys(), key=lambda x: {
            '15m': 1, '1h': 2, '4h': 3, '1d': 4
        }.get(x, 999))
        
        for timeframe in sorted_timeframes:
            data = cross_timeframe_volume_data[timeframe]
            
            # Convert volume trend to Turkish
            trend_str = {
                "increasing": "Artıyor",
                "decreasing": "Azalıyor", 
                "flat": "Yatay",
                "insufficient_data": "Veri Yetersiz"
            }.get(data.get('volume_trend', 'N/A'), 'N/A')
            
            # Format data values
            trend_pct = format_indicator_value(data.get('trend_pct_change'), 2)
            current_vol = format_indicator_value(data.get('current_volume'), 0)
            ma_20 = format_indicator_value(data.get('volume_ma_20'), 0)
            current_vs_ma = format_indicator_value(data.get('current_vs_ma'), 2)
            normalized = format_indicator_value(data.get('normalized_volume'), 2)
            
            # Build table row
            prompt_data += f"| {timeframe} | {trend_str} | {trend_pct}% | {current_vol} | {ma_20} | {current_vs_ma}% | {normalized} |\n"
        
        # Add interpretation
        prompt_data += "\n**Zaman Dilimleri Arası Hacim Yorumu:**\n"
        
        # Check if there's consistent direction across timeframes
        trends = [data.get('volume_trend') for data in cross_timeframe_volume_data.values() 
                  if data.get('volume_trend') not in ['insufficient_data', None]]
        
        if all(trend == 'increasing' for trend in trends if trend):
            prompt_data += "- Tüm zaman dilimlerinde hacim artış eğiliminde, bu güçlü bir alım baskısı göstergesi olabilir.\n"
        elif all(trend == 'decreasing' for trend in trends if trend):
            prompt_data += "- Tüm zaman dilimlerinde hacim azalış eğiliminde, bu ilginin azaldığının göstergesi olabilir.\n"
        else:
            prompt_data += "- Farklı zaman dilimlerinde hacim trendi değişkenlik gösteriyor.\n"
            
            # Check if shorter timeframes show more activity than longer ones
            shorter_tfs = sorted_timeframes[:len(sorted_timeframes)//2]
            longer_tfs = sorted_timeframes[len(sorted_timeframes)//2:]
            
            if shorter_tfs and longer_tfs:
                shorter_increasing = any(cross_timeframe_volume_data[tf].get('volume_trend') == 'increasing' for tf in shorter_tfs)
                longer_flat_or_decreasing = all(cross_timeframe_volume_data[tf].get('volume_trend') in ['flat', 'decreasing'] 
                                          for tf in longer_tfs if cross_timeframe_volume_data[tf].get('volume_trend'))
                
                if shorter_increasing and longer_flat_or_decreasing:
                    prompt_data += "- Kısa vadeli zaman dilimlerinde hacim artışı, uzun vadede ise düşüş/stabilite görülüyor. Bu, yeni başlayan bir trend değişimi işareti olabilir.\n"
        
        # Compare current volume to moving averages across timeframes
        above_ma_count = sum(1 for data in cross_timeframe_volume_data.values() 
                           if data.get('current_vs_ma') and data.get('current_vs_ma') > 100)
        below_ma_count = sum(1 for data in cross_timeframe_volume_data.values() 
                           if data.get('current_vs_ma') and data.get('current_vs_ma') < 100)
        
        total_valid = above_ma_count + below_ma_count
        if total_valid > 0:
            if above_ma_count > below_ma_count:
                prompt_data += f"- Çoğu zaman diliminde ({above_ma_count}/{total_valid}) güncel hacim, ortalamanın üzerinde seyrediyor.\n"
            elif below_ma_count > above_ma_count:
                prompt_data += f"- Çoğu zaman diliminde ({below_ma_count}/{total_valid}) güncel hacim, ortalamanın altında seyrediyor.\n"
            
        prompt_data += "\n"
    
    prompt_data += "# Çoklu Zaman Dilimi Analizi (Geçmiş Veri ve İndikatörler):\n"
    prompt_data += f"(Not: Analiz için her zaman diliminden {DEFAULT_KLINE_LIMIT} mum çubuğu kullanılmıştır.)\n\n"

    for interval_code, data in processed_data_by_interval.items():
        interval_str = KLINE_INTERVAL_MAP.get(interval_code, interval_code)
        if data.get('error'):
            prompt_data += f"--- Zaman Dilimi: {interval_str} ---\n"
            prompt_data += f"  Durum: {data['error']}\n\n"
            continue

        price_summary = data['price_summary']
        latest_indicators = data['latest_indicators']
        
        prompt_data += f"--- Zaman Dilimi: {interval_str} ---\n"
        prompt_data += f"  Bu Periyottaki En Yüksek Fiyat (Son {DEFAULT_KLINE_LIMIT} Mum): {format_indicator_value(price_summary['highest_price_period'], 2)} USDT\n"
        prompt_data += f"  Bu Periyottaki En Düşük Fiyat (Son {DEFAULT_KLINE_LIMIT} Mum): {format_indicator_value(price_summary['lowest_price_period'], 2)} USDT\n"
        prompt_data += f"  Son {RECENT_SR_CANDLE_COUNT} Mumun En Yüksek Fiyatı: {format_indicator_value(price_summary['recent_high_last_N'], 2)} USDT\n"
        prompt_data += f"  Son {RECENT_SR_CANDLE_COUNT} Mumun En Düşük Fiyatı: {format_indicator_value(price_summary['recent_low_last_N'], 2)} USDT\n"
        prompt_data += f"  Son 5 Kapanış Fiyatı (en sondan başlayarak): {price_summary['last_n_closes'][::-1]}\n"
        prompt_data += f"  Teknik İndikatörler (Son Değerler):\n"
        prompt_data += f"    RSI({RSI_PERIOD}): {format_indicator_value(latest_indicators.get('rsi'))}\n"
        rsi_divergence_status = latest_indicators.get('rsi_divergence', 'N/A') # Get divergence status
        if rsi_divergence_status and rsi_divergence_status not in ["None", "N/A", "Data Missing", "Not Enough Data", "RSI/Price Invalid"]:
            prompt_data += f"    RSI Uyumsuzluk: {rsi_divergence_status}\n"
        prompt_data += f"    SMA({SMA_SHORT_PERIOD}): {format_indicator_value(latest_indicators.get(f'sma_{SMA_SHORT_PERIOD}'), 2)} USDT\n"
        prompt_data += f"    SMA({SMA_LONG_PERIOD}): {format_indicator_value(latest_indicators.get(f'sma_{SMA_LONG_PERIOD}'), 2)} USDT\n"
        prompt_data += f"    EMA({EMA_SHORT_PERIOD}): {format_indicator_value(latest_indicators.get(f'ema_{EMA_SHORT_PERIOD}'), 2)} USDT\n"
        prompt_data += f"    EMA({EMA_LONG_PERIOD}): {format_indicator_value(latest_indicators.get(f'ema_{EMA_LONG_PERIOD}'), 2)} USDT\n"
        prompt_data += f"    ATR({ATR_PERIOD}): {format_indicator_value(latest_indicators.get(f'atr_{ATR_PERIOD}'), 4)} (Volatilite Göstergesi)\n"
        prompt_data += f"    MACD({MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}): {format_indicator_value(latest_indicators.get('macd'))}\n"
        prompt_data += f"    MACD Sinyal: {format_indicator_value(latest_indicators.get('macd_signal'))}\n"
        
        # --- GELIŞMIŞ HACIM ANALIZI BÖLÜMÜ ---
        prompt_data += f"    Hacim İndikatörleri:\n"
        # Temel hacim değeri
        prompt_data += f"      Güncel Hacim: {format_indicator_value(latest_indicators.get('volume'), 0)}\n"
        
        # Hacim trendi
        volume_trend = latest_indicators.get('volume_trend')
        volume_trend_pct = latest_indicators.get('volume_trend_pct_change')
        if volume_trend and volume_trend not in ["insufficient_data", "error", "None", "N/A"]:
            trend_str = {
                "increasing": "Artıyor",
                "decreasing": "Azalıyor",
                "flat": "Yatay"
            }.get(volume_trend, volume_trend)
            prompt_data += f"      Hacim Trendi (Son 10 Mum): {trend_str} (%{format_indicator_value(volume_trend_pct, 2)} değişim)\n"
        
        # Hacim hareketli ortalamaları
        for period in [20, 50, 100]:
            ma_key = f'volume_ma_{period}'
            vs_ma_key = f'volume_vs_ma_{period}'
            ma_value = latest_indicators.get(ma_key)
            vs_ma_value = latest_indicators.get(vs_ma_key)
            
            if ma_value is not None and vs_ma_value is not None:
                prompt_data += f"      Hacim MA({period}): {format_indicator_value(ma_value, 0)} "
                prompt_data += f"(Güncel Hacim: MA'nın %{format_indicator_value(vs_ma_value, 2)} seviyesinde)\n"
        
        # Fiyat-hacim ilişkisi
        pv_correlation = latest_indicators.get('pv_correlation')
        pv_interpretation = latest_indicators.get('pv_interpretation')
        pv_strength = latest_indicators.get('pv_strength')
        pv_is_confirming = latest_indicators.get('pv_is_confirming')
        
        if pv_interpretation and pv_interpretation not in ["insufficient_data", "error", "unknown", "None", "N/A"]:
            prompt_data += f"      Fiyat-Hacim İlişkisi:\n"
            
            # Korelasyon yorumu
            correlation_str = f"Korelasyon: {format_indicator_value(pv_correlation, 2)}"
            if pv_strength:
                strength_str = {
                    "weak": "zayıf",
                    "moderate": "orta",
                    "strong": "güçlü"
                }.get(pv_strength, pv_strength)
                correlation_str += f" ({strength_str})"
            prompt_data += f"        {correlation_str}\n"
            
            # Yorum
            interpretation_str = {
                "healthy_trend": "Sağlıklı trend (Hacim, fiyat hareketlerini destekliyor)",
                "potential_trend_reversal": "Potansiyel trend dönüşü (Hacim, fiyat hareketlerini desteklemiyor)",
                "inconsistent_confirmation": "Tutarsız onaylama (Hacim bazen fiyat hareketlerini destekliyor)",
                "indecisive_market": "Kararsız piyasa (Hacim ile fiyat arasında belirgin bir ilişki yok)"
            }.get(pv_interpretation, pv_interpretation)
            prompt_data += f"        Yorum: {interpretation_str}\n"
            
            # Yükseliş/düşüş hacmi karşılaştırması
            confirming_str = "Evet" if pv_is_confirming else "Hayır"
            prompt_data += f"        Hacim Fiyat Yönünü Onaylıyor mu: {confirming_str}\n"
        
        # Hacim anomalileri
        va_detected = latest_indicators.get('volume_anomaly_detected')
        va_type = latest_indicators.get('volume_anomaly_type')
        va_z_score = latest_indicators.get('volume_anomaly_z_score')
        va_deviation_pct = latest_indicators.get('volume_anomaly_deviation_pct')
        
        if va_detected is not None and va_detected is not False and va_type not in ["none", "None", "N/A"]:
            prompt_data += f"      Hacim Anomalisi:\n"
            type_str = "Ani yükseliş" if va_type == "spike" else "Ani düşüş" if va_type == "drop" else va_type
            prompt_data += f"        Tip: {type_str}\n"
            
            if va_z_score is not None:
                prompt_data += f"        Z-skor: {format_indicator_value(va_z_score, 2)}\n"
                
            if va_deviation_pct is not None:
                deviation_dir = "üzerinde" if va_deviation_pct > 0 else "altında"
                prompt_data += f"        Sapma: Normal hacmin %{format_indicator_value(abs(va_deviation_pct), 2)} {deviation_dir}\n"
              
        # Bollinger Bantları
        bb_lower = latest_indicators.get('bb_lower')
        bb_middle = latest_indicators.get('bb_middle')
        bb_upper = latest_indicators.get('bb_upper')
        
        if bb_lower is not None and bb_middle is not None and bb_upper is not None:
            prompt_data += f"    Bollinger Bantları ({BBANDS_LENGTH}, {BBANDS_STD}):\n"
            prompt_data += f"      Alt Bant: {format_indicator_value(bb_lower, 2)}\n"
            prompt_data += f"      Orta Bant: {format_indicator_value(bb_middle, 2)}\n"
            prompt_data += f"      Üst Bant: {format_indicator_value(bb_upper, 2)}\n"
            
            # Son fiyatın bantlara göre konumu
            current_price = float(header_price_info.get('current_price', 0)) if header_price_info.get('current_price') != 'N/A' else None
            if current_price is not None:
                if current_price > bb_upper:
                    prompt_data += f"      Konum: Fiyat üst bandın üzerinde (aşırı alım bölgesi)\n"
                elif current_price < bb_lower:
                    prompt_data += f"      Konum: Fiyat alt bandın altında (aşırı satım bölgesi)\n"
                else:
                    prompt_data += f"      Konum: Fiyat bantlar arasında\n"

        # Fibonacci Seviyeleri
        fib_levels_str = latest_indicators.get('fib_levels')
        fib_high = latest_indicators.get('fib_high')
        fib_low = latest_indicators.get('fib_low')
        
        if fib_high is not None and fib_low is not None and fib_high != fib_low:
            prompt_data += f"    Fibonacci Düzeltme Seviyeleri (Son {FIB_LOOKBACK_PERIOD} muma dayanarak):\n"
            prompt_data += f"      Kullanılan Yüksek: {format_indicator_value(fib_high, 2)} USDT\n"
            prompt_data += f"      Kullanılan Düşük: {format_indicator_value(fib_low, 2)} USDT\n"
            
            if fib_levels_str:
                try:
                    import json
                    fib_levels = json.loads(fib_levels_str)
                    for level_name, level_value in fib_levels.items():
                        if level_name not in ['0.0%', '100.0%']:  # Zaten Yüksek/Düşük olarak gösterdik
                            prompt_data += f"      {level_name}: {format_indicator_value(level_value, 2)} USDT\n"
                except:
                    prompt_data += f"      Fibonacci Seviyelerini Okurken Hata!\n"
        
        # Ekstra Destek Direnç / Pivot Seviyeleri
        pivot_fields = ['pivot_p', 'pivot_r1', 'pivot_r2', 'pivot_r3', 'pivot_s1', 'pivot_s2', 'pivot_s3']
        has_pivot_data = any(latest_indicators.get(field) is not None for field in pivot_fields)
        
        if has_pivot_data:
            prompt_data += f"    Pivot Seviyeleri (Fibonacci tabanlı):\n"
            pivot_titles = {
                'pivot_p': 'Pivot Noktası', 
                'pivot_r1': 'Direnç 1', 
                'pivot_r2': 'Direnç 2',
                'pivot_r3': 'Direnç 3',
                'pivot_s1': 'Destek 1',
                'pivot_s2': 'Destek 2', 
                'pivot_s3': 'Destek 3'
            }
            
            # Seviyeleri sırayla yan yana göster:
            # Önce P, sonra S1,S2,S3 sonra R1,R2,R3 (yükselen fiyat sırasıyla)
            for field in ['pivot_s3', 'pivot_s2', 'pivot_s1', 'pivot_p', 'pivot_r1', 'pivot_r2', 'pivot_r3']:
                pivot_value = latest_indicators.get(field)
                if pivot_value is not None:
                    prompt_data += f"      {pivot_titles.get(field)}: {format_indicator_value(pivot_value, 2)} USDT\n"
        
        prompt_data += "\n"  # Extra newline for readability between timeframes
    
    return prompt_data

async def perform_analysis(coin_symbol: str) -> str:
    """
    Wrapper function for analyze_coin in main.py for use by the Telegram bot.
    
    Args:
        coin_symbol: The cryptocurrency symbol to analyze (e.g., 'BTCUSDT')
        
    Returns:
        str: Analysis result as text
    """
    logging.info(f"[perform_analysis] Starting analysis for {coin_symbol}")
    
    try:
        # Initialize clients - all clients read their API keys from config.py
        binance_client = BinanceClient()
        llm_client = GeminiClient()
        
        # Initialize CryptoPanicClient if API key is available
        cryptopanic_client = None
        if CRYPTOPANIC_API_KEY:
            cryptopanic_client = CryptoPanicClient(CRYPTOPANIC_API_KEY)
        
        # Get Bitcoin trend summary for context (needed by analyze_coin)
        from main import get_bitcoin_trend_summary
        btc_trend_summary = await get_bitcoin_trend_summary(binance_client)
        
        # Call the analyze_coin function from main.py
        from main import analyze_coin
        analysis_result = await analyze_coin(
            binance_client, 
            llm_client, 
            cryptopanic_client, 
            coin_symbol, 
            btc_trend_summary
        )
        
        return analysis_result
    
    except Exception as e:
        error_message = f"Error in perform_analysis for {coin_symbol}: {str(e)}"
        logging.error(error_message)
        logging.exception("Exception details:")
        return f"❌ Analysis failed: {error_message}"