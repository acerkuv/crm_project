import os
import openai
from apps.clients.models import Client

class AIGreetingService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
    
    def generate_birthday_greeting(self, client: Client) -> str:
        try:
            return f"С днём рождения, {client.first_name}! Желаю счастья и успехов!"
        except:
            return "С днём рождения!"
