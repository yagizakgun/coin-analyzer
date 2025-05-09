"""
Example script demonstrating how to use the modular analysis architecture.
"""
import asyncio
import logging
import sys
import os
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout)
    ]
)

logger = logging.getLogger("analysis_example")

# Import clients and analysis system
from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from fundamental_analysis.cryptopanic_client import CryptoPanicClient

from config import EXCHANGE_API_KEY, EXCHANGE_API_SECRET, LLM_API_KEY, CRYPTOPANIC_API_KEY
from core_logic.analysis_facade import initialize_analysis_system, get_analysis_system

async def run_modular_analysis_example():
    """Example function showing how to use the modular analysis system."""
    logger.info("Initializing clients...")
    
    # Initialize clients
    binance_client = BinanceClient(EXCHANGE_API_KEY, EXCHANGE_API_SECRET)
    llm_client = GeminiClient(LLM_API_KEY)
    
    # Initialize CryptoPanicClient if API key is available
    cryptopanic_client = None
    if CRYPTOPANIC_API_KEY:
        cryptopanic_client = CryptoPanicClient(CRYPTOPANIC_API_KEY)
    
    # Initialize the analysis system
    logger.info("Initializing analysis system...")
    analysis_system = initialize_analysis_system(
        binance_client, 
        llm_client, 
        cryptopanic_client
    )
    
    # List available modules
    modules = analysis_system.list_available_modules()
    logger.info(f"Available modules: {[module['name'] for module in modules]}")
    
    # Example: Perform analysis with each module
    symbol = "BTCUSDT"  # Example symbol
    
    for module_info in modules:
        module_name = module_info['name']
        logger.info(f"\n{'='*50}\nPerforming {module_name} analysis on {symbol}...\n{'='*50}")
        
        # Get module parameters
        params = await analysis_system.get_module_parameters(module_name)
        logger.info(f"Module '{module_name}' parameters: {params}")
        
        # Perform analysis with the module
        result = await analysis_system.analyze(module_name, symbol)
        
        # Print a preview of the result (first 500 chars)
        preview = result[:500] + "..." if len(result) > 500 else result
        logger.info(f"Analysis result preview:\n{preview}")
        
        # Save result to file
        output_dir = "analysis_results"
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, f"{symbol}_{module_name}_analysis.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        
        logger.info(f"Full analysis result saved to {output_file}")
    
    logger.info("\nAnalysis example completed.")

if __name__ == "__main__":
    # Run the async example
    asyncio.run(run_modular_analysis_example()) 