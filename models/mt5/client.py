import MetaTrader5 as mt5   # Para conectarse y realizar solicitudes a una terminal de metatrader5
import numpy as np          # Para realizar operaciones numéricas eficientes

# Importaciones para el manejo de datos
from .telegram.client import TelegramApi
from .enums import FieldType, TimeFrame, CopyTicks, OrderType, TradeActions, TickFlag
from .models import Tick, MqlTradeResult, SymbolInfo, TradeDeal, TradeOrder, TradePosition, AccountInfo
from numpy import ndarray

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import time
import pytz

# Importaciones necesarias para definir tipos de datos
from typing import List, Tuple, Any

# Importación de módulos externos
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde un archivo .env
load_dotenv()
    
class MT5Api:
    """
    Clase para interactuar con MetaTrader 5 a través de su API.

    Esta clase proporciona métodos para conectarse a MetaTrader 5, obtener información de la cuenta, colocar órdenes y más.
    """    
    
    #region Lifecycle
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
    #endregion

    #region Getters
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
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_from)
        rates = mt5.copy_rates_from(
            symbol,       # nombre del símbolo
            timeframe,    # marco temporal
            date_from_mt5,    # fecha de apertura de la barra inicial
            count         # número de barras
            )
        if rates is None:
            return None
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
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
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        rates = mt5.copy_rates_from_pos(
            symbol,       # nombre del símbolo
            timeframe,    # marco temporal
            start_pos,    # número de la barra inicial
            count         # número de barras
            )
        if rates is None:
            return None
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
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
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_from)
        date_to_gmt_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_to)
        rates = mt5.copy_rates_range(
            symbol,       # nombre del símbolo
            timeframe,    # marco temporal
            date_from_mt5,    # fecha a partir de la cual se solicitan las barras
            date_to_gmt_mt5       # fecha hasta la cual se solicitan las barras
            )
        if rates is None:
            return None
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
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
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_from)
        ticks = mt5.copy_ticks_from(
            symbol,       # nombre del símbolo
            date_from_mt5,    # fecha a partir de la cual se solicitan los ticks (hora en UTC)
            count,        # número de ticks
            flag          # combinación de banderas que determina el tipo de ticks solicitados
        )
        if ticks is None:
            return None
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
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
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_from)
        date_to_gmt_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_to)
        flags_value = sum(flags.value)
        ticks = mt5.copy_ticks_range(
            symbol,       # nombre del símbolo
            date_from_mt5,    # fecha a partir de la cual se solicitan los ticks (hora en UTC)
            date_to_gmt_mt5,      # fecha hasta la cual se solicitan los ticks (hora en UTC)
            flags_value   # combinación de banderas que determina el tipo de ticks solicitados
        )
        if ticks is None:
            return None
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        return ticks

    def get_positions(symbol: str = None, ticket: int = None, magic:int = None)-> Tuple[TradePosition, ...]:
        """
        Obtiene las posiciones abiertas para un símbolo específico en MetaTrader 5.
        
        Si se llama el metodo sin argumentos, devuelve las posiciones para todos los símbolos.

        Args:
            symbol (str, optional): El símbolo del instrumento financiero para el cual se desean obtener las posiciones.
            ticket (int, optional): El número de ticket de la posición que se desea obtener de manera específica.
            magic(int, optional): Identificador del experto. Permite organizar el procesamiento analítico de órdenes comerciales. Cada experto puede colocar su propio identificador único al enviar una solicitud comercial

        Returns:
            Tuple[TradePosition, ...] or None: Una tupla de objetos TradePosition que representan las posiciones abiertas.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        if magic is not None:
            positions = mt5.positions_get(magic=magic)
        if ticket is not None:
            positions = mt5.positions_get(ticket=ticket)
        elif symbol is not None:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        return positions
    
    def get_history_orders(date_from: datetime, date_to: datetime, symbol: str = None) -> Tuple[TradeOrder, ...]:
        """
        Obtiene un historial de órdenes de trading en un rango de fechas y, opcionalmente, para un símbolo específico.
        Las fechas se convierten a la zona horaria del broker.

        Args:
            date_from (datetime): Fecha a partir de la cual se solicitan las órdenes en UTC.
            date_to (datetime): Fecha hasta la cual se solicitan las órdenes en UTC.
            symbol (str, optional): Símbolo o grupo de órdenes a filtrar (opcional).

        Returns:
            Tuple[TradeOrder, ...]: Tupla de objetos TradeOrder que representan las órdenes obtenidas.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_from)
        date_to_gmt_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_to)
        
        if symbol is None:
            history_orders = mt5.history_orders_get(
                date_from_mt5,  # Fecha a partir de la cual se solicitan las órdenes en GMT+3
                date_to_gmt_mt5,    # Fecha hasta la cual se solicitan las órdenes en GMT+3
            )
        else:
            history_orders = mt5.history_orders_get(
                date_from_mt5,  # Fecha a partir de la cual se solicitan las órdenes en GMT+3
                date_to_gmt_mt5,    # Fecha hasta la cual se solicitan las órdenes en GMT+3
                group=symbol           # Filtro de selección de órdenes según los símbolos
            )
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        return history_orders

    def get_history_deals(date_from: datetime, date_to: datetime, symbol: str = None)-> Tuple[TradeDeal, ...]:
        """
        Obtiene un historial de transacciones de trading en un rango de fechas y, opcionalmente, para un símbolo específico.
        Las fechas se convierten a la zona horaria del broker.

        Args:
            date_from (datetime): Fecha a partir de la cual se solicitan las transacciones en UTC.
            date_to (datetime): Fecha hasta la cual se solicitan las transacciones en UTC.
            symbol (str, optional): Símbolo o grupo de órdenes a filtrar (opcional).

        Returns:
            Tuple[TradeDeal, ...]: Tupla de objetos TradeDeal que representan las transacciones obtenidas.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Convierte las fechas a MT5
        date_from_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_from)
        date_to_gmt_mt5 = MT5Api.convert_utc_to_mt5_timezone(date_to)
        
        if symbol is None:
            history_deals = mt5.history_deals_get(
                date_from_mt5,  # Fecha a partir de la cual se solicitan las transacciones en GMT+3
                date_to_gmt_mt5,    # Fecha hasta la cual se solicitan las transacciones en GMT+3
            )
        else:
            history_deals = mt5.history_deals_get(
                date_from_mt5,  # Fecha a partir de la cual se solicitan las transacciones en GMT+3
                date_to_gmt_mt5,    # Fecha hasta la cual se solicitan las transacciones en GMT+3
                group=symbol           # Filtro de selección de órdenes según los símbolos
            )
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        return history_deals
    
    def get_symbol_info(symbol: str) -> SymbolInfo:
        """
        Obtiene información detallada del símbolo especificado en MetaTrader 5.

        Args:
            symbol (str): El nombre del símbolo que deseas consultar.

        Returns:
            SymbolInfo: Un objeto SymbolInfo que contiene información detallada del símbolo.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Obtiene la información del símbolo
        symbol_info: SymbolInfo = mt5.symbol_info(symbol)
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        
        return symbol_info

    def get_symbol_info_tick(symbol: str)->Tick :
        """
        Obtiene información de la última cotización (tick) del símbolo especificado en MetaTrader 5.

        Args:
            symbol (str): El nombre del símbolo del que deseas obtener la última cotización.

        Returns:
            SymbolInfoTick: Un objeto SymbolInfoTick que contiene información del último tick del símbolo.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Obtiene la información del último tick del símbolo
        symbol_info_tick = mt5.symbol_info_tick(symbol)
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        
        return symbol_info_tick
    
    def get_last_price(symbol:str)->float:
        """
        Obtiene el precio de cierre más reciente para un símbolo en MetaTrader 5.

        Parameters:
            symbol (str): El nombre del símbolo del cual se desea obtener el precio de cierre.

        Returns:
            float: El precio de cierre más reciente del símbolo.
        """
        last_rate = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 0, 1)
        close = last_rate[-1]['close']
        return close

    def get_last_bar(symbol:str)->np.ndarray[FieldType.ticks_dtype]:
        """
        Obtiene la barra más reciente para un símbolo en MetaTrader 5.

        Parameters:
            symbol (str): El nombre del símbolo del cual se desea obtener el precio de cierre.

        Returns:
            float: El precio de cierre más reciente del símbolo.
        """
        last_rate = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 0, 1)
        return last_rate[-1]
    
    def get_account_info() -> AccountInfo:
        """
        Obtiene la información de la cuenta en MetaTrader 5.

        Returns:
            AccountInfo: Un objeto que contiene información de la cuenta en MetaTrader 5.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        # Obtener información de la cuenta
        account_info: AccountInfo = mt5.account_info()
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        return account_info
        
    #endregion
    
    #region Setters
    def send_order(symbol:str, order_type:OrderType, volume:float, price:float=None, stop_loss:float=None, take_profit:float=None, ticket:int=None, comment:str=None, magic: int = None) -> MqlTradeResult:
        """
        Envía una orden al servidor de MetaTrader 5.

        Args:
            symbol (str): Nombre del instrumento comercial del que se coloca la orden. No es necesario en las operaciones de modificación de órdenes y el cierre de posiciones.
            order_type (int): El tipo de orden (por ejemplo, ORDER_TYPE_BUY o ORDER_TYPE_SELL).
            volume (float): Volumen de la transacción solicitado en lotes. El valor real del volumen al darse la apertura dependerá del tipo de orden según la ejecución.
            price (float, optional): El precio al que deseas realizar la orden. Si no se especifica, se utilizará el precio de mercado actual.
            stop_loss (float, optional): El nivel de Stop Loss para la orden.
            take_profit (float, optional): El nivel de Take Profit para la orden.
            ticket (int, optional): Ticket de la orden. Es necesario para modificar las órdenes pendientes.
            comment (str, optional): Comentario opcional para la orden.
            magic(int, optional): Identificador del experto. Permite organizar el procesamiento analítico de órdenes comerciales. Cada experto puede colocar su propio identificador único al enviar una solicitud comercial

        Returns:
            MqlTradeResult: Contiene la informacion sobre el resultado de la orden, None si la orden no es valida.

        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        request = {}
        if price is None:
            # Si no se especifica el precio, obtener el precio actual del mercado
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                TelegramApi.send_text(f"No se pudo obtener el precio actual para {symbol}.")
            if order_type == OrderType.MARKET_BUY:
                request['price'] = tick.ask  # Precio ask (venta) como precio de compra
            elif order_type == OrderType.MARKET_SELL:
                request['price'] = tick.bid  # Precio bid (oferta) como precio de venta

        request['action'] = TradeActions.TRADE_ACTION_DEAL
        request['symbol'] = symbol
        request['volume'] = volume
        request["type"] = order_type
        
        if stop_loss is not None:
            request["sl"] = float(stop_loss)

        if take_profit is not None:
            request["tp"] = float(take_profit)
        
        if comment is not None:
            request["comment"] = comment
            
        if magic is not None:
            request["magic"] = magic

        order_request: MqlTradeResult = mt5.order_send(request)

        #Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
        
        if order_request.retcode != mt5.TRADE_RETCODE_DONE:
            TelegramApi.send_text(f"No se pudo realizar la orden. Código de error: {order_request.retcode}")
            TelegramApi.send_text(f"Comentario: {order_request.comment}")
            return None
        else:
            TelegramApi.send_text(f"Orden completada: {request}")

        
        return order_request
    
    def send_sell_partial_order(symbol: str, volume_to_sell: float, ticket:int, comment:str = None)->bool:
        """
        Vende una parte de una posición abierta en MT5.

        Args:
            symbol (str): El símbolo del instrumento.
            volume_to_sell (float): El volumen de la posición a vender.
            ticket (int): El número de ticket de la posición a vender.
            comment (str, opcional): Un comentario opcional para la orden de venta.
                Si no se establece, se conservará el comentario anterior de la posición.
        
        Returns: 
            bool: Retorna True si la orden se ejecuto con exito, en caso contrario False
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()

        positions = mt5.positions_get(ticket=ticket)
        
        request_type = 0
        
        
        if positions is not None:
            position = positions[-1]
            if position.type == 0:
                request_type = OrderType.MARKET_SELL
            else:
                request_type = OrderType.MARKET_BUY
            
            if comment is None:
                comment = position.comment
                
            request = {
                "action": TradeActions.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume_to_sell,
                "type": request_type,
                "price": mt5.symbol_info_tick(symbol).ask,
                "position": ticket,
                "comment": comment
            }

            order_request = mt5.order_send(request)
            
            #Cierra la conexión con MetaTrader 5
            MT5Api.shutdown()

            if order_request.retcode != mt5.TRADE_RETCODE_DONE:
                TelegramApi.send_text(f"No se pudo realizar la venta parcial. Código de error: {order_request.retcode}")
                TelegramApi.send_text(f"Comentario: {order_request.comment}")
                return False
            else:
                TelegramApi.send_text("Venta parcial completada.")
                return True
                
        else:
            #Cierra la conexión con MetaTrader 5
            MT5Api.shutdown()
            TelegramApi.send_text("Ticket no encontrado.")
            return False
    
    def send_change_stop_loss_and_take_profit(symbol:str, new_stop_loss: float,  new_take_profit: float, ticket:int)->bool:
        """
        Cambia el nivel de stop loss  y el take profit de una posición abierta en MT5.

        Args:
            symbol (str): El símbolo del instrumento.
            new_stop_loss (float): El nuevo nivel de stop loss.
            new_take_profit (float): El nuevo nivel de take profit.
            ticket (int): El número de ticket de la posición a modificar.
        
        Return:
            Bool: True Si la orden se ejecuto con exito, false si no
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()

        modify_request = {
            "action": TradeActions.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": new_stop_loss,
            "tp": new_take_profit,
        }

        modify_result = mt5.order_send(modify_request)
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()

        if modify_result.retcode == mt5.TRADE_RETCODE_DONE:
            TelegramApi.send_text(f"Modificación del sl y tp ejecutada. {symbol}: sl {new_stop_loss} tp {new_take_profit}")
            return True
        else:
            TelegramApi.send_text(f"Error al ejecutar la modificación del sl y tp: {modify_result.retcode}")
            TelegramApi.send_text(f"Comentario: {modify_result.comment}")
            return False  
    
    def send_change_stop_loss(symbol:str, new_stop_loss: float, ticket:int)->bool:
        """
        Cambia el nivel de stop loss de una posición abierta en MT5.

        Args:
            symbol (str): El símbolo del instrumento.
            new_stop_loss (float): El nuevo nivel de stop loss.
            ticket (int): El número de ticket de la posición a modificar.
        
        Return:
            Bool: True Si la orden se ejecuto con exito, false si no
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()

        modify_request = {
            "action": TradeActions.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": float(new_stop_loss),
        }

        modify_result = mt5.order_send(modify_request)
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()

        if modify_result.retcode == mt5.TRADE_RETCODE_DONE:
            TelegramApi.send_text(f"Modificación del stop loss ejecutada. {symbol}: {new_stop_loss}")
            return True
        else:
            TelegramApi.send_text(f"Error al ejecutar la modificación del stop loss: {modify_result.retcode}")
            TelegramApi.send_text(f"Comentario: {modify_result.comment}")
            return False  
        
    def send_change_take_profit(symbol:str, new_take_profit: float, ticket:int):
        """
        Cambia el nivel de take profit de una posición abierta en MT5.

        Args:
            symbol (str): El símbolo del instrumento.
            new_take_profit (float): El nuevo nivel de take profit.
            ticket (int): El número de ticket de la posición a modificar.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        modify_request = {
            "action": TradeActions.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "tp": new_take_profit,
        }

        modify_result = mt5.order_send(modify_request)

        if modify_result.retcode == mt5.TRADE_RETCODE_DONE:
            TelegramApi.send_text(f"Modificación del take profit ejecutada. {symbol}: {new_take_profit}")
        else:
            TelegramApi.send_text(f"Error al ejecutar la modificación del take profit: {modify_result.retcode}")
            TelegramApi.send_text(f"Comentario: {modify_result.comment}")
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
    
    def send_close_all_position():
        """
        Cierra todas las posiciones abiertas en la plataforma MetaTrader 5.
        
        Esta función se conecta a MetaTrader 5, obtiene todas las posiciones abiertas,
        y las cierra una por una. Luego muestra un mensaje de éxito o error para cada posición cerrada.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        # Obtiene todas las posiciones abiertas
        positions = mt5.positions_get()
        
        if positions is not None:
            # Itera sobre todas las posiciones abiertas y las cierra
            for position in positions:  
                close_result = mt5.Close(position.symbol,ticket=position.ticket)
                
                if close_result:
                    TelegramApi.send_text(f"Posición en {position.symbol} cerrada con éxito")
                else:
                    TelegramApi.send_text(f"Error al cerrar la posición en {position.symbol}")
        else:
            TelegramApi.send_text("No hay posiciones abiertas para cerrar")
            
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
    
    def send_remove_take_profit_and_stop_loss(ticket: int):
        """
        Elimina el stop loss y el take profit de una posición abierta en MetaTrader 5.

        Parameters:
        ticket (int): El número de ticket de la posición que se desea modificar.
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        # Verificamos si la conexión con MetaTrader 5 está establecida
        if not mt5.initialize():
            TelegramApi.send_text("Error: No se pudo establecer la conexión con MetaTrader 5.")
            return False
        
        # Configuramos los parámetros para eliminar el stop loss y el take profit
        request = {
            "position": ticket,
            "action": TradeActions.TRADE_ACTION_SLTP,
            "order": OrderType.CLOSE_BY
        }

        # Enviamos la solicitud para eliminar el stop loss y el take profit
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            TelegramApi.send_text(f"Take profit y stop loss eliminados.")
        else:
            TelegramApi.send_text(f"Error al ejecutar la eliminación de Take profit y stop loss: {result.retcode}")
            TelegramApi.send_text(f"Comentario: {result.comment}")
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
    
    def send_close_position(symbol:str, ticket:int)-> bool:
        """
        Cierra una posicion abiertas en la plataforma MetaTrader 5.
        
        Args:
            symbol (str): El símbolo del instrumento.
            ticket (int): El número de ticket de la posición a vender.
        Returns:
            bool: Verdadero si se ejecuto con exito, falso en caso contrario
        """
        # Inicializa la conexión con la plataforma MetaTrader 5
        MT5Api.initialize()
        
        close_result = mt5.Close(symbol=symbol, ticket=ticket)
        
        # Cierra la conexión con MetaTrader 5
        MT5Api.shutdown()
                   
        if close_result:
            TelegramApi.send_text(f"Posición {ticket} cerrada con éxito")
            return True
        else:
            TelegramApi.send_text(f"Error al cerrar la posición ticket")
            return False
            
    
    
    #endregion
    
    #region Utilities
    def convert_utc_to_mt5_timezone(date: datetime) -> datetime:
        """
        Suma 3 horas a la fecha y hora proporcionada.

        Args:
            date (datetime): Fecha y hora en formato UTC.

        Returns:
            datetime: La fecha y hora resultante después de sumar 3 horas.
        """
        # Suma 3 horas a la fecha y hora original
        dt_mt5 = date + timedelta(hours=3)
        
        return dt_mt5
    #endregion

