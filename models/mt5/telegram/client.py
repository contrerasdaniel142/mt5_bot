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
        self._group_id = int(os.getenv("GROUP_ID"))

    def _get_bot(self):
        return telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))

    def send_text(self, text):
        print(text)
        bot = self._get_bot()
        asyncio.run(bot.send_message(chat_id=self._group_id, text=text))


