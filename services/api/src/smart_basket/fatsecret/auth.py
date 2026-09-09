import logging

logger = logging.getLogger(__name__)

def get_fatsecret_auth_url() -> str:
    # Генерує лінк для логіну у FatSecret.
    # Офіційний Auth URL згідно з документацією:
    return "https://oauth.fatsecret.com/connect/authorize"

def process_fatsecret_callback(oauth_verifier: str) -> dict:
    # Обмінює verifier з колбеку на постійний Access Token.
    # Офіційний Token URL: https://oauth.fatsecret.com/connect/token
    logger.info(f"FatSecret callback отримано з verifier: {oauth_verifier}")
    
    # Тут згодом буде реальний HTTP-запит до Token URL. Поки залишаємо структуру для тестів.
    return {
        "access_token": "fs_access_123",
        "access_secret": "fs_secret_456"
    }