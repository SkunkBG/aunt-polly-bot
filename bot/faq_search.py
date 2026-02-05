import logging
from difflib import SequenceMatcher
from bot.config import FAQ_FILE, load_json

logger = logging.getLogger(__name__)


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Вычисляет схожесть двух текстов (от 0 до 1).
    """
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def search_faq(user_question: str, similarity_threshold: float = 0.4) -> dict:
    """
    Ищет ответ в FAQ на основе вопроса пользователя.
    
    Args:
        user_question: Вопрос пользователя
        similarity_threshold: Порог схожести (от 0 до 1). По умолчанию 0.4
        
    Returns:
        dict: Словарь с ключами 'found' (bool), 'answer' (str), 'question' (str), 'media' (dict)
              Если ничего не найдено, возвращает {'found': False}
    """
    faq_data = load_json(FAQ_FILE, default_data=[])
    
    if not faq_data:
        logger.debug("FAQ is empty, nothing to search")
        return {'found': False}
    
    best_match = None
    best_similarity = 0.0
    
    # Ищем наиболее похожий вопрос
    for item in faq_data:
        faq_question = item.get('question', '')
        similarity = calculate_similarity(user_question, faq_question)
        
        logger.debug(f"Comparing with FAQ: '{faq_question[:50]}...' - similarity: {similarity:.2f}")
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = item
    
    # Если нашли достаточно похожий вопрос
    if best_match and best_similarity >= similarity_threshold:
        logger.info(f"Found FAQ match with similarity {best_similarity:.2f}: '{best_match.get('question', '')[:50]}...'")
        return {
            'found': True,
            'answer': best_match.get('answer', ''),
            'question': best_match.get('question', ''),
            'media': best_match.get('media'),
            'similarity': best_similarity
        }
    
    logger.debug(f"No FAQ match found. Best similarity was {best_similarity:.2f}, threshold is {similarity_threshold}")
    return {'found': False}
