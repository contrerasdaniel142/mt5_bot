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
    def __init__(self) -> None:
        self._bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))
        self._group_id = int(os.getenv("GROUP_ID"))

    def send_text(self, text):
        print(text)
        loop = asyncio.get_event_loop()
        loop.create_task(self._send_message_to_telegram(text))
        
    async def _send_message_to_telegram(self, text):
        await asyncio.run(self._bot.send_message(chat_id=self._group_id, text=text))

