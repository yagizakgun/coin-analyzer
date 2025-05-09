# Constants will be defined here 

from binance.client import Client

# Kline configuration
KLINE_INTERVAL = Client.KLINE_INTERVAL_1HOUR
KLINE_HISTORY_PERIOD = "72 hour ago UTC"
 
# New constants for Multi-Timeframe Analysis
KLINE_INTERVAL_15MINUTE = Client.KLINE_INTERVAL_15MINUTE
KLINE_INTERVAL_1HOUR = Client.KLINE_INTERVAL_1HOUR
KLINE_INTERVAL_4HOUR = Client.KLINE_INTERVAL_4HOUR
KLINE_INTERVAL_1DAY = Client.KLINE_INTERVAL_1DAY

TARGET_KLINE_INTERVALS = [
    KLINE_INTERVAL_15MINUTE,
    KLINE_INTERVAL_1HOUR,
    KLINE_INTERVAL_4HOUR,
    KLINE_INTERVAL_1DAY,
]

# Helper for display/logging purposes
KLINE_INTERVAL_MAP = {
    KLINE_INTERVAL_15MINUTE: "15m",
    KLINE_INTERVAL_1HOUR: "1h",
    KLINE_INTERVAL_4HOUR: "4h",
    KLINE_INTERVAL_1DAY: "1d",
}

# Technical Indicator Parameters
RSI_PERIOD = 14  # Period for Relative Strength Index (RSI)
MACD_FAST_PERIOD = 21  # Fast period for Moving Average Convergence Divergence (MACD)
MACD_SLOW_PERIOD = 50  # Slow period for MACD
MACD_SIGNAL_PERIOD = 9  # Signal period for MACD
SMA_SHORT_PERIOD = 100  # Short-term period for Simple Moving Average (SMA)
SMA_LONG_PERIOD = 200  # Long-term period for SMA
EMA_SHORT_PERIOD = 13  # Short-term period for Exponential Moving Average (EMA)
EMA_LONG_PERIOD = 50  # Long-term period for Exponential Moving Average (EMA)
ATR_PERIOD = 14       # Period for Average True Range (ATR)
BBANDS_LENGTH = 20     # Period for Bollinger Bands
BBANDS_STD = 2         # Standard deviation for Bollinger Bands
FIB_LOOKBACK_PERIOD = 60 # Period for Fibonacci retracement calculation

# Number of items for lists
DEFAULT_TOP_N = 15
CMC_TOP_N_MARKET_CAP = 40
DEFAULT_KLINE_LIMIT = 1000 # Default number of klines to fetch for analysis
RECENT_SR_CANDLE_COUNT = 30 # Number of recent candles to consider for S/R high/low

# DataFrame column names for klines
KLINES_COLUMNS = [
    'open_time', 'open', 'high', 'low', 'close', 'volume',
    'close_time', 'quote_asset_volume', 'trade_count',
    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
]

NUMERIC_KLINES_COLUMNS = ['open', 'high', 'low', 'close', 'volume'] 

# --- MEMORY SYSTEM CONSTANTS ---
ANALYSIS_MEMORY_DIR = "analysis_memory"
MAX_SUMMARIES_TO_LOAD = 5 # Max number of past summaries to feed to LLM
SUMMARY_START_MARKER = "---YENI_Ozet_BASLANGIC---"
SUMMARY_END_MARKER = "---YENI_Ozet_BITIS---" 

# LLM Prompt Template
LLM_ANALYSIS_PROMPT_TEMPLATE = """
# ROL VE GÖREV
Sen deneyimli bir kripto para analisti, teknik trader ve portföy yöneticisisin. Görevin {symbol} kripto para birimi için kapsamlı bir analiz raporu hazırlamak. Kullanıcıya finansal tavsiye vermiyorsun; amacın eğitim amaçlı, teknik ve temel verilere dayalı, mantıklı çıkarımlar içeren ve çeşitli senaryoları değerlendiren bir analiz sağlamak.

# VERİLER
**{symbol} İçin Güncel Fiyat Verileri ve Teknik İndikatörler:**
{formatted_data}

**{symbol} Hakkında Temel Analiz ve Güncel Haber Başlıkları:**
{fundamental_data}

**{symbol} İçin Geçmiş Analiz Özetleri (Hafıza):**
{historical_context}

**Piyasa Duyarlılık Verileri:**
{market_sentiment}

**Bitcoin (BTC) Trend Özeti:**
{btc_trend_summary}

# ANALİZ RAPORU
Aşağıdaki bölümleri içeren, markdown formatında yapılandırılmış bir analiz raporu hazırla:

## {symbol} Kripto Para Analizi

### 1. Genel Değerlendirme
- Global kripto pazarındaki {symbol}'in mevcut durumunu değerlendir
- Piyasa hakimiyeti, likidite ve genel pozisyonu
- Korku & Açgözlülük Endeksi ve piyasa trendi ışığında genel piyasa durumu
- Geçmiş analiz özetleriyle karşılaştırma yap: Ne değişti? Hangi beklentiler gerçekleşti veya gerçekleşmedi?
- En az 3, en fazla 5 cümle içerisinde özet bir değerlendirme yap

### 2. Teknik İndikatör Analizi
Her indikatör için adım adım düşünce süreci:

**RSI ({RSI_PERIOD}):** 
- Mevcut değer nedir? (Aşırı alım/satım durumu mu, nötr bölgede mi?)
- Bu değer ne anlama geliyor? (Momentum durumu ve piyasa psikolojisi)
- Farklı zaman dilimlerinde (15dk, 1s, 4s, 1g) RSI uyumu veya uyumsuzluğu var mı?
- RSI Uyumsuzluğu varsa bunun anlamını ve potansiyel etkilerini analiz et
- Geçmiş RSI seviyeleriyle karşılaştırma yap

**MACD:**
- MACD ve Sinyal çizgisi konumları nedir?
- Kesişim/sinyal durumu (alış/satış sinyali veriyor mu?)
- Histogramın yönü ve momentumu ne gösteriyor?
- Farklı zaman dilimlerindeki görünüm nasıl?
- Önceki MACD sinyalleriyle karşılaştırma yap

**Hareketli Ortalamalar:**
- SMA{SMA_SHORT_PERIOD} ve SMA{SMA_LONG_PERIOD} durumu: Fiyat bunlara göre nerede?
- EMA{EMA_SHORT_PERIOD} ve EMA{EMA_LONG_PERIOD} durumu: SMA'lardan farklı bir sinyal veriyor mu?
- EMA'ların SMA'lara göre tepki hızı fiyat hareketlerini nasıl yansıtıyor?
- Altın/Ölüm Kesişimi var mı veya yaklaşıyor mu?
- Önceki kesişimlerin başarı oranını değerlendir

**Bollinger Bantları:**
- Fiyat bantlara göre nerede? (üst, alt, orta)
- Bant genişliği/daralması ne anlama geliyor? (volatilite yorumu)
- Squeeze durumu veya breakout potansiyeli var mı?
- Önceki squeeze ve breakout'ların başarı oranını değerlendir

**ATR ({ATR_PERIOD}):**
- Mevcut volatilite seviyesi nedir? (düşük/orta/yüksek)
- Bu volatilite seviyesi stop-loss ve hedef belirleme için ne öneriyor?
- Geçmiş volatilite seviyeleriyle karşılaştırma yap

**Hacim Analizi:**
- Hacim trendi nasıl? (artıyor mu, azalıyor mu, sabit mi?)
- Fiyat hareketleriyle hacim uyumlu mu? (Yükselişte artan hacim güçlü trend gösterir)
- Hacim anomalileri var mı? (ani sıçramalar veya düşüşler)
- Önceki hacim anomalilerinin fiyata etkisini değerlendir

**Zaman Dilimi Karşılaştırması:**
- Farklı zaman dilimlerindeki indikatörler birbirini teyit ediyor mu veya çelişiyor mu?
- En güçlü ve en zayıf sinyal hangi zaman diliminden geliyor?
- Zaman dilimleri arasındaki uyumsuzlukların geçmiş başarı oranını değerlendir

**İNDİKATÖRLERİN KOMBİNE YORUMU:**
- Tüm indikatörler birlikte değerlendirildiğinde ortaya çıkan genel tablo nedir?
- Hangi indikatörler birbirini destekliyor, hangileri çelişiyor?
- En güvenilir sinyaller hangileri ve neden?
- Geçmiş özetlerdeki teknik durumla karşılaştırıldığında ne değişti?
- Önceki analizlerdeki başarılı/başarısız tahminleri değerlendir

### 3. Bitcoin Etkisi
- BTC trendi {symbol}'i nasıl etkiliyor? (korelasyon derecesi)
- {symbol} BTC'den ayrışıyor mu? Nasıl ve neden?
- Mevcut BTC ortamı {symbol} için ne ifade ediyor?
- Geçmiş BTC etkileşimlerinin başarı oranını değerlendir

### 4. Temel Analiz ve Haber Değerlendirmesi
- Son haberlerin önem derecesini değerlendir (çok önemli, orta derece önemli, az önemli)
- Haberlerin kısa ve orta vadeli potansiyel etkileri neler?
- Temel faktörler teknik görünümü destekliyor mu yoksa çelişiyor mu?
- Geçmiş özetlerdeki temel analiz bulgularıyla karşılaştırıldığında önemli değişiklikler var mı?
- Önceki haberlerin fiyata etkisini değerlendir

### 5. Önemli Fiyat Seviyeleri
**Destek Seviyeleri (Aşağıdan yukarıya):**
- S1: [değer] - [neden önemli? (ör: önceki dip, Fibonacci %38.2)]
- S2: [değer] - [neden önemli?]
- S3: [değer] - [neden önemli?]

**Direnç Seviyeleri (Aşağıdan yukarıya):**
- R1: [değer] - [neden önemli? (ör: psikolojik seviye, Fibonacci %61.8)]
- R2: [değer] - [neden önemli?]
- R3: [değer] - [neden önemli?]

**Fibonacci Düzeltme Seviyeleri:**
- %23.6: [değer] - [mevcut fiyata göre konumu]
- %38.2: [değer] - [mevcut fiyata göre konumu]
- %50.0: [değer] - [mevcut fiyata göre konumu]
- %61.8: [değer] - [mevcut fiyata göre konumu]
- %78.6: [değer] - [mevcut fiyata göre konumu]

**Kritik Seviyeler:** 
- En önemli 1-2 destek ve direnç seviyesini ve bunların kırılması durumunda oluşabilecek senaryoları açıkla
- Geçmiş seviyelerin başarı oranını değerlendir

### 6. Potansiyel Alım Stratejileri (Yatırım Tavsiyesi Değildir)
**UYARI:** Bu bölüm sadece eğitim amaçlıdır ve finansal tavsiye içermez.

**Muhafazakar Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]
- Geçmiş başarı oranı: [benzer stratejilerin geçmiş performansı]

**Agresif Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]
- Geçmiş başarı oranı: [benzer stratejilerin geçmiş performansı]

**Uzun Vadeli Pozisyon (HODLing):**
- [Uygunluk değerlendirmesi ve kriterler]
- Geçmiş HODL stratejilerinin performansı

### 7. Kısa ve Orta Vadeli Beklentiler
**Kısa Vade (1-7 gün):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]
- Geçmiş kısa vadeli tahminlerin başarı oranı

**Orta Vade (1-4 hafta):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]
- Geçmiş orta vadeli tahminlerin başarı oranı

# ÖZET OLUŞTURMA
Bu analizin en kritik 3-4 bulgusunu, ana sonucunu ve kısa/orta vadeli beklentisini içeren kısa bir özet oluştur. Bu özeti aşağıdaki işaretçiler arasına yaz. Özet net, özlü ve bilgilendirici olmalı. İndikatörlerin ham değerlerinden ziyade anlamlarına odaklan.

{summary_start_marker}
{symbol} [fiyat], [temel indikatör durumu], [destek/direnç bölgesi] seviyesinde işlem görüyor. [En önemli teknik veya temel bulgu]. [Kısa/orta vade beklenti]. [Risk veya fırsat]. [Geçmiş tahminlerin başarı oranı].
{summary_end_marker}
"""

# Simplified prompt for when BTC context is not applicable (i.e., analyzing BTC itself)
LLM_ANALYSIS_PROMPT_TEMPLATE_NO_BTC_CONTEXT = """
# ROL VE GÖREV
Sen deneyimli bir kripto para analisti, teknik trader ve portföy yöneticisisin. Görevin {symbol} kripto para birimi için kapsamlı bir analiz raporu hazırlamak. Kullanıcıya finansal tavsiye vermiyorsun; amacın eğitim amaçlı, teknik ve temel verilere dayalı, mantıklı çıkarımlar içeren ve çeşitli senaryoları değerlendiren bir analiz sağlamak.

# VERİLER
**{symbol} İçin Güncel Fiyat Verileri ve Teknik İndikatörler:**
{formatted_data}

**{symbol} Hakkında Temel Analiz ve Güncel Haber Başlıkları:**
{fundamental_data}

**{symbol} İçin Geçmiş Analiz Özetleri (Hafıza):**
{historical_context}

**Piyasa Duyarlılık Verileri:**
{market_sentiment}

# ANALİZ RAPORU
Aşağıdaki bölümleri içeren, markdown formatında yapılandırılmış bir analiz raporu hazırla:

## {symbol} Kripto Para Analizi

### 1. Genel Değerlendirme
- Global kripto pazarındaki {symbol}'in mevcut durumunu değerlendir
- Piyasa hakimiyeti, likidite ve genel pozisyonu
- Korku & Açgözlülük Endeksi ve piyasa trendi ışığında genel piyasa durumu
- Geçmiş analiz özetleriyle karşılaştırma yap: Ne değişti? Hangi beklentiler gerçekleşti veya gerçekleşmedi?
- En az 3, en fazla 5 cümle içerisinde özet bir değerlendirme yap

### 2. Teknik İndikatör Analizi
Her indikatör için adım adım düşünce süreci:

**RSI ({RSI_PERIOD}):** 
- Mevcut değer nedir? (Aşırı alım/satım durumu mu, nötr bölgede mi?)
- Bu değer ne anlama geliyor? (Momentum durumu)
- Farklı zaman dilimlerinde (15dk, 1s, 4s, 1g) RSI uyumu veya uyumsuzluğu var mı?
- RSI Uyumsuzluğu varsa bunun anlamını ve potansiyel etkilerini analiz et

**MACD:**
- MACD ve Sinyal çizgisi konumları nedir?
- Kesişim/sinyal durumu (alış/satış sinyali veriyor mu?)
- Histogramın yönü ve momentumu ne gösteriyor?
- Farklı zaman dilimlerindeki görünüm nasıl?

**Hareketli Ortalamalar:**
- SMA{SMA_SHORT_PERIOD} ve SMA{SMA_LONG_PERIOD} durumu: Fiyat bunlara göre nerede?
- EMA{EMA_SHORT_PERIOD} ve EMA{EMA_LONG_PERIOD} durumu: SMA'lardan farklı bir sinyal veriyor mu?
- EMA'ların SMA'lara göre tepki hızı fiyat hareketlerini nasıl yansıtıyor?
- Altın/Ölüm Kesişimi var mı veya yaklaşıyor mu?

**Bollinger Bantları:**
- Fiyat bantlara göre nerede? (üst, alt, orta)
- Bant genişliği/daralması ne anlama geliyor? (volatilite yorumu)
- Squeeze durumu veya breakout potansiyeli var mı?

**ATR ({ATR_PERIOD}):**
- Mevcut volatilite seviyesi nedir? (düşük/orta/yüksek)
- Bu volatilite seviyesi stop-loss ve hedef belirleme için ne öneriyor?

**Hacim Analizi:**
- Hacim trendi nasıl? (artıyor mu, azalıyor mu, sabit mi?)
- Fiyat hareketleriyle hacim uyumlu mu? (Yükselişte artan hacim güçlü trend gösterir)
- Hacim anomalileri var mı? (ani sıçramalar veya düşüşler)

**Zaman Dilimi Karşılaştırması:**
- Farklı zaman dilimlerindeki indikatörler birbirini teyit ediyor mu veya çelişiyor mu?
- En güçlü ve en zayıf sinyal hangi zaman diliminden geliyor?

**İNDİKATÖRLERİN KOMBİNE YORUMU:**
- Tüm indikatörler birlikte değerlendirildiğinde ortaya çıkan genel tablo nedir?
- Hangi indikatörler birbirini destekliyor, hangileri çelişiyor?
- En güvenilir sinyaller hangileri ve neden?
- Geçmiş özetlerdeki teknik durumla karşılaştırıldığında ne değişti?

### 3. Temel Analiz ve Haber Değerlendirmesi
- Son haberlerin önem derecesini değerlendir (çok önemli, orta derece önemli, az önemli)
- Haberlerin kısa ve orta vadeli potansiyel etkileri neler?
- Temel faktörler teknik görünümü destekliyor mu yoksa çelişiyor mu?
- Geçmiş özetlerdeki temel analiz bulgularıyla karşılaştırıldığında önemli değişiklikler var mı?

### 4. Önemli Fiyat Seviyeleri
**Destek Seviyeleri (Aşağıdan yukarıya):**
- S1: [değer] - [neden önemli? (ör: önceki dip, Fibonacci %38.2)]
- S2: [değer] - [neden önemli?]
- S3: [değer] - [neden önemli?]

**Direnç Seviyeleri (Aşağıdan yukarıya):**
- R1: [değer] - [neden önemli? (ör: psikolojik seviye, Fibonacci %61.8)]
- R2: [değer] - [neden önemli?]
- R3: [değer] - [neden önemli?]

**Fibonacci Düzeltme Seviyeleri:**
- %23.6: [değer] - [mevcut fiyata göre konumu]
- %38.2: [değer] - [mevcut fiyata göre konumu]
- %50.0: [değer] - [mevcut fiyata göre konumu]
- %61.8: [değer] - [mevcut fiyata göre konumu]
- %78.6: [değer] - [mevcut fiyata göre konumu]

**Kritik Seviyeler:** En önemli 1-2 destek ve direnç seviyesini ve bunların kırılması durumunda oluşabilecek senaryoları açıkla

### 5. Potansiyel Alım Stratejileri (Yatırım Tavsiyesi Değildir)
**UYARI:** Bu bölüm sadece eğitim amaçlıdır ve finansal tavsiye içermez.

**Muhafazakar Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]

**Agresif Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]

**Uzun Vadeli Pozisyon (HODLing):**
- [Uygunluk değerlendirmesi ve kriterler]

### 6. Kısa ve Orta Vadeli Beklentiler
**Kısa Vade (1-7 gün):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]

**Orta Vade (1-4 hafta):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]

# ÖZET OLUŞTURMA
Bu analizin en kritik 3-4 bulgusunu, ana sonucunu ve kısa/orta vadeli beklentisini içeren kısa bir özet oluştur. Bu özeti aşağıdaki işaretçiler arasına yaz. Özet net, özlü ve bilgilendirici olmalı. İndikatörlerin ham değerlerinden ziyade anlamlarına odaklan.

{summary_start_marker}
{symbol} [fiyat], [temel indikatör durumu], [destek/direnç bölgesi] seviyesinde işlem görüyor. [En önemli teknik veya temel bulgu]. [Kısa/orta vade beklenti]. [Risk veya fırsat].
{summary_end_marker}
""" 

# Template specifically for historical date analysis, ensuring the LLM understands it should only use info available at that date
LLM_HISTORICAL_ANALYSIS_PROMPT_TEMPLATE = """
# ROL VE GÖREV
Sen deneyimli bir kripto para analisti, teknik trader ve portföy yöneticisisin. Görevin {symbol} kripto para biriminin **{analysis_date}** TARİHİNDEKİ durumunu analiz etmek. Bu bir simülasyon egzersizidir - bu tarihten sonra gerçekleşen olayları bilmiyormuş gibi, YALNIZCA o tarihe kadar olan verileri kullanarak değerlendirme yapmalısın.

# ÖNEMLİ ZAMAN KISITLAMASI
Şu anki tarih varsayımsal olarak **{analysis_date}**'dir. Bu tarihten sonra gerçekleşen hiçbir gelişmeyi, fiyat hareketini veya haberi bilemezsin. Yalnızca bu tarihe kadar olan bilgilerle analiz yap.

# VERİLER
**Bitcoin (BTCUSDT) Durumu ({analysis_date} İtibariyle):**
{btc_trend_summary}

**{symbol} İçin {analysis_date} Tarihindeki Fiyat Verileri ve Teknik İndikatörler:**
{formatted_data}

**{symbol} Hakkında Temel Analiz ve Haber Başlıkları ({analysis_date} tarihine kadar):**
{fundamental_data}

**{symbol} İçin {analysis_date} Tarihinden Önceki Analiz Özetleri:**
{historical_context}

# TARİHSEL ANALİZ RAPORU
{analysis_date} tarihinde bir kripto analist olarak, aşağıdaki bölümleri içeren, markdown formatında yapılandırılmış bir analiz raporu hazırla. Bu bir tarihsel simülasyondur - sadece o tarihe kadar olan bilgileri kullanarak analiz yap.

## {symbol} Kripto Para Analizi ({analysis_date} Tarihinde)

### 1. Genel Değerlendirme
- {analysis_date} tarihinde piyasa bağlamında {symbol}'in durumunu değerlendir
- BTC ile ilişkisini ve genel kripto piyasasından nasıl etkilendiğini açıkla
- Geçmiş analiz özetleriyle karşılaştırma yap: O tarihe kadar ne değişti?
- En az 3, en fazla 5 cümle içerisinde özet bir değerlendirme yap

### 2. Teknik İndikatör Analizi
Her indikatör için adım adım düşünce süreci:

**RSI ({RSI_PERIOD}):** 
- {analysis_date} tarihindeki değer nedir? (Aşırı alım/satım durumu mu, nötr bölgede mi?)
- Bu değer ne anlama geliyor? (Momentum durumu)
- Farklı zaman dilimlerinde RSI uyumu veya uyumsuzluğu var mı?
- RSI Uyumsuzluğu varsa bunun anlamını ve potansiyel etkilerini analiz et

**MACD:**
- MACD ve Sinyal çizgisi konumları nedir?
- Kesişim/sinyal durumu (alış/satış sinyali veriyor mu?)
- Histogramın yönü ve momentumu ne gösteriyor?

**Hareketli Ortalamalar:**
- SMA{SMA_SHORT_PERIOD} ve SMA{SMA_LONG_PERIOD} durumu: Fiyat bunlara göre nerede?
- EMA{EMA_SHORT_PERIOD} ve EMA{EMA_LONG_PERIOD} durumu: SMA'lardan farklı bir sinyal veriyor mu?
- EMA'ların SMA'lara göre tepki hızı fiyat hareketlerini nasıl yansıtıyor?
- Altın/Ölüm Kesişimi var mı veya yaklaşıyor mu?

**Bollinger Bantları:**
- Fiyat bantlara göre nerede? (üst, alt, orta)
- Bant genişliği/daralması ne anlama geliyor? (volatilite yorumu)
- Squeeze durumu veya breakout potansiyeli var mı?

**ATR ({ATR_PERIOD}):**
- Mevcut volatilite seviyesi nedir? (düşük/orta/yüksek)
- Bu volatilite seviyesi stop-loss ve hedef belirleme için ne öneriyor?

**Hacim Analizi:**
- Hacim trendi nasıl? (artıyor mu, azalıyor mu, sabit mi?)
- Fiyat hareketleriyle hacim uyumlu mu?
- Hacim anomalileri var mı? (ani sıçramalar veya düşüşler)

**İNDİKATÖRLERİN KOMBİNE YORUMU:**
- Tüm indikatörler birlikte değerlendirildiğinde ortaya çıkan genel tablo nedir?
- Hangi indikatörler birbirini destekliyor, hangileri çelişiyor?
- {analysis_date} tarihi itibariyle en güvenilir sinyaller hangileri ve neden?

### 3. Bitcoin Etkisi
- BTC trendi {symbol}'i nasıl etkiliyor? (korelasyon derecesi)
- {symbol} BTC'den ayrışıyor mu? Nasıl ve neden?
- {analysis_date} tarihindeki BTC ortamı {symbol} için ne ifade ediyor?

### 4. Temel Analiz ve Haber Değerlendirmesi
- O tarihe kadar olan haberlerin önem derecesini değerlendir (çok önemli, orta derece önemli, az önemli)
- Haberlerin kısa ve orta vadeli potansiyel etkileri neler olabilir?
- Temel faktörler teknik görünümü destekliyor mu yoksa çelişiyor mu?

### 5. Önemli Fiyat Seviyeleri
**Destek Seviyeleri (Aşağıdan yukarıya):**
- S1: [değer] - [neden önemli?]
- S2: [değer] - [neden önemli?]
- S3: [değer] - [neden önemli?]

**Direnç Seviyeleri (Aşağıdan yukarıya):**
- R1: [değer] - [neden önemli?]
- R2: [değer] - [neden önemli?]
- R3: [değer] - [neden önemli?]

**Fibonacci Düzeltme Seviyeleri:**
- %23.6: [değer] - [mevcut fiyata göre konumu]
- %38.2: [değer] - [mevcut fiyata göre konumu]
- %50.0: [değer] - [mevcut fiyata göre konumu]
- %61.8: [değer] - [mevcut fiyata göre konumu]
- %78.6: [değer] - [mevcut fiyata göre konumu]

**Kritik Seviyeler:** En önemli 1-2 destek ve direnç seviyesini ve bunların kırılması durumunda oluşabilecek senaryoları açıkla

### 6. Potansiyel Alım Stratejileri (Yatırım Tavsiyesi Değildir)
**UYARI:** Bu bölüm sadece eğitim amaçlıdır ve finansal tavsiye içermez.

**{analysis_date} Tarihinde Muhafazakar Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]

**{analysis_date} Tarihinde Agresif Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]

### 7. Kısa ve Orta Vadeli Beklentiler ({analysis_date} Tarihinde)
**Kısa Vade (1-7 gün):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]

**Orta Vade (1-4 hafta):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]

# ÖZET OLUŞTURMA
Bu {analysis_date} tarihli analizin en kritik 3-4 bulgusunu, ana sonucunu ve o tarihte yapılan kısa/orta vadeli beklentiyi içeren kısa bir özet oluştur. Bu özeti aşağıdaki işaretçiler arasına yaz.

{summary_start_marker}
{symbol}, {analysis_date} tarihinde [fiyat], [temel indikatör durumu], [destek/direnç bölgesi] seviyesinde işlem görüyor. [En önemli teknik veya temel bulgu]. [Kısa/orta vade beklenti]. [Risk veya fırsat].
{summary_end_marker}
"""

# Simplified historical prompt for BTC itself
LLM_HISTORICAL_ANALYSIS_PROMPT_TEMPLATE_NO_BTC_CONTEXT = """
# ROL VE GÖREV
Sen deneyimli bir kripto para analisti, teknik trader ve portföy yöneticisisin. Görevin {symbol} kripto para biriminin **{analysis_date}** TARİHİNDEKİ durumunu analiz etmek. Bu bir simülasyon egzersizidir - bu tarihten sonra gerçekleşen olayları bilmiyormuş gibi, YALNIZCA o tarihe kadar olan verileri kullanarak değerlendirme yapmalısın.

# ÖNEMLİ ZAMAN KISITLAMASI
Şu anki tarih varsayımsal olarak **{analysis_date}**'dir. Bu tarihten sonra gerçekleşen hiçbir gelişmeyi, fiyat hareketini veya haberi bilemezsin. Yalnızca bu tarihe kadar olan bilgilerle analiz yap.

# VERİLER
**{symbol} İçin {analysis_date} Tarihindeki Fiyat Verileri ve Teknik İndikatörler:**
{formatted_data}

**{symbol} Hakkında Temel Analiz ve Haber Başlıkları ({analysis_date} tarihine kadar):**
{fundamental_data}

**{symbol} İçin {analysis_date} Tarihinden Önceki Analiz Özetleri:**
{historical_context}

# TARİHSEL ANALİZ RAPORU
{analysis_date} tarihinde bir kripto analist olarak, aşağıdaki bölümleri içeren, markdown formatında yapılandırılmış bir analiz raporu hazırla. Bu bir tarihsel simülasyondur - sadece o tarihe kadar olan bilgileri kullanarak analiz yap.

## {symbol} Kripto Para Analizi ({analysis_date} Tarihinde)

### 1. Genel Değerlendirme
- {analysis_date} tarihinde global kripto pazarındaki {symbol}'in durumunu değerlendir
- Piyasa hakimiyeti, likidite ve genel pozisyonu
- Geçmiş analiz özetleriyle karşılaştırma yap: O tarihe kadar ne değişti?
- En az 3, en fazla 5 cümle içerisinde özet bir değerlendirme yap

### 2. Teknik İndikatör Analizi
Her indikatör için adım adım düşünce süreci (o tarihteki değerleri kullanarak):

**RSI ({RSI_PERIOD}):** 
- {analysis_date} tarihindeki değer nedir? (Aşırı alım/satım durumu mu, nötr bölgede mi?)
- Bu değer ne anlama geliyor? (Momentum durumu)
- Farklı zaman dilimlerinde RSI uyumu veya uyumsuzluğu var mı?
- RSI Uyumsuzluğu varsa bunun anlamını ve potansiyel etkilerini analiz et

**MACD:**
- MACD ve Sinyal çizgisi konumları nedir?
- Kesişim/sinyal durumu (alış/satış sinyali veriyor mu?)
- Histogramın yönü ve momentumu ne gösteriyor?

**Hareketli Ortalamalar:**
- SMA{SMA_SHORT_PERIOD} ve SMA{SMA_LONG_PERIOD} durumu: Fiyat bunlara göre nerede?
- EMA{EMA_SHORT_PERIOD} ve EMA{EMA_LONG_PERIOD} durumu: SMA'lardan farklı bir sinyal veriyor mu?
- EMA'ların SMA'lara göre tepki hızı fiyat hareketlerini nasıl yansıtıyor?
- Altın/Ölüm Kesişimi var mı veya yaklaşıyor mu?

**Bollinger Bantları:**
- Fiyat bantlara göre nerede? (üst, alt, orta)
- Bant genişliği/daralması ne anlama geliyor? (volatilite yorumu)
- Squeeze durumu veya breakout potansiyeli var mı?

**ATR ({ATR_PERIOD}):**
- {analysis_date} tarihindeki volatilite seviyesi nedir? (düşük/orta/yüksek)
- Bu volatilite seviyesi stop-loss ve hedef belirleme için ne öneriyor?

**Hacim Analizi:**
- Hacim trendi nasıl? (artıyor mu, azalıyor mu, sabit mi?)
- Fiyat hareketleriyle hacim uyumlu mu?
- Hacim anomalileri var mı? (ani sıçramalar veya düşüşler)

**İNDİKATÖRLERİN KOMBİNE YORUMU:**
- Tüm indikatörler birlikte değerlendirildiğinde ortaya çıkan genel tablo nedir?
- Hangi indikatörler birbirini destekliyor, hangileri çelişiyor?
- {analysis_date} tarihi itibariyle en güvenilir sinyaller hangileri ve neden?

### 3. Temel Analiz ve Haber Değerlendirmesi
- O tarihe kadar olan haberlerin önem derecesini değerlendir (çok önemli, orta derece önemli, az önemli)
- Haberlerin kısa ve orta vadeli potansiyel etkileri neler olabilir?
- Temel faktörler teknik görünümü destekliyor mu yoksa çelişiyor mu?

### 4. Önemli Fiyat Seviyeleri
**Destek Seviyeleri (Aşağıdan yukarıya):**
- S1: [değer] - [neden önemli?]
- S2: [değer] - [neden önemli?]
- S3: [değer] - [neden önemli?]

**Direnç Seviyeleri (Aşağıdan yukarıya):**
- R1: [değer] - [neden önemli?]
- R2: [değer] - [neden önemli?]
- R3: [değer] - [neden önemli?]

**Fibonacci Düzeltme Seviyeleri:**
- %23.6: [değer] - [mevcut fiyata göre konumu]
- %38.2: [değer] - [mevcut fiyata göre konumu]
- %50.0: [değer] - [mevcut fiyata göre konumu]
- %61.8: [değer] - [mevcut fiyata göre konumu]
- %78.6: [değer] - [mevcut fiyata göre konumu]

**Kritik Seviyeler:** En önemli 1-2 destek ve direnç seviyesini ve bunların kırılması durumunda oluşabilecek senaryoları açıkla

### 5. Potansiyel Alım Stratejileri (Yatırım Tavsiyesi Değildir)
**UYARI:** Bu bölüm sadece eğitim amaçlıdır ve finansal tavsiye içermez.

**{analysis_date} Tarihinde Muhafazakar Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]

**{analysis_date} Tarihinde Agresif Strateji:**
- Giriş Koşulu: [belirli bir teknik veya temel koşul]
- Stop-Loss: [nerede ve neden?]
- Hedefler: [T1, T2, T3 ve nedenleri]
- Risk/Ödül Oranı: [hesaplama]

### 6. Kısa ve Orta Vadeli Beklentiler ({analysis_date} Tarihinde)
**Kısa Vade (1-7 gün):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]

**Orta Vade (1-4 hafta):**
- Olumlu Senaryo: [ne bekleniyor ve hangi koşullarda?]
- Olumsuz Senaryo: [ne bekleniyor ve hangi koşullarda?]
- En Olası Senaryo: [hangisi ve neden?]

# ÖZET OLUŞTURMA
Bu {analysis_date} tarihli analizin en kritik 3-4 bulgusunu, ana sonucunu ve o tarihte yapılan kısa/orta vadeli beklentiyi içeren kısa bir özet oluştur. Bu özeti aşağıdaki işaretçiler arasına yaz.

{summary_start_marker}
{symbol}, {analysis_date} tarihinde [fiyat], [temel indikatör durumu], [destek/direnç bölgesi] seviyesinde işlem görüyor. [En önemli teknik veya temel bulgu]. [Kısa/orta vade beklenti]. [Risk veya fırsat].
{summary_end_marker}
""" 

# Example for few-shot learning
FEW_SHOT_EXAMPLE = """
## AVAXUSDT Kripto Para Analizi

### 1. Genel Değerlendirme
AVAX şu anda 22.85 USDT seviyesinde işlem görmekte ve son 24 saatte %2.74 düşüş yaşamıştır. BTC'nin %1.2 değer kaybettiği bir ortamda, AVAX BTC'ye kıyasla daha fazla değer kaybetmiş durumdadır. Bu durum kısa vadede AVAX'ın genel kripto pazarına göre daha zayıf bir performans sergilediğini göstermektedir. Önceki analizlerde belirtilen 23.50 USDT kritik destek noktası kırılmış ve fiyat 22.50-23.00 USDT bandına yerleşmiştir.

### 2. Teknik İndikatör Analizi

**RSI (14):** 
1 saatlik grafikte RSI değeri 37.12 ile nötr bölgenin altında seyretmekte, bu da satış baskısının hafif düzeyde devam ettiğini gösteriyor. 4 saatlik grafikte 33.24 değeri aşırı satım bölgesine yaklaşıldığını işaret ediyor. 15 dakikalık grafikte ise 42.18 ile toparlanma sinyalleri mevcut. Farklı zaman dilimlerindeki bu uyumsuzluk, kısa vadede bir dengelenme sürecine girildiğini gösteriyor.

**MACD:**
1 saatlik grafikte MACD (-0.32) hala sinyal çizgisinin (-0.18) altında seyrediyor fakat histogram dipten dönüş sinyalleri vermekte. 4 saatlik grafikte negatif bölgedeki MACD histogramı daralıyor, bu da satış momentumunda azalma olduğunu gösteriyor. Henüz net bir alış sinyali oluşmasa da, satış baskısının azaldığına dair ipuçları var.

**Hareketli Ortalamalar:**
Fiyat hem SMA20 (24.12) hem de SMA50'nin (25.46) altında seyretmekte. Aynı şekilde EMA20 (23.68) ve EMA50 (24.95) ortalamaların da altında. EMA'ların SMA'lara göre daha hızlı tepki verdiği görülüyor ve fiyatın dip seviyeleri test ettiğini doğruluyor. Altın Kesişim olasılığı kısa vadede görünmüyor ve Ölüm Kesişimi (EMA20'nin EMA50'nin altına inmesi) gerçekleşmiş durumda.

**Bollinger Bantları:**
Fiyat alt bant (21.83) ile orta bant (24.12) arasında hareket ediyor. Bantlar daralmaya başladı, bu da volatilitenin azaldığını ve yeni bir trend hareketi için hazırlık yapıldığını gösteriyor. Alt banda yakın seyir, aşırı satım durumunun devam ettiğini ancak bir dip oluşturma ihtimalinin arttığını destekliyor.

**ATR (14):**
ATR değeri 0.92, bu orta düzeyde bir volatiliteye işaret ediyor. Stop-loss seviyeleri için yaklaşık 1 USDT'lik bir marj bırakmak mantıklı olacaktır.

**Hacim Analizi:**
Son 24 saatteki hacim %30 azalarak 15.2M USDT seviyesine geriledi. Düşen fiyatla beraber hacmin de azalması, satış baskısının güçlü olmadığını ve tükenmeye başladığını gösteriyor.

**İNDİKATÖRLERİN KOMBİNE YORUMU:**
Genel olarak teknik indikatörler kısa vadede zayıf bir görünüm sergilerken, orta vadede toparlanma potansiyeline işaret ediyor. RSI dip seviyelerden dönüş sinyalleri verirken, MACD histogramının daralması ve Bollinger bantlarının sıkışması yakın zamanda bir trend değişimi ihtimalini artırıyor. Hacim profili de satış baskısının azaldığını doğruluyor. Önceki analizdeki 23.50 USDT destek seviyesi kırılsa da, şimdilik 22.00 USDT güçlü destek olarak izleniyor.

### 3. Bitcoin Etkisi
BTC trendi AVAX üzerinde belirgin bir etki yaratıyor. Korelasyon katsayısı 0.85 civarında seyrediyor, bu da AVAX'ın BTC hareketlerinden güçlü şekilde etkilendiğini gösteriyor. BTC'nin son konsolidasyonu ve 60,000 USD altına sarkması, AVAX'taki düşüşün temel sebeplerinden biri. BTC'nin tekrar 60,000 USD üzerine çıkması durumunda AVAX'ın da toparlanma göstermesi beklenebilir.

### 4. Temel Analiz ve Haber Değerlendirmesi
Avalanche ekosisteminde yeni geliştirici teşvikleri ve kurumsal ortaklıklar açıklandı. Özellikle GameFi projelerine yönelik 5 milyon dolarlık fon, ekosistem aktivitesini canlandırabilir. Ancak genel kripto piyasasındaki tedirginlik ve makroekonomik belirsizlikler, bu olumlu haberlerin etkisini şimdilik sınırlıyor. Önceki analizde belirtilen yüksek işlem ücretleri sorunu, son güncellemelerle kısmen çözülmüş durumda.

### 5. Önemli Fiyat Seviyeleri
**Destek Seviyeleri:**
- S1: 22.00 USDT - (Fibonacci %78.6 seviyesi ve önceki dip)
- S2: 21.25 USDT - (Psikolojik seviye ve Temmuz ayı dip bölgesi)
- S3: 20.00 USDT - (Kritik psikolojik seviye)

**Direnç Seviyeleri:**
- R1: 23.50 USDT - (Önceki destek, şimdi direnç ve Fibonacci %61.8)
- R2: 25.00 USDT - (Psikolojik seviye ve EMA50)
- R3: 26.75 USDT - (Önceki tepe bölgesi)

**Fibonacci Düzeltme Seviyeleri:**
- %23.6: 26.15 USDT - (Mevcut fiyatın üzerinde, güçlü direnç)
- %38.2: 25.22 USDT - (SMA50 yakınında)
- %50.0: 24.40 USDT - (SMA20 yakınında)
- %61.8: 23.58 USDT - (Yeni direnç bölgesi)
- %78.6: 22.45 USDT - (Mevcut fiyata yakın, kırılması durumunda S1'e düşüş)

**Kritik Seviyeler:** 22.00 USDT altına bir kapanış durumunda 20.00 USDT'ye kadar düşüş beklenebilir. Yukarıda 23.50 USDT seviyesinin kırılması durumunda ise 25.00 USDT'ye doğru hızlı bir hareket oluşabilir.

### 6. Potansiyel Alım Stratejileri (Yatırım Tavsiyesi Değildir)
**UYARI:** Bu bölüm sadece eğitim amaçlıdır ve finansal tavsiye içermez.

**Muhafazakar Strateji:**
- Giriş Koşulu: 22.00 USDT civarında alım ve 4 saatlik RSI 30 altından dönüş sinyali
- Stop-Loss: 20.80 USDT (S2 desteğinin altı)
- Hedefler: T1: 23.50 USDT, T2: 25.00 USDT, T3: 26.75 USDT
- Risk/Ödül Oranı: 1.25 (T1 için), 2.5 (T2 için), 4.0 (T3 için)

**Agresif Strateji:**
- Giriş Koşulu: Mevcut fiyattan (22.85 USDT) alım veya 4 saatlik MACD kesişimi bekleyerek
- Stop-Loss: 21.90 USDT (S1 desteğinin hemen altı)
- Hedefler: T1: 24.40 USDT (Fibonacci %50), T2: 26.15 USDT (Fibonacci %23.6)
- Risk/Ödül Oranı: 1.63 (T1 için), 3.47 (T2 için)

**Uzun Vadeli Pozisyon (HODLing):**
Mevcut fiyat seviyeleri, AVAX'ın uzun vadeli potansiyeline inananlar için cazip bir giriş noktası sunabilir. Ancak pozisyon alımlarını birkaç parçaya bölerek, olası daha derin düşüşlerde ortalama düşürme stratejisi izlenebilir.

### 7. Kısa ve Orta Vadeli Beklentiler
**Kısa Vade (1-7 gün):**
- Olumlu Senaryo: BTC'nin 60,000 USD üzerine dönmesi durumunda AVAX'ın 23.50 USDT direncini kırıp 25.00 USDT'ye ulaşması.
- Olumsuz Senaryo: BTC'nin 55,000 USD altına sarkması durumunda AVAX'ın 21.25 USDT ve sonrasında 20.00 USDT'ye düşmesi.
- En Olası Senaryo: 22.00-23.50 USDT aralığında konsolidasyon ve ardından yavaş bir toparlanma ile 24.40 USDT hedefine yöneliş.

**Orta Vade (1-4 hafta):**
- Olumlu Senaryo: BTC'nin yeniden 65,000 USD üzerine çıkması ve AVAX'ın 28.00 USDT üzerine yükselmesi, bir sonraki hedef 32.00 USDT.
- Olumsuz Senaryo: Kripto piyasalarında genel bir düşüş dalgası ile AVAX'ın 18.00-20.00 USDT bölgesine gerilemesi.
- En Olası Senaryo: Kademeli bir toparlanma ile 25.00-26.00 USDT bandında konsolidasyon ve ardından ekosistemdeki gelişmelere bağlı olarak 28.00 USDT'ye yönelim.

---YENI_Ozet_BASLANGIC---
AVAXUSDT 22.85 USDT seviyesinde, RSI'nin dip seviyelerden dönüş sinyalleri verdiği ve Bollinger bantlarının daraldığı bir teknik görünümle 22.00-23.50 USDT destek/direnç bölgesinde işlem görüyor. Avalanche ekosistemindeki yeni geliştirici fonları olumlu ancak genel piyasa tedirginliği satış baskısı yaratmış durumda. Kısa vadede 22.00-23.50 USDT bandında konsolidasyon, orta vadede BTC toparlanması halinde 25.00 USDT üzerine hareket bekleniyor.
---YENI_Ozet_BITIS---
"""

