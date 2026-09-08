import logging

logger = logging.getLogger(__name__)

def get_fatsecret_auth_url() -> str:
    #Генерує лінк для логіну у FatSecret (OAuth 1.0 Request Token).
    # Тут буде реальний виклик authlib для генерації лінку
    return "https://www.fatsecret.com/oauth/authorize?oauth_token=test_token"

def process_fatsecret_callback(oauth_verifier: str) -> dict:
    #Обмінює verifier з колбеку на постійний Access Token.
    logger.info(f"FatSecret callback отримано з verifier: {oauth_verifier}")
    # Тут буде обмін токенів. Поки віддаємо фейкові для тесту.
    return {
        "access_token": "fs_access_123",
        "access_secret": "fs_secret_456"
    }