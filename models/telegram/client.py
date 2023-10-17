# Importaciones necesarias para manejar telegram
import telegram
from telegram import Update

import asyncio

# Importación de módulos externos
import os
from dotenv import load_dotenv
# Carga las variables de entorno desde un archivo .env
load_dotenv()

class TelegramApi:
    def send_text(text):
        print(text)
        # bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))
        # asyncio.run(bot.send_message(chat_id=int(os.getenv("GROUP_ID")), text=text))