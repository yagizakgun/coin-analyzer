"""
Module Registry to manage all analysis modules in the system.
"""
import logging
from typing import Dict, List, Type, Optional

from .base_analysis import BaseAnalysisModule

class AnalysisModuleRegistry:
    """
    Registry to manage all analysis modules in the system.
    
    This class handles registration, lookup, and management of analysis modules.
    It ensures that modules are properly initialized and accessible.
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self.modules: Dict[str, BaseAnalysisModule] = {}
        self.logger = logging.getLogger("analysis.registry")
    
    def register_module(self, module: BaseAnalysisModule) -> None:
        """
        Register an analysis module with the registry.
        
        Args:
            module: The analysis module instance to register
        """
        module_name = module.name
        
        if module_name in self.modules:
            self.logger.warning(f"Module '{module_name}' is already registered. Overwriting.")
        
        self.modules[module_name] = module
        self.logger.info(f"Registered analysis module: {module_name} ({module.description})")
    
    def register_module_class(self, module_class: Type[BaseAnalysisModule], *args, **kwargs) -> None:
        """
        Instantiate and register a module class.
        
        Args:
            module_class: The analysis module class to instantiate and register
            *args: Positional arguments to pass to the module constructor
            **kwargs: Keyword arguments to pass to the module constructor
        """
        module = module_class(*args, **kwargs)
        self.register_module(module)
    
    def get_module(self, name: str) -> Optional[BaseAnalysisModule]:
        """
        Get a module by name.
        
        Args:
            name: The name of the module to retrieve
            
        Returns:
            Optional[BaseAnalysisModule]: The module instance or None if not found
        """
        if name not in self.modules:
            self.logger.warning(f"Module '{name}' not found in registry")
            return None
        
        return self.modules[name]
    
    def list_modules(self) -> List[Dict[str, str]]:
        """
        List all registered modules.
        
        Returns:
            List[Dict[str, str]]: List of module info dictionaries
        """
        return [module.module_info for module in self.modules.values()]
    
    def has_module(self, name: str) -> bool:
        """
        Check if a module is registered.
        
        Args:
            name: The name of the module to check
            
        Returns:
            bool: True if module is registered, False otherwise
        """
        return name in self.modules
    
    def unregister_module(self, name: str) -> bool:
        """
        Unregister a module.
        
        Args:
            name: The name of the module to unregister
            
        Returns:
            bool: True if module was unregistered, False if not found
        """
        if name in self.modules:
            del self.modules[name]
            self.logger.info(f"Unregistered module: {name}")
            return True
        return False

# Global instance of the registry
registry = AnalysisModuleRegistry() 