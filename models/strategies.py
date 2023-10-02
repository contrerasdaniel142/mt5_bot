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
from .mt5.models import TradePosition

# Importacion de los clientes de las apis para hacer solicitudes
from .mt5.client import MT5Api

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz, time

#endregion

class HardHedgeTrading:
    def __init__(self, symbol_data:DictProxy, symbols: ListProxy, is_on:ValueProxy[bool], orders_time: int = 60, max_hedge: int = 5) -> None:
        # Lista de symbolos para administar dentro de la estrategia
        self.symbols = symbols
        
        # Tiempo de espera en segundos que habra entre cada compra
        self.interval_seconds_in_orders = orders_time
        
        # Diccionario que contendra la data necesaria para ejecutar la estrategia cada symbolo
        self.symbol_data = symbol_data
        
        # El numero que identificara las ordenes de esta estrategia
        self.magic = 33
        
        # True para que la estrategia siga ejecutandose y False para detenerse
        self.is_on = is_on
        
        # El maximo hedge permitido
        self.max_hedge = max_hedge
                
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
    def manage_profit(self, positions: Tuple[TradePosition]):
        """
        Gestiona las posiciones para maximizar las ganancias de HardHedge mediante la actualización del stop loss y el trailing stop.

        Args:
            positions (Tuple[TradePosition]): Tupla de posiciones de operaciones.
        """
        # Itera sobre todas las posiciones en la lista "positions"
        info_symbol = {}
        for position in positions:
            
            # Obtiene el precio actual para el symbolo
            if position.symbol not in info_symbol:
                info_symbol[position.symbol] = MT5Api.get_symbol_info(position.symbol)
                
            info = info_symbol[position.symbol]
            
            if position.type == OrderType.MARKET_BUY: # Compra
                if info.bid >= position.tp:
                    MT5Api.send_close_position(position.symbol, position.ticket)
                
                if info.bid <= position.sl:
                    MT5Api.send_close_position(position.symbol, position.ticket)
                    
            else: # Venta
                if info.ask <= position.tp:
                    MT5Api.send_close_position(position.symbol, position.ticket)

                if info.ask >= position.sl:
                    MT5Api.send_close_position(position.symbol, position.ticket)
    
    #endregion             
    
    #region HardHedge strategy           
    def _preparing_symbols_data(self):
        """
        Prepara la data que se usara en la estrategia de HardHedge.
        """
        print("HardHedge: Preparando la data...")
        current_time = datetime.now(pytz.utc)
        
        # Establece el periodo de tiempo para calcular el rango
        start_time = current_time.replace(hour=self._market_opening_time['hour'], minute=0, second=0, microsecond=0)
        end_time = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'], second=0, microsecond=0)
        
        # Se usa como base para escoger el recovery range
        seconds_in_range = (end_time - start_time).total_seconds()

        # Cantidad por la que hay que dividir el rango para hallar el recovery range
        times_divisible = seconds_in_range / self.interval_seconds_in_orders
        
        # Variable auxiliar
        symbol_data = {}
        
        # Obtener la informacion necesaria para cada symbolo
        for symbol in self.symbols:
            rates_in_range = MT5Api.get_rates_range(symbol, TimeFrame.MINUTE_1, start_time, end_time)
            
            if rates_in_range is None or rates_in_range.size == 0:
                rates_in_range = MT5Api.get_rates_range(symbol, TimeFrame.MINUTE_1, (current_time - timedelta(minutes=31)), (current_time - timedelta(minutes=1)))
            
            info = MT5Api.get_symbol_info(symbol)
            
            # Obtiene la cantidad de decimales que debe teber una orden en su volumen
            digits = info.digits

            high = np.max(rates_in_range['high'])
            low = np.min(rates_in_range['low'])
            range_value = abs(high - low)
            dividing_price = round(((high + low)/2), digits)
            recovery_range = round((range_value/times_divisible), digits)

            min_range = info.spread * info.point
            
            if recovery_range < min_range:
                recovery_range = min_range                      
            
            counter_hedge = 0.3
            for i in range(1, self.max_hedge):
                if i % 2 == 0: 
                    counter_hedge += 0.3 * (2 ** (i))
                else:
                    counter_hedge -=  0.3 * (2 ** (i))
                
                
            symbol_data[symbol] = {
                'symbol': symbol,
                'digits': digits,
                'recovery_range': recovery_range,
                'dividing_price': dividing_price,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'counter_hedge': counter_hedge
            }
            
            print(symbol_data)
            
            
        # Actualiza la variable compartida
        self.symbol_data.update(symbol_data)
    
    def _hedge_buyer(self):
        """
        Prepara órdenes para ser enviadas a MetaTrader 5. Las ordenes se preparan cada self.orders_time, en función de los datos establecidos.
        """
        # Verifica si el margen disponible es menor al 10% de el balance de la cuenta
        account_info = MT5Api.get_account_info()
        minimun_margin =  0.10 *  account_info.balance
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
                    "volume": data['volume_min'],
                    "price": None,
                    "stop_loss": None,
                    "take_profit": None,
                    "ticket": None,
                    "comment": None,
                    "magic": self.magic
                }
                
                # Obtiene la ultima barra
                last_bar = MT5Api.get_last_bar(symbol)
                # Obtiene el precio actual
                current_price = last_bar['close']
                
                # Se establece el tipo de orden, su tp y su sl
                radius = data['recovery_range']*3
                
                # Se establece el tp y el sl
                if current_price > data['dividing_price']:
                    recovery_high = current_price
                    tp = recovery_high + data['recovery_range']*2
                    sl = recovery_high - data['recovery_range']*3
                    order['order_type'] = OrderType.MARKET_BUY
                    
                else:
                    recovery_low = current_price
                    tp = recovery_low - data['recovery_range']*2
                    sl = recovery_low + data['recovery_range']*3
                    order['order_type'] = OrderType.MARKET_SELL
                    
                order['take_profit'] = round(tp, data['digits'])
                order['stop_loss'] = round(sl, data['digits'])
                
                # Se establece el tp y el sl
                if current_price > data['dividing_price']:
                    order['order_type'] = OrderType.MARKET_BUY
                    
                else:
                    order['order_type'] = OrderType.MARKET_SELL
                
                # El comment representara al numero de veces que se ha apliacado el HardHedge
                order['comment'] = str(0)
                
                # Envía la orden a MetaTrader 5
                MT5Api.send_order(**order)
            
        # Espera el tiempo establecido para volver a realizar las ordenes
        time.sleep(self.interval_seconds_in_orders)
        
    def _hedge_strategy(self):
        """
        Ejecuta la estrategia a las posiciones abiertas.
        """
        while self.is_on:
            last_price = {}
            # Se obtienen las posiciones abiertas
            positions = MT5Api.get_positions(magic=self.magic)
            for position in positions:
                # Si la posicion tiene un take profit igual a cero, significa que ya tiene ganancias y se ignora
                if self.find_position_in_txt(position.ticket):
                    continue
                
                data = self.symbol_data[position.symbol]
                
                # Obtiene el precio actual para el symbolo
                if position.symbol not in last_price:
                    last_price[position.symbol] = MT5Api.get_last_price(position.symbol)
                    
                if position.type == OrderType.MARKET_BUY: # Long
                    recovery_low = position.sl + (data["recovery_range"]*2)
                    if last_price <= recovery_low:
                        self._hedge_order(position, data, recovery_low)
                else: # Short
                    recovery_high = position.sl - (data["recovery_range"]*2)
                    if last_price >= recovery_high:
                        self._hedge_order(position, data, recovery_high)
        
    def _hedge_order(self, position:TradePosition, data:Dict[str, Any], recovery_price:float) -> None:
        """
        Prepara órdenes para ser enviadas a MetaTrader 5. Cada orden se prepara en función de los datos recibidos.

        Args:
            position (TradePosition): La posición de la orden original.
            data (Dict[str, Any]): Datos relevantes para la preparación de la orden.
            recovery_price (float): El precio de recuperación utilizado para establecer take-profit y stop-loss.
        """         
        # Se establece la orden y se envia
        next_hedge = int(position.comment)+1
                        
        if next_hedge < self.max_hedge:
            new_volume = data['volume_min'] * (2 ** (next_hedge))
            comment = str(next_hedge)
        else:
            new_volume = data['counter_hedge']
            comment = -1
                
        if new_volume > data['volume_max']:
            new_volume = float(data['volume_max'])
                
        if position.type == OrderType.MARKET_BUY:
            new_order_type = OrderType.MARKET_SELL
            tp = recovery_price - data['recovery_range']*2 
            sl = recovery_price + data['recovery_range']*3
        else:
            new_order_type = OrderType.MARKET_BUY
            tp = recovery_price + data['recovery_range']*2
            sl = recovery_price - data['recovery_range']*3
        
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
        # Crea los hilos necesarios
        strategy_process = multiprocessing.Process(target=self._hedge_strategy)
        strategy_process.start()
        
        # Inicio del cilco
        while self.is_on:
            # Salir del bucle si no quedan símbolos
            if not self.symbols:
                print("HardHedge: No hay símbolos por analizar.")
                self.is_on.value = False
                break
                        
            self._hedge_buyer()
        
        strategy_process.join()
        
        # Limpiamos el archivo txt para la proxima iteración
        self.clean_positions_in_txt()
        
        # Fin del ciclo
        print("HardHedge: Finalizando estrategia...")
          
    #endregion