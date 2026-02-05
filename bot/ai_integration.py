import logging
import google.generativeai as genai
from groq import AsyncGroq
from bot import config

logger = logging.getLogger(__name__)

# Инициализируем только клиент Groq, т.к. у Gemini модель создается динамически
groq_client = AsyncGroq(api_key=config.GROQ_API_KEY)
# Настраиваем Gemini, но не создаем модель сразу
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
    logger.info("Gemini API configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")


async def get_ai_response(prompt: str, service_name: str) -> str:
    """
    Получает ответ от ИИ с логикой отказоустойчивости (failover).
    Пробует модели из списка в .env по очереди.
    """
    settings = config.load_json(config.SETTINGS_FILE)
    system_prompt = settings.get('ai_prompt', config.DEFAULT_AI_PROMPT)

    full_prompt = f"{system_prompt}\n\n---\nВот вопрос пользователя:\n\"{prompt}\""
    logger.debug(f"Constructed full prompt for service '{service_name}'.")

    # --- ЛОГИКА ДЛЯ GROQ ---
    if service_name == "groq":
        logger.info(f"Attempting to get response from Groq models: {config.GROQ_MODELS}")
        for model in config.GROQ_MODELS:
            logger.debug(f"Trying Groq model: '{model}'...")
            try:
                chat_completion = await groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": full_prompt}],
                    model=model,
                )
                logger.info(f"SUCCESS! Got response from Groq model: '{model}'.")
                return chat_completion.choices[0].message.content
            except Exception as e:
                logger.warning(f"Groq model '{model}' failed: {e}. Trying next model...")
                continue # Переходим к следующей модели в списке

        # Если цикл завершился, а ответа нет
        logger.error("All Groq models in the list failed.")
        return "Извините, сервис Groq временно недоступен. Попробовали все резервные варианты."

    # --- ЛОГИКА ДЛЯ GEMINI ---
    elif service_name == "gemini":
        logger.info(f"Attempting to get response from Gemini models: {config.GEMINI_MODELS}")
        for model in config.GEMINI_MODELS:
            logger.debug(f"Trying Gemini model: '{model}'...")
            try:
                # Создаем объект модели прямо в цикле
                gemini_model = genai.GenerativeModel(model)
                response = await gemini_model.generate_content_async(full_prompt)
                logger.info(f"SUCCESS! Got response from Gemini model: '{model}'.")
                return response.text
            except Exception as e:
                logger.warning(f"Gemini model '{model}' failed: {e}. Trying next model...")
                continue

        logger.error("All Gemini models in the list failed.")
        return "Извините, сервис Gemini временно недоступен. Попробовали все резервные варианты."

    else:
        logger.warning(f"Unknown or disabled AI service called: '{service_name}'")
        return "ИИ выключен или не выбран."
