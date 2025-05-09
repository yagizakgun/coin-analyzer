# Coin Tarayıcı Bot Projesi Kontrol Listesi

## Faz 1: Temel Kurulum ve Fonksiyonellik (Tamamlandı)

- [x] **Proje Kurulumu**
  - [x] Proje klasörü oluşturuldu (`coin-scanner-bot`).
  - [x] Sanal ortam (`venv`) kuruldu ve aktive edildi.
  - [x] `requirements.txt` dosyası oluşturuldu ve temel bağımlılıklar eklendi (`requests`, `python-dotenv`).
  - [x] Git deposu başlatıldı ve `.gitignore` dosyası yapılandırıldı.
- [x] **Yapılandırma Yönetimi**
  - [x] `.env.example` dosyası oluşturuldu.
  - [x] `.env` dosyası (kullanıcı tarafından) API anahtarları için hazırlandı.
  - [x] `config.py` dosyası oluşturuldu (ortam değişkenlerini yüklemek için).
- [x] **Borsa Entegrasyonu (Binance)**
  - [x] `python-binance` kütüphanesi `requirements.txt`'e eklendi ve kuruldu.
  - [x] `exchange_client.py` oluşturuldu:
    - [x] API anahtarları ile `Client` başlatma.
    - [x] Sunucu saatini alma (`get_server_time`).
    - [x] Tüm ticker'ları alma (`get_all_tickers`) (temel fonksiyon eklendi, `main.py`'de `get_ticker` kullanılıyor).
    - [x] Geçmiş mum verilerini (OHLCV) alma (`get_historical_klines`).
- [x] **LLM Entegrasyonu (Gemini)**
  - [x] `google-generativeai` kütüphanesi `requirements.txt`'e eklendi ve kuruldu.
  - [x] `llm_client.py` oluşturuldu:
    - [x] API anahtarı ile `GenerativeModel` başlatma.
    - [x] Verilen prompt'a göre metin üretme (`generate_text`).
- [x] **Temel Bot Mantığı (`main.py`)**
  - [x] `pandas` kütüphanesi `requirements.txt`'e eklendi.
  - [x] İstemci (`BinanceClient`, `GeminiClient`) nesneleri başlatıldı.
  - [x] Hedef semboller listesi (`TARGET_SYMBOLS`) tanımlandı.
  - [x] Semboller üzerinde döngü ile analiz:
    - [x] Geçmiş mum verileri ve anlık ticker bilgisi çekildi.
    - [x] Veriler LLM için formatlandı (`format_price_data_for_llm`).
    - [x] LLM'e analiz için prompt gönderildi.
    - [x] LLM yanıtı ekrana yazdırıldı.
  - [x] API hız limitleri için bekleme (`time.sleep`) eklendi.
  - [x] Temel hata yönetimi (`try-except` blokları) eklendi.

---

## Faz 2: Geliştirmeler ve Analiz Derinliği (Devam Ediyor)

- [x] **Teknik İndikatörler**
  - [x] `pandas-ta` kütüphanesini `requirements.txt`'e ekle ve kur.
    - [x] **Not:** `numpy v2.0+` ile uyumluluk sorunu yaşandı ve `numpy==1.26.3` sürümüne sabitlenerek çözüldü.
  - [x] `main.py` içinde indikatör hesaplama fonksiyonları ekle (RSI, MACD, SMA).
  - [x] Hesaplanan indikatör değerlerini `format_price_data_for_llm` fonksiyonuna dahil et.
  - [x] LLM prompt'unu bu indikatörleri dikkate alacak şekilde güncelle.
- [x] **Gelişmiş LLM Prompt Mühendisliği**
  - [x] LLM'e daha fazla bağlam sağla:
    - [x] Programatik olarak Bitcoin (BTCUSDT) trend özeti oluşturup (fiyat, 24s değişim, RSI, SMA, MACD durumları) altcoin analizleri için LLM prompt'una ekle.
    - [x] LLM prompt'unu, sağlanan Bitcoin özetini dikkate alması ve analizinde "Bitcoin Etkisi" başlığı altında yorumlaması için güncelle.
  - [x] LLM'den daha spesifik ve yapılandırılmış çıktılar iste:
    - [x] Analiz çıktısı için belirli başlıklar içeren bir format tanımla (Genel Değerlendirme, Teknik İndikatör Analizi, Bitcoin Etkisi, Önemli Fiyat Seviyeleri, Potansiyel Alım Stratejisi, Kısa/Orta Vade Potansiyel).
    - [x] Potansiyel giriş aralığı, stop-loss seviyesi (yasal uyarı ile) gibi eyleme yönelik bilgiler talep et.
  - [ ] Farklı prompt şablonlarını dene ve sonuçları karşılaştır (Gelecekteki iyileştirme).
- [ ] **Coin Listesini Dinamikleştirme ve Kullanıcı Seçimi**
  - [x] CoinMarketCap API entegrasyonu (`market_data_client.py`) ile piyasa değerine göre top N coin listesi oluşturuldu.
  - [x] Binance API (`exchange_client.py` ve `main.py`) ile 24 saatlik hacim, en çok yükselenler ve en çok düşenler listeleri oluşturuldu.
  - [x] `main.py` içinde bu listeler kullanıcıya sunularak analiz edilecek coinin interaktif olarak seçilmesi sağlandı.
  - [x] `TARGET_SYMBOLS` statik listesi kaldırıldı, yerine dinamik ve kullanıcı seçimli yapı getirildi.
  - [ ] Coinleri filtrelemek için ek kriterler (örn: min. hacim, fiyat aralığı - *kısmen hacim sıralaması ile mevcut, daha detaylı filtreleme gelecekte eklenebilir*).
- [ ] **Veri Saklama ve Geçmiş Takibi**
  - [ ] Analiz sonuçlarını (sembol, tarih/saat, güncel fiyat, LLM kararı, LLM gerekçesi, önemli seviyeler, BTC özeti) kaydet:
    - [ ] Seçenek 1: CSV dosyasına (`results.csv`).
    - [ ] Seçenek 2: Basit bir SQLite veritabanına.
  - [ ] `main.py` içine kayıt fonksiyonları ekle.
  - [ ] (İleri Seviye) LLM tavsiyelerinin geçmiş performansını izlemek için bir yapı düşün.
- [x] **Hata Yönetimi ve Kayıt Tutma (Logging)**
  - [x] Python'un `logging` modülünü kullanarak daha yapılandırılmış loglama ekle (`main.py` ve diğer modüllerde).
  - [x] Farklı log seviyeleri (DEBUG, INFO, WARNING, ERROR) kullan.
  - [x] Logları bir dosyaya kaydet (Örn: `bot.log`).
  - [ ] API bağlantı hataları, veri eksikliği gibi durumlar için daha spesifik hata mesajları ve retry mekanizmaları (isteğe bağlı).

---

## Faz 3: Otomasyon ve İyileştirme (Gelecek Değerlendirmeleri)

- [ ] **Kullanıcı Arayüzü / Bildirimler**
  - [ ] Basit bir CLI (Komut Satırı Arayüzü) için `argparse` veya `Click` kütüphanesini kullan:
    - [ ] Kullanıcının `TARGET_SYMBOLS`, `KLINE_INTERVAL`, `KLINE_HISTORY_PERIOD` gibi parametreleri komut satırından girmesine izin ver.
    - [ ] Sadece belirli bir coini analiz etme seçeneği.
  - [ ] (İleri Seviye) Önemli alım/satım sinyalleri için bildirim sistemi:
    - [ ] E-posta ile bildirim.
    - [ ] Telegram/Discord botu ile bildirim.
- [x] **Kod Yapılandırması ve Modülerlik İyileştirmeleri**
  - [x] `utils.py` gibi yardımcı fonksiyonlar için ayrı dosyalar oluştur (Örn: veri formatlama, tarih işlemleri). (`utils/general_utils.py` oluşturuldu)
  - [x] `constants.py` dosyası ile sabit değerleri (varsayılan semboller, aralıklar vb.) merkezi bir yerden yönet. (`core_logic/constants.py` oluşturuldu)
  - [x] Sınıfları ve fonksiyonları daha küçük, iyi tanımlanmış ve test edilebilir parçalara böl. (Fonksiyonlar `clients`, `core_logic`, `handlers`, `utils` klasörlerine taşındı).
- [x] **Performans ve Optimizasyon**
  - [x] Çok sayıda coin taranacaksa API çağrılarını optimize et:
    - [x] `asyncio` ve `python-binance` kütüphanesinin `AsyncClient`'ı ile eşzamansız (asynchronous) API çağrıları başarıyla uygulandı.
- [x] **Çoklu Zaman Dilimi Analizi**
  - [x] Tek bir zaman dilimi (Örn: 1 saatlik) yerine birden fazla zaman diliminden (Örn: 15dk, 1s, 4s, 1g, 1h) veri alıp LLM'e sunarak daha kapsamlı analiz yap.
  - [x] `format_price_data_for_llm` ve prompt'u buna göre güncelle.

---

## Faz 4: İleri Düzey Özellikler (Vizyon)

- [ ] **Geriye Dönük Test (Backtesting) Çerçevesi**
  - [ ] LLM stratejisinin geçmiş veriler üzerinde nasıl performans göstereceğini test etmek için basit bir yapı oluştur.
  - [ ] Bu, stratejinin etkinliği hakkında fikir verebilir ve prompt'ları iyileştirmek için kullanılabilir.
- [ ] **Temel Analiz Verileri Entegrasyonu (Çok İleri Seviye)**
  - [x] CryptoPanic API ile haberleri çekme modülü eklendi (`fundamental_analysis/cryptopanic_client.py`).
  - [x] CryptoPanic API anahtarı yapılandırmaya (`config.py`, `.env.example`) eklendi.
  - [x] Haber verileri LLM prompt şablonlarına (`core_logic/constants.py`) ve `main.py` analiz akışına entegre edildi.
  - [ ] Sosyal medya duyarlılığı (Örn: Twitter API) entegrasyonu.
  - [ ] Proje güncellemeleri (Örn: proje web sitelerinden scraping) entegrasyonu.
  - [ ] Diğer potansiyel temel analiz veri kaynakları.
  - *Not: Bu, karmaşıklığı ve geliştirme süresini önemli ölçüde artırır.*
- [ ] **Web Arayüzü / Kontrol Paneli (Dashboard)**
  - [ ] Flask veya Django gibi bir web framework ile basit bir arayüz oluşturarak:
    - [ ] Analiz sonuçlarını ve grafiklerini göster.
    - [ ] Botu kontrol etme (başlatma, durdurma, ayarları değiştirme).

---

Bu kontrol listesi projenin yol haritasını belirlememize yardımcı olacaktır. Önceliklendirerek adımları teker teker ele alabiliriz. 