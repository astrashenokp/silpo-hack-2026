import logging

logger = logging.getLogger(__name__)

class FatSecretClient:
    def __init__(self, consumer_key: str, consumer_secret: str):
        self.base_url = "https://platform.fatsecret.com/rest/server.api"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = None
        self.access_secret = None

    def set_user_tokens(self, token: str, secret: str):
        #Зберігає токени конкретного юзера після авторизації.
        self.access_token = token
        self.access_secret = secret

    async def search_food(self, query: str):
        #Шукає калорійність продукту.
        if not self.access_token:
            logger.warning("FatSecret: Немає токена доступу. Потрібна авторизація.")
            return {}
            
        logger.info(f"Шукаємо нутрієнти для: {query}")
        
        # Заглушка для тестування інтеграції, поки немає реальних ключів
        return {
            "food": {
                "food_name": query,
                "servings": {
                    "serving": {
                        "calories": "150",
                        "carbohydrate": "20.5",
                        "protein": "5.0",
                        "fat": "4.2"
                    }
                }
            }
        }