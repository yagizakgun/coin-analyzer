"""
Analysis modules package for different types of cryptocurrency analysis.
Each module provides specialized analysis capabilities.
"""

from .base_analysis import BaseAnalysisModule
from .crypto_analysis import CryptoAnalysisModule
from .spot_trading_analysis import SpotTradingAnalysisModule
from .futures_trading_analysis import FuturesTradingAnalysisModule
from .module_registry import registry, AnalysisModuleRegistry 