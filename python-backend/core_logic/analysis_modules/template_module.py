"""
Template Analysis Module - Template for creating new analysis modules.

To create a new analysis module:
1. Copy this file and rename it appropriately
2. Modify the class name, description, and implementation
3. Register the module in analysis_facade.py
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import numpy as np

from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from utils.general_utils import (
    preprocess_klines_df, calculate_technical_indicators, extract_latest_indicators
)

from .base_analysis import BaseAnalysisModule

# Example template for an LLM prompt if needed
TEMPLATE_PROMPT = """
You are an expert cryptocurrency analyst.
Analyze the following data for {symbol} and provide insights:

1. First area to analyze
2. Second area to analyze
3. Third area to analyze

Market Data:
{market_data}

Technical Indicators:
{technical_indicators}

Make your analysis concise, actionable, and focused on practical decisions.
"""

class TemplateAnalysisModule(BaseAnalysisModule):
    """
    Template module for creating new analysis modules.
    
    This is a starter template - replace this docstring with a description
    of your analysis module's purpose and focus.
    """
    
    def __init__(self, binance_client: BinanceClient, llm_client: GeminiClient, **kwargs):
        """
        Initialize the template analysis module.
        
        Args:
            binance_client: Client for accessing Binance exchange data
            llm_client: Client for accessing language model services
            **kwargs: Additional clients or dependencies if needed
        """
        super().__init__(
            name="template_analysis",  # Change this to your module's unique name
            description="Template for creating new analysis modules"  # Change this description
        )
        self.binance_client = binance_client
        self.llm_client = llm_client
        
        # Add any additional instance variables you need
        self.timeframe = kwargs.get('timeframe', '1h')  # Default timeframe
    
    async def perform_analysis(self, symbol: str, **kwargs) -> str:
        """
        Perform analysis on a cryptocurrency.
        
        Args:
            symbol: The cryptocurrency symbol to analyze (e.g., 'BTCUSDT')
            **kwargs: Additional parameters specific to this analysis type
            
        Returns:
            str: Formatted analysis result
        """
        self.log_info(f"Starting analysis for {symbol}")
        
        try:
            # Standardize symbol format if needed
            if not any(symbol.upper().endswith(suffix) for suffix in ['USDT', 'BTC', 'ETH', 'BUSD']):
                symbol = f"{symbol.upper()}USDT"
            else:
                symbol = symbol.upper()
            
            # Get parameters from kwargs or use defaults
            timeframe = kwargs.get('timeframe', self.timeframe)
            
            # Fetch market data
            ticker_data = await self.binance_client.client.get_ticker(symbol=symbol)
            if not ticker_data:
                return f"❌ Could not retrieve market data for {symbol}"
            
            # Fetch klines (candlestick) data
            klines = await self.binance_client.get_klines(symbol, timeframe, limit=300) # 300 candles required for reliable technical indicator calculations (especially SMA200)
            if not klines or len(klines) < 50:
                return f"❌ Insufficient historical data for {symbol} on {timeframe} timeframe"
            
            # Process data
            df = preprocess_klines_df(klines)
            df_with_indicators = calculate_technical_indicators(df)
            latest_indicators = extract_latest_indicators(df_with_indicators)
            
            # Extract relevant data for analysis
            current_price = float(ticker_data.get('lastPrice', 'N/A'))
            price_change = float(ticker_data.get('priceChangePercent', 'N/A'))
            
            # Create LLM prompt with data if using LLM
            # Replace with your custom analysis logic if not using LLM
            prompt = TEMPLATE_PROMPT.format(
                symbol=symbol,
                market_data=f"Current Price: {current_price} USDT\n24h Change: {price_change}%",
                technical_indicators=f"RSI: {latest_indicators.get('rsi', 'N/A')}\nMACD: {latest_indicators.get('macd', 'N/A')}"
            )
            
            # Get analysis result - either from LLM or your custom logic
            analysis_text = self.llm_client.generate_text(prompt)
            
            # Format the result
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = f"# {symbol} ANALYSIS REPORT\n\n"
            result += f"Analysis Time: {timestamp}\n"
            result += f"Timeframe: {timeframe}\n\n"
            result += f"Current Price: {current_price} USDT ({price_change}% 24h)\n\n"
            result += analysis_text
            
            self.log_info(f"Completed analysis for {symbol}")
            return result
            
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
            "name": self.name,
            "description": self.description,
            "default_timeframe": self.timeframe,
            "supported_timeframes": ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"],
            # Add any other parameters specific to your module
        }

    def _convert_numpy_types(self, obj):
        """
        Recursively convert numpy types to native Python types for JSON serialization.
        
        Args:
            obj: Object to convert (can be dict, list, or scalar value)
            
        Returns:
            Object with numpy types converted to native Python types
        """
        if isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif obj is np.True_:
            return True
        elif obj is np.False_:
            return False
        elif isinstance(obj, np.ndarray):
            return self._convert_numpy_types(obj.tolist())
        else:
            return obj 