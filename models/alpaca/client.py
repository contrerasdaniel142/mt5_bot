# Importaciones necesarias de la biblioteca Alpaca y otras utilidades
from alpaca.trading.client import TradingClient
from alpaca.trading.models import Calendar, Clock
from alpaca.trading.requests import GetCalendarRequest
from alpaca.common.enums import BaseURL

# Importaciones necesarias para manejar fechas
from datetime import datetime, timedelta


# Importaciones necesarias para definir tipos de datos
from typing import List

# Importación de módulos externos
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde un archivo .env
load_dotenv()

class AlpacaApi:
    def __init__(self) -> None:
        """
        Inicializa la clase AlpacaApi.

        Carga las credenciales de Alpaca desde un archivo .env y crea una instancia del cliente de Alpaca.
        """
        self._trading_client = TradingClient(api_key=os.getenv("ALPACA_API_KEY_ID"), secret_key=os.getenv("ALPACA_API_SECRET_KEY"), url_override=BaseURL.TRADING_LIVE)
        
    def get_current_market_time(self) -> datetime:
        """
        Obtiene la hora actual del mercado.

        Returns:
            datetime: Hora actual del mercado en formato datetime.
        """
        return self._trading_client.get_clock().timestamp
    
    def get_next_days_of_market(self, par_days:int = 0) -> List[Calendar]:
        """
        Obtiene el calendario de los próximos días de mercado de Nueva York (NY).

        Args:
            par_days (int): Número de días a partir de hoy para los que se desea obtener el calendario.
                            Si es 0, se devuelve únicamente el calendario del día actual.

        Returns:
            List[Calendar]: Lista de objetos Calendar con el calendario de los próximos días de mercado de NY.
        """
        current_time = self.get_current_market_time()
        today = current_time.date()
        next_days = today + timedelta(days=par_days)
        calendar_request = GetCalendarRequest(start=today, end=next_days)
        calendar_list = self._trading_client.get_calendar(calendar_request)
        return calendar_list
        
