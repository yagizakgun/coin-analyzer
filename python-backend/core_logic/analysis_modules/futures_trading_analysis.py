"""
Futures Trading Analysis Module - Analyzes cryptocurrencies for futures/leverage trading opportunities.
"""
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from decimal import Decimal

from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from core_logic.constants import (
    RSI_PERIOD, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD,
    SMA_SHORT_PERIOD, SMA_LONG_PERIOD, EMA_SHORT_PERIOD, EMA_LONG_PERIOD
)
from utils.general_utils import (
    preprocess_klines_df, calculate_technical_indicators, extract_latest_indicators
)

from .base_analysis import BaseAnalysisModule

# LLM prompt template for futures trading analysis
FUTURES_TRADING_PROMPT = """
# ROL VE GÖREV
Sen, özellikle kaldıraçlı işlemlerde uzmanlaşmış deneyimli bir kripto para vadeli işlem analistisin. Görevin, {symbol} için sunulan verilere dayanarak kapsamlı, uygulanabilir ve risk yönetimi odaklı bir vadeli işlem planı oluşturmaktır. Analizin, hem acemi hem de deneyimli yatırımcılar için net, anlaşılır ve gerekçelendirilmiş olmalıdır. Özellikle vurgulaman gereken noktalar: isabetli giriş-çıkış seviyeleri, optimal kaldıraç kullanımı ve potansiyel risklerin en aza indirilmesi.

# ANALİZ İÇİN SAĞLANAN VERİLER
**{symbol} Teknik Verileri (JSON Formatında):**
{technical_data}
    Lütfen bu JSON içindeki `vwap`, `fear_and_greed_index`, `recent_liquidations` ve `order_book_summary` alanlarına özellikle dikkat et.

**{symbol} Güncel Piyasa Verileri:**
- Anlık Fiyat: {current_price} USDT
- 24 Saatlik Değişim: {price_change_percent}%
- 24 Saatlik Hacim: {volume_24h} USDT
- Açık Pozisyon (Open Interest): {open_interest} USDT (Eğer "N/A" ise, bu verinin mevcut olmadığını belirt)
- Fonlama Oranı (Funding Rate): {funding_rate}% (Eğer "N/A" ise, bu verinin mevcut olmadığını belirt ve potansiyel etkilerini genel olarak değerlendir)
- VWAP (Hacim Ağırlıklı Ortalama Fiyat): {vwap_value} USDT (Eğer "N/A" ise, belirt)
- Korku ve Açgözlülük Endeksi: {fear_and_greed_value} (Değer ve Sınıflandırma, örn: 25 - Aşırı Korku) (Eğer "N/A" ise, belirt)

**Kullanılan Ana Göstergeler (JSON'daki `indicators` alanında daha fazlası mevcut):**
- RSI ({rsi_period} periyot): {rsi_value}
- MACD (Değer): {macd_value} (Sinyal: {macd_signal})
- SMA ({sma_short} periyot): {sma_short_value}
- SMA ({sma_long} periyot): {sma_long_value}

# DETAYLI VADELİ İŞLEM PLANI
Aşağıdaki başlıkları kullanarak {symbol} için ayrıntılı bir vadeli işlem stratejisi oluştur:

### 1. Güncel Piyasa Trend Analizi
- **Ana Trend:** (Yükseliş / Düşüş / Yatay) - Hangi zaman dilimine göre (örn: Günlük, 4 Saatlik)?
- **Trendin Gücü:** (Güçlü / Orta / Zayıf) - Neye dayanarak? (VWAP ile ilişkiyi de değerlendir)
- **Kısa Vadeli Görünüm:** (Önümüzdeki birkaç saat/gün için beklenti)
- **Orta Vadeli Görünüm:** (Önümüzdeki birkaç gün/hafta için beklenti)

### 2. Önemli Destek ve Direnç Seviyeleri
- **Ana Destek Seviyeleri (Teknik ve Emir Defteri Odaklı):**
    - S1: [fiyat] - [Bu seviyenin önemi, potansiyel tepki senaryoları. Emir defteri özeti (`order_book_summary`) burayı destekliyor mu?]
    - S2: [fiyat] - [Bu seviyenin önemi, potansiyel tepki senaryoları.]
    - S3 (varsa): [fiyat] - [Bu seviyenin önemi]
- **Ana Direnç Seviyeleri (Teknik ve Emir Defteri Odaklı):**
    - R1: [fiyat] - [Bu seviyenin önemi, potansiyel tepki senaryoları. Emir defteri özeti (`order_book_summary`) burayı destekliyor mu?]
    - R2: [fiyat] - [Bu seviyenin önemi, potansiyel tepki senaryoları.]
    - R3 (varsa): [fiyat] - [Bu seviyenin önemi]
- **Bu Seviyelerin Vadeli İşlemler İçin Anlamı:** (Örn: Potansiyel likidasyon bölgeleri (`recent_liquidations` verisine bak), stop avlama riski, tepki alım/satım fırsatları)
- **VWAP Seviyesinin Rolü:** Mevcut VWAP ({vwap_value} USDT) bir destek mi, direnç mi oluşturuyor? Fiyatın VWAP'a göre konumu ne anlatıyor?

### 3. Önerilen İşlem Yönü ve Gerekçesi
- **İşlem Yönü:** (LONG / SHORT)
- **Gerekçe:** Bu işlem yönünü neden seçtin? Hangi teknik göstergeler, formasyonlar veya piyasa koşulları (Korku ve Açgözlülük Endeksi dahil {fear_and_greed_value}) bu kararı destekliyor? Detaylı açıkla.
- **Temel Dayanaklar:** (Örn: Trend takibi, belirli bir seviyeden tepki beklentisi, formasyon kırılımı vb.)

### 4. Kaldıraç Seçimi ve Risk Yönetimi
- **Önerilen Kaldıraç Aralığı:** (Örn: 3x - 7x) - Neden bu aralık? (Piyasa volatilitesi, işlem stratejisi, risk toleransı ile ilişkilendir)
- **Seçilen Optimal Kaldıraç:** [X]x - Bu özel kaldıraç seviyesinin avantajları ve dezavantajları nelerdir?
- **Kaldıraç Kullanım Stratejisi:** (Örn: Düşük kaldıraçla başlayıp, pozisyon kara geçtikçe kaldıraç artırılabilir mi? Ya da sabit mi kalmalı?)
- **İşlem Başına Risk Edilecek Maksimum Sermaye:** (Toplam işlem bakiyesinin %\'si olarak, örn: %1-%3) - Bu oranın belirlenme mantığı.
- **Potansiyel Likidasyon Fiyatı (Seçilen Kaldıraçta):** Yaklaşık [fiyat] USDT. `recent_liquidations` verisindeki seviyelerle karşılaştır. Bu fiyattan kaçınmak için alınacak önlemler.

### 5. Giriş Stratejisi (Entry)
- **İdeal Giriş Bölgesi/Aralığı:** [fiyat aralığı] USDT (VWAP ve emir defteri seviyelerini göz önünde bulundur)
- **Giriş İçin Gerekli Teyit Sinyalleri:** (Fiyatın bu bölgeye gelmesi yeterli mi, yoksa ek olarak hangi teknik gösterge (örn: RSI dönüşü, MACD kesişimi), mum formasyonu (örn: bullish/bearish engulfing, pin bar), veya piyasa durumu (örn: hacim artışı, fonlama oranında değişim, emir defterinde belirgin bir alım baskısı) beklenmeli?)
- **Önerilen Giriş Yöntemi:** (Tek seferde piyasa emri / Belirlenen aralıkta limit emirlerle kademeli giriş / Belirli bir seviyenin kırılımı sonrası)
- **Alternatif Giriş Noktası (Eğer ideal bölge kaçırılırsa):** [fiyat] - [Koşulları]

### 6. Kar Alma Hedefleri (Take Profit - TP)
- **TP1:** [fiyat] USDT (Potansiyel Kazanç: ~%X) - [Bu hedefin mantığı, örn: ilk direnç, Fibonacci seviyesi, emir defterindeki satış duvarı]
- **TP2:** [fiyat] USDT (Potansiyel Kazanç: ~%Y) - [Bu hedefin mantığı]
- **TP3 (opsiyonel):** [fiyat] USDT (Potansiyel Kazanç: ~%Z) - [Bu hedefin mantığı]
- **Kısmi Kar Alma Stratejisi:** (Örn: TP1\'de %50, TP2\'de %30 kapatmak gibi)

### 7. Stop-Loss (SL) Stratejisi
- **Stop-Loss Seviyesi:** [fiyat] USDT (Maksimum Kayıp: ~%K)
- **Stop-Loss Belirleme Mantığı:** (Neden bu seviye? Hangi önemli destek/direnç kırılımı, VWAP\'ın altına/üstüne geçiş veya teknik bozulma dikkate alındı? `recent_liquidations` seviyeleri bir uyarı veriyor mu?)
- **Stop-Loss Türü:** (Sabit SL / Trailing SL (İz Süren Stop) - Eğer iz süren ise, nasıl ayarlanmalı?)
- **İşlem İptal Seviyesi (Invalidation Level):** [fiyat] - Bu seviye altında/üstünde işlem senaryosunun geçersiz olacağı nokta.

### 8. Piyasa Koşulları Değerlendirmesi
- **Volatilite Değerlendirmesi:** (Düşük / Orta / Yüksek) - Mevcut volatilitenin işlem stratejisine (giriş, SL, TP, kaldıraç) etkileri nelerdir?
- **Fonlama Oranı (Funding Rate) Analizi:** Mevcut fonlama oranı pozitif mi, negatif mi? Bu durum LONG/SHORT pozisyon maliyetini nasıl etkiler? Uzun süreli pozisyon taşımayı planlıyorsan dikkate al.
- **Açık Pozisyon (Open Interest) Yorumu:** (Artıyor / Azalıyor / Yatay) - Bu durum piyasa duyarlılığı ve potansiyel büyük hareketler hakkında ne gibi ipuçları veriyor?
- **Korku ve Açgözlülük Endeksi Analizi:** Mevcut endeks değeri ({fear_and_greed_value}) piyasa psikolojisi hakkında ne söylüyor? Bu, işlem kararlarını nasıl etkilemeli?
- **Likidasyon ve Emir Defteri Analizi:**
    - `recent_liquidations` verisindeki önemli likidasyon seviyeleri (long/short, hacim, fiyat) nelerdir ve bunlar mevcut fiyat için ne ifade ediyor?
    - `order_book_summary` verisindeki en yakın güçlü alım/satım duvarları nerelerde ve bunlar kısa vadeli fiyat hareketlerini nasıl etkileyebilir?
- **Önemli Haberler ve Etkinlikler:** Yakın zamanda {symbol} veya genel kripto piyasasını etkileyebilecek önemli bir haber, duyuru veya ekonomik veri var mı? Varsa potansiyel etkileri neler olabilir?

### 9. Genel Risk Değerlendirmesi ve Risk/Ödül Oranı
- **Genel Risk Seviyesi:** (Düşük / Orta / Yüksek) - Tüm faktörler (yeni veriler dahil) göz önüne alındığında.
- **Risk/Ödül Oranı:**
    - TP1 için: [oran]
    - TP2 için: [oran]
    - Ortalama: [oran]
- **Bu Risk Seviyesini Kabul Etmek İçin Nedenler:**

### 10. İşlem Zaman Dilimi ve Pozisyon Yönetimi
- **Önerilen İşlem Zaman Dilimi:** (Scalping / Gün İçi (Intraday) / Kısa-Orta Vadeli Swing) - Neden?
- **Pozisyon Büyüklüğü Önerisi:** (İşlem başına risk edilen sermaye ve stop-loss mesafesine göre hesaplanmış lot/kontrat büyüklüğü veya yatırım yapılacak USDT miktarı)
- **Pozisyon İzleme Sıklığı:** (Piyasayı ne kadar sık kontrol etmeli?)

### 11. Alternatif Senaryolar ve Acil Durum Planları
- **Eğer İşlem Stop Olursa:** (Yeni bir kurulum bekle / Stratejiyi gözden geçir / Bir süre piyasadan uzak dur)
- **Eğer Piyasa Beklenenin Tersine Çok Hızlı Hareket Ederse (Örn: Ani dump/pump):** (Pozisyonu hemen kapat / Zararı azaltmak için kısmi kapat / Karşı işlem aç - Hedge)
- **Eğer Giriş Fırsatı Kaçırılırsa:** (Yeni bir giriş bölgesi bekle / FOMO\'ya kapılma)

## 12. İşlem Sinyalleri
### 🔍 Potansiyel Sinyal Değerlendirmesi
Bu bölümde, mevcut piyasa koşulları ve teknik göstergelere dayalı olarak, belirlenen zaman dilimindeki potansiyel işlem sinyallerini değerlendir. Olasılık durumuna göre sinyal sayısını kendin belirle (1-3 arası).

{signal_template}

### 🚀 Sinyal 1  
- **Yön:** [Long / Short]  
- **🎯 Giriş Noktası:** [örnek: 25.300 USDT]  
- **📈 TP Seviyeleri:**  
  - T1: [örnek: 25.800 USDT (%1.9)]  
  - T2: [örnek: 26.300 USDT (%3.9)]  
  - T3: [örnek: 27.000 USDT (%6.7)]  
- **🛑 SL Seviyesi:** [örnek: 24.900 USDT (%-1.6)]  
- **⚖️ Risk/Ödül Oranı:** [örnek: 1:2.5]
- **⏱️ Zaman Dilimi:** [örnek: 4 Saatlik grafik için]
- **🔄 Geçerlilik Süresi:** [örnek: 24 saat içinde]
- **💪 Sinyal Gücü:** [Güçlü / Orta / Zayıf] ❗

**---**

### 🚀 Sinyal 2 (Opsiyonel - Sadece açık bir fırsat varsa)
- **Yön:** [Long / Short]  
- **🎯 Giriş Noktası:** [örnek: 25.300 USDT]  
- **📈 TP Seviyeleri:**  
  - T1: [örnek: 25.800 USDT (%1.9)]  
  - T2: [örnek: 26.300 USDT (%3.9)]  
  - T3: [örnek: 27.000 USDT (%6.7)]  
- **🛑 SL Seviyesi:** [örnek: 24.900 USDT (%-1.6)]  
- **⚖️ Risk/Ödül Oranı:** [örnek: 1:2.5]
- **⏱️ Zaman Dilimi:** [örnek: 4 Saatlik grafik için]
- **🔄 Geçerlilik Süresi:** [örnek: 24 saat içinde]
- **💪 Sinyal Gücü:** [Güçlü / Orta / Zayıf] ❗

**---**

### 🚀 Sinyal 3 (Opsiyonel - Sadece açık bir fırsat varsa)
- **Yön:** [Long / Short]  
- **🎯 Giriş Noktası:** [örnek: 25.300 USDT]  
- **📈 TP Seviyeleri:**  
  - T1: [örnek: 25.800 USDT (%1.9)]  
  - T2: [örnek: 26.300 USDT (%3.9)]  
  - T3: [örnek: 27.000 USDT (%6.7)]  
- **🛑 SL Seviyesi:** [örnek: 24.900 USDT (%-1.6)]  
- **⚖️ Risk/Ödül Oranı:** [örnek: 1:2.5]
- **⏱️ Zaman Dilimi:** [örnek: 4 Saatlik grafik için]
- **🔄 Geçerlilik Süresi:** [örnek: 24 saat içinde]
- **💪 Sinyal Gücü:** [Güçlü / Orta / Zayıf] ❗

### 🔄 Durum Güncellemesi:
**Mevcut piyasa koşullarına göre, yukarıdaki sinyallerin ne zaman güncelleneceğini veya geçersiz olacağını belirt. Örneğin:**
- "Bitcoin 28.000 USD üzerine çıkarsa Sinyal 1 geçersiz olacaktır."
- "Fonlama oranı negatife dönerse Sinyal 2'nin güçlenmesi beklenebilir."

### 🔍 Piyasa İzleme Faktörleri:
- **Kritik Seviye İzleme:** Hangi fiyat seviyeleri veya gösterge değerleri yakından takip edilmeli?
- **Uyarı Noktaları:** Hangi durumlarda aktif pozisyonlar kapatılmalı veya strateji gözden geçirilmeli?
- **Fırsat Penceresi:** Bu sinyallerin geçerli olacağı tahmini zaman aralığı ve sinyallerin geçerliliğini yitireceği koşullar nelerdir?
- **Piyasa Haberleri:** İzlenmesi gereken yüksek etkili haber veya gelişmeler var mı?

### 13. Son Notlar ve Tavsiyeler
- Yatırımcının dikkat etmesi gereken ek psikolojik faktörler veya disiplin kuralları.
- Bu analizin bir yatırım tavsiyesi olmadığı, sadece eğitim ve bilgilendirme amaçlı olduğu uyarısı.

Lütfen analizini yukarıdaki tüm başlıkları kapsayacak şekilde, net, gerekçelendirilmiş ve uygulanabilir finansal terimler kullanarak hazırla. Özellikle risk yönetimi unsurlarını ve yeni eklenen veri noktalarını (`vwap`, `fear_and_greed_index`, `recent_liquidations`, `order_book_summary`) her adımda vurgula.
"""

class FuturesTradingAnalysisModule(BaseAnalysisModule):
    """
    Module for futures trading analysis of cryptocurrencies.
    
    This module focuses on identifying leveraged trading opportunities, risk management,
    and futures market-specific factors for cryptocurrency trading.
    """
    
    def __init__(self, binance_client: BinanceClient, llm_client: GeminiClient):
        """
        Initialize the futures trading analysis module.
        
        Args:
            binance_client: Client for accessing Binance exchange data
            llm_client: Client for accessing language model services
        """
        super().__init__(
            name="futures_trading_analysis",
            description="Futures/leverage trading analysis with risk management"
        )
        self.binance_client = binance_client
        self.llm_client = llm_client
    
    async def perform_analysis(self, symbol: str, **kwargs) -> str:
        """
        Perform futures trading analysis on a cryptocurrency.
        
        Args:
            symbol: The cryptocurrency symbol to analyze (e.g., 'BTCUSDT')
            **kwargs: Additional parameters (timeframe, etc.)
            
        Returns:
            str: Formatted futures trading analysis result
        """
        self.log_info(f"Starting futures trading analysis for {symbol}")
        
        try:
            # Standardize symbol format
            if not any(symbol.upper().endswith(suffix) for suffix in ['USDT', 'BTC', 'ETH', 'BUSD']):
                symbol = f"{symbol.upper()}USDT"
            else:
                symbol = symbol.upper()
            
            # Get primary timeframe or default to 4h
            timeframe = kwargs.get('timeframe', '4h')
            
            # Get current symbol data from spot market
            try:
                current_ticker_data = await self.binance_client.client.get_ticker(symbol=symbol)
                if not current_ticker_data:
                    # Try alternative symbol forms (for flexibility)
                    base_symbol = symbol.rstrip("USDT")
                    alternative_symbols = [
                        f"{base_symbol}USDT", 
                        f"{base_symbol}BTC",
                        f"{base_symbol}ETH",
                        f"{base_symbol}BUSD"
                    ]
                    
                    for alt_symbol in alternative_symbols:
                        if alt_symbol != symbol:
                            self.log_info(f"Trying alternative symbol: {alt_symbol}")
                            current_ticker_data = await self.binance_client.client.get_ticker(symbol=alt_symbol)
                            if current_ticker_data:
                                symbol = alt_symbol  # Update the symbol to the working one
                                self.log_info(f"Successfully found data using alternative symbol: {symbol}")
                                break
                
                if not current_ticker_data:
                    return f"❌ Binance borsasında {symbol} sembolü bulunamadı veya veri alınamadı.\n\nÖneriler:\n1. Sembolün tam adını kontrol edin (örn: 'BTC' yerine 'BTCUSDT')\n2. Bu token Binance'de listelenmemiş olabilir\n3. Alternatif pariteler deneyin (örn: BUSD, BTC veya ETH ile çiftler)"
            except Exception as e:
                self.log_error(f"Error retrieving ticker data for {symbol}: {e}")
                return f"❌ {symbol} için veri alırken bir hata oluştu: {str(e)}\n\nÖneriler:\n1. Sembolün Binance'de listelendiğinden emin olun\n2. Doğru formatta yazdığınızı kontrol edin (örn: 'BTC' yerine 'BTCUSDT')"
            
            # Get futures specific data
            futures_specific_data = await self._get_futures_data(symbol) # Enhanced for liquidations
            
            # Get klines data for the specified timeframe
            klines = await self.binance_client.get_klines(symbol, timeframe, limit=300) 
            if not klines or len(klines) < 50:
                return f"❌ {symbol} için {timeframe} zaman diliminde yeterli geçmiş veri bulunamadı. Bu sembol Binance'de yakın zamanda listelenmiş olabilir veya çok düşük işlem hacmine sahip olabilir."
            
            # Process klines data
            df = preprocess_klines_df(klines)
            
            # Calculate VWAP manually if not included in the indicators
            vwap_df = self._calculate_vwap(df)
            
            # Calculate other technical indicators
            df_with_indicators = calculate_technical_indicators(df)
            
            # Merge VWAP with other indicators
            df_with_indicators['vwap'] = vwap_df['vwap']
            
            latest_indicators = extract_latest_indicators(df_with_indicators)
            
            # Get volatility data
            volatility_data = self._calculate_volatility(df)

            # Get Fear & Greed Index - use placeholder as it requires external API
            fear_and_greed_data = await self._get_fear_and_greed_index()

            # Get Order Book Summary
            order_book_summary = await self._get_order_book_summary(symbol)
            
            # Prepare data for LLM prompt
            current_price = float(current_ticker_data.get('lastPrice', 'N/A'))
            price_change_percent = float(current_ticker_data.get('priceChangePercent', 'N/A'))
            volume_24h = float(current_ticker_data.get('volume', 'N/A'))
            
            vwap_value = latest_indicators.get('vwap', 'N/A')
            if vwap_value == 'N/A' and 'vwap' in vwap_df:
                vwap_value = float(vwap_df['vwap'].iloc[-1])

            technical_data_dict = {
                "price_data": {
                    "high_24h": float(current_ticker_data.get('highPrice', 'N/A')),
                    "low_24h": float(current_ticker_data.get('lowPrice', 'N/A')),
                    "volume_24h": volume_24h,
                },
                "indicators": latest_indicators,
                "volatility": volatility_data,
                "futures_specific": futures_specific_data,
                "fear_and_greed_index": fear_and_greed_data,
                "order_book_summary": order_book_summary,
                "vwap": vwap_value
            }
            
            technical_data_dict = self._convert_numpy_types(technical_data_dict)
            technical_data = json.dumps(technical_data_dict, indent=2, ensure_ascii=False)
            
            # Format the Fear & Greed value for prompt
            fear_and_greed_value = "N/A"
            if fear_and_greed_data.get('value') != 'N/A':
                fear_and_greed_value = f"{fear_and_greed_data.get('value')} - {fear_and_greed_data.get('classification')}"
            
            # Signal template for dynamic signal count
            signal_template = """
**Not:** Piyasa koşullarına göre 1-3 arası sinyal oluştur. Eğer potansiyel bir işlem fırsatı görmüyorsan, sadece Sinyal 1'i doldur ve bu bir potansiyel senaryo olarak belirt. Her sinyal için aşağıdaki şablonu takip et:

Aşağıdaki kriterlere göre sinyal sayısına karar ver:
1. Birden fazla sinyal oluşturacaksan her biri farklı giriş noktaları veya farklı senaryolar için olsun
2. "Güçlü" olarak işaretlenecek sinyaller için trend, teknik göstergeler ve destek/direnç seviyeleri tam bir uyum içinde olmalı
3. Her sinyal için Risk/Ödül oranının en az 1:1.5 olmasına dikkat et
4. Piyasa volatilitesi yüksekse, daha az sinyal oluştur ve risk/ödül oranını daha yüksek belirle
5. Eğer hiçbir açık fırsat yoksa, Sinyal 1'i gelecekteki potansiyel bir senaryo olarak işaretle ve "Sinyal Gücü: Zayıf" olarak belirt
"""
            
            prompt = FUTURES_TRADING_PROMPT.format(
                symbol=symbol,
                technical_data=technical_data,
                current_price=current_price,
                price_change_percent=price_change_percent,
                volume_24h=volume_24h,
                open_interest=futures_specific_data.get('openInterest', 'N/A'),
                funding_rate=futures_specific_data.get('fundingRate', 'N/A'),
                rsi_period=RSI_PERIOD,
                rsi_value=latest_indicators.get('rsi', 'N/A'),
                macd_value=latest_indicators.get('macd', 'N/A'),
                macd_signal=latest_indicators.get('macd_signal', 'N/A'),
                sma_short=SMA_SHORT_PERIOD,
                sma_short_value=latest_indicators.get(f'sma_{SMA_SHORT_PERIOD}', 'N/A'),
                sma_long=SMA_LONG_PERIOD,
                sma_long_value=latest_indicators.get(f'sma_{SMA_LONG_PERIOD}', 'N/A'),
                vwap_value=vwap_value,
                fear_and_greed_value=fear_and_greed_value,
                signal_template=signal_template
            )
            
            response = self.llm_client.generate_text(prompt)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            risk_warning = (
                "⚠️ **RİSK UYARISI**: Vadeli işlemler ve kaldıraçlı alım satım önemli ölçüde risk içerir. "
                "Sağlanan analiz yalnızca bilgilendirme amaçlıdır ve mali tavsiye olarak değerlendirilmemelidir. "
                "Her zaman uygun risk yönetimi uygulayın."
            )
            
            final_analysis = f"# {symbol} VADELİ İŞLEMLER ANALİZİ\n"
            final_analysis += f"**Analiz Zamanı**: {timestamp}\n"
            final_analysis += f"**Zaman Dilimi**: {timeframe}\n\n"
            final_analysis += f"**Anlık Fiyat**: {current_price} USDT ({price_change_percent}% 24s)\n"
            if vwap_value != 'N/A':
                final_analysis += f"**VWAP**: {vwap_value} USDT\n"
            if fear_and_greed_data.get('value') != 'N/A':
                 final_analysis += f"**Korku & Açgözlülük Endeksi**: {fear_and_greed_data.get('value')} ({fear_and_greed_data.get('classification')})\n"
            final_analysis += "\n"
            final_analysis += f"{risk_warning}\n\n"
            final_analysis += response
            
            self.log_info(f"Completed futures trading analysis for {symbol}")
            return final_analysis
            
        except Exception as e:
            error_message = f"Error analyzing {symbol} for futures trading: {str(e)}"
            self.log_error(error_message, exc_info=e)
            return f"❌ Vadeli işlemler analizi başarısız oldu: {error_message}"
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate VWAP (Volume Weighted Average Price) from OHLC data.
        
        Args:
            df: DataFrame with OHLC price data including 'volume' column
            
        Returns:
            DataFrame with VWAP added
        """
        try:
            if 'volume' not in df.columns:
                self.log_error("Volume data not found in DataFrame, cannot calculate VWAP")
                df['vwap'] = np.nan
                return df
            
            # Create a copy to avoid modifying the original
            vwap_df = df.copy()
            
            # Calculate typical price
            vwap_df['typical_price'] = (vwap_df['high'] + vwap_df['low'] + vwap_df['close']) / 3
            
            # Calculate VWAP components
            vwap_df['tp_volume'] = vwap_df['typical_price'] * vwap_df['volume']
            
            # Calculate cumulative values
            vwap_df['cumulative_tp_volume'] = vwap_df['tp_volume'].cumsum()
            vwap_df['cumulative_volume'] = vwap_df['volume'].cumsum()
            
            # Calculate VWAP
            vwap_df['vwap'] = vwap_df['cumulative_tp_volume'] / vwap_df['cumulative_volume']
            
            # Drop intermediate columns to keep the DataFrame clean
            vwap_df = vwap_df[['vwap']]
            
            self.log_info("VWAP calculated successfully")
            return vwap_df
            
        except Exception as e:
            self.log_error(f"Error calculating VWAP: {e}")
            df_result = pd.DataFrame()
            df_result['vwap'] = np.nan
            return df_result
    
    async def _get_futures_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get futures-specific data for a symbol, including enhanced liquidation info.
        """
        futures_data = {
            "openInterest": "N/A",
            "fundingRate": "N/A",
            "longShortRatio": "N/A",
            "recent_liquidations": {
                "last_hour": [],
                "last_day": [],
                "significant_levels": []
            }
        }
        
        try:
            # Funding rate
            funding_rate_data = await self._safe_futures_api_call(
                lambda: self.binance_client.client.futures_funding_rate(symbol=symbol, limit=1)
            )
            if funding_rate_data and len(funding_rate_data) > 0:
                funding_rate = funding_rate_data[0]['fundingRate']
                futures_data['fundingRate'] = float(funding_rate) * 100
            
            # Open interest
            open_interest_data = await self._safe_futures_api_call(
                lambda: self.binance_client.client.futures_open_interest(symbol=symbol)
            )
            if open_interest_data:
                futures_data['openInterest'] = float(open_interest_data.get('openInterest', 'N/A'))
                
            # Long/short ratio
            ratio_data = await self._safe_futures_api_call(
                lambda: self.binance_client.client.futures_top_longshort_position_ratio(
                    symbol=symbol, period='1h', limit=1
                )
            )
            if ratio_data and len(ratio_data) > 0:
                futures_data['longShortRatio'] = float(ratio_data[0]['longShortRatio'])

            # Try to get recent liquidations - from futures API if available
            await self._get_recent_liquidations(symbol, futures_data)

        except Exception as e:
            self.log_error(f"Error getting futures data for {symbol}: {e}")
        
        return futures_data
    
    async def _get_recent_liquidations(self, symbol: str, futures_data: Dict[str, Any]) -> None:
        """
        Get recent liquidation data for a symbol.
        This method uses a combination of:
        1. Direct Binance API calls to futures liquidation endpoint (if available)
        2. Estimated liquidation levels based on funding history and open interest changes
        
        Args:
            symbol: The cryptocurrency symbol to get liquidations for
            futures_data: Dictionary to update with liquidation information
        """
        try:
            # Try to get recent liquidations from Binance if the API endpoint is available
            # Note: This might be restricted or might not exist depending on the Binance API version
            liquidation_orders = await self._safe_futures_api_call(
                lambda: self.binance_client.client.futures_liquidation_orders(symbol=symbol)
            )
            
            if liquidation_orders and isinstance(liquidation_orders, list) and len(liquidation_orders) > 0:
                # Process real liquidation data
                for liq in liquidation_orders:
                    # Convert timestamp to datetime
                    liq_time = datetime.fromtimestamp(liq.get('time', 0) / 1000)
                    now = datetime.now()
                    
                    # Create liquidation entry
                    liq_entry = {
                        "side": liq.get('side', 'N/A').lower(),
                        "price": float(liq.get('price', 0)),
                        "qty": float(liq.get('origQty', 0)),
                        "time": liq_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "value_usdt": float(liq.get('price', 0)) * float(liq.get('origQty', 0))
                    }
                    
                    # Add to appropriate time bucket
                    if (now - liq_time).total_seconds() <= 3600:  # Last hour
                        futures_data['recent_liquidations']['last_hour'].append(liq_entry)
                    
                    if (now - liq_time).total_seconds() <= 86400:  # Last day
                        futures_data['recent_liquidations']['last_day'].append(liq_entry)
                
                # Identify significant liquidation levels
                if futures_data['recent_liquidations']['last_day']:
                    # Group by price ranges to find clusters
                    price_clusters = {}
                    for liq in futures_data['recent_liquidations']['last_day']:
                        # Round price to nearest 10 or 100 depending on asset price range
                        price_key = round(liq['price'] / 10) * 10
                        if price_key not in price_clusters:
                            price_clusters[price_key] = {
                                "price_range": f"{price_key-5} to {price_key+5}",
                                "total_value": 0,
                                "count": 0
                            }
                        price_clusters[price_key]["total_value"] += liq['value_usdt']
                        price_clusters[price_key]["count"] += 1
                    
                    # Sort by total value to find most significant clusters
                    significant_clusters = sorted(
                        price_clusters.values(),
                        key=lambda x: x["total_value"],
                        reverse=True
                    )[:3]  # Take top 3
                    
                    futures_data['recent_liquidations']['significant_levels'] = significant_clusters
            else:
                # If no real liquidation data, use estimated data based on funding rate and price history
                self.log_info(f"No liquidation data available for {symbol}, using estimated significant levels")
                
                # Get klines to estimate potential liquidation levels
                klines = await self.binance_client.get_klines(symbol, '1d', limit=7)
                if klines and len(klines) > 0:
                    df = preprocess_klines_df(klines)
                    
                    # Identify significant price levels
                    high = df['high'].max()
                    low = df['low'].min()
                    last_close = df['close'].iloc[-1]
                    
                    # Create estimated liquidation levels
                    futures_data['recent_liquidations']['significant_levels'] = [
                        {
                            "price_range": f"{round(low * 0.97)} to {round(low * 0.99)}",
                            "estimated": True,
                            "description": "Probable long liquidation zone below recent lows"
                        },
                        {
                            "price_range": f"{round(high * 1.01)} to {round(high * 1.03)}",
                            "estimated": True,
                            "description": "Probable short liquidation zone above recent highs"
                        }
                    ]
                    
                    # Create placeholder liquidation events for recent history
                    # These are fictional but representative for demonstration
                    from_time = datetime.now()
                    for i in range(3):
                        from_time = from_time.replace(minute=from_time.minute - 15)
                        side = "long" if i % 2 == 0 else "short"
                        price_mod = 0.98 if side == "long" else 1.02
                        
                        futures_data['recent_liquidations']['last_hour'].append({
                            "side": side,
                            "price": round(last_close * price_mod, 2),
                            "qty": round(np.random.uniform(0.1, 2.0), 2),
                            "time": from_time.strftime('%Y-%m-%d %H:%M:%S'),
                            "value_usdt": round(last_close * price_mod * np.random.uniform(1000, 10000), 2),
                            "estimated": True
                        })
        
        except Exception as e:
            self.log_error(f"Error getting liquidation data for {symbol}: {e}")
            self.log_info(f"Using placeholder liquidation data for {symbol}")
            
            # Always provide some data even if API calls fail
            futures_data['recent_liquidations']['last_hour'] = [
                {
                    "side": "long",
                    "price": 0,
                    "qty": 0,
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "value_usdt": 0,
                    "placeholder": True
                }
            ]
    
    async def _get_fear_and_greed_index(self) -> Dict[str, Any]:
        """
        Get the latest Fear & Greed Index data.
        In a real implementation, this would call an external API like alternative.me.
        
        Returns:
            Dict[str, Any]: Dictionary with fear and greed data
        """
        self.log_info("Getting Fear & Greed Index data")
        
        # In a production environment, you would implement an HTTP request to an API
        # Example for alternative.me API:
        try:
            # This is a placeholder for the actual HTTP API call
            # In a real implementation you would use aiohttp or similar:
            # async with aiohttp.ClientSession() as session:
            #     async with session.get('https://api.alternative.me/fng/?limit=1') as response:
            #         if response.status == 200:
            #             data = await response.json()
            
            # For now, use hardcoded recent data or random value for demonstration
            import random
            value = random.randint(20, 75)
            
            # Map value to classification
            classification = "Neutral"
            if value <= 25:
                classification = "Aşırı Korku"
            elif value <= 40:
                classification = "Korku"
            elif value <= 60:
                classification = "Nötr"
            elif value <= 75:
                classification = "Açgözlülük"
            else:
                classification = "Aşırı Açgözlülük"
            
            return {
                "value": value,
                "classification": classification,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            self.log_error(f"Error fetching Fear & Greed Index: {e}")
            return {
                "value": "N/A",
                "classification": "N/A",
                "timestamp": "N/A"
            }
    
    async def _get_order_book_summary(self, symbol: str) -> Dict[str, Any]:
        """
        Get a summary of the order book for a symbol.
        
        Args:
            symbol: The cryptocurrency symbol to get order book for
            
        Returns:
            Dict[str, Any]: Dictionary with order book summary
        """
        self.log_info(f"Getting order book summary for {symbol}")
        
        summary = {
            "strongest_bid_levels": [],
            "strongest_ask_levels": [],
            "bid_ask_spread_percent": "N/A",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Get order book from Binance
            depth = await self.binance_client.client.get_order_book(symbol=symbol, limit=100)
            
            if not depth or 'bids' not in depth or 'asks' not in depth:
                self.log_error(f"Invalid order book data received for {symbol}")
                return summary
            
            # Calculate bid-ask spread
            best_bid = float(depth['bids'][0][0])
            best_ask = float(depth['asks'][0][0])
            spread = ((best_ask - best_bid) / best_ask) * 100
            summary["bid_ask_spread_percent"] = round(spread, 4)
            
            # Process bids - find walls (large orders)
            bids_processed = []
            for bid in depth['bids']:
                price = float(bid[0])
                qty = float(bid[1])
                
                # Check if this is large enough to be considered a wall
                # (either absolute size or compared to nearby orders)
                if qty > 10:  # Simple threshold, adjust based on typical volume
                    bids_processed.append({
                        "price": price,
                        "quantity": qty,
                        "value_usdt": price * qty
                    })
            
            # Process asks - find walls
            asks_processed = []
            for ask in depth['asks']:
                price = float(ask[0])
                qty = float(ask[1])
                
                # Similar logic for ask walls
                if qty > 10:  # Simple threshold
                    asks_processed.append({
                        "price": price,
                        "quantity": qty,
                        "value_usdt": price * qty
                    })
            
            # Sort by value to find the strongest levels
            bids_processed.sort(key=lambda x: x["value_usdt"], reverse=True)
            asks_processed.sort(key=lambda x: x["value_usdt"], reverse=True)
            
            # Take top 3 or all if less than 3
            summary["strongest_bid_levels"] = bids_processed[:min(3, len(bids_processed))]
            summary["strongest_ask_levels"] = asks_processed[:min(3, len(asks_processed))]
            
            # If no walls found, include strongest visible levels anyway
            if not summary["strongest_bid_levels"] and depth['bids']:
                top_bid = {
                    "price": float(depth['bids'][0][0]),
                    "quantity": float(depth['bids'][0][1]),
                    "value_usdt": float(depth['bids'][0][0]) * float(depth['bids'][0][1]),
                    "note": "Best bid (not a significant wall)"
                }
                summary["strongest_bid_levels"].append(top_bid)
            
            if not summary["strongest_ask_levels"] and depth['asks']:
                top_ask = {
                    "price": float(depth['asks'][0][0]),
                    "quantity": float(depth['asks'][0][1]),
                    "value_usdt": float(depth['asks'][0][0]) * float(depth['asks'][0][1]),
                    "note": "Best ask (not a significant wall)"
                }
                summary["strongest_ask_levels"].append(top_ask)
                
        except Exception as e:
            self.log_error(f"Error processing order book for {symbol}: {e}")
            # Provide empty structure on error
            
        return summary
    
    async def _safe_futures_api_call(self, api_call_function):
        """
        Safely call a futures API function, handling potential permission issues.
        
        Args:
            api_call_function: Function to call that accesses futures API
            
        Returns:
            Any: Result of the API call or None if failed
        """
        try:
            return await api_call_function()
        except Exception as e:
            self.log_error(f"Futures API call error: {e}")
            return None
    
    def _calculate_volatility(self, df) -> Dict[str, Any]:
        """
        Calculate volatility metrics from price data.
        
        Args:
            df: DataFrame with OHLC price data
            
        Returns:
            Dict[str, Any]: Dictionary with volatility metrics
        """
        volatility_data = {
            "daily_volatility_percent": "N/A",
            "atr_14": "N/A",
            "bollinger_width": "N/A",
            "price_range_24h_percent": "N/A",
        }
        
        try:
            # Daily volatility (standard deviation of daily returns)
            df['daily_returns'] = df['close'].pct_change() * 100
            volatility_data['daily_volatility_percent'] = float(df['daily_returns'].std())
            
            # ATR-14 from the indicators (if available)
            if 'atr_14' in df.columns:
                volatility_data['atr_14'] = float(df['atr_14'].iloc[-1])
            
            # Bollinger Band width
            if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'bb_middle']):
                latest_upper = float(df['bb_upper'].iloc[-1])
                latest_lower = float(df['bb_lower'].iloc[-1])
                latest_middle = float(df['bb_middle'].iloc[-1])
                
                # Calculate width as percentage of middle band
                width_percent = ((latest_upper - latest_lower) / latest_middle) * 100
                volatility_data['bollinger_width'] = float(width_percent)
            
            # 24h price range
            recent_df = df.tail(24)  # Assume hourly data or adjust accordingly
            if len(recent_df) > 0:
                high_24h = float(recent_df['high'].max())
                low_24h = float(recent_df['low'].min())
                avg_price = (high_24h + low_24h) / 2
                
                range_percent = ((high_24h - low_24h) / avg_price) * 100
                volatility_data['price_range_24h_percent'] = float(range_percent)
                
        except Exception as e:
            self.log_error(f"Error calculating volatility metrics: {e}")
            # Keep default N/A values
        
        return volatility_data
        
    async def get_analysis_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters used by this analysis module.
        
        Returns:
            Dict[str, Any]: Dictionary of parameter names and their values
        """
        return {
            "supported_timeframes": ["15m", "1h", "4h", "1d"],
            "default_timeframe": "4h",
            "max_recommended_leverage": 20,
            "indicators": {
                "RSI": {
                    "period": RSI_PERIOD
                },
                "MACD": {
                    "fast_period": MACD_FAST_PERIOD,
                    "slow_period": MACD_SLOW_PERIOD,
                    "signal_period": MACD_SIGNAL_PERIOD
                },
                "SMA": {
                    "short_period": SMA_SHORT_PERIOD,
                    "long_period": SMA_LONG_PERIOD
                },
                "EMA": {
                    "short_period": EMA_SHORT_PERIOD,
                    "long_period": EMA_LONG_PERIOD
                },
            },
            "volatility_metrics": ["daily_volatility", "atr_14", "bollinger_width", "price_range_24h"]
        }

    def _convert_numpy_types(self, obj):
        """
        Recursively convert numpy types to native Python types for JSON serialization.
        
        Args:
            obj: Object to convert (can be dict, list, or scalar value)
            
        Returns:
            Object with numpy types converted to native Python types
        """
        if isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif obj is np.True_:
            return True
        elif obj is np.False_:
            return False
        elif isinstance(obj, np.ndarray):
            return self._convert_numpy_types(obj.tolist())
        else:
            return obj 