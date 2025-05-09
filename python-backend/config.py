import os
from dotenv import load_dotenv
import logging

# Logger oluştur
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Exchange API Credentials
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
EXCHANGE_API_SECRET = os.getenv("EXCHANGE_API_SECRET")

# LLM API Credentials
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

# CoinMarketCap API Key
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

# Fundamental Analysis API Keys
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Load from .env file
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")    # Load from .env file (optional)

# Diğer Ayarlar
DEFAULT_KLINE_INTERVAL = "1h" # Varsayılan mum aralığı (örn: 15m, 1h, 4h, 1d)
DEFAULT_KLINE_LIMIT = 500 # Asenkron çağrılar için varsayılan kline limiti

if not EXCHANGE_API_KEY or not EXCHANGE_API_SECRET:
    logger.warning("Borsa API anahtarı (EXCHANGE_API_KEY) veya gizli anahtar (EXCHANGE_API_SECRET) .env dosyasında bulunamadı veya ayarlanmadı.")

if not LLM_API_KEY:
    logger.warning("LLM API anahtarı (LLM_API_KEY) .env dosyasında bulunamadı veya ayarlanmadı.")

if not COINMARKETCAP_API_KEY:
    logger.warning("CoinMarketCap API anahtarı (COINMARKETCAP_API_KEY) .env dosyasında bulunamadı veya ayarlanmadı.")

# Add warnings for Telegram Bot Token if not found
if not TELEGRAM_BOT_TOKEN:
    logger.warning("Telegram Bot Token (TELEGRAM_BOT_TOKEN) .env dosyasında bulunamadı veya ayarlanmadı.")