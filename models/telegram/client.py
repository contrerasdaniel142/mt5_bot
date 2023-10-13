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
        loop = asyncio.get_event_loop()
        loop.create_task(TelegramApi._async_send_text(text))
        
    async def _async_send_text(text):
        bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))
        await bot.send_message(chat_id=int(os.getenv("GROUP_ID")), text=text)

