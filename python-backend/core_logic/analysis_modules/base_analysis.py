"""
Base Analysis Module that defines the common interface for all analysis modules.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAnalysisModule(ABC):
    """
    Base class for all analysis modules.
    
    All specialized analysis modules must inherit from this class and implement
    its abstract methods to ensure consistent interface across modules.
    """
    
    def __init__(self, name: str, description: str):
        """
        Initialize base analysis module.
        
        Args:
            name: Name of the analysis module
            description: Description of the analysis module
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"analysis.{name}")
    
    @abstractmethod
    async def perform_analysis(self, symbol: str, **kwargs) -> str:
        """
        Perform analysis on the specified symbol.
        
        Args:
            symbol: The cryptocurrency symbol to analyze
            **kwargs: Additional parameters specific to the analysis type
            
        Returns:
            str: Analysis result as a formatted string
        """
        pass
    
    @abstractmethod
    async def get_analysis_parameters(self) -> Dict[str, Any]:
        """
        Returns the parameters used by this analysis module.
        
        Returns:
            Dict[str, Any]: Dictionary of parameter names and their values
        """
        pass
    
    @property
    def module_info(self) -> Dict[str, str]:
        """
        Returns basic information about this module.
        
        Returns:
            Dict[str, str]: Dictionary with name and description
        """
        return {
            "name": self.name,
            "description": self.description
        }
    
    def log_info(self, message: str) -> None:
        """Helper method to log info messages with module context."""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str, exc_info: Optional[Exception] = None) -> None:
        """Helper method to log error messages with module context."""
        if exc_info:
            self.logger.error(f"[{self.name}] {message}", exc_info=exc_info)
        else:
            self.logger.error(f"[{self.name}] {message}") 