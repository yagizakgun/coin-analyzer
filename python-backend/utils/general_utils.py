import pandas as pd
import pandas_ta as ta
import logging
# Constants will be imported from core_logic.constants after it's moved
# from constants import KLINES_COLUMNS, NUMERIC_KLINES_COLUMNS
from core_logic.constants import (
    KLINES_COLUMNS, NUMERIC_KLINES_COLUMNS,
    RSI_PERIOD, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD,
    SMA_SHORT_PERIOD, SMA_LONG_PERIOD, EMA_SHORT_PERIOD, EMA_LONG_PERIOD, ATR_PERIOD,
    RECENT_SR_CANDLE_COUNT, BBANDS_LENGTH, BBANDS_STD, FIB_LOOKBACK_PERIOD
)
# Import volume analysis functions
from utils.volume_analysis import (
    calculate_volume_trend,
    calculate_volume_moving_averages,
    analyze_price_volume_relationship,
    detect_volume_anomalies
)

logger = logging.getLogger(__name__)

def calculate_fibonacci_pivot_points(high, low, close):
    """Calculates Fibonacci pivot points (P, S1, R1, S2, R2, S3, R3)."""
    if pd.isna(high) or pd.isna(low) or pd.isna(close):
        return {'P': None, 'S1': None, 'R1': None, 'S2': None, 'R2': None, 'S3': None, 'R3': None}

    P = (high + low + close) / 3
    R1 = P + (0.382 * (high - low))
    S1 = P - (0.382 * (high - low))
    R2 = P + (0.618 * (high - low))
    S2 = P - (0.618 * (high - low))
    R3 = P + (1.000 * (high - low))
    S3 = P - (1.000 * (high - low))
    return {'P': P, 'S1': S1, 'R1': R1, 'S2': S2, 'R2': R2, 'S3': S3, 'R3': R3}

def find_peaks_valleys(series, window=5):
    """
    Finds peaks (highs) and valleys (lows) in a series.
    A simple approach: a point is a peak if it's higher than `window` points on both sides.
    A point is a valley if it's lower than `window` points on both sides.
    Returns two lists: indices of peaks, indices of valleys.
    """
    peaks = []
    valleys = []
    # Ensure series has a proper index for iloc
    series = series.reset_index(drop=True) # Ensures 0-based indexing for iloc
    if len(series) < 2 * window + 1: # Not enough data to find peaks/valleys with the given window
        return peaks, valleys

    for i in range(window, len(series) - window):
        is_peak = all(series.iloc[i] > series.iloc[i - j] for j in range(1, window + 1)) and \
                    all(series.iloc[i] > series.iloc[i + j] for j in range(1, window + 1))
        if is_peak:
            peaks.append(i)
            continue

        is_valley = all(series.iloc[i] < series.iloc[i - j] for j in range(1, window + 1)) and \
                      all(series.iloc[i] < series.iloc[i + j] for j in range(1, window + 1))
        if is_valley:
            valleys.append(i)
    return peaks, valleys

def calculate_rsi_divergence(df, rsi_col_name, lookback_pivots=2, peak_valley_window=3, divergence_window=30, a=0.005): # a=0.5%
    """
    Calculates simple RSI divergence by comparing last two significant peaks/valleys.
    `peak_valley_window`: Window to determine local peaks/valleys (e.g., 3 means a peak is higher than 3 points on each side).
    `divergence_window`: How far back from the latest candle the *second* (most recent) pivot can be.
    `a` (alpha): Tolerance for comparing highs/lows (e.g., 0.005 means 0.5% difference).

    Returns a string: "Positive", "Negative", or "None".
    """
    if rsi_col_name not in df.columns or 'close' not in df.columns:
        logger.warning(f"RSI divergence: RSI column '{rsi_col_name}' or 'close' column missing.")
        return "Data Missing"
    
    # Use at least enough data for 2 pivots considering the window for each.
    # A simple heuristic: (lookback_pivots * (2 * peak_valley_window + 1)) + divergence_window
    # Let's simplify, ensure at least divergence_window + a buffer.
    min_data_needed = divergence_window + (2 * peak_valley_window * lookback_pivots) 
    if len(df) < min_data_needed:
        logger.warning(f"RSI divergence: Not enough data. Have {len(df)}, need at least ~{min_data_needed}")
        return "Not Enough Data"

    # Take a recent slice of the DataFrame for performance and relevance
    # The slice should be large enough to find multiple pivots
    analysis_df = df.tail(min_data_needed + 20).copy() # Add a small buffer
    analysis_df.reset_index(drop=True, inplace=True)

    price = analysis_df['close']
    rsi = analysis_df[rsi_col_name]

    if rsi.isnull().all() or price.isnull().all():
        logger.warning("RSI divergence: RSI or Price data contains all NaNs in the analysis window.")
        return "RSI/Price Invalid"

    # Find peaks and valleys
    price_peaks_idx, price_valleys_idx = find_peaks_valleys(price, window=peak_valley_window)
    rsi_peaks_idx, rsi_valleys_idx = find_peaks_valleys(rsi, window=peak_valley_window)
    
    # --- Negative Divergence (Bearish) ---
    # Price: Higher Highs (HH)
    # RSI: Lower Highs (LH)
    # We need at least two peaks to compare
    if len(price_peaks_idx) >= lookback_pivots and len(rsi_peaks_idx) >= lookback_pivots:
        # Iterate backwards through price peaks to find two suitable ones
        for i in range(len(price_peaks_idx) -1, lookback_pivots - 2, -1): # e.g. if lookback=2, range(1, -1, -1) -> p_peak_idx2 = price_peaks_idx[1], p_peak_idx1 = price_peaks_idx[0]
            p_peak_idx2 = price_peaks_idx[i]
            p_peak_idx1 = price_peaks_idx[i - (lookback_pivots -1) ]
            
            # Ensure the most recent price peak (p_peak_idx2) is within the divergence_window from the end of the analysis_df
            if (len(analysis_df) - 1) - p_peak_idx2 > divergence_window:
                continue # This set of peaks is too old

            # Find corresponding RSI peaks - simple approach: find RSI peaks that are "close enough" to price peaks
            # More robust: ensure RSI peaks are between or very near price peak times.
            # For this version, we'll find the RSI peaks that are closest BEFORE or AT the price peaks.
            
            # Find rsi_peak_idx2 (corresponding to p_peak_idx2)
            # Must be <= p_peak_idx2
            r_peak_idx2 = -1
            for r_idx in reversed(rsi_peaks_idx):
                if r_idx <= p_peak_idx2:
                    r_peak_idx2 = r_idx
                    break
            
            # Find rsi_peak_idx1 (corresponding to p_peak_idx1)
            # Must be <= p_peak_idx1 AND before r_peak_idx2
            r_peak_idx1 = -1
            if r_peak_idx2 != -1:
                for r_idx in reversed(rsi_peaks_idx):
                    if r_idx <= p_peak_idx1 and r_idx < r_peak_idx2 :
                        r_peak_idx1 = r_idx
                        break
            
            if p_peak_idx1 < p_peak_idx2 and r_peak_idx1 != -1 and r_peak_idx2 != -1 and r_peak_idx1 < r_peak_idx2:
                price_high1 = price.iloc[p_peak_idx1]
                price_high2 = price.iloc[p_peak_idx2]
                rsi_high1 = rsi.iloc[r_peak_idx1]
                rsi_high2 = rsi.iloc[r_peak_idx2]

                # Condition: Price HH, RSI LH
                if price_high2 > price_high1 * (1 - a) and rsi_high2 < rsi_high1 * (1 + a):
                    # Check if price_high2 is truly higher (beyond tolerance for LH)
                    # And rsi_high2 is truly lower (beyond tolerance for HH)
                    if price_high2 > price_high1 and rsi_high2 < rsi_high1 : # Stricter check after tolerance
                        logger.info(f"Negative RSI Divergence detected: Price({p_peak_idx1}:{price_high1:.2f}, {p_peak_idx2}:{price_high2:.2f}), RSI({r_peak_idx1}:{rsi_high1:.2f}, {r_peak_idx2}:{rsi_high2:.2f})")
                        return "Negative"
                        
    # --- Positive Divergence (Bullish) ---
    # Price: Lower Lows (LL)
    # RSI: Higher Lows (HL)
    if len(price_valleys_idx) >= lookback_pivots and len(rsi_valleys_idx) >= lookback_pivots:
        for i in range(len(price_valleys_idx) -1, lookback_pivots - 2, -1):
            p_valley_idx2 = price_valleys_idx[i]
            p_valley_idx1 = price_valleys_idx[i - (lookback_pivots -1)]

            if (len(analysis_df) - 1) - p_valley_idx2 > divergence_window:
                continue

            r_valley_idx2 = -1
            for r_idx in reversed(rsi_valleys_idx):
                if r_idx <= p_valley_idx2:
                    r_valley_idx2 = r_idx
                    break
            
            r_valley_idx1 = -1
            if r_valley_idx2 != -1:
                for r_idx in reversed(rsi_valleys_idx):
                    if r_idx <= p_valley_idx1 and r_idx < r_valley_idx2:
                        r_valley_idx1 = r_idx
                        break

            if p_valley_idx1 < p_valley_idx2 and r_valley_idx1 != -1 and r_valley_idx2 != -1 and r_valley_idx1 < r_valley_idx2:
                price_low1 = price.iloc[p_valley_idx1]
                price_low2 = price.iloc[p_valley_idx2]
                rsi_low1 = rsi.iloc[r_valley_idx1]
                rsi_low2 = rsi.iloc[r_valley_idx2]

                # Condition: Price LL, RSI HL
                if price_low2 < price_low1 * (1 + a) and rsi_low2 > rsi_low1 * (1 - a):
                    if price_low2 < price_low1 and rsi_low2 > rsi_low1: # Stricter check
                        logger.info(f"Positive RSI Divergence detected: Price({p_valley_idx1}:{price_low1:.2f}, {p_valley_idx2}:{price_low2:.2f}), RSI({r_valley_idx1}:{rsi_low1:.2f}, {r_valley_idx2}:{rsi_low2:.2f})")
                        return "Positive"

    return "None"

def calculate_fibonacci_levels(df, lookback_period=60):
    """
    Calculates Fibonacci retracement levels based on the high and low of the last `lookback_period` candles.

    Args:
        df (pd.DataFrame): DataFrame containing 'high' and 'low' columns.
        lookback_period (int): Number of candles to look back to find high and low.

    Returns:
        dict: A dictionary containing the high, low, and calculated Fibonacci levels (23.6%, 38.2%, 50%, 61.8%, 78.6%).
              Returns None for levels if data is insufficient.
    """
    if len(df) < lookback_period:
        logger.warning(f"Fibonacci: Not enough data for lookback period {lookback_period}. Have {len(df)}.")
        return {'fib_high': None, 'fib_low': None, 'fib_levels': None}

    relevant_df = df.tail(lookback_period)
    period_high = relevant_df['high'].max()
    period_low = relevant_df['low'].min()

    if pd.isna(period_high) or pd.isna(period_low) or period_high == period_low:
        logger.warning("Fibonacci: Could not determine valid high/low for the period.")
        return {'fib_high': period_high, 'fib_low': period_low, 'fib_levels': None}

    diff = period_high - period_low
    levels = {
        '0.0%': period_high, # Top of the range
        '23.6%': period_high - diff * 0.236,
        '38.2%': period_high - diff * 0.382,
        '50.0%': period_high - diff * 0.5,
        '61.8%': period_high - diff * 0.618,
        '78.6%': period_high - diff * 0.786,
        '100.0%': period_low # Bottom of the range
    }
    
    logger.info(f"Calculated Fibonacci Levels (High: {period_high:.4f}, Low: {period_low:.4f}) over last {lookback_period} candles.")
    return {'fib_high': period_high, 'fib_low': period_low, 'fib_levels': levels}

# Utility functions will be defined here 

def format_indicator_value(value, precision=2):
    """Formats an indicator value to a string with specified precision if it's a float."""
    if pd.isna(value):
        return 'N/A'
    if isinstance(value, float):
        # Eğer değer çok küçükse (0.0001'den küçük) bilimsel gösterim kullan
        if abs(value) < 0.0001 and value != 0:
            return f"{value:.2e}"
        # Eğer değer 0.01'den küçükse daha fazla ondalık basamak kullan
        elif abs(value) < 0.01 and value != 0:
            return f"{value:.6f}"
        # Normal durumda standart formatlama kullan
        else:
            return f"{value:.{precision}f}"
    return str(value) # For 'N/A' or other non-float cases 

def preprocess_klines_df(klines):
    """Converts klines data to a DataFrame and handles numeric conversions."""
    df = pd.DataFrame(klines, columns=KLINES_COLUMNS)
    for col in NUMERIC_KLINES_COLUMNS:
        df[col] = pd.to_numeric(df[col])
    return df

def calculate_technical_indicators(df):
    """Calculates various technical indicators and adds them to the DataFrame."""
    min_len_for_indicators = max(RSI_PERIOD, MACD_SLOW_PERIOD, SMA_LONG_PERIOD, EMA_LONG_PERIOD, ATR_PERIOD, BBANDS_LENGTH, 1)
    if df.empty or len(df) < min_len_for_indicators:
        logger.warning(f"DataFrame does not have enough data to calculate all indicators. Required: {min_len_for_indicators}, Got: {len(df)}")
        return df

    try:
        logger.debug(f"Calculating individual indicators. Initial df columns: {df.columns.tolist()}")
        
        df.ta.rsi(length=RSI_PERIOD, append=True)
        df.ta.macd(fast=MACD_FAST_PERIOD, slow=MACD_SLOW_PERIOD, signal=MACD_SIGNAL_PERIOD, append=True)
        df.ta.sma(length=SMA_SHORT_PERIOD, append=True)
        df.ta.sma(length=SMA_LONG_PERIOD, append=True)
        df.ta.ema(length=EMA_SHORT_PERIOD, append=True)
        df.ta.ema(length=EMA_LONG_PERIOD, append=True)
        df.ta.atr(length=ATR_PERIOD, append=True)
        # Log ATR values after calculation
        atr_col_name = f'ATRr_{ATR_PERIOD}' # Use pandas_ta default name with 'r'
        if atr_col_name in df.columns:
             logger.debug(f"DataFrame tail after ATR calculation (first 5 of {atr_col_name}):\n{df[atr_col_name].tail().to_string()}") # Log ATR values
        else:
             logger.warning(f"ATR column '{atr_col_name}' not found after calculation.")
        df.ta.bbands(length=BBANDS_LENGTH, std=BBANDS_STD, append=True)

        # Fibonacci Pivot noktalarını manuel olarak hesapla
        # Genellikle bir önceki periyodun HLC'si kullanılır.
        # Bu örnekte, mevcut DataFrame'in son satırını kullanacağız.
        # Eğer DataFrame boş değilse ve yeterli veri varsa.
        if not df.empty:
            last_high = df['high'].iloc[-1]
            last_low = df['low'].iloc[-1]
            last_close = df['close'].iloc[-1]
            pivot_values = calculate_fibonacci_pivot_points(last_high, last_low, last_close)
            # Bu değerleri DataFrame'e yeni sütunlar olarak ekleyelim (son satıra)
            # Diğer indikatörler gibi tüm DataFrame boyunca hesaplanmadığı için sadece son satırda olacaklar.
            # extract_latest_indicators bunu hesaba katmalı.
            for key, value in pivot_values.items():
                df.loc[df.index[-1], key] = value # Sadece son satıra ata
            logger.debug(f"Manually calculated Fibonacci pivot points for the last row: {pivot_values}")
            logger.debug(f"DataFrame columns after manual pivot calculation: {df.columns.tolist()}")
        else:
            logger.warning("DataFrame is empty, cannot calculate manual pivot points.")
            # Ensure pivot columns exist with None if not calculated
            for key in ['P', 'S1', 'R1', 'S2', 'R2', 'S3', 'R3']:
                 if key not in df.columns: df[key] = None

        # RSI Uyumsuzluğunu Hesapla
        # RSI sütununun adını doğru bir şekilde almamız gerekiyor (pandas_ta tarafından oluşturulan)
        rsi_col_name = f'RSI_{RSI_PERIOD}'
        if rsi_col_name in df.columns:
            divergence_status = calculate_rsi_divergence(df, rsi_col_name=rsi_col_name)
            # Uyumsuzluk durumunu DataFrame'in son satırına ekleyelim
            if not df.empty:
                df.loc[df.index[-1], 'RSI_Divergence'] = divergence_status
            else:
                if 'RSI_Divergence' not in df.columns: df['RSI_Divergence'] = None
            logger.info(f"Calculated RSI Divergence Status: {divergence_status}")
        else:
            logger.warning(f"RSI column '{rsi_col_name}' not found. Skipping RSI divergence calculation.")
            if 'RSI_Divergence' not in df.columns: df['RSI_Divergence'] = "RSI Data Missing"

        # Fibonacci Seviyelerini Hesapla ve Son Satıra Ekle
        fib_data = calculate_fibonacci_levels(df, lookback_period=FIB_LOOKBACK_PERIOD)
        if not df.empty:
            # We store the high/low used for calculation
            df.loc[df.index[-1], 'Fib_High'] = fib_data.get('fib_high')
            df.loc[df.index[-1], 'Fib_Low'] = fib_data.get('fib_low')
            
            # Dikkat: fib_levels bir dictionary, direkt olarak DataFrame hücresine atanamaz
            # String olarak saklayalım veya individual değerleri ayrı sütunlara ekleyelim
            fib_levels = fib_data.get('fib_levels')
            if fib_levels:
                # Opsiyonel: Eğer ihtiyaç varsa tüm seviyeler için ayrı sütunlar oluşturalım
                for key, value in fib_levels.items():
                    col_name = f'Fib_{key.replace("%", "pct").replace(".", "_")}'
                    df.loc[df.index[-1], col_name] = value
                
                # Veya sadece string olarak dönüştürelim
                import json
                df.loc[df.index[-1], 'Fib_Levels_Str'] = json.dumps(fib_levels)
            else:
                df.loc[df.index[-1], 'Fib_Levels_Str'] = None
        else:
             if 'Fib_High' not in df.columns: df['Fib_High'] = None
             if 'Fib_Low' not in df.columns: df['Fib_Low'] = None
             if 'Fib_Levels_Str' not in df.columns: df['Fib_Levels_Str'] = None
             
        # --- GELIŞMIŞ HACIM ANALIZI ---
        # Hacim trendi hesaplama
        if len(df) >= 10:  # En az 10 mum gerekiyor
            try:
                volume_trend, trend_pct_change = calculate_volume_trend(df, period=10)
                df.loc[df.index[-1], 'Volume_Trend'] = volume_trend
                df.loc[df.index[-1], 'Volume_Trend_Pct_Change'] = trend_pct_change
                logger.debug(f"Volume trend calculated: {volume_trend} ({trend_pct_change:.2f}%)")
            except Exception as e:
                logger.error(f"Error calculating volume trend: {e}")
                if 'Volume_Trend' not in df.columns: df['Volume_Trend'] = None
                if 'Volume_Trend_Pct_Change' not in df.columns: df['Volume_Trend_Pct_Change'] = None
        else:
            if 'Volume_Trend' not in df.columns: df['Volume_Trend'] = None
            if 'Volume_Trend_Pct_Change' not in df.columns: df['Volume_Trend_Pct_Change'] = None
            
        # Hacim hareketli ortalamaları
        if len(df) >= 20:  # En kısa MA için en az 20 mum gerekiyor
            try:
                volume_ma_data = calculate_volume_moving_averages(df, periods=[20, 50, 100])
                # Hacim MA'ları ve oranlar DataFrame'e ekle
                for key, value in volume_ma_data.items():
                    df.loc[df.index[-1], key] = value
                logger.debug(f"Volume moving averages calculated: {volume_ma_data}")
            except Exception as e:
                logger.error(f"Error calculating volume moving averages: {e}")
                # Ensure columns exist
                for period in [20, 50, 100]:
                    if f'volume_ma_{period}' not in df.columns:
                        df[f'volume_ma_{period}'] = None
                    if f'volume_vs_ma_{period}' not in df.columns:
                        df[f'volume_vs_ma_{period}'] = None
        else:
            # Ensure columns exist
            for period in [20, 50, 100]:
                if f'volume_ma_{period}' not in df.columns:
                    df[f'volume_ma_{period}'] = None
                if f'volume_vs_ma_{period}' not in df.columns:
                    df[f'volume_vs_ma_{period}'] = None
                    
        # Fiyat-hacim ilişkisi analizi
        if len(df) >= 20:  # En az 20 mum gerekiyor
            try:
                price_volume_rel = analyze_price_volume_relationship(df, lookback_period=20)
                # İlişki verisini DataFrame'e ekle
                for key, value in price_volume_rel.items():
                    df.loc[df.index[-1], f'PriceVolume_{key}'] = value
                logger.debug(f"Price-volume relationship analyzed: {price_volume_rel}")
            except Exception as e:
                logger.error(f"Error analyzing price-volume relationship: {e}")
                # Ensure columns exist
                for key in ['correlation', 'interpretation', 'strength', 'is_confirming']:
                    col_name = f'PriceVolume_{key}'
                    if col_name not in df.columns:
                        df[col_name] = None
        else:
            # Ensure columns exist
            for key in ['correlation', 'interpretation', 'strength', 'is_confirming']:
                col_name = f'PriceVolume_{key}'
                if col_name not in df.columns:
                    df[col_name] = None
                    
        # Hacim anomali tespiti
        if len(df) >= 30:  # En az 30 mum gerekiyor
            try:
                volume_anomalies = detect_volume_anomalies(df, lookback_period=30)
                # Anomali verisini DataFrame'e ekle
                for key, value in volume_anomalies.items():
                    df.loc[df.index[-1], f'VolumeAnomaly_{key}'] = value
                logger.debug(f"Volume anomalies detected: {volume_anomalies}")
            except Exception as e:
                logger.error(f"Error detecting volume anomalies: {e}")
                # Ensure columns exist
                for key in ['anomaly_detected', 'type', 'z_score', 'deviation_percent']:
                    col_name = f'VolumeAnomaly_{key}'
                    if col_name not in df.columns:
                        df[col_name] = None
        else:
            # Ensure columns exist
            for key in ['anomaly_detected', 'type', 'z_score', 'deviation_percent']:
                col_name = f'VolumeAnomaly_{key}'
                if col_name not in df.columns:
                    df[col_name] = None

        logger.debug(f"DataFrame columns after ALL TA calculations: {df.columns.tolist()}")
        logger.debug(f"DataFrame tail after TA calculations:\\n{df.tail().to_string()}") # GÜNCELLENDİ: Log mesajı
    except Exception as e:
        logger.error(f"Error calculating technical indicators: {e}", exc_info=True)
        return df 
    return df

def extract_latest_indicators(df_with_indicators):
    """Extracts the latest values of all calculated indicators from the DataFrame."""
    if df_with_indicators.empty:
        logger.warning("Cannot extract latest indicators from an empty DataFrame.")
        return {}
    
    latest = df_with_indicators.iloc[-1]
    logger.debug(f"Latest row for indicator extraction:\n{latest.to_string()}")
    
    raw_atr_value = latest.get(f'ATRr_{ATR_PERIOD}') # Get raw ATR using correct column name
    logger.debug(f"Raw ATR value extracted: {raw_atr_value}, type: {type(raw_atr_value)}") # Log raw ATR

    # MACD Sinyal sütun adı genellikle 'MACDs' ile başlar, 'MACDSignal' değil.
    macd_signal_col_name = f'MACDs_{MACD_FAST_PERIOD}_{MACD_SLOW_PERIOD}_{MACD_SIGNAL_PERIOD}' # Pandas TA default

    # Extract Pivot Points (classic method usually generates P, S1, R1, etc.)
    # Varsayılan sütun adları. Eğer pandas-ta farklı adlar üretiyorsa, loglardan kontrol edilip güncellenmeli.
    pivot_p = latest.get('P') 
    pivot_s1 = latest.get('S1')
    pivot_s2 = latest.get('S2')
    pivot_s3 = latest.get('S3')
    pivot_r1 = latest.get('R1')
    pivot_r2 = latest.get('R2')
    pivot_r3 = latest.get('R3')

    logger.debug(f"Pivot columns check: P={pivot_p}, S1={pivot_s1}, R1={pivot_r1}")
    
    # Extract volume analysis related data
    volume_trend = latest.get('Volume_Trend')
    volume_trend_pct = latest.get('Volume_Trend_Pct_Change')
    
    # Extract volume moving averages
    volume_ma_20 = latest.get('volume_ma_20')
    volume_ma_50 = latest.get('volume_ma_50')
    volume_ma_100 = latest.get('volume_ma_100')
    
    # Volume vs moving averages (percentages)
    volume_vs_ma_20 = latest.get('volume_vs_ma_20')
    volume_vs_ma_50 = latest.get('volume_vs_ma_50')
    volume_vs_ma_100 = latest.get('volume_vs_ma_100')
    
    # Price-volume relationship data
    pv_correlation = latest.get('PriceVolume_correlation')
    pv_interpretation = latest.get('PriceVolume_interpretation')
    pv_strength = latest.get('PriceVolume_strength')
    pv_is_confirming = latest.get('PriceVolume_is_confirming')
    
    # Volume anomaly data
    va_detected = latest.get('VolumeAnomaly_anomaly_detected')
    va_type = latest.get('VolumeAnomaly_type')
    va_z_score = latest.get('VolumeAnomaly_z_score')
    va_deviation_pct = latest.get('VolumeAnomaly_deviation_percent')
    
    # Create the combined indicator dict with both standard and new volume indicators
    result = {
        # Standard indicators
        'rsi': latest.get(f'RSI_{RSI_PERIOD}'),
        'macd': latest.get(f'MACD_{MACD_FAST_PERIOD}_{MACD_SLOW_PERIOD}_{MACD_SIGNAL_PERIOD}'),
        'macd_signal': latest.get(macd_signal_col_name),
        'macd_hist': latest.get(f'MACDh_{MACD_FAST_PERIOD}_{MACD_SLOW_PERIOD}_{MACD_SIGNAL_PERIOD}'),
        f'sma_{SMA_SHORT_PERIOD}': latest.get(f'SMA_{SMA_SHORT_PERIOD}'),
        f'sma_{SMA_LONG_PERIOD}': latest.get(f'SMA_{SMA_LONG_PERIOD}'),
        f'ema_{EMA_SHORT_PERIOD}': latest.get(f'EMA_{EMA_SHORT_PERIOD}'),
        f'ema_{EMA_LONG_PERIOD}': latest.get(f'EMA_{EMA_LONG_PERIOD}'),
        f'atr_{ATR_PERIOD}': raw_atr_value,
        'bb_lower': latest.get(f'BBL_{BBANDS_LENGTH}_{BBANDS_STD:.1f}'),
        'bb_middle': latest.get(f'BBM_{BBANDS_LENGTH}_{BBANDS_STD:.1f}'),
        'bb_upper': latest.get(f'BBU_{BBANDS_LENGTH}_{BBANDS_STD:.1f}'),
        'volume': latest.get('volume'),
        'pivot_p': pivot_p,
        'pivot_s1': pivot_s1,
        'pivot_s2': pivot_s2,
        'pivot_s3': pivot_s3,
        'pivot_r1': pivot_r1,
        'pivot_r2': pivot_r2,
        'pivot_r3': pivot_r3,
        'rsi_divergence': latest.get('RSI_Divergence'),
        'fib_levels': latest.get('Fib_Levels_Str'),  # Güncellendi: Artık string tipinde
        'fib_high': latest.get('Fib_High'),
        'fib_low': latest.get('Fib_Low'),
        
        # Volume analysis indicators
        'volume_trend': volume_trend,
        'volume_trend_pct_change': volume_trend_pct,
        'volume_ma_20': volume_ma_20,
        'volume_ma_50': volume_ma_50,
        'volume_ma_100': volume_ma_100,
        'volume_vs_ma_20': volume_vs_ma_20,
        'volume_vs_ma_50': volume_vs_ma_50,
        'volume_vs_ma_100': volume_vs_ma_100,
        'pv_correlation': pv_correlation,
        'pv_interpretation': pv_interpretation,
        'pv_strength': pv_strength,
        'pv_is_confirming': pv_is_confirming,
        'volume_anomaly_detected': va_detected,
        'volume_anomaly_type': va_type,
        'volume_anomaly_z_score': va_z_score,
        'volume_anomaly_deviation_pct': va_deviation_pct
    }
    return result

def extract_price_summary_data(df, current_ticker_details):
    """Extracts key price summary data from the DataFrame and ticker details."""
    
    # Calculate recent highs/lows from the last N candles
    recent_high_last_N = 'N/A'
    recent_low_last_N = 'N/A'
    if len(df) >= 1:
        # Ensure we don't try to slice more than available rows
        slice_count = min(RECENT_SR_CANDLE_COUNT, len(df))
        recent_df_slice = df.tail(slice_count)
        recent_high_last_N = recent_df_slice['high'].max()
        recent_low_last_N = recent_df_slice['low'].min()

    price_summary = {
        'last_n_closes': df['close'].tail(5).tolist(),
        'highest_price_period': df['high'].max(), # Max high over the entire df period (e.g., 500 candles)
        'lowest_price_period': df['low'].min(),   # Max low over the entire df period
        'recent_high_last_N': recent_high_last_N, # Max high over last N candles
        'recent_low_last_N': recent_low_last_N,   # Max low over last N candles
        'current_price': current_ticker_details.get('lastPrice', 'N/A') if current_ticker_details else 'N/A',
        'price_change_percent': current_ticker_details.get('priceChangePercent', 'N/A') if current_ticker_details else 'N/A',
    }
    return price_summary

def get_top_n_by_volume(all_binance_usdt_tickers, n):
    """Returns top N coins by quoteVolume from Binance tickers."""
    if not all_binance_usdt_tickers:
        return []
    return sorted([t for t in all_binance_usdt_tickers if t['quoteVolume'] > 0], key=lambda x: x['quoteVolume'], reverse=True)[:n]

def get_top_n_gainers(all_binance_usdt_tickers, n):
    """Returns top N gainer coins by priceChangePercent from Binance tickers."""
    if not all_binance_usdt_tickers:
        return []
    return sorted([t for t in all_binance_usdt_tickers if t['priceChangePercent'] > 0], key=lambda x: x['priceChangePercent'], reverse=True)[:n]

def get_top_n_decliners(all_binance_usdt_tickers, n):
    """Returns top N decliner coins by priceChangePercent from Binance tickers."""
    if not all_binance_usdt_tickers:
        return []
    return sorted([t for t in all_binance_usdt_tickers if t['priceChangePercent'] < 0], key=lambda x: x['priceChangePercent'])[:n]

def get_recent_high_low(df, window=RECENT_SR_CANDLE_COUNT):
    # Implementation of get_recent_high_low function
    pass 