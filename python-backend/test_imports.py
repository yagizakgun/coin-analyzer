"""
Simple script to test imports.
"""
import sys
import os

print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Add the current directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print("Updated Python path:", sys.path)

try:
    print("Importing analysis modules...")
    from core_logic.analysis_modules import (
        BaseAnalysisModule,
        CryptoAnalysisModule,
        SpotTradingAnalysisModule,
        FuturesTradingAnalysisModule,
        registry
    )
    print("Successfully imported analysis modules")
    print(f"Available modules in registry: {registry.modules}")
    
    print("\nImporting analysis facade...")
    from core_logic.analysis_facade import initialize_analysis_system, get_analysis_system, AnalysisFacade
    print("Successfully imported analysis facade")
    
    print("\nAll imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 