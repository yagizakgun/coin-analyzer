"""
Volume analysis utilities for cryptocurrency analysis.

This module provides functions for analyzing trading volume patterns and trends,
which can provide insights into the strength of price movements and potential
reversals. The functions include volume trend analysis, moving averages, 
price-volume correlations, anomaly detection, and cross-timeframe comparisons.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Union

# Setup logging
logger = logging.getLogger(__name__)

def calculate_volume_trend(df: pd.DataFrame, 
                           period: int = 10,
                           volume_col: str = 'volume') -> Tuple[str, float]:
    """
    Calculate the volume trend over the specified period.
    
    Args:
        df: DataFrame containing volume data
        period: Number of candles to analyze for trend
        volume_col: Name of the volume column in the DataFrame
        
    Returns:
        Tuple containing trend direction ("increasing", "decreasing", "flat") 
        and percentage change
    """
    if df.empty or len(df) < period:
        logger.warning(f"Insufficient data for volume trend analysis. Required: {period}, got: {len(df)}")
        return ("insufficient_data", 0.0)
    
    try:
        # Use the most recent 'period' candles
        recent_df = df.tail(period)
        
        # Linear regression to determine trend
        x = np.arange(len(recent_df))
        y = recent_df[volume_col].values
        
        # Handle zero or negative values in volume (shouldn't happen, but just in case)
        if (y <= 0).any():
            y = np.maximum(y, 0.000001)  # Replace zeros/negatives with a small value
        
        # Calculate the linear regression (polyfit degree 1)
        slope, _ = np.polyfit(x, y, 1)
        
        # Calculate percentage change from start to end
        start_volume = recent_df[volume_col].iloc[0]
        end_volume = recent_df[volume_col].iloc[-1]
        
        # Avoid division by zero
        if start_volume == 0:
            start_volume = 0.000001
            
        pct_change = ((end_volume - start_volume) / start_volume) * 100
        
        # Determine trend direction with a small threshold for "flat"
        threshold = 5.0  # 5% change threshold for considering it flat
        if abs(pct_change) < threshold:
            trend = "flat"
        elif pct_change > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
            
        return (trend, pct_change)
    
    except Exception as e:
        logger.error(f"Error calculating volume trend: {e}")
        return ("error", 0.0)

def calculate_volume_moving_averages(df: pd.DataFrame, 
                                    periods: List[int] = [20, 50, 100],
                                    volume_col: str = 'volume') -> Dict[str, float]:
    """
    Calculate moving averages of volume for multiple periods.
    
    Args:
        df: DataFrame containing volume data
        periods: List of periods for moving averages
        volume_col: Name of the volume column in the DataFrame
        
    Returns:
        Dictionary mapping period names to moving average values
    """
    result = {}
    
    if df.empty:
        logger.warning("Empty DataFrame provided for volume moving averages calculation")
        return {f"volume_ma_{period}": None for period in periods}
    
    try:
        for period in periods:
            if len(df) < period:
                logger.warning(f"Insufficient data for {period}-period volume MA. Required: {period}, got: {len(df)}")
                result[f"volume_ma_{period}"] = None
                continue
                
            # Calculate the simple moving average
            result[f"volume_ma_{period}"] = df[volume_col].rolling(window=period).mean().iloc[-1]
        
        # Add volume relative to moving averages
        current_volume = df[volume_col].iloc[-1]
        for period in periods:
            ma_key = f"volume_ma_{period}"
            if result[ma_key] is not None and result[ma_key] > 0:
                # Calculate volume as percentage of its moving average
                result[f"volume_vs_ma_{period}"] = (current_volume / result[ma_key]) * 100
            else:
                result[f"volume_vs_ma_{period}"] = None
                
        return result
    
    except Exception as e:
        logger.error(f"Error calculating volume moving averages: {e}")
        return {f"volume_ma_{period}": None for period in periods}

def analyze_price_volume_relationship(df: pd.DataFrame, 
                                     lookback_period: int = 20,
                                     price_col: str = 'close', 
                                     volume_col: str = 'volume') -> Dict[str, Union[str, float]]:
    """
    Analyze the relationship between price and volume movements.
    
    Args:
        df: DataFrame containing price and volume data
        lookback_period: Number of candles to analyze
        price_col: Name of the price column in the DataFrame
        volume_col: Name of the volume column in the DataFrame
        
    Returns:
        Dictionary with price-volume correlation metrics and interpretation
    """
    if df.empty or len(df) < lookback_period:
        logger.warning(f"Insufficient data for price-volume analysis. Required: {lookback_period}, got: {len(df)}")
        return {
            "correlation": None,
            "interpretation": "insufficient_data",
            "strength": None,
            "is_confirming": None
        }
    
    try:
        # Use the most recent 'lookback_period' candles
        recent_df = df.tail(lookback_period).copy()
        
        # Calculate price changes and ensure volume is positive
        recent_df['price_change'] = recent_df[price_col].pct_change()
        recent_df['price_change_abs'] = recent_df['price_change'].abs()
        recent_df[volume_col] = recent_df[volume_col].clip(lower=0.000001)
        
        # Calculate correlation between absolute price change and volume
        correlation = recent_df['price_change_abs'].corr(recent_df[volume_col])
        
        # Check if volume confirms price direction
        # Upward price movements should have higher volume than downward movements
        up_moves = recent_df[recent_df['price_change'] > 0]
        down_moves = recent_df[recent_df['price_change'] < 0]
        
        up_volume_avg = up_moves[volume_col].mean() if not up_moves.empty else 0
        down_volume_avg = down_moves[volume_col].mean() if not down_moves.empty else 0
        
        # Determine if volume is confirming price movements
        is_confirming = up_volume_avg > down_volume_avg
        
        # Calculate strength of relationship based on correlation
        if pd.isna(correlation):
            strength = None
            interpretation = "unknown"
        else:
            if abs(correlation) < 0.3:
                strength = "weak"
            elif abs(correlation) < 0.7:
                strength = "moderate"
            else:
                strength = "strong"
                
            # Build interpretation based on findings
            if correlation > 0.5 and is_confirming:
                interpretation = "healthy_trend"
            elif correlation > 0.5 and not is_confirming:
                interpretation = "potential_trend_reversal"
            elif correlation <= 0.5 and is_confirming:
                interpretation = "inconsistent_confirmation"
            else:
                interpretation = "indecisive_market"
                
        return {
            "correlation": correlation,
            "interpretation": interpretation,
            "strength": strength,
            "is_confirming": is_confirming,
            "up_volume_avg": up_volume_avg,
            "down_volume_avg": down_volume_avg
        }
        
    except Exception as e:
        logger.error(f"Error analyzing price-volume relationship: {e}")
        return {
            "correlation": None,
            "interpretation": "error",
            "strength": None,
            "is_confirming": None
        }

def detect_volume_anomalies(df: pd.DataFrame, 
                           lookback_period: int = 30,
                           threshold: float = 2.0,
                           volume_col: str = 'volume') -> Dict[str, Union[bool, float, int]]:
    """
    Detect anomalies in trading volume such as unusual spikes or drops.
    
    Args:
        df: DataFrame containing volume data
        lookback_period: Number of candles to establish baseline
        threshold: Multiplier for standard deviation to identify anomalies
        volume_col: Name of the volume column in the DataFrame
        
    Returns:
        Dictionary with anomaly detection results
    """
    if df.empty or len(df) < lookback_period:
        logger.warning(f"Insufficient data for volume anomaly detection. Required: {lookback_period}, got: {len(df)}")
        return {
            "anomaly_detected": None,
            "type": None,
            "current_volume": None,
            "baseline_mean": None,
            "baseline_std": None,
            "z_score": None
        }
    
    try:
        # Use a lookback period for baseline, excluding the most recent candle
        baseline_df = df.iloc[-(lookback_period+1):-1]
        current_volume = df[volume_col].iloc[-1]
        
        # Calculate baseline statistics
        baseline_mean = baseline_df[volume_col].mean()
        baseline_std = baseline_df[volume_col].std()
        
        # Prevent division by zero
        if baseline_std == 0:
            baseline_std = 0.000001
            
        # Calculate z-score
        z_score = (current_volume - baseline_mean) / baseline_std
        
        # Determine if there's an anomaly
        anomaly_detected = abs(z_score) > threshold
        
        if anomaly_detected:
            if z_score > 0:
                anomaly_type = "spike"
            else:
                anomaly_type = "drop"
        else:
            anomaly_type = "none"
            
        # Find recent anomalies
        rolling_z = (df[volume_col] - baseline_mean) / baseline_std
        recent_anomalies = (abs(rolling_z.tail(5)) > threshold).sum()
            
        return {
            "anomaly_detected": anomaly_detected,
            "type": anomaly_type,
            "current_volume": current_volume,
            "baseline_mean": baseline_mean,
            "baseline_std": baseline_std,
            "z_score": z_score,
            "deviation_percent": ((current_volume / baseline_mean) - 1) * 100,
            "recent_anomalies": recent_anomalies
        }
        
    except Exception as e:
        logger.error(f"Error detecting volume anomalies: {e}")
        return {
            "anomaly_detected": None,
            "type": None,
            "current_volume": None,
            "baseline_mean": None,
            "baseline_std": None,
            "z_score": None
        }

def compare_volume_across_timeframes(timeframe_dfs: Dict[str, pd.DataFrame],
                                    normalize: bool = True,
                                    volume_col: str = 'volume') -> Dict[str, Dict[str, float]]:
    """
    Compare volume patterns across different timeframes.
    
    Args:
        timeframe_dfs: Dictionary mapping timeframe names to DataFrames
        normalize: Whether to normalize volumes for comparison
        volume_col: Name of the volume column in the DataFrames
        
    Returns:
        Dictionary with comparative volume metrics for each timeframe
    """
    result = {}
    
    if not timeframe_dfs:
        logger.warning("No timeframes provided for volume comparison")
        return result
    
    try:
        # Calculate volume metrics for each timeframe
        for timeframe, df in timeframe_dfs.items():
            if df.empty or len(df) < 20:  # Minimum requirement for meaningful analysis
                logger.warning(f"Insufficient data for timeframe {timeframe}")
                result[timeframe] = {
                    "volume_trend": "insufficient_data",
                    "trend_pct_change": None,
                    "volume_ma_20": None,
                    "current_volume": None,
                    "current_vs_ma": None
                }
                continue
                
            # Get current volume and calculate 20-period MA
            current_volume = df[volume_col].iloc[-1]
            volume_ma_20 = df[volume_col].rolling(window=20).mean().iloc[-1]
            
            # Get volume trend
            volume_trend, trend_pct_change = calculate_volume_trend(df, period=10, volume_col=volume_col)
            
            result[timeframe] = {
                "volume_trend": volume_trend,
                "trend_pct_change": trend_pct_change,
                "volume_ma_20": volume_ma_20,
                "current_volume": current_volume,
                "current_vs_ma": (current_volume / volume_ma_20 * 100) if volume_ma_20 > 0 else None
            }
            
        # Add cross-timeframe analysis
        if normalize and len(result) > 1:
            # Normalize volumes based on the highest timeframe average
            highest_tf = list(result.keys())[-1]  # Assumes timeframes are ordered from lowest to highest
            if highest_tf in result and result[highest_tf]["volume_ma_20"] is not None:
                base_volume = result[highest_tf]["volume_ma_20"]
                
                # Add normalized comparison
                for timeframe in result:
                    if result[timeframe]["volume_ma_20"] is not None and base_volume > 0:
                        result[timeframe]["normalized_volume"] = result[timeframe]["volume_ma_20"] / base_volume
                    else:
                        result[timeframe]["normalized_volume"] = None
        
        return result
        
    except Exception as e:
        logger.error(f"Error comparing volume across timeframes: {e}")
        return result 