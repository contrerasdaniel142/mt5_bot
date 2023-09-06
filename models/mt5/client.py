import MetaTrader5 as mt5   # Para conectarse y realizar solicitudes a una terminal de metatrader5
from MetaTrader5 import TradePosition, TradeOrder, TradeDeal
import numpy as np          # Para realizar operaciones numéricas eficientes

# Importaciones para el manejo de datos
from .enums import FieldType, TimeFrame, CopyTicks, OrderType, TradeActions, TickFlag
from numpy import ndarray

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import time
import pytz

# Importaciones necesarias para definir tipos de datos
from typing import List, Any

# Importación de módulos externos
import os
from dotenv import load_dotenv

import pandas as pd

# Carga las variables de entorno desde un archivo .env
load_dotenv()
    
class MT5Api:
    """
    Clase para interactuar con MetaTrader 5 a través de su API.

    Esta clase proporciona métodos para conectarse a MetaTrader 5, obtener información de la cuenta, colocar órdenes y más.
    """    
    def initialize(sleep: int = 0) -> bool:
        """
        Inicializa la conexión con MetaTrader 5.

        Esta función inicializa la conexión con MetaTrader 5 utilizando la ruta predefinida en la variable de entorno MT5_PATH.

        Args:
            sleep (int, optional): El tiempo en segundos para esperar después de la inicialización antes de retornar. 
                Valor predeterminado es 0, lo que significa que no se espera ningún tiempo.

        Returns:
            bool: True si la inicialización fue exitosa, False en caso contrario.
        """
        request = mt5.initialize(path=os.getenv("MT5_PATH"))
        time.sleep(sleep)
        return request
        
    def shutdown(sleep: int = 0):
        """
        Detiene la conexión con MetaTrader 5.

        Esta función detiene la conexión con MetaTrader 5 y debe llamarse al finalizar la interacción con MetaTrader 5.

        Args:
            sleep (int, optional): El tiempo en segundos para esperar después de la detención antes de retornar. 
                Valor predeterminado es 0, lo que significa que no se espera ningún tiempo.

        Returns:
            None
        """
        request = mt5.shutdown()
        time.sleep(sleep)
        return request

    def get_rates_from_date(symbol:str, timeframe:TimeFrame, date_from:datetime, count: int) -> ndarray[FieldType.rates_dtype]:
        """
        Obtiene datos históricos de precios (velas) para un símbolo y marco temporal específicos a partir de una fecha dada.

        Esta función utiliza la función `copy_rates_from()` de MetaTrader 5 para obtener barras históricas de precios
        a partir de la fecha especificada hacia atrás en el tiempo.

        Args:
            symbol (str): El nombre del instrumento financiero (por ejemplo, "EURUSD").
            timeframe (TimeFrame): El marco temporal de las velas (ejemplo: TimeFrame.H1 para velas de 1 hora).
            date_from (datetime): La fecha de apertura de la primera vela que se desea obtener (hora en UTC).
            count (int): El número de velas históricas que se desean obtener.

        Returns:
            np.ndarray: Un arreglo NumPy que contiene los datos históricos de precios en forma de velas.
                Cada fila del arreglo representa una vela y contiene columnas con datos como
                'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', y 'real_volume'.

            None: En caso de error durante la obtención de datos, se retorna None.
                La información detallada sobre el error se puede obtener mediante last_error().

        Example:
            Para obtener las últimas 100 velas de EURUSD en un marco temporal de 1 hora a partir de una fecha específica:
            >>> symbol = "EURUSD"
            >>> timeframe = TimeFrame.H1
            >>> date_from = datetime(2023, 1, 1, tzinfo=timezone.utc)  # Fecha específica en hora UTC
            >>> count = 100
            >>> historical_data = api.get_rates_from_date(symbol, timeframe, date_from, count)
        """
        rates = mt5.copy_rates_from(
            symbol,       # nombre del símbolo
            timeframe,    # marco temporal
            date_from,    # fecha de apertura de la barra inicial
            count         # número de barras
            )
        if rates is None:
            return None
        return rates
    
    def get_rates_from_pos(symbol:str, timeframe:TimeFrame, start_pos:int, count: int) -> ndarray[FieldType.rates_dtype]:
        """
        Obtiene datos históricos de precios (velas) para un símbolo y marco temporal específicos a partir de una posición dada.

        Esta función utiliza la función `copy_rates_from_pos()` de MetaTrader 5 para obtener barras históricas de precios
        a partir de la posición especificada hacia atrás en el tiempo.

        Args:
            symbol (str): El nombre del instrumento financiero (por ejemplo, "EURUSD").
            timeframe (TimeFrame): El marco temporal de las velas (ejemplo: TimeFrame.H1 para velas de 1 hora).
            start_pos (int): El número de la barra inicial a partir del cual se desean obtener los datos.
                La numeración de las barras va del presente hacia el pasado, donde la barra cero es la actual.
            count (int): El número de barras históricas que se desean obtener.

        Returns:
            np.ndarray: Un arreglo NumPy que contiene los datos históricos de precios en forma de velas.
                Cada fila del arreglo representa una vela y contiene columnas con datos como
                'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', y 'real_volume'.

            None: En caso de error durante la obtención de datos, se retorna None.
                La información detallada sobre el error se puede obtener mediante last_error().

        Example:
            Para obtener las últimas 100 velas de EURUSD en un marco temporal de 1 hora a partir de una posición específica:
            >>> symbol = "EURUSD"
            >>> timeframe = TimeFrame.H1
            >>> start_pos = 500  # Posición inicial deseada
            >>> count = 100
            >>> historical_data = api.get_rates_from_pos(symbol, timeframe, start_pos, count)
        """
        rates = mt5.copy_rates_from_pos(
            symbol,       # nombre del símbolo
            timeframe,    # marco temporal
            start_pos,    # número de la barra inicial
            count         # número de barras
            )
        if rates is None:
            return None
        return rates
    
    def get_rates_range(symbol:str, timeframe:TimeFrame, date_from:datetime, date_to:datetime) -> ndarray[FieldType.rates_dtype]:
        """
        Obtiene datos históricos de precios (velas) para un símbolo y marco temporal específicos dentro de un rango de fechas.

        Esta función utiliza la función `copy_rates_range()` de MetaTrader 5 para obtener barras históricas de precios
        dentro del rango de fechas especificado.

        Args:
            symbol (str): El nombre del instrumento financiero (por ejemplo, "EURUSD").
            timeframe (TimeFrame): El marco temporal de las velas (ejemplo: TimeFrame.H1 para velas de 1 hora).
            date_from (datetime): La fecha a partir de la cual se solicitan las barras (hora en UTC).
            date_to (datetime): La fecha hasta la cual se solicitan las barras (hora en UTC).

        Returns:
            np.ndarray: Un arreglo NumPy que contiene los datos históricos de precios en forma de velas
                dentro del rango de fechas especificado.
                Cada fila del arreglo representa una vela y contiene columnas con datos como
                'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', y 'real_volume'.

            None: En caso de error durante la obtención de datos, se retorna None.
                La información detallada sobre el error se puede obtener mediante last_error().

        Example:
            Para obtener las velas de EURUSD en un marco temporal de 1 hora dentro del rango de fechas:
            >>> symbol = "EURUSD"
            >>> timeframe = TimeFrame.H1
            >>> date_from = datetime(2023, 1, 1, tzinfo=timezone.utc)  # Fecha inicial en hora UTC
            >>> date_to = datetime(2023, 2, 1, tzinfo=timezone.utc)  # Fecha final en hora UTC
            >>> historical_data = api.get_rates_range(symbol, timeframe, date_from, date_to)
        """
        rates = mt5.copy_rates_range(
            symbol,       # nombre del símbolo
            timeframe,    # marco temporal
            date_from,    # fecha a partir de la cual se solicitan las barras
            date_to       # fecha hasta la cual se solicitan las barras
            )
        if rates is None:
            return None
        return rates
    
    def get_ticks_from(symbol: str, date_from: datetime, count: int, flag: CopyTicks) -> np.ndarray[FieldType.ticks_dtype]:
        """
        Obtiene ticks del terminal MetaTrader 5 a partir de la fecha indicada.

        Args:
            symbol (str): El nombre del instrumento financiero (por ejemplo, "EURUSD").
            date_from (datetime): La fecha a partir de la cual se solicitan los ticks (hora en UTC).
            count (int): Número de ticks que se deben obtener.
            flags (CopyTicks): Bandera que determina el tipo de ticks solicitados (COPY_TICKS_ALL, COPY_TICKS_INFO, o COPY_TICKS_TRADE).

        Returns:
            np.ndarray: Un arreglo NumPy que contiene los ticks en forma de matriz con las columnas nombradas 'time', 'bid', 'ask', 'last' y 'flags'.
                El valor 'flags' es una combinación de banderas de la enumeración TickFlag.
            None: En caso de error durante la obtención de datos, se retorna None.
                La información detallada sobre el error se puede obtener mediante last_error().
        """
        ticks = mt5.copy_ticks_from(
            symbol,       # nombre del símbolo
            date_from,    # fecha a partir de la cual se solicitan los ticks (hora en UTC)
            count,        # número de ticks
            flag          # combinación de banderas que determina el tipo de ticks solicitados
        )
        if ticks is None:
            return None
        return ticks
    
    def get_ticks_range(symbol: str, date_from: datetime, date_to: datetime, flags: CopyTicks) -> np.ndarray[FieldType.ticks_dtype]:
        """
        Obtiene ticks del terminal MetaTrader 5 en un intervalo de fechas indicado.

        Args:
            symbol (str): El nombre del instrumento financiero (por ejemplo, "EURUSD").
            date_from (datetime): La fecha a partir de la cual se solicitan los ticks (hora en UTC).
            date_to (datetime): La fecha hasta la cual se solicitan los ticks (hora en UTC).
            flags (CopyTicks): Bandera que determina el tipo de ticks solicitados (COPY_TICKS_ALL, COPY_TICKS_INFO, o COPY_TICKS_TRADE).

        Returns:
            np.ndarray: Un arreglo NumPy que contiene los ticks en forma de matriz con las columnas nombradas 'time', 'bid', 'ask', 'last' y 'flags'.
                El valor 'flags' es una combinación de banderas de la enumeración TickFlag.
            None: En caso de error durante la obtención de datos, se retorna None.
                La información detallada sobre el error se puede obtener mediante last_error().
        """
        flags_value = sum(flags.value)
        ticks = mt5.copy_ticks_range(
            symbol,       # nombre del símbolo
            date_from,    # fecha a partir de la cual se solicitan los ticks (hora en UTC)
            date_to,      # fecha hasta la cual se solicitan los ticks (hora en UTC)
            flags_value   # combinación de banderas que determina el tipo de ticks solicitados
        )
        if ticks is None:
            return None
        return ticks

    def get_price(symbol:str, type:str = 'buy')->float:
        """
        Obtiene el precio actual de un símbolo en MetaTrader 5 (MT5).

        Args:
            symbol (str): El símbolo del instrumento financiero para el que se desea obtener el precio.
            type (str): El tipo de precio que se desea obtener ('buy' para precio de compra o 'sell' para precio de venta).

        Returns:
            float: El precio actual del símbolo en la plataforma MT5.

        Note:
            - Si el tipo es 'buy', se devuelve el precio ask (venta) como precio de compra.
            - Si el tipo es 'sell', se devuelve el precio bid (oferta) como precio de venta.

        Example:
            >>> get_price('EURUSD', 'buy')
            1.12345
        """
        tick = mt5.symbol_info_tick(symbol)
        price = None
        if tick is None:
            print(f"No se pudo obtener el precio actual para {symbol}.")
        if type == 'buy':
            price = tick.ask  # Precio ask (venta) como precio de compra
        elif type == 'sell':
            price = tick.bid  # Precio bid (oferta) como precio de venta
        return price
    
    def get_positions(symbol: str)->List[TradePosition]:
        """
        Obtiene las posiciones abierta para un símbolo específico en MetaTrader 5.

        Args:
            symbol (str): El símbolo del instrumento financiero.

        Returns:
            TradePosition or None: La última posición abierta si se encuentra una, None si no se encuentran posiciones abiertas.
        """
        positions = mt5.positions_get(symbol=symbol)
        return positions
    
    def convert_to_mt5_timezone(date: datetime) -> datetime:
        """
        Suma 3 horas a la fecha y hora proporcionada.

        Args:
            date (datetime): Fecha y hora en cualquier zona horaria.

        Returns:
            datetime: La fecha y hora resultante después de sumar 3 horas.
        """
        # Suma 3 horas a la fecha y hora original
        dt_mt5 = date + timedelta(hours=3)
        
        return dt_mt5

    def get_history_orders(date_from: datetime, date_to: datetime, symbol: str) -> List[TradeOrder]:
        """
        Obtiene un historial de órdenes de trading en un rango de fechas y para un símbolo específico.
        Las fechas se convierten a la zona horaria del broker.

        Arg:
            date_from (datetime): Fecha a partir de la cual se solicitan las órdenes en UTC.
            date_to (datetime): Fecha hasta la cual se solicitan las órdenes en UTC.
            symbol (str): Símbolo o grupo de órdenes a filtrar.

        Return:
            List[TradeOrder]: Lista de objetos TradeOrder que representan las órdenes obtenidas.
        """
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_to_mt5_timezone(date_from)
        date_to_gmt_mt5 = MT5Api.convert_to_mt5_timezone(date_to)
        history_orders = mt5.history_orders_get(
            date_from_mt5,  # Fecha a partir de la cual se solicitan las órdenes en GMT+3
            date_to_gmt_mt5,    # Fecha hasta la cual se solicitan las órdenes en GMT+3
            group=symbol           # Filtro de selección de órdenes según los símbolos
        )
        return history_orders

    def get_history_deals(date_from: datetime, date_to: datetime, symbol: str)-> List[TradeDeal]:
        """
        Obtiene un historial de transacciones de trading en un rango de fechas y para un símbolo específico.
        Las fechas se convierten a la zona horaria del broker.

        Arg:
            date_from (datetime): Fecha a partir de la cual se solicitan las transacciones en UTC.
            date_to (datetime): Fecha hasta la cual se solicitan las transacciones en UTC.
            symbol (str): Símbolo o grupo de órdenes a filtrar.

        Return:
            List[TradeDeal]: Lista de objetos TradeDeal que representan las transacciones obtenidas.
        """
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_to_mt5_timezone(date_from)
        date_to_gmt_mt5 = MT5Api.convert_to_mt5_timezone(date_to)
        
        history_deals = mt5.history_deals_get(
            date_from_mt5,  # Fecha a partir de la cual se solicitan las transacciones en GMT+3
            date_to_gmt_mt5,    # Fecha hasta la cual se solicitan las transacciones en GMT+3
            group=symbol           # Filtro de selección de órdenes según los símbolos
        )
        return history_deals

    def send_order(symbol:str, order_type:OrderType, volume:float, price:float=None, stop_loss:float=None, take_profit:float=None, ticket:int=None, comment:str=None) -> int:
        """
        Envía una orden al servidor de MetaTrader 5.

        Args:
            symbol (str): El nombre del símbolo en el que deseas realizar la orden.
            order_type (int): El tipo de orden (por ejemplo, ORDER_TYPE_BUY o ORDER_TYPE_SELL).
            volume (float): El volumen (cantidad) que deseas comprar o vender.
            price (float, optional): El precio al que deseas realizar la orden. Si no se especifica, se utilizará el precio de mercado actual.
            stop_loss (float, optional): El nivel de Stop Loss para la orden.
            take_profit (float, optional): El nivel de Take Profit para la orden.
            comment (str, optional): Comentario opcional para la orden.

        Returns:
            int: El número de ticket de la orden creada.

        Raises:
            ValueError: Si se proporciona un tipo de orden no válido.
        """
        request = {}
        if price is None:
            # Si no se especifica el precio, obtener el precio actual del mercado
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                print(f"No se pudo obtener el precio actual para {symbol}.")
            if order_type == OrderType.MARKET_BUY:
                request['price'] = tick.ask  # Precio ask (venta) como precio de compra
            elif order_type == OrderType.MARKET_SELL:
                request['price'] = tick.bid  # Precio bid (oferta) como precio de venta

        request['action'] = TradeActions.TRADE_ACTION_DEAL
        request['symbol'] = symbol
        request['volume'] = volume

        if comment is not None:
            request["comment"] = comment

        if stop_loss is not None:
            request["sl"] = stop_loss

        if take_profit is not None:
            request["tp"] = take_profit

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"No se pudo realizar la compra. Código de error: {result.retcode}")
            return None
        else:
            print("Orden completada.")

        return result.order

