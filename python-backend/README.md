# Coin Analiz Botu

Kripto para analizleri için yapay zeka destekli analiz botu.

## Mimari

Bu proje iki ana bileşenden oluşur:

1. **Python Backend (API)**: Veri toplama, analiz ve LLM (Large Language Model) entegrasyonu sağlar.
2. **Next.js Frontend**: Kullanıcı arayüzü ve etkileşimini sağlar.

## Kurulum ve Çalıştırma

### Python Backend Kurulumu

1. Python 3.10+ yüklü olduğundan emin olun
2. Sanal ortam oluşturun ve aktive edin:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```
3. Gereksinimleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
4. `.env` dosyasını oluşturun (`.env.example` dosyasını kopyalayarak başlayabilirsiniz)
   ```
   EXCHANGE_API_KEY=your_binance_api_key
   EXCHANGE_API_SECRET=your_binance_api_secret
   LLM_API_KEY=your_gemini_api_key
   CRYPTOPANIC_API_KEY=your_cryptopanic_api_key
   ```

### Backend API'yi Çalıştırma

Python backend'i API modunda çalıştırmak için:

```bash
python run_backend_api.py
```

API sunucusu http://localhost:5000 adresinde çalışacaktır.

### Next.js Frontend'i Çalıştırma

1. `nextjs-coin-analyzer` klasörüne gidin:
   ```bash
   cd nextjs-coin-analyzer
   ```
2. Bağımlılıkları yükleyin:
   ```bash
   npm install
   # veya
   yarn install
   ```
3. `.env.local` dosyasını oluşturun:
   ```
   BACKEND_URL=http://localhost:5000
   ```
4. Geliştirme sunucusunu başlatın:
   ```bash
   npm run dev
   # veya
   yarn dev
   ```
5. Tarayıcınızda http://localhost:3000 adresini açın

## API Endpoints

- `/analyze` - Coin analizi
- `/train_memory` - Hafıza eğitimi
- `/get_popular_coins` - Popüler coinleri getirme
- `/api/health` - API sağlık kontrolü

## Notlar

- Backend API sunucusu çalışır durumda olmalıdır.
- Frontend ve backend arasındaki iletişim CORS ile korunur.
- Production ortamına taşırken CORS ayarlarını güncelleyin. 