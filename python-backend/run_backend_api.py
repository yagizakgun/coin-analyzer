"""
Coin Analiz Botu API Server
Bu script, yalnızca API fonksiyonlarını sağlayan Flask uygulamasını başlatır.
"""

import os
from webapi.app import app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"Coin Analiz Botu API başlatılıyor... http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True) 