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

# Para trabajo en paralelo
import multiprocessing
from multiprocessing import Queue
from multiprocessing.managers import DictProxy, ListProxy, ValueProxy

# Importacion de los clientes de las apis para hacer solicitudes
from .mt5.enums import TimeFrame, OrderType
from .mt5.models import TradePosition, SymbolInfo

# Importacion de los clientes de las apis para hacer solicitudes
from .mt5.client import MT5Api

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz, time

#endregion

class HardHedgeTrading:
    def __init__(self, symbol_data:DictProxy, symbols: ListProxy, is_on:ValueProxy[bool], max_hedge: int = 5, volume_size: int = 1) -> None:
        # Lista de symbolos para administar dentro de la estrategia
        self.symbols = symbols
                
        # Diccionario que contendra la data necesaria para ejecutar la estrategia cada symbolo
        self.symbol_data = symbol_data
        
        # El numero que identificara las ordenes de esta estrategia
        self.magic = 33
        
        # True para que la estrategia siga ejecutandose y False para detenerse
        self.is_on = is_on
        
        # El maximo hedge permitido
        self.max_hedge = max_hedge
        
        # El tamaño del lote
        if volume_size is None:
            self.volume_size = None
        else:
            self.volume_size = float(volume_size)
                
        # Horario de apertura y cierre del mercado
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':19, 'minute':55}
      
    #region Utilities
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
    
    #endregion   
    
    #region Profit Management
                    
    def manage_positions(self, positions: Tuple[TradePosition]):
        """
        Gestiona las posiciones para maximizar las ganancias de HardHedge mediante la actualización del stop loss y el trailing stop.

        Args:
            positions (Tuple[TradePosition]): Tupla de posiciones de operaciones.
        """
        # Itera sobre todas las posiciones en la lista "positions"
        if not positions:
            self.clean_positions_in_txt()
            self._hedge_buyer()
            
        for position in positions:
            # Obtiene los datos relacionados con el símbolo de la posición
            data = self.symbol_data[position.symbol]
            submit_changes = False
            
            symbol_info = MT5Api.get_symbol_info(position.symbol)
            
            if position.type == OrderType.MARKET_BUY: # Compra
                new_stop_loss = position.tp - data['recovery_range']
                new_take_profit = position.tp + data['recovery_range']
                if symbol_info.bid > new_stop_loss:
                    submit_changes = True
                    
            else: # Venta
                new_stop_loss = position.tp + data['recovery_range']
                new_take_profit = position.tp - data['recovery_range']
                if symbol_info.ask < new_stop_loss:
                    submit_changes = True
                
            if submit_changes is True:                 
                # Actualiza el stop loss y el take profit con el nuevo valor calculado
                MT5Api.send_change_stop_loss_and_take_profit(position.symbol, new_stop_loss, new_take_profit, position.ticket)

    
    #endregion             
    
    #region HardHedge strategy           
    def _preparing_symbols_data(self):
        """
        Prepara la data que se usara en la estrategia de HardHedge.
        """
        print("HardHedge: Preparando la data...")
        # Variable auxiliar
        symbol_data = {}
        
        # Obtener la informacion necesaria para cada symbolo
        for symbol in self.symbols:
            
            number_bars = 30
            
            rates_in_range = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1, number_bars)
            
            info = MT5Api.get_symbol_info(symbol)
            
            digits = info.digits
            high = np.max(rates_in_range['high'])
            low = np.min(rates_in_range['low'])
            range_value = abs(high - low)
            dividing_price = round(((high + low)/2), digits)
            recovery_range = round((range_value/3), digits)

            min_range = info.trade_stops_level * info.point
            
            if recovery_range < min_range:
                recovery_range = min_range
            
            if self.volume_size is None:
                self.volume_size = info.volume_min
            
            counter_hedge = self.volume_size
            for i in range(1, self.max_hedge):
                if i % 2 == 0: 
                    counter_hedge += self.volume_size * (2 ** (i))
                else:
                    counter_hedge -=  self.volume_size * (2 ** (i))
            
            counter_hedge = round(abs(counter_hedge), digits)
                
            symbol_data[symbol] = {
                'symbol': symbol,
                'digits': digits,
                'recovery_range': recovery_range,
                'dividing_price': dividing_price,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'counter_hedge': abs(counter_hedge)
            }
            
            print(symbol_data)
            
            
        # Actualiza la variable compartida
        self.symbol_data.update(symbol_data)
    
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
                
                # Variables para el calculo de tp y sl
                radius = data['recovery_range']*3
                spread_point = info_symbol.spread * info_symbol.point
                
                # Se establece el tp y el sl
                if info_symbol.bid > data['dividing_price']:
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
                
                # Se establece el tp y el sl
                if info_symbol.bid > data['dividing_price']:
                    order['order_type'] = OrderType.MARKET_BUY
                    
                else:
                    order['order_type'] = OrderType.MARKET_SELL
                
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
        
        if positions:
            last_position = positions[-1]
                
            data = self.symbol_data[last_position.symbol]
            
            # Obtiene el precio actual para el symbolo                
            info_symbol =  MT5Api.get_symbol_info(last_position.symbol)
            
            if last_position.type == OrderType.MARKET_BUY:  # Long
                recovery_low = last_position.sl + (data["recovery_range"] * 3)
                if info_symbol.ask < recovery_low:  
                    self._hedge_order(last_position, data, recovery_low, info_symbol)
            else:  # Short
                recovery_high = last_position.sl - (data["recovery_range"] * 3.5)
                if info_symbol.bid > recovery_high:
                    self._hedge_order(last_position, data, recovery_high, info_symbol)
        
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
            new_volume = self.volume_size * (2 ** (next_hedge))
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

    
    #endregion
    
    #region start
    def start(self):
        """
        Inicia la estrategia de HardHedge trading para los símbolos especificados.
        """

        print("HardHedge: Iniciando estrategia...")
        
        # Inicio del cilco
        while self.is_on:
            # Salir del bucle si no quedan símbolos
            if not self.symbols:
                print("HardHedge: No hay símbolos por analizar.")
                self.is_on.value = False
                break
            self._hedge_strategy()
                    
        # Fin del ciclo
        print("HardHedge: Finalizando estrategia...")
          
    #endregion