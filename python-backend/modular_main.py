"""
Modular Coin Scanner - Main Script

This script demonstrates the modular analysis architecture where different
analysis modules can be selected and used for cryptocurrency analysis.
"""
import sys
import os

print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Add the current directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print("Updated Python path:", sys.path)

print("Importing required modules...")

try:
    import asyncio
    import logging
    import json
    from datetime import datetime
    from typing import List, Dict, Any, Optional
    print("Basic imports successful")
except ImportError as e:
    print(f"Error importing basic modules: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("modular_scanner")

# Import clients and dependencies
try:
    from clients.exchange_client import BinanceClient
    print("Imported BinanceClient")
    from clients.llm_client import GeminiClient
    print("Imported GeminiClient") 
    from clients.market_data_client import CoinMarketCapClient
    print("Imported CoinMarketCapClient")
    from fundamental_analysis.cryptopanic_client import CryptoPanicClient
    print("Imported CryptoPanicClient")
except ImportError as e:
    print(f"Error importing client modules: {e}")
    sys.exit(1)

try:
    from config import (
        EXCHANGE_API_KEY, EXCHANGE_API_SECRET, LLM_API_KEY, CRYPTOPANIC_API_KEY,
        DEFAULT_TOP_N, CMC_TOP_N_MARKET_CAP
    )
    print("Imported config variables")
except ImportError as e:
    print(f"Error importing config: {e}")
    sys.exit(1)

# Import analysis system
try:
    from core_logic.analysis_facade import initialize_analysis_system, get_analysis_system, AnalysisFacade
    print("Imported analysis_facade")
    from core_logic.analysis_logic import get_bitcoin_trend_summary
    print("Imported analysis_logic")
    from utils.general_utils import (
        get_top_n_by_volume, get_top_n_gainers, get_top_n_decliners
    )
    print("Imported general_utils")
    from core_logic.data_services import fetch_and_format_cmc_top_coins
    print("Imported data_services")
except ImportError as e:
    print(f"Error importing analysis modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("All imports successful") 