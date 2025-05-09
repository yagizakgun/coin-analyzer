'''Telegram Bot Integration for Coin Analyzer'''
import logging
import sys  # Added
import os  # Added
from datetime import datetime  # Added for timing analysis requests

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Add the parent directory (python-backend) to sys.path
# This allows imports from 'config' and 'core_logic' when running this script directly
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_CURRENT_DIR)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

try:
    from config import TELEGRAM_BOT_TOKEN
except ImportError:
    logging.getLogger(__name__).critical(
        "Could not import TELEGRAM_BOT_TOKEN from config.py. "
        "Ensure 'config.py' exists in the 'python-backend' directory and contains TELEGRAM_BOT_TOKEN."
    )
    TELEGRAM_BOT_TOKEN = "FALLBACK_TOKEN_CONFIG_PY_MISSING"  # Bot will warn and likely fail to start

# Try to import core components needed for analysis
_ANALYSIS_READY = False
_import_error = ""

try:
    # Import required clients
    from clients.exchange_client import BinanceClient
    from clients.llm_client import GeminiClient
    from fundamental_analysis.cryptopanic_client import CryptoPanicClient
    
    # Import the new analysis system
    from core_logic.analysis_facade import initialize_analysis_system, get_analysis_system
    
    # Import config for API keys
    from config import EXCHANGE_API_KEY, EXCHANGE_API_SECRET, LLM_API_KEY, CRYPTOPANIC_API_KEY
    
    # Initialize clients
    _exchange_client = BinanceClient(EXCHANGE_API_KEY, EXCHANGE_API_SECRET)
    _llm_client = GeminiClient(LLM_API_KEY)
    
    # Initialize CryptoPanicClient if API key is available
    _cryptopanic_client = None
    if CRYPTOPANIC_API_KEY:
        _cryptopanic_client = CryptoPanicClient(CRYPTOPANIC_API_KEY)
    
    # Initialize the analysis system
    initialize_analysis_system(_exchange_client, _llm_client, _cryptopanic_client)
    
    _ANALYSIS_READY = True
    logging.getLogger(__name__).info("Successfully initialized the modular analysis system")
    
except ImportError as e:
    _import_error = f"Error importing required components: {str(e)}"
    logging.getLogger(__name__).error(f"Could not import required components: {e}")

if not _ANALYSIS_READY:
    # Define a placeholder if analysis system couldn't be initialized
    async def perform_analysis(coin_symbol: str, module_name: str = "crypto_analysis") -> str:
        return (f"❌ {coin_symbol} analiz edilemiyor. İçe aktarma hataları: {_import_error}. "
                f"Lütfen telegram_bot.py dosyasının doğru konumda olduğundan ve tüm bağımlılıkların kurulu olduğundan emin olun.")

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Updated analysis command to use the modular analysis system
async def analyze_coin_command(coin_symbol: str, module_name: str = "crypto_analysis") -> str:
    """
    Analyze a cryptocurrency using the modular analysis system.
    
    Args:
        coin_symbol: The cryptocurrency symbol to analyze (e.g., 'BTCUSDT')
        module_name: The analysis module to use (default: "crypto_analysis")
        
    Returns:
        str: Analysis result or error message
    """
    logger.info(f"Attempting to analyze coin: {coin_symbol} with module: {module_name}")
    try:
        # Start a timer to track how long the analysis takes
        start_time = datetime.now()
        
        # Standardize symbol format (add USDT if not present)
        if not any(coin_symbol.upper().endswith(suffix) for suffix in ['USDT', 'BTC', 'ETH', 'BUSD']):
            coin_symbol = f"{coin_symbol.upper()}USDT"
            logger.info(f"Standardized symbol to {coin_symbol}")
        else:
            coin_symbol = coin_symbol.upper()
            
        logger.info(f"Starting analysis for {coin_symbol} with module {module_name}...")
        
        # Get the analysis system
        analysis_system = get_analysis_system()
        if not analysis_system:
            return f"❌ Analysis system is not initialized. Please check the logs for details."
        
        # Call the analysis function from the selected module
        analysis_result = await analysis_system.analyze(module_name, coin_symbol)
        
        # Calculate and log time taken
        time_taken = (datetime.now() - start_time).total_seconds()
        logger.info(f"Analysis for {coin_symbol} completed in {time_taken:.2f} seconds")
        
        # Truncate very long results if needed for logging
        log_preview = str(analysis_result)[:100] + "..." if len(str(analysis_result)) > 100 else str(analysis_result)
        logger.info(f"Analysis result for {coin_symbol} (preview): {log_preview}")
        
        return str(analysis_result)  # Ensure the result is a string
    except Exception as e:
        logger.error(f"Error during analysis of {coin_symbol}: {e}", exc_info=True)
        return f"❌ {coin_symbol} analizi sırasında hata: {str(e)}. Lütfen daha sonra tekrar deneyin veya yönetici ile iletişime geçin."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Sends a welcome message when the /start command is issued.'''
    user = update.effective_user
    await update.message.reply_html(
        rf"Merhaba {user.mention_html()}! Analiz etmek için bana bir kripto para birimi sembolü (örn: BTCUSDT) gönder.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Sends a help message when the /help command is issued.'''
    # Get list of available modules
    available_modules = []
    if _ANALYSIS_READY:
        analysis_system = get_analysis_system()
        if analysis_system:
            modules_info = analysis_system.list_available_modules()
            available_modules = [f"{m['name']} - {m['description']}" for m in modules_info]
    
    help_text = "Analiz için bana bir kripto para birimi sembolü gönder (örn: BTCUSDT).\n\n"
    
    if available_modules:
        help_text += "Kullanılabilir analiz modülleri:\n"
        for module in available_modules:
            help_text += f"• {module}\n"
        
        help_text += "\nÖzel bir modül kullanmak için: /analyze_with [modül_adı] [coin]\n"
        help_text += "Örnek: /analyze_with spot_trading_analysis BTCUSDT"
    
    await update.message.reply_text(help_text)

async def analyze_with_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Handles the /analyze_with command to analyze a coin with a specific module.'''
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Lütfen modül adı ve coin sembolü belirtin.\n"
            "Örnek: /analyze_with spot_trading_analysis BTCUSDT"
        )
        return
    
    module_name = context.args[0].lower()
    coin_symbol = context.args[1].upper()
    
    # Send a "typing" action to show the bot is working
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Reply with analysis start message
    waiting_message = await update.message.reply_text(
        f"⏳ {coin_symbol} analizi '{module_name}' modülü ile yapılıyor...\n"
        f"Bu işlem biraz zaman alabilir."
    )
    
    try:
        # Perform the analysis with the specified module
        analysis_result = await analyze_coin_command(coin_symbol, module_name)
        
        # Delete the waiting message
        try:
            await waiting_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete waiting message: {e}")
        
        # Format the analysis result for better readability
        formatted_result = format_analysis_for_telegram(analysis_result, coin_symbol)
        
        # Split long messages if needed (Telegram has a 4096 character limit)
        if len(formatted_result) <= 4000:
            await update.message.reply_text(formatted_result, parse_mode="HTML")
        else:
            # Split into logical sections with a max size of 4000 characters
            chunks = smart_split_message(formatted_result, max_length=4000)
            for i, chunk in enumerate(chunks):
                part_header = f"<b>Bölüm {i+1}/{len(chunks)}</b> - " if len(chunks) > 1 else ""
                await update.message.reply_text(f"{part_header}{chunk}", parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Error processing /analyze_with command: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Üzgünüm, '{module_name}' modülü ile {coin_symbol} analiz edilirken bir hata oluştu.\n"
            f"Hata detayları: {str(e)}"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Handles non-command messages and attempts to analyze them as coin symbols.'''
    message_text = update.message.text
    user_name = update.effective_user.first_name if update.effective_user else "Kullanıcı"
    logger.info(f"Received message from {user_name}: {message_text}")
    
    # Clean up the message text - remove spaces and convert to uppercase
    clean_text = message_text.strip().upper().replace(" ", "")
    
    # Check if it looks like a coin symbol
    common_suffixes = ["USDT", "USTD", "BTC", "ETH", "BUSD"]
    
    is_coin_symbol = False
    # Check for common suffixes
    if any(clean_text.endswith(suffix) for suffix in common_suffixes):
        is_coin_symbol = True
    # Or if it's a common coin without suffix (we'll add USDT)
    elif len(clean_text) >= 2 and clean_text.isalnum():
        is_coin_symbol = True
        # Symbol will be standardized in analyze_coin_command
    
    if is_coin_symbol:
        # Send a "typing" action to show the bot is working
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Reply with analysis start message
        waiting_message = await update.message.reply_text(
            f"⏳ {clean_text} analiz ediliyor...\n"
            f"Teknik ve temel verileri toplarken bu işlem biraz zaman alabilir."
        )
        
        try:
            # Perform the analysis with the default module (crypto_analysis)
            analysis_result = await analyze_coin_command(clean_text)
            
            # Delete the waiting message
            try:
                await waiting_message.delete()
            except Exception as e:
                logger.warning(f"Could not delete waiting message: {e}")
            
            # Format the analysis result for better readability
            formatted_result = format_analysis_for_telegram(analysis_result, clean_text)
            
            # Split long messages if needed (Telegram has a 4096 character limit)
            if len(formatted_result) <= 4000:
                await update.message.reply_text(formatted_result, parse_mode="HTML")
            else:
                # Split into logical sections with a max size of 4000 characters
                chunks = smart_split_message(formatted_result, max_length=4000)
                for i, chunk in enumerate(chunks):
                    part_header = f"<b>Bölüm {i+1}/{len(chunks)}</b> - " if len(chunks) > 1 else ""
                    await update.message.reply_text(f"{part_header}{chunk}", parse_mode="HTML")
                    
        except Exception as e:
            logger.error(f"Error analyzing {clean_text} in handle_message: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Üzgünüm, {clean_text} analiz edilirken bir hata oluştu.\n"
                f"Hata detayları: {str(e)}"
            )
    else:
        await update.message.reply_text(
            "Lütfen geçerli bir kripto para birimi sembolü gönder (örn: BTC, ETH, SOL, BTCUSDT, ETHBTC).\n"
            "Kripto parayı analiz edip teknik ve temel içgörüler sunacağım."
        )

def format_analysis_for_telegram(analysis_text: str, symbol: str) -> str:
    """
    Formats the raw analysis text to make it more readable in Telegram
    using HTML tags for better visualization.
    
    Args:
        analysis_text: The raw analysis result text
        symbol: The cryptocurrency symbol
        
    Returns:
        str: HTML formatted analysis text
    """
    # Escape HTML special characters to prevent formatting issues
    # But be careful not to double-escape if text might already have some HTML
    if "<" not in analysis_text and ">" not in analysis_text:
        analysis_text = analysis_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Add title
    formatted_text = f"<b>📊 {symbol} ANALİZ RAPORU</b>\n\n"
    
    # Process the analysis text to add formatting
    # Look for sections and highlight them
    sections = [
        "Fiyat Bilgisi", "Teknik Analiz", "Temel Analiz", "Özet",
        "Destek ve Direnç", "Hacim Analizi", "İndikatörler", "Trend Analizi"
    ]
    
    # Split the text by lines to process each line
    lines = analysis_text.split('\n')
    
    for line in lines:
        # Format section headers
        is_section = False
        for section in sections:
            if section in line:
                # Skip adding the symbol title if it's already in our header
                if "Coin Sembolü:" in line:
                    continue
                
                # Format section headers with bold and emoji
                formatted_text += f"\n<b>{'=' * 30}</b>\n"
                formatted_text += f"<b>{line}</b>\n"
                is_section = True
                break
        
        # If it's not a section header, check for other patterns
        if not is_section:
            # Highlight values in technical indicators
            if any(indicator in line for indicator in ["RSI", "MACD", "SMA", "EMA", "ATR", "Bollinger"]):
                # Split by colon to separate label from value
                if ":" in line:
                    parts = line.split(":", 1)
                    formatted_text += f"<b>{parts[0]}:</b>{parts[1]}\n"
                else:
                    formatted_text += f"{line}\n"
            
            # Highlight price information
            elif "Fiyat" in line or "USDT" in line:
                formatted_text += f"<b>{line}</b>\n"
            
            # Add warning emoji for negative statements
            elif any(word in line.lower() for word in ["düşüş", "azal", "negatif", "olumsuz", "risk"]):
                formatted_text += f"⚠️ {line}\n"
            
            # Add positive emoji for positive statements
            elif any(word in line.lower() for word in ["yüksel", "artış", "pozitif", "olumlu", "fırsat"]):
                formatted_text += f"✅ {line}\n"
            
            # Default formatting
            else:
                formatted_text += f"{line}\n"
    
    # Add signature at the end
    formatted_text += "\n<i>Bu analiz otomatik olarak oluşturulmuştur. Yatırım tavsiyesi değildir.</i>"
    
    return formatted_text

def smart_split_message(text: str, max_length: int = 4000) -> list:
    """
    Splits a long message into smaller chunks at logical break points
    like paragraph or section boundaries.
    
    Args:
        text: The text to split
        max_length: Maximum length of each chunk
        
    Returns:
        list: List of message chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Section break markers
    section_markers = ["<b>==", "\n\n", "</b>\n"]
    
    # Split by newlines to process paragraph by paragraph
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit
        if len(current_chunk) + len(paragraph) + 1 > max_length:
            # First, try to find a good breaking point if current chunk is not empty
            if current_chunk:
                # Look for section breaks for a cleaner split
                break_found = False
                for marker in section_markers:
                    if marker in current_chunk:
                        last_marker_pos = current_chunk.rindex(marker)
                        if last_marker_pos > len(current_chunk) // 2:  # If marker is in second half
                            chunks.append(current_chunk[:last_marker_pos])
                            current_chunk = current_chunk[last_marker_pos:] + '\n' + paragraph
                            break_found = True
                            break
                
                # If no good breaking point, just add the chunk as is
                if not break_found:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
            else:
                # If we need to split a single paragraph
                chunks.append(paragraph[:max_length])
                remaining = paragraph[max_length:]
                
                # If there's more text remaining, process it in chunks of max_length
                while remaining:
                    if len(remaining) <= max_length:
                        current_chunk = remaining
                        break
                    else:
                        chunks.append(remaining[:max_length])
                        remaining = remaining[max_length:]
        else:
            # Add paragraph with newline if current chunk is not empty
            if current_chunk:
                current_chunk += '\n' + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def run_bot(telegram_token: str):
    '''Starts the Telegram bot.'''
    application = Application.builder().token(telegram_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze_with", analyze_with_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting Telegram bot polling...")
    application.run_polling()

if __name__ == '__main__':
    if (not TELEGRAM_BOT_TOKEN or
            TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or
            TELEGRAM_BOT_TOKEN == "FALLBACK_TOKEN_CONFIG_PY_MISSING"):
        logger.critical(
            "CRITICAL: Telegram Bot Token is not configured or is still a placeholder. "
            "Please set your actual bot token in 'python-backend/config.py' "
            "as the value of the 'TELEGRAM_BOT_TOKEN' variable."
        )
        logger.critical("Bot will not start without a valid token.")
        sys.exit("Telegram token not configured. Exiting.")  # Exit if token is invalid
    else:
        # Mask parts of the token for security in logs
        masked_token = TELEGRAM_BOT_TOKEN[:4] + "****" + TELEGRAM_BOT_TOKEN[-4:]
        logger.info(f"Attempting to start bot with token: {masked_token}")
        if not _ANALYSIS_READY:
            logger.warning("Bot is using a PLACEHOLDER analysis function because required components could not be imported.")
            logger.warning(f"Import errors: {_import_error}")
        run_bot(TELEGRAM_BOT_TOKEN)
