"""
Crypto Analysis Module - Provides technical and fundamental analysis of cryptocurrencies.
"""
import logging
from typing import Dict, Any, Optional

from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from fundamental_analysis.cryptopanic_client import CryptoPanicClient
from core_logic.constants import (
    TARGET_KLINE_INTERVALS, KLINE_INTERVAL_MAP, RSI_PERIOD, MACD_FAST_PERIOD, 
    MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD, SMA_SHORT_PERIOD, SMA_LONG_PERIOD,
    EMA_SHORT_PERIOD, EMA_LONG_PERIOD, ATR_PERIOD, BBANDS_LENGTH, BBANDS_STD
)

# Import actual analysis functions
from core_logic.analysis_logic import get_bitcoin_trend_summary, perform_analysis

from .base_analysis import BaseAnalysisModule

class CryptoAnalysisModule(BaseAnalysisModule):
    """
    Module for comprehensive cryptocurrency technical and fundamental analysis.
    
    This module analyzes cryptocurrencies using technical indicators, price action,
    market trends, and fundamental data to provide a complete analysis report.
    """
    
    def __init__(self, binance_client: BinanceClient, llm_client: GeminiClient, 
                 cryptopanic_client: Optional[CryptoPanicClient] = None):
        """
        Initialize the crypto analysis module.
        
        Args:
            binance_client: Client for accessing Binance exchange data
            llm_client: Client for accessing language model services
            cryptopanic_client: Optional client for accessing fundamental data
        """
        super().__init__(
            name="crypto_analysis",
            description="Comprehensive cryptocurrency technical and fundamental analysis"
        )
        self.binance_client = binance_client
        self.llm_client = llm_client
        self.cryptopanic_client = cryptopanic_client
    
    async def perform_analysis(self, symbol: str, **kwargs) -> str:
        """
        Perform comprehensive analysis on a cryptocurrency.
        
        Args:
            symbol: The cryptocurrency symbol to analyze (e.g., 'BTCUSDT')
            **kwargs: Additional parameters (currently unused)
            
        Returns:
            str: Formatted analysis result
        """
        self.log_info(f"Starting analysis for {symbol}")
        
        try:
            # Get Bitcoin trend for context if not provided
            btc_trend_summary = kwargs.get('btc_trend_summary')
            if not btc_trend_summary:
                btc_trend_summary = await get_bitcoin_trend_summary(self.binance_client)
            
            # Call the existing perform_analysis function from analysis_logic.py
            # This reuses all the existing analysis logic
            analysis_result = await perform_analysis(
                coin_symbol=symbol
            )
            
            self.log_info(f"Completed analysis for {symbol}")
            return analysis_result
            
        except Exception as e:
            error_message = f"Error analyzing {symbol}: {str(e)}"
            self.log_error(error_message, exc_info=e)
            return f"❌ Analysis failed: {error_message}"
    
    async def get_analysis_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters used by this analysis module.
        
        Returns:
            Dict[str, Any]: Dictionary of parameter names and their values
        """
        return {
            "timeframes": [KLINE_INTERVAL_MAP.get(interval, interval) for interval in TARGET_KLINE_INTERVALS],
            "indicators": {
                "RSI": {
                    "period": RSI_PERIOD
                },
                "MACD": {
                    "fast_period": MACD_FAST_PERIOD,
                    "slow_period": MACD_SLOW_PERIOD,
                    "signal_period": MACD_SIGNAL_PERIOD
                },
                "SMA": {
                    "short_period": SMA_SHORT_PERIOD,
                    "long_period": SMA_LONG_PERIOD
                },
                "EMA": {
                    "short_period": EMA_SHORT_PERIOD,
                    "long_period": EMA_LONG_PERIOD
                },
                "ATR": {
                    "period": ATR_PERIOD
                },
                "Bollinger Bands": {
                    "length": BBANDS_LENGTH,
                    "std": BBANDS_STD
                }
            },
            "fundamental_data": self.cryptopanic_client is not None
        } 