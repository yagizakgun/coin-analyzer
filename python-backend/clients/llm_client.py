import google.generativeai as genai
# Adjust import path for config
import config 
import logging

# Logger oluştur
logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, model_name=config.LLM_MODEL):
        if not config.LLM_API_KEY:
            logger.error("GeminiClient başlatılamadı: LLM API anahtarı eksik.")
            raise ValueError("Gemini API anahtarı (LLM_API_KEY) config.py üzerinden ayarlanmalı (.env dosyasını kontrol edin).")
        genai.configure(api_key=config.LLM_API_KEY)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini istemcisi '{model_name}' modeli ile başarıyla başlatıldı.")

    def generate_text(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            # Yanıtın yapısı Gemini API versiyonuna göre değişebilir.
            # Genellikle response.text veya response.parts[0].text gibi erişilir.
            if hasattr(response, 'text') and response.text:
                return response.text
            elif hasattr(response, 'parts') and response.parts and hasattr(response.parts[0], 'text'):
                return response.parts[0].text
            else:
                logger.warning(f"LLM yanıt formatı beklenenden farklı. Yanıt objesi: {response}")
                # Güvenli bir şekilde metin içeriğini bulmaya çalışalım
                try:
                    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                        full_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
                        if full_text:
                            logger.info("LLM yanıtı parçalardan başarıyla birleştirildi.")
                            return full_text
                except Exception as ex_parse:
                    logger.error(f"LLM yanıtını ayrıştırırken ek hata: {ex_parse}")
                
                logger.error("LLM'den metin içeriği alınamadı. Yanıt yapısı uygun değil.")
                return "LLM'den metin içeriği alınamadı."
            
        except Exception as e:
            logger.error(f"Gemini API'den metin üretirken hata: {e}")
            logger.exception("Gemini API metin üretimi sırasında bir istisna oluştu:")
            return None

# Test amaçlı - Bu kısım modül yapısı değişince çalışmayabilir.
# if __name__ == '__main__':
#     try:
#         gemini_handler = GeminiClient()
#         # ... (test kodları)
#     except Exception as e:
#         logger.error(f"Test sırasında hata: {e}") 