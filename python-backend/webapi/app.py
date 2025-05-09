from flask import Flask, jsonify, request
from markupsafe import Markup
import asyncio
import os # os.path.join için
import sys # sys.path için
import markdown2 # ADDED
from datetime import datetime
from flask_cors import CORS # CORS desteği ekle

# Proje kök dizinini sys.path'e ekle (eğer app.py webapp klasöründeyse)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Artık ana projedeki modülleri import edebiliriz
from config import EXCHANGE_API_KEY, EXCHANGE_API_SECRET, LLM_API_KEY, CRYPTOPANIC_API_KEY # config.py'dan import
from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from fundamental_analysis.cryptopanic_client import CryptoPanicClient
from core_logic.analysis_logic import get_bitcoin_trend_summary # BTC özeti için
from main import analyze_coin, analyze_coin_at_date # analyze_coin_at_date eklendi

# Import modular analysis system
from core_logic.analysis_facade import initialize_analysis_system, get_analysis_system
from core_logic.analysis_modules import (
    CryptoAnalysisModule,
    SpotTradingAnalysisModule,
    FuturesTradingAnalysisModule
)

app = Flask(__name__)
# CORS yapılandırması - geliştirme sırasında '*' kullanılabilir, 
# production'da spesifik origin belirtilmelidir
# Örnek production için: CORS(app, resources={r"/*": {"origins": "https://your-nextjs-domain.com"}})
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}})

# Function to allow CORS headers for all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

async def run_analysis(symbol: str, module_name: str = "crypto_analysis"):
    """
    Analiz işlemini yürüten asenkron yardımcı fonksiyon.
    İstemcileri başlatır, BTC özetini alır ve asıl analizi yapar.
    
    Args:
        symbol: Symbol to analyze (e.g., "BTCUSDT")
        module_name: Name of the analysis module to use (default: "crypto_analysis")
        
    Returns a dictionary with 'success': True/False and 'data' or 'error'.
    """
    binance_client = None # Hata durumunda close çağrılabilmesi için None ile başlat
    try:
        # İstemcileri başlat
        # Not: exchange_client ve llm_client API anahtarlarını config.py üzerinden alıyor.
        binance_client = BinanceClient()
        gemini_client = GeminiClient()
        
        cryptopanic_client = None
        if CRYPTOPANIC_API_KEY:
            cryptopanic_client = CryptoPanicClient(api_key=CRYPTOPANIC_API_KEY)
        else:
            print("CryptoPanic API anahtarı ayarlanmamış, temel analiz verileri olmadan devam edilecek.")

        # Initialize the analysis system
        initialize_analysis_system(binance_client, gemini_client, cryptopanic_client)
        analysis_system = get_analysis_system()

        # Check if the requested module exists
        if not analysis_system.has_module(module_name):
            return {'success': False, 'error': f"Analiz modülü '{module_name}' bulunamadı."}
        
        # BTC Trend Özeti
        btc_summary = await get_bitcoin_trend_summary(binance_client)

        # Modular analysis with selected module
        if module_name in ["spot_trading_analysis", "futures_trading_analysis"]:
            # For modular system, use the facade
            result_markdown = await analysis_system.analyze(module_name, symbol)
        else:
            # Legacy analysis (crypto_analysis)
            result_markdown = await analyze_coin(binance_client, gemini_client, cryptopanic_client, symbol, btc_summary)
        
        if result_markdown:
            # Convert Markdown to HTML with extras
            result_html = markdown2.markdown(
                result_markdown,
                extras=["tables", "fenced-code-blocks", "header-ids", "footnotes", "strike", "code-friendly", "break-on-newline"]
            )
            return {'success': True, 'data': result_html}
        else:
            return {'success': False, 'error': "Analiz sonucu alınamadı veya boş."}

    except Exception as e:
        print(f"run_analysis içinde hata: {e}") # veya logging
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': f"Analiz sırasında bir hata oluştu: {e}"}
    finally:
        if binance_client:
            await binance_client.close()

async def run_historical_analysis(symbol: str, target_date_iso: str):
    """
    Geçmiş tarihli analiz işlemini yürüten asenkron yardımcı fonksiyon.
    İstemcileri başlatır ve asıl analizi yapar.
    Returns a dictionary with 'success': True/False and 'message' or 'error'.
    """
    binance_client = None # Hata durumunda close çağrılabilmesi için None ile başlat
    try:
        # İstemcileri başlat
        binance_client = BinanceClient()
        gemini_client = GeminiClient()
        
        cryptopanic_client = None
        if CRYPTOPANIC_API_KEY:
            cryptopanic_client = CryptoPanicClient(api_key=CRYPTOPANIC_API_KEY)
        else:
            print("CryptoPanic API anahtarı ayarlanmamış, temel analiz verileri olmadan devam edilecek.")

        # Geçmiş tarihli coin analizi
        # Bu fonksiyon da async, bu yüzden await ile çağrılmalı
        result = await analyze_coin_at_date(
            binance_client, 
            gemini_client, 
            cryptopanic_client, 
            symbol, 
            target_date_iso
        )
        
        if result:
            return {'success': True, 'data': f"Hafıza eğitimi başarılı. {symbol} için {target_date_iso} tarihli analiz kaydedildi."}
        else:
            return {'success': False, 'error': f"Hafıza eğitimi başarısız. {symbol} için {target_date_iso} tarihli analiz kaydedilemedi."}

    except Exception as e:
        print(f"run_historical_analysis içinde hata: {e}") # veya logging
        return {'success': False, 'error': f"Geçmiş tarihli analiz sırasında bir hata oluştu: {e}"}
    finally:
        if binance_client:
            await binance_client.close()

async def create_binance_client():
    """Helper function to create and return a Binance client."""
    return BinanceClient()

@app.route('/api/health', methods=['GET'])
def health_check():
    """API sağlık kontrolü için basit bir endpoint"""
    return jsonify({'status': 'ok', 'service': 'coin-analyzer-backend'})

@app.route('/api/modules', methods=['GET'])
def get_available_modules():
    """Returns a list of available analysis modules"""
    try:
        # We define the modules statically to avoid initializing clients
        modules = [
            {
                "id": "crypto_analysis",
                "name": "Temel Kripto Analizi",
                "description": "Comprehensive cryptocurrency technical and fundamental analysis"
            },
            {
                "id": "spot_trading_analysis",
                "name": "Spot Trading Analizi",
                "description": "Spot trading analysis with entry/exit points and risk management"
            },
            {
                "id": "futures_trading_analysis",
                "name": "Futures Trading Analizi",
                "description": "Futures/leverage trading analysis with risk management"
            }
        ]
        return jsonify({'success': True, 'modules': modules})
    except Exception as e:
        print(f"Error getting available modules: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze_route():
    selected_coin_symbol_for_response = None
    selected_module_for_response = None
    try:
        data = request.get_json()
        if not data or 'coin_symbol' not in data:
            return jsonify({'success': False, 'error': 'Coin sembolü eksik.'}), 400

        selected_coin_symbol = data.get('coin_symbol')
        selected_module = data.get('module', 'crypto_analysis')  # Default to crypto_analysis
        
        selected_coin_symbol_for_response = selected_coin_symbol # Store for response
        selected_module_for_response = selected_module # Store for response

        if not selected_coin_symbol:
            return jsonify({'success': False, 'error': 'Lütfen bir coin sembolü girin.'}), 400

        selected_coin_symbol = selected_coin_symbol.upper()
        if not selected_coin_symbol.endswith('USDT'):
            selected_coin_symbol += 'USDT'
        
        # run_analysis asenkron olduğu için asyncio.run ile çalıştırılmalı
        analysis_response = asyncio.run(run_analysis(selected_coin_symbol, selected_module)) # Pass module name

        if analysis_response['success']:
            return jsonify({
                'success': True, 
                'analysis_result': analysis_response['data'], 
                'selected_coin': selected_coin_symbol_for_response,
                'selected_module': selected_module_for_response
            })
        else:
            return jsonify({
                'success': False, 
                'error': analysis_response['error'], 
                'selected_coin': selected_coin_symbol_for_response,
                'selected_module': selected_module_for_response
            }), 500
            
    except RuntimeError as e:
        error_message = f"Analiz sırasında beklenmedik bir çalışma zamanı hatası: {e}"
        if "cannot run event loop while another loop is running" in str(e):
            print("RuntimeError: İç içe event loop sorunu. Çözüm gerekiyor.")
            error_message = "Analiz motoruyla ilgili bir yapılandırma sorunu oluştu (event loop)."
        else:
            print(f"Anlık analiz sırasında genel bir RuntimeError: {e}")
        return jsonify({
            'success': False, 
            'error': error_message, 
            'selected_coin': selected_coin_symbol_for_response,
            'selected_module': selected_module_for_response
        }), 500
    except Exception as e:
        print(f"Anlık analiz sırasında hata: {e}")
        return jsonify({
            'success': False, 
            'error': f"Analiz sırasında beklenmedik bir hata oluştu: {e}", 
            'selected_coin': selected_coin_symbol_for_response,
            'selected_module': selected_module_for_response
        }), 500

@app.route('/train_memory', methods=['POST'])
def train_memory_route():
    selected_coin_symbol_for_response = None
    target_date_for_response = None
    try:
        data = request.get_json()
        if not data or 'coin_symbol' not in data or 'target_date' not in data:
            return jsonify({'success': False, 'error': 'Coin sembolü veya hedef tarih eksik.'}), 400

        selected_coin_symbol = data.get('coin_symbol')
        target_date_str = data.get('target_date') # Expected format: YYYY-MM-DD

        selected_coin_symbol_for_response = selected_coin_symbol
        target_date_for_response = target_date_str

        if not selected_coin_symbol or not target_date_str:
            return jsonify({'success': False, 'error': 'Lütfen bir coin sembolü ve hedef tarih girin.'}), 400

        selected_coin_symbol = selected_coin_symbol.upper()
        if not selected_coin_symbol.endswith('USDT'):
            selected_coin_symbol += 'USDT'
        
        # Tarih formatını YYYY-MM-DD'den YYYY-MM-DDTHH:MM:SS ISO formatına çevir.
        # Varsayılan olarak günün başlangıcını (00:00:00) kullanabiliriz.
        try:
            # Kullanıcı sadece YYYY-MM-DD girdiyse, saat, dakika, saniye ekleyelim.
            # Veya kullanıcıdan tam ISO formatını almayı zorunlu kılabiliriz.
            # Şimdilik günün sonunu (23:59:59) kullanalım ki o günkü tüm veriler dahil olsun.
            dt_object = datetime.strptime(target_date_str, "%Y-%m-%d")
            # dt_object = dt_object.replace(hour=23, minute=59, second=59) # Gün sonu
            # Ya da günün başı daha mantıklı olabilir, kline'lar o günün başlangıcını içerir.
            dt_object = dt_object.replace(hour=0, minute=0, second=0) # Gün başı
            target_date_iso = dt_object.isoformat()
        except ValueError:
            return jsonify({'success': False, 'error': 'Geçersiz tarih formatı. Lütfen YYYY-MM-DD formatında girin.', 'selected_coin': selected_coin_symbol_for_response, 'target_date': target_date_for_response}), 400
        
        analysis_response = asyncio.run(run_historical_analysis(selected_coin_symbol, target_date_iso))

        if analysis_response['success']:
            return jsonify({
                'success': True, 
                'message': analysis_response['data'], 
                'selected_coin': selected_coin_symbol_for_response,
                'target_date': target_date_for_response
            })
        else:
            return jsonify({
                'success': False, 
                'error': analysis_response['error'], 
                'selected_coin': selected_coin_symbol_for_response,
                'target_date': target_date_for_response
            }), 500
            
    except RuntimeError as e:
        error_message = f"Geçmişe yönelik analiz sırasında beklenmedik bir çalışma zamanı hatası: {e}"
        if "cannot run event loop while another loop is running" in str(e):
            print("RuntimeError: İç içe event loop sorunu. Çözüm gerekiyor.")
            error_message = "Analiz motoruyla ilgili bir yapılandırma sorunu oluştu (event loop)."
        else:
            print(f"Geçmişe yönelik analiz sırasında genel bir RuntimeError: {e}")
        return jsonify({
            'success': False, 
            'error': error_message, 
            'selected_coin': selected_coin_symbol_for_response,
            'target_date': target_date_for_response
        }), 500
    except Exception as e:
        print(f"Geçmişe yönelik analiz sırasında hata: {e}")
        return jsonify({
            'success': False, 
            'error': f"Geçmişe yönelik analiz sırasında beklenmedik bir hata oluştu: {e}", 
            'selected_coin': selected_coin_symbol_for_response,
            'target_date': target_date_for_response
        }), 500

@app.route('/get_popular_coins', methods=['GET'])
def get_popular_coins():
    """
    Returns a list of popular USDT coin pairs from Binance, sorted by trading volume.
    """
    async def fetch_popular_coins():
        # Create a temporary client to fetch the data
        temp_binance_client = await create_binance_client()
        
        try:
            # Get 24hr ticker for all symbols
            all_tickers = await temp_binance_client.client.get_ticker()
            
            # Filter for USDT pairs and sort by volume
            usdt_pairs = [ticker for ticker in all_tickers if ticker['symbol'].endswith('USDT')]
            usdt_pairs.sort(key=lambda x: float(x.get('volume', 0) or 0) * float(x.get('lastPrice', 0) or 0), reverse=True)
            
            # Get top 30 pairs and format the response
            top_pairs = usdt_pairs[:30]
            result = []
            
            for pair in top_pairs:
                symbol = pair['symbol']
                base_asset = symbol.replace('USDT', '')
                price_change = pair.get('priceChangePercent', '0')
                
                # Add plus sign explicitly for positive changes
                if price_change and float(price_change) > 0:
                    price_change = f"+{price_change}"
                
                result.append({
                    'symbol': base_asset,
                    'fullSymbol': symbol,
                    'lastPrice': pair.get('lastPrice', 'N/A'),
                    'priceChange': price_change,
                    'volume': pair.get('volume', 'N/A'),
                })
            
            return {'success': True, 'data': result}
        finally:
            # Always close the client
            await temp_binance_client.close()
    
    try:
        # Use a single asyncio.run call to run the entire async operation
        result = asyncio.run(fetch_popular_coins())
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching popular coins: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 