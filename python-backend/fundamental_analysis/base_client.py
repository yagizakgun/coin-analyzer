from abc import ABC, abstractmethod

class BaseFundamentalClient(ABC):
    """
    Abstract base class for fundamental analysis data clients.
    """
    def __init__(self, api_key=None):
        self.api_key = api_key

    @abstractmethod
    async def get_data(self, symbol: str, **kwargs):
        """
        Fetches fundamental data for a given symbol.

        Args:
            symbol (str): The cryptocurrency symbol (e.g., BTC, ETH).
            **kwargs: Additional arguments specific to the client.

        Returns:
            str: Formatted string of fundamental data or None if an error occurs.
        """
        pass 