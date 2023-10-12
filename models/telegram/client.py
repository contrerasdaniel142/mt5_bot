# Importaciones necesarias para manejar telegram
import telegram
from telegram.ext import Updater
# Importación de módulos externos
import os
from dotenv import load_dotenv
# Carga las variables de entorno desde un archivo .env
load_dotenv()

class TelegramApi:
    def __init__(self) -> None:
        self._bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))
        
        


      
# Initialize the bot
bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))
bot.initialize()

# Now you can access the properties or methods of the bot
print(bot.can_join_groups)