# Modüler Analiz Sistemi

Bu belge, kripto para analiz sisteminin modüler mimarisini açıklar ve yeni analiz modülleri eklemeyi gösterir.

## Genel Bakış

Modüler analiz sistemi, farklı türlerdeki kripto para analizlerini ayrı, bağımsız modüller halinde organize etmek için tasarlanmıştır. Bu yaklaşım şu avantajları sağlar:

- **Esneklik:** Farklı analiz türleri için özel modüller
- **Bakım Kolaylığı:** Her modül bağımsız olarak güncellenebilir
- **Genişletilebilirlik:** Yeni analiz türleri kolayca eklenebilir
- **Tutarlı Arayüz:** Tüm modüller aynı temel arayüzü uygular

## Mevcut Analiz Modülleri

Şu anda sistem aşağıdaki analiz modüllerini içermektedir:

1. **CryptoAnalysisModule (crypto_analysis)** - Kapsamlı teknik ve temel kripto para analizi
2. **SpotTradingAnalysisModule (spot_trading_analysis)** - Spot alım-satım için giriş/çıkış noktaları ve risk yönetimi
3. **FuturesTradingAnalysisModule (futures_trading_analysis)** - Vadeli işlem/kaldıraçlı işlem analizi ve risk değerlendirmesi

## Modüler Sistemi Kullanma

### Komut Satırı Arayüzü

Modüler analiz sistemini kullanmak için:

1. `modular_main.py` scripti çalıştırın:
   ```
   python modular_main.py
   ```

2. Görüntülenen listeden analiz etmek istediğiniz kripto parayı seçin.

3. Kullanmak istediğiniz analiz modülünü seçin:
   ```
   --- Analiz Modülleri ---
   No.  Modül Adı                Açıklama                                           
   1.   crypto_analysis          Comprehensive cryptocurrency technical and fundamental analysis
   2.   spot_trading_analysis    Spot trading analysis with entry/exit points and risk management
   3.   futures_trading_analysis Futures/leverage trading analysis with risk management
   
   👉 Kullanmak istediğiniz analiz modülünün numarasını girin (varsayılan: 1): 
   ```

4. Seçilen modül kullanılarak analiz gerçekleştirilecek ve sonuçlar ekranda gösterilecektir.

### Programlama Arayüzü

Kendi uygulamanızda modüler analiz sistemini kullanmak için:

```python
from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from fundamental_analysis.cryptopanic_client import CryptoPanicClient
from core_logic.analysis_facade import initialize_analysis_system

# İstemcileri başlat
binance_client = BinanceClient(EXCHANGE_API_KEY, EXCHANGE_API_SECRET)
llm_client = GeminiClient(LLM_API_KEY)
cryptopanic_client = CryptoPanicClient(CRYPTOPANIC_API_KEY)

# Analiz sistemini başlat
analysis_system = initialize_analysis_system(
    binance_client, 
    llm_client, 
    cryptopanic_client
)

# Kullanılabilir modülleri listele
available_modules = analysis_system.list_available_modules()
print(available_modules)  # [{'name': 'crypto_analysis', 'description': '...'}, ...]

# Analiz yap
result = await analysis_system.analyze(
    "crypto_analysis",  # veya "spot_trading_analysis", "futures_trading_analysis"
    "BTCUSDT"
)
print(result)
```

## Yeni Analiz Modülü Ekleme

Sisteme yeni bir analiz modülü eklemek için:

1. `core_logic/analysis_modules/` dizininde yeni bir Python dosyası oluşturun
2. `BaseAnalysisModule` sınıfından miras alan bir sınıf tanımlayın
3. `perform_analysis` ve `get_analysis_parameters` metotlarını uygulayın
4. Modülü registry'e kaydedin

Örnek:

```python
from typing import Dict, Any, Optional
from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from .base_analysis import BaseAnalysisModule

class YeniAnalysisModule(BaseAnalysisModule):
    def __init__(self, binance_client: BinanceClient, llm_client: GeminiClient):
        super().__init__(
            name="yeni_analysis",
            description="Yeni tür kripto para analizi"
        )
        self.binance_client = binance_client
        self.llm_client = llm_client
    
    async def perform_analysis(self, symbol: str, **kwargs) -> str:
        # Analiz mantığını burada uygulayın
        return f"{symbol} için yeni analiz sonuçları..."
    
    async def get_analysis_parameters(self) -> Dict[str, Any]:
        return {
            "param1": "value1",
            "param2": "value2"
        }
```

Modülü yükleme:

```python
# core_logic/analysis_facade.py içindeki _initialize_modules metodunu güncelleyin:
def _initialize_modules(self) -> None:
    # Mevcut modüller...
    
    # Yeni modül
    yeni_modul = YeniAnalysisModule(
        self.binance_client,
        self.llm_client
    )
    
    # Registry'e kaydet
    registry.register_module(yeni_modul)
```

## Mimari Detaylar

Modüler analiz sistemi aşağıdaki bileşenlerden oluşur:

- **BaseAnalysisModule:** Tüm analiz modülleri için temel sınıf
- **AnalysisModuleRegistry:** Modülleri yönetir ve erişim sağlar
- **AnalysisFacade:** Modül sistemi için basit bir arayüz sağlar

### Dizin Yapısı

```
python-backend/
├── core_logic/
│   ├── analysis_modules/
│   │   ├── __init__.py
│   │   ├── base_analysis.py          # Temel modül sınıfı
│   │   ├── module_registry.py        # Modül kayıt sistemi
│   │   ├── crypto_analysis.py        # Kripto analiz modülü
│   │   ├── spot_trading_analysis.py  # Spot ticaret analiz modülü
│   │   └── futures_trading_analysis.py # Vadeli işlem analiz modülü
│   ├── analysis_facade.py            # Analiz sistemi arayüzü
│   └── ...
└── ...
```

## Notlar ve Sınırlamalar

- Her modül analiz yapmak için gerekli tüm bağımlılıklara erişimi olmalıdır
- Modüller iyi dokümante edilmelidir
- Yeni modüller eklerken mevcut kod ve veri yapılarını inceleyerek tutarlılığı koruyun 