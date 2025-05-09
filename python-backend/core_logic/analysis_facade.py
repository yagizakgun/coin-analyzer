"""
Analysis Facade - Provides a simple interface to access the analysis modules.
"""
import logging
from typing import Dict, List, Any, Optional

from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from fundamental_analysis.cryptopanic_client import CryptoPanicClient
from core_logic.analysis_modules import (
    BaseAnalysisModule, 
    CryptoAnalysisModule, 
    SpotTradingAnalysisModule, 
    FuturesTradingAnalysisModule,
    registry
)

logger = logging.getLogger("analysis.facade")

class AnalysisFacade:
    """
    Facade for the analysis system that simplifies interaction with the various analysis modules.
    
    This class handles initialization of all analysis modules and provides a simplified
    interface for performing analysis with different modules.
    """
    
    def __init__(self, 
                 binance_client: BinanceClient, 
                 llm_client: GeminiClient, 
                 cryptopanic_client: Optional[CryptoPanicClient] = None):
        """
        Initialize the analysis facade.
        
        Args:
            binance_client: Binance API client
            llm_client: LLM API client
            cryptopanic_client: Optional CryptoPanic API client for fundamental analysis
        """
        self.binance_client = binance_client
        self.llm_client = llm_client
        self.cryptopanic_client = cryptopanic_client
        
        # Initialize and register modules
        self._initialize_modules()
    
    def _initialize_modules(self) -> None:
        """Initialize all available analysis modules."""
        # Initialize core crypto analysis module
        crypto_module = CryptoAnalysisModule(
            self.binance_client, 
            self.llm_client, 
            self.cryptopanic_client
        )
        
        # Initialize spot trading module
        spot_module = SpotTradingAnalysisModule(
            self.binance_client,
            self.llm_client
        )
        
        # Initialize futures trading module
        futures_module = FuturesTradingAnalysisModule(
            self.binance_client,
            self.llm_client
        )
        
        # Register modules in registry
        registry.register_module(crypto_module)
        registry.register_module(spot_module)
        registry.register_module(futures_module)
        
        logger.info(f"Initialized and registered {len(registry.modules)} analysis modules")
    
    def has_module(self, module_name: str) -> bool:
        """
        Check if a module with the given name is registered.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            bool: True if module exists, False otherwise
        """
        return registry.get_module(module_name) is not None
    
    async def analyze(self, 
                      module_name: str, 
                      symbol: str, 
                      **kwargs) -> str:
        """
        Perform analysis using a specified module.
        
        Args:
            module_name: Name of the module to use for analysis
            symbol: Cryptocurrency symbol to analyze
            **kwargs: Additional parameters to pass to the module
            
        Returns:
            str: Analysis result from the specified module
        """
        module = registry.get_module(module_name)
        if not module:
            available_modules = ", ".join(registry.modules.keys())
            error_message = f"Module '{module_name}' not found. Available modules: {available_modules}"
            logger.error(error_message)
            return f"❌ Analysis Error: {error_message}"
        
        logger.info(f"Performing {module_name} analysis on {symbol}")
        return await module.perform_analysis(symbol, **kwargs)
    
    def list_available_modules(self) -> List[Dict[str, str]]:
        """
        Get a list of all available analysis modules.
        
        Returns:
            List[Dict[str, str]]: List of module info dictionaries
        """
        return registry.list_modules()
    
    async def get_module_parameters(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Get parameters for a specific module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Optional[Dict[str, Any]]: Module parameters or None if module not found
        """
        module = registry.get_module(module_name)
        if not module:
            logger.error(f"Cannot get parameters: Module '{module_name}' not found")
            return None
        
        return await module.get_analysis_parameters()

# Create a global instance for easy imports
# This will be initialized by the application on startup
analysis_system = None  # type: Optional[AnalysisFacade]

def initialize_analysis_system(binance_client: BinanceClient, 
                               llm_client: GeminiClient,
                               cryptopanic_client: Optional[CryptoPanicClient] = None) -> AnalysisFacade:
    """
    Initialize the global analysis system.
    
    Args:
        binance_client: Binance API client
        llm_client: LLM API client
        cryptopanic_client: Optional CryptoPanic API client
        
    Returns:
        AnalysisFacade: The initialized analysis system
    """
    global analysis_system
    analysis_system = AnalysisFacade(binance_client, llm_client, cryptopanic_client)
    return analysis_system

def get_analysis_system() -> Optional[AnalysisFacade]:
    """
    Get the global analysis system.
    
    Returns:
        Optional[AnalysisFacade]: The global analysis system or None if not initialized
    """
    return analysis_system 