"""
Spot Trading Analysis Module - Analyzes cryptocurrencies for spot trading opportunities.
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np

from clients.exchange_client import BinanceClient
from clients.llm_client import GeminiClient
from core_logic.constants import (
    TARGET_KLINE_INTERVALS, KLINE_INTERVAL_MAP, RSI_PERIOD, SMA_SHORT_PERIOD, SMA_LONG_PERIOD
)
from utils.general_utils import (
    preprocess_klines_df, calculate_technical_indicators, extract_latest_indicators
)

from .base_analysis import BaseAnalysisModule

# LLM prompt template for spot trading analysis
SPOT_TRADING_PROMPT = """
# ROL VE GÖREV
Sen deneyimli bir kripto para spot trading uzmanısın. Ana görevin {symbol} için mevcut verilere dayanarak net alım-satım stratejileri ve özellikle isabetli alım noktaları belirleyerek fırsatları önermektir. Detaylı piyasa analizi yerine, yalnızca spot trading açısından önemli noktalara odaklan, pratik, uygulanabilir işlem stratejileri sun ve önerdiğin her alım seviyesinin gerekçelerini detaylıca açıkla.

# VERİLER
**{symbol} İçin Teknik Veriler:**
{technical_data}

**Mevcut Durum:**
Güncel Fiyat: {current_price} USDT
24s Değişim: {price_change_percent}%
RSI({rsi_period}): {rsi_value}
SMA{sma_short}: {sma_short_value}
SMA{sma_long}: {sma_long_value}

# SPOT TİCARET ANALİZİ
Aşağıdaki bölümleri içeren, ticaret odaklı bir analiz hazırla:

## {symbol} Spot Ticaret Fırsatı Analizi

### 1. Piyasa Pozisyonu Özeti
- Şu anki trend durumu (Yükseliş, Düşüş, Yatay)
- İşlem yapılabilir bir fırsat var mı? Varsa, bu fırsatın niteliği (örn: Düşüş sonrası tepki alımı, trend devam formasyonu vb.)
- En çok 3-4 cümleyle mevcut pozisyonu ve potansiyel alım fırsatlarını özetle

### 2. Kritik Fiyat Seviyeleri
**Potansiyel Alım Bölgeleri (Destekler):**
- S1: [değer] - [neden önemli? Bu seviye alım için neden uygun olabilir?]
- S2: [değer] - [neden önemli? Bu seviye alım için neden uygun olabilir?]
- S3 (varsa): [değer] - [neden önemli? Bu seviye alım için neden uygun olabilir?]

**Güçlü Direnç Seviyeleri:**
- R1: [değer] - [neden önemli?]
- R2: [değer] - [neden önemli?]

**Anlık Kilit Seviye:**
Şu an için en kritik izlenmesi gereken fiyat seviyesi hangisi ve neden? Bu seviye potansiyel bir alım veya satım sinyali için nasıl kullanılabilir?

### 3. Giriş ve Çıkış Stratejisi
**Alım Fırsatı Detayları:**
- **Öncelikli Alım Bölgesi/Noktası:** [değer/değer aralığı]
    - Gerekçe: [Bu bölgenin/noktanın seçilme nedeni nedir? Teknik olarak neden güçlü bir alım potansiyeli taşıyor?]
    - Giriş için Gerekli Koşullar: [Fiyatın bu seviyeye gelmesi yeterli mi, yoksa ek olarak hangi teknik gösterge (örn: RSI, MACD kesişimi), mum formasyonu (örn: bullish engulfing, pin bar) veya piyasa durumu (örn: hacim artışı) beklenmeli?]
    - Önerilen Giriş Tipi: [Limit emir mi, piyasa emri mi? Teyit bekleyerek mi, yoksa direkt giriş mi?]
- **Alternatif Alım Bölgesi/Noktası (varsa):** [değer/değer aralığı]
    - Gerekçe:
    - Giriş için Gerekli Koşullar:
    - Önerilen Giriş Tipi:

**Kar Alma Hedefleri (Öncelikli Alım Noktasına Göre):**
- T1 (Kısa Vadeli): [değer ve % kazanç] - [Bu hedefin belirlenme mantığı nedir?]
- T2 (Orta Vadeli): [değer ve % kazanç] - [Bu hedefin belirlenme mantığı nedir?]
- T3 (Uzun Vadeli, opsiyonel): [değer ve % kazanç] - [Bu hedefin belirlenme mantığı nedir?]

**Stop-Loss (Öncelikli Alım Noktasına Göre):**
- Stop-Loss Seviyesi: [değer ve % risk]
- Stop-Loss Belirleme Mantığı: [Neden bu seviye seçildi? Hangi destek seviyesinin altı veya hangi teknik bozulma dikkate alındı?]
- Stop-Loss esnetilebilir mi? Hangi durumlarda stop-loss seviyesi güncellenmeli?

### 4. Risk Yönetimi
- Seçilen Giriş Noktası için Risk/Ödül Oranı: [T1, T2 ve T3 hedefleri için ayrı ayrı hesapla]
- Önerilen Pozisyon Büyüklüğü: [Portföyün %'si olarak, risk iştahına göre (örn: düşük, orta, yüksek riskli portföyler için farklı öneriler)]
- Maksimum Kabul Edilebilir Kayıp: [İşlem başına portföyün %'si]
- Risk Azaltma Stratejileri: [Kademeli alım, kısmi kar alma, trailing stop kullanımı, pozisyonu hedge etme (mümkünse) vb. somut öneriler]

### 5. Teknik Gösterge Sinyalleri ve Alım Fırsatıyla İlişkisi
- RSI Sinyali: [aşırı alım/satım/nötr, değeri] - [Bu durum potansiyel bir alım fırsatını nasıl etkiliyor? Alım için onay veriyor mu, yoksa bekle mi diyor?]
- MACD Durumu: [pozisyon, kesişim durumu ve trend] - [MACD alım sinyali üretiyor mu? Mevcut alım stratejisini destekliyor mu?]
- Hareketli Ortalamalar (SMA{sma_short} ve SMA{sma_long}): [Fiyatın ortalamalara göre konumu, ortalamaların birbirine göre durumu (golden cross/death cross)] - [Ortalamalar destek görevi görüyor mu? Alım için uygun bir ortam sunuyorlar mı?]
- Bollinger Bantları Pozisyonu: [Fiyat bantların neresinde (alt, orta, üst)? Bant genişliği ne ifade ediyor (daralma/genişleme)?] - [Alt banda temas veya dışına taşma bir alım sinyali olabilir mi? Nasıl yorumlanmalı?]
- En güçlü alım sinyali veren gösterge hangisi ve bu sinyal nasıl değerlendirilmeli? Diğer göstergeler bu sinyali teyit ediyor mu?

### 6. İşlem Tavsiyesi
- Genel Pozisyon: [Güçlü Al / Al / Kademeli Al / Nötr-Bekle / Sat / Güçlü Sat]
- Alım İçin Zamanlama: [Hemen (koşullar uygunsa) / Belirli bir fiyat seviyesi veya teknik teyit beklendikten sonra / Piyasa sakinleşince]
- İşlem için En Uygun Zaman Dilimi: [Kısa (saatlik grafikler), orta (4s-günlük), uzun (haftalık)] - [Neden bu zaman dilimi öneriliyor?]
- Pozisyon Alma Taktiği: [Tek seferde mi, yoksa belirlenen alım bölgelerine kademeli emirler mi (örn: %X'i S1'den, %Y'si S2'den)? Agresif giriş mi, yoksa teyit bekleyerek mi?]
- Alım Yapmadan Önce Dikkat Edilmesi Gereken Ek Faktörler: [Piyasa genel duyarlılığı, önemli haberler, BTC dominasyonu vb.]

### 7. Alternatif Senaryolar
- **Beklenen Alım Bölgesi Çalışmazsa:**
    - Bir sonraki potansiyel alım bölgesi neresi olabilir?
    - Stop-loss stratejisi nasıl güncellenmeli?
- **Ani Yükseliş Senaryosu (Fırsat Kaçırılırsa):**
    - Yükselen trende dahil olmak için hangi seviyeler ve koşullar beklenebilir (pullback, retest vb.)?
    - Bu durumda risk yönetimi nasıl olmalı?
- Bu senaryolarda nasıl hareket edilmeli?

Analizini spot alım-satım kararları verecek kişiler için net, özlü, gerekçelendirilmiş ve uygulanabilir yap. Özellikle fiyat seviyelerine, giriş koşullarına, risk yönetimine ve alım stratejilerine odaklan. Her önerinin nedenini açıkla.
"""

class SpotTradingAnalysisModule(BaseAnalysisModule):
    """
    Module for spot trading analysis of cryptocurrencies.
    
    This module focuses on identifying trading opportunities, entry/exit points,
    and risk management for spot trading of cryptocurrencies.
    """
    
    def __init__(self, binance_client: BinanceClient, llm_client: GeminiClient):
        """
        Initialize the spot trading analysis module.
        
        Args:
            binance_client: Client for accessing Binance exchange data
            llm_client: Client for accessing language model services
        """
        super().__init__(
            name="spot_trading_analysis",
            description="Spot trading analysis with entry/exit points and risk management"
        )
        self.binance_client = binance_client
        self.llm_client = llm_client
    
    async def perform_analysis(self, symbol: str, **kwargs) -> str:
        """
        Perform spot trading analysis on a cryptocurrency.
        
        Args:
            symbol: The cryptocurrency symbol to analyze (e.g., 'BTCUSDT')
            **kwargs: Additional parameters (timeframe, etc.)
            
        Returns:
            str: Formatted trading analysis result
        """
        self.log_info(f"Starting spot trading analysis for {symbol}")
        
        try:
            # Standardize symbol format
            if not any(symbol.upper().endswith(suffix) for suffix in ['USDT', 'BTC', 'ETH', 'BUSD']):
                symbol = f"{symbol.upper()}USDT"
            else:
                symbol = symbol.upper()
            
            # Get primary timeframe or default to 4h
            timeframe = kwargs.get('timeframe', '4h')
            
            # Get current symbol data
            current_ticker_data = await self.binance_client.client.get_ticker(symbol=symbol)
            if not current_ticker_data:
                return f"❌ {symbol} için güncel piyasa verisi alınamadı"
            
            # Get klines data for the specified timeframe
            klines = await self.binance_client.get_klines(symbol, timeframe, limit=300) # 300 candles required for reliable technical indicator calculations (especially SMA200)
            if not klines or len(klines) < 50:
                return f"❌ {symbol} için {timeframe} zaman diliminde yeterli geçmiş veri bulunamadı"
            
            # Process klines data
            df = preprocess_klines_df(klines)
            df_with_indicators = calculate_technical_indicators(df)
            latest_indicators = extract_latest_indicators(df_with_indicators)
            
            # Prepare data for LLM prompt
            current_price = float(current_ticker_data.get('lastPrice', 'N/A'))
            price_change_percent = float(current_ticker_data.get('priceChangePercent', 'N/A'))
            
            # Get support and resistance levels
            sr_levels = self._calculate_support_resistance(df)
            
            # Format technical data as JSON for LLM
            technical_data_dict = {
                "price_data": {
                    "high_24h": float(current_ticker_data.get('highPrice', 'N/A')),
                    "low_24h": float(current_ticker_data.get('lowPrice', 'N/A')),
                    "volume_24h": float(current_ticker_data.get('volume', 'N/A')),
                },
                "indicators": latest_indicators,
                "support_resistance": sr_levels
            }
            
            # Convert numpy types to native Python types before JSON serialization
            technical_data_dict = self._convert_numpy_types(technical_data_dict)
            technical_data = json.dumps(technical_data_dict, indent=2)
            
            # Create LLM prompt
            prompt = SPOT_TRADING_PROMPT.format(
                symbol=symbol,
                technical_data=technical_data,
                current_price=current_price,
                price_change_percent=price_change_percent,
                rsi_period=RSI_PERIOD,
                rsi_value=latest_indicators.get('rsi', 'N/A'),
                sma_short=SMA_SHORT_PERIOD,
                sma_short_value=latest_indicators.get(f'sma_{SMA_SHORT_PERIOD}', 'N/A'),
                sma_long=SMA_LONG_PERIOD,
                sma_long_value=latest_indicators.get(f'sma_{SMA_LONG_PERIOD}', 'N/A')
            )
            
            # Get analysis from LLM
            response = self.llm_client.generate_text(prompt)
            
            # Format the final analysis
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_analysis = f"# {symbol} SPOT TİCARET ANALİZİ\n"
            final_analysis += f"**Analiz Zamanı**: {timestamp}\n"
            final_analysis += f"**Zaman Dilimi**: {timeframe}\n\n"
            final_analysis += f"**Güncel Fiyat**: {current_price} USDT (%{price_change_percent} 24s)\n\n"
            final_analysis += response
            
            self.log_info(f"Completed spot trading analysis for {symbol}")
            return final_analysis
            
        except Exception as e:
            error_message = f"Error analyzing {symbol} for spot trading: {str(e)}"
            self.log_error(error_message, exc_info=e)
            return f"❌ Spot ticaret analizi başarısız oldu: {error_message}"
    
    def _calculate_support_resistance(self, df) -> List[Dict[str, float]]:
        """
        Calculate support and resistance levels from price data.
        
        Args:
            df: DataFrame with OHLC price data
            
        Returns:
            List[Dict[str, float]]: List of support and resistance levels
        """
        # Simple implementation - find local highs and lows
        sr_levels = []
        
        # Use last 50 candles for analysis
        recent_df = df.tail(50)
        
        # Find local highs (potential resistance)
        for i in range(2, len(recent_df)-2):
            if (recent_df.iloc[i]['high'] > recent_df.iloc[i-1]['high'] and 
                recent_df.iloc[i]['high'] > recent_df.iloc[i-2]['high'] and
                recent_df.iloc[i]['high'] > recent_df.iloc[i+1]['high'] and
                recent_df.iloc[i]['high'] > recent_df.iloc[i+2]['high']):
                sr_levels.append({
                    "type": "resistance",
                    "price": float(recent_df.iloc[i]['high']),
                    "strength": 1  # Simple strength indicator
                })
        
        # Find local lows (potential support)
        for i in range(2, len(recent_df)-2):
            if (recent_df.iloc[i]['low'] < recent_df.iloc[i-1]['low'] and 
                recent_df.iloc[i]['low'] < recent_df.iloc[i-2]['low'] and
                recent_df.iloc[i]['low'] < recent_df.iloc[i+1]['low'] and
                recent_df.iloc[i]['low'] < recent_df.iloc[i+2]['low']):
                sr_levels.append({
                    "type": "support",
                    "price": float(recent_df.iloc[i]['low']),
                    "strength": 1  # Simple strength indicator
                })
        
        return sr_levels
    
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
    
    async def get_analysis_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters used by this analysis module.
        
        Returns:
            Dict[str, Any]: Dictionary of parameter names and their values
        """
        return {
            "supported_timeframes": ["15m", "1h", "4h", "1d"],
            "default_timeframe": "4h",
            "indicators": {
                "RSI": {
                    "period": RSI_PERIOD
                },
                "SMA": {
                    "short_period": SMA_SHORT_PERIOD,
                    "long_period": SMA_LONG_PERIOD
                }
            }
        } 