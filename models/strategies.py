#region Descripción:
# Componente esencial en el sistema de trading automatizado basado en MetaTrader 5 (MT5). 
# Su función principal es contener y definir las estrategias específicas de trading que 
# desean implementar y ejecutar en la plataforma MT5.
#endregion

#region Importaciones
# Importaciones necesarias para definir tipos de datos
from typing import List, Dict, Any, Tuple
# importaciones para realizar operaciones numéricas eficientes
import numpy as np
import pandas as pd

# Para trabajo en paralelo
import multiprocessing

# Importacion de los clientes de las apis para hacer solicitudes
from .mt5.enums import TimeFrame, OrderType
from .mt5.models import TradePosition, SymbolInfo

# Importacion de los clientes de las apis para hacer solicitudes
from .mt5.enums import TimeFrame, OrderType
from .mt5.client import MT5Api
from .telegram.client import TelegramApi

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz, time

# Importaciones de indicatores técnicos
import pandas_ta as ta
from .technical_indicators import HeikenAshi, vRenko

#endregion

class PositionState:
    waiting = 0
    rupture = 1
    false_rupture = 2

class SymbolState:
    in_range = 0
    long = 1
    short = -1

class TrendState:
    unassigned = 0
    bullish = 1
    bearish = -1


class HardHedgeTrading:
    def __init__(self, symbol: str, volume_size: int = 1) -> None:
        # Indica si el programa debe seguir activo
        self.is_on = None
        
        # Lista de symbolos para administar dentro de la estrategia
        self.symbol = symbol
        
        # El numero que identificara las ordenes de esta estrategia
        self.magic = 33
        
        # El tamaño del lote
        if volume_size is None:
            self.volume_size = None
        else:
            self.volume_size = float(volume_size)
                
        # Horario de apertura y cierre del mercado
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':19, 'minute':55}
    
    def _is_in_market_hours(self):
        """
        Comprueba si el momento actual se encuentra en horario de mercado.

        Returns:
            bool: True si se encuentra en horario de mercado, False si no lo está.
        """
        # Obtener la hora y minutos actuales en UTC
        current_time = datetime.now(pytz.utc).time()

        # Crear objetos time para el horario de apertura y cierre del mercado
        market_open = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'], second=0)
        market_close = current_time.replace(hour=self._market_closed_time['hour'], minute=self._market_closed_time['minute'], second=0)

        # Verificar si la hora actual está dentro del horario de mercado
        if market_open <= current_time <= market_close:
            return True
        else:
            print("El mercado está cerrado.")
            return False
    
    def _sleep_to_next_minute(self):
        """
        Espera hasta que finalice el minuto actual antes de tomar una decisión.

        Este método calcula cuántos segundos faltan para que finalice el minuto actual,
        y luego espera ese tiempo antes de continuar.

        Args:
            None

        Returns:
            None
        """
        # Obtener la hora actual
        current_time = datetime.now()

        # Calcular el momento en que comienza el próximo minuto (segundo 1, microsegundo 0)
        next_minute = current_time.replace(second=1, microsecond=0) + timedelta(minutes=1)

        # Calcular la cantidad de segundos que faltan hasta el próximo minuto
        seconds = (next_minute - current_time).total_seconds()

        # Dormir durante la cantidad de segundos necesarios
        time.sleep(seconds)
    
    def save_position_in_txt(self, ticket: int):
        """
        Guarda la posición especificada en un archivo de texto.
        No se aplicará hedge a las posiciones guardadas en este archivo.

        Args:
            ticket (int): El número de ticket de la posición a guardar.
        """
        with open("hedge_positions.txt", "a") as file:
            file.write(f"Ticket: {ticket} ")

    def find_position_in_txt(self, ticket: int) -> bool:
        """
        Busca si un ticket de posición está presente en el archivo de texto.

        Args:
            ticket (int): El número de ticket de la posición a buscar.

        Returns:
            bool: True si se encuentra el ticket en el archivo, False en caso contrario.
        """
        try:
            with open("hedge_positions.txt", "r") as file:
                content = file.read()  # Cambia readlines() a read()
                if f"Ticket: {ticket}" in content:  # Verifica si la cadena está en el contenido
                    return True
                return False
        except FileNotFoundError:
            return False

    def clean_positions_in_txt(self):
        """
        Limpia el archivo de texto que almacena las posiciones guardadas.            
        """
        with open("hedge_positions.txt", "w") as file:
            file.truncate(0)
        
    def manage_positions(self):
        TelegramApi.send_text("tr3nd: Iniciando administrador de posiciones")
        # Comienza el administrador de posiciones
        while self.is_on.value:
            if self.
                
    
    #region HardHedge strategy 
    def _preparing_symbols_data(self):
        """
        Prepara la data que se usara en la estrategia de HardHedge.
        """
        print("HardHedge: Preparando la data...")
        # Variable auxiliar
        symbol_data = {}
        
        # Establece el periodo de tiempo para calcular el rango
        current_time = datetime.now(pytz.utc)
        start_time = current_time.replace(hour=self._market_opening_time['hour'], minute=0, second=0, microsecond=0)
        end_time = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'], second=0, microsecond=0)
        
                
        while True:
            info = MT5Api.get_symbol_info(self.symbol)
            rates_in_range = MT5Api.get_rates_range(self.symbol, TimeFrame.MINUTE_1, start_time, end_time)
            
            # Para testear fuera de horarios de mercado 
            if rates_in_range is None or rates_in_range.size == 0:
                number_bars = 30
                rates_in_range = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, number_bars)

            if info is not None and rates_in_range is not None:
                break
        
        
        digits = info.digits
        high = np.max(rates_in_range['high'])
        low = np.min(rates_in_range['low'])
        range_value = abs(high - low)
        recovery_range = range_value
                
        if self.volume_size is None:
            self.volume_size = info.volume_min
  
        symbol_data= {
            'symbol': self.symbol,
            'digits': digits,
            'recovery_range': recovery_range,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
        }
        
        print(symbol_data)
            
            
        # Actualiza la variable compartida
        self.symbol_data.update(symbol_data)
        
    def get_atr(self, symbol: str,  number_bars:int=14)->float:
        """
        Calcula el Average True Range (ATR) de un symbolo especifico en mt5.

        Args:
            high_prices (list or np.array): Lista o arreglo NumPy de precios altos.
            low_prices (list or np.array): Lista o arreglo NumPy de precios bajos.
            close_prices (list or np.array): Lista o arreglo NumPy de precios de cierre.
            n (int): Número de períodos para el cálculo del ATR. El valor predeterminado es 14.

        Returns:
            float: Valor del Average True Range (ATR).
        """
        # Obtiene las barras para el simbolo
        rates_in_range = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1, number_bars)
        # Crear un DataFrame con los precios de alta, baja y cierre
        data = {
            'High': rates_in_range['high'],
            'Low': rates_in_range['low'],
            'Close': rates_in_range['close']
        }

        df = pd.DataFrame(data)

        # Calcular el True Range (TR) utilizando Pandas y NumPy
        df['High-Low'] = df['High'] - df['Low']
        df['High-Close-Prev'] = abs(df['High'] - df['Close'].shift(1))
        df['Low-Close-Prev'] = abs(df['Low'] - df['Close'].shift(1))
        df['True-Range'] = df[['High-Low', 'High-Close-Prev', 'Low-Close-Prev']].max(axis=1)

        # Calcular el ATR como un promedio exponencial ponderado (SMA)
        atr = df['True-Range'].rolling(window=number_bars).mean().iloc[-1]

        return atr
    
    def _hedge_buyer(self):
        """
        Prepara órdenes para ser enviadas a MetaTrader 5 en función de los datos establecidos.
        """
        # Verifica si el margen disponible es menor al 10% de el balance de la cuenta
        account_info = MT5Api.get_account_info()
        minimun_margin =  0.20 *  account_info.balance
        positions = MT5Api.get_positions(magic=self.magic)
        if account_info.margin_free > minimun_margin and (len(positions)*2) < account_info.limit_orders:
            # Se crea una copia de la lista de symbolos para evitar al modificarse
            copy_symbols = list(self.symbols)
            
            for symbol in copy_symbols:
                data = self.symbol_data[symbol]
                
                # Diccionario que contendra la informacion de la orden
                order = {
                    "symbol": symbol,
                    "order_type": None, 
                    "volume": self.volume_size,
                    "price": None,
                    "stop_loss": None,
                    "take_profit": None,
                    "ticket": None,
                    "comment": None,
                    "magic": self.magic
                }
                
                # Obtiene la informacion actual para el symbolo                
                info_symbol =  MT5Api.get_symbol_info(symbol)
                
                # Obtiene la ultima barra
                last_bar = MT5Api.get_last_bar(symbol)
                
                # Variables para el calculo de tp y sl
                radius = data['recovery_range']*3
                spread_point = info_symbol.spread * info_symbol.point
                
                # Se establece el tp y el sl
                if last_bar['open'] < last_bar['close']:
                    order['price'] = info_symbol.ask    # recovery high
                    tp = order['price'] + radius
                    sl = order['price'] - radius - spread_point
                    order['order_type'] = OrderType.MARKET_BUY
                    
                else:
                    order['price'] = info_symbol.bid    # recovery low
                    tp = order['price'] - radius
                    sl = order['price'] + radius + spread_point
                    order['order_type'] = OrderType.MARKET_SELL
                    
                order['take_profit'] = round(tp, data['digits'])
                order['stop_loss'] = round(sl, data['digits'])
                
                # El comment representara al numero de veces que se ha apliacado el HardHedge
                order['comment'] = str(0)
                
                # Envía la orden a MetaTrader 5
                MT5Api.send_order(**order)
       
    def _hedge_strategy(self):
        """
        Ejecuta la estrategia a las posiciones abiertas.
        """
        # Se obtienen las posiciones abiertas
        positions = MT5Api.get_positions(magic=self.magic)
        for position in positions:
            # Si la posicion tiene un take profit igual a cero, significa que ya tiene ganancias y se ignora
            if self.find_position_in_txt(position.ticket):
                continue
                
            data = self.symbol_data[position.symbol]
            
            # Obtiene el precio actual para el symbolo                
            info_symbol =  MT5Api.get_symbol_info(position.symbol)
            
            # Variables para el calculo de tp y sl
            recovery_radius = data['recovery_range']*4
                       
            
            if position.type == OrderType.MARKET_BUY:  # Long
                recovery_low = position.tp - recovery_radius
                if info_symbol.bid < recovery_low:  
                    self._hedge_order(position, data, recovery_low, info_symbol)
            else:  # Short
                recovery_high = position.tp + recovery_radius
                if info_symbol.ask > recovery_high:
                    self._hedge_order(position, data, recovery_high, info_symbol)
        
        self._sleep_to_next_minute()
        
    def _hedge_order(self, position:TradePosition, data:Dict[str, Any], recovery_price:float, info_symbol: SymbolInfo) -> None:
        """
        Prepara órdenes para ser enviadas a MetaTrader 5. Cada orden se prepara en función de los datos recibidos.

        Args:
            position (TradePosition): La posición de la orden original.
            data (Dict[str, Any]): Datos relevantes para la preparación de la orden.
            recovery_price (float): El precio de recuperación utilizado para establecer take-profit y stop-loss.
            info_symbol (SymbolInfo): Información acerca del simbolo en mt5.
        """         
        # Se establece la orden y se envia
        next_hedge = int(position.comment)+1
                        
        if next_hedge < self.max_hedge:
            new_volume = self.volume_size * (3 ** (next_hedge))
            comment = str(next_hedge)
        else:
            new_volume = data['counter_hedge'] + self.volume_size
            comment = str(0)
                
        if new_volume > data['volume_max']:
            new_volume = float(data['volume_max'])
            
        # Variables para el calculo de tp y sl
        radius = data['recovery_range']*3
        spread_point = info_symbol.spread * info_symbol.point
        
        if position.type == OrderType.MARKET_BUY:
            new_order_type = OrderType.MARKET_SELL
            tp = recovery_price - radius 
            sl = recovery_price + radius + spread_point
        else:
            new_order_type = OrderType.MARKET_BUY
            tp = recovery_price + radius
            sl = recovery_price - radius - spread_point
        
        order = {
            "symbol": position.symbol, 
            "order_type": new_order_type, 
            "volume": new_volume,
            "price": None,
            "stop_loss": round(sl, data['digits']),
            "take_profit": round(tp, data['digits']),
            "ticket": None,
            "comment": comment,
            "magic": self.magic
        }
        # Envía la orden a MetaTrader 5
        MT5Api.send_order(**order)
        # Guarda la posicion en un txt para evitar volver hacerle hedge
        self.save_position_in_txt(position.ticket)

    
    #endregion
    
    #region start
    def start(self):
        """
        Inicia la estrategia de HardHedge trading para los símbolos especificados.
        """

        print("HardHedge: Iniciando estrategia...")
        
        while True:
            positions = MT5Api.get_positions(magic=self.magic)
            if positions is not None:
                break
        
        # Se crea las variables compartidas
        manager = multiprocessing.Manager()
        self.symbol_data = manager.dict()
        self.is_on = manager.Value("b", True)
        self.trend_state = manager.Value("i", TrendState.unassigned)
        self.symbol_state = manager.Value("i", SymbolState.in_range)
                
        self._preparing_symbols_data()
        
        # crea los procesos y los inicia
        self._hedge_strategy()
                    
        # Fin del ciclo
        print("HardHedge: Finalizando estrategia...")
          
    #endregion