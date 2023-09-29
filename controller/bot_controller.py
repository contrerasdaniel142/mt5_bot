import os
import sys
# Obtiene la ruta absoluta del directorio actual
current_file = os.path.abspath(os.getcwd())
# Agrega el directorio actual al sys.path para poder ejecutar el programa
sys.path.append(current_file)

# Importaciones necesarias para definir tipos de datos
from typing import List, Dict, Any, Tuple

# importaciones para realizar operaciones numéricas eficientes
import numpy as np

# Importacion de los clientes de las apis para hacer solicitudes
from models.alpaca.client import AlpacaApi
from models.mt5.client import MT5Api
from models.mt5.enums import TimeFrame, OrderType
from models.mt5.models import TradePosition

# Imporacion para manejro y busqueda en texto
import re

# Para trabajo en paralelo
import multiprocessing
from multiprocessing import Queue
from multiprocessing.managers import DictProxy, ListProxy, ValueProxy

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz
import time


#-------------------------------------------------------------------------------------------------------------------------------------


class BotController:
    def __init__(self) -> None:
        # Estos horarios estan en utc
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':19, 'minute':55}
        self._alpaca_api = AlpacaApi()

    #region Positions Management
    def manage_positions(self, strategies: List[object]):
        """
        Administra las posiciones abiertas según las estrategias proporcionadas.

        Este método revisa las estrategias proporcionadas y gestiona las posiciones abiertas de acuerdo con ellas.
        
        Args:
            strategies (List[object]): Una lista de objetos que representan las estrategias a seguir.

        Returns:
            None
        """
        print("Iniciando administrador de posiciones abiertas.")
        while True:
            number_of_active_positions = 0
            number_of_active_strategies = 0
            
            # Iterar a través de las estrategias proporcionadas
            for strategy in strategies:
                # Revisa si la estrategia está activa aún
                if strategy.is_on:
                    number_of_active_strategies += 1
                # Obtiene las posiciones para la estrategia con su identificador magic
                positions = MT5Api.get_positions(magic=strategy.magic)
                if positions:
                    number_of_active_positions += 1
                    # Llama al método 'manage_profit' de la estrategia para gestionar las posiciones
                    strategy.manage_profit(positions)

            # # Si no hay posiciones abiertas ni estrategias activas, sal del bucle
            # if number_of_active_positions == 0 and number_of_active_strategies == 0:
            #     print("Sin posiciones abiertas ni estrategias activas.")
            #     break

            # Salir del bucle si terminó el horario de mercado
            if not self._is_in_market_hours():
                print("Finalizó el horario de mercado. Cerrando posiciones abiertas")
                # Envia una solicitud para cerrar todas las posiciones abiertas
                MT5Api.send_close_all_position()
                break
    #endregion

    #region utilities
    def _get_business_hours_today(self):
        """
        Obtiene las horas de apertura y cierre del mercado para el día de hoy.

        Returns:
            dict: Un diccionario con las horas de apertura y cierre ajustadas a utc. 
                  Si el diccionario está vacío, significa que no hubo mercado hoy.

        Example:
            Usar esta función para obtener las horas de apertura y cierre del mercado hoy:
            mi_instancia = MiClase()
            horas_mercado = mi_instancia.get_business_hours_today()
            
            if horas_mercado:
                print(f"Hora de apertura del mercado: {horas_mercado['open']}")
                print(f"Hora de cierre del mercado: {horas_mercado['close']}")
            else:
                print("Hoy no hubo mercado.")
        """
        # Obtiene la hora de apertura y cierre del mercado para el dia de hoy en el horario de estados unidos
        calendar_today = self._alpaca_api.get_next_days_of_market(0)
        business_hours = {}
        if calendar_today:
            # Convierte el open y close al tiempo manejado en utc
            business_hours['open'] = calendar_today[0].open.astimezone(pytz.utc)
            business_hours['close'] = calendar_today[0].close.astimezone(pytz.utc)
            return business_hours
        return business_hours   
    
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
        if market_open <= current_time <= market_close and self._get_business_hours_today():
            return True
        else:
            print("El mercado está cerrado.")
            return False

    def _sleep_to_next_market_opening(self, sleep_in_market:bool = True):
        """Espera hasta la próxima apertura del mercado.

        Args:
            sleep_in_market (bool): Indica si el método debe ejecutarse durante el mercado abierto (False) o no (True).

        Returns:
            None
        """
        
        if sleep_in_market == False and self._is_in_market_hours():
            print("El mercado está abierto")
            return
        
        print("Obteniendo proxima apertura de mercado...")
    
        # Obtener la hora actual en UTC
        current_time = datetime.now(pytz.utc)
        
        # Obtiene los calendarios de mercado desde el día actual hasta 10 días después.
        calendars = self._alpaca_api.get_next_days_of_market(10)
        
        next_market_open = None
        
        for calendar in calendars:
            next_market_open = calendar.open.astimezone(pytz.utc).replace(
                hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute']
            )
            if current_time < next_market_open:
                break
            
        print("Hora actual utc: ", current_time)
        print("Apertura del mercado utc: ", next_market_open)
        
        # Calcular la cantidad de segundos que faltan hasta la apertura
        seconds_until_open = (next_market_open - current_time).total_seconds()
        
        print(f"Esperando {seconds_until_open} segundos hasta la apertura...")
        time.sleep(seconds_until_open)
    
        # Obtener la hora actual en UTC después de esperar
        current_time = datetime.now(pytz.utc)
        print("Hora actual utc: ", current_time)

    def _find_value_in_text(self, text: str, pattern: str):
        """
        Busca un patrón en un texto y devuelve el valor encontrado o None si no se encuentra.
        
        Args:
            text (str): El texto en el que se buscará el patrón.
            pattern (str): El patrón de expresión regular a buscar en el texto.

        Returns:
            str or None: El valor encontrado si se encuentra, o None si no se encuentra.
        """
        result = re.search(pattern, text)
        
        if result:
            return result.group(1)  # Devuelve el primer grupo capturado
        else:
            return None
    
    #endregion
    
    #region start
    def start(self):
        """
        Inicia el programa principal.

        Esta función se encarga de comenzar la ejecución del programa principal. 
        Realiza las siguientes tareas:
        1. Obtiene el horario comercial del día actual.
        2. Verifica si el horario comercial está disponible.
        3. Si está disponible, inicia las estrategias.

        Returns:
            None
        """
        print("")
        print("Iniciando bot..")
                
        # Establece los symbolos
        symbols= ["US30.cash"] 
        
        # Crea un administrador para multiprocessing
        manager = multiprocessing.Manager()
                
        # Abre mt5 y espera 4 segundos
        MT5Api.initialize(4)
        MT5Api.shutdown()
                
        while True:
            print("")
                                    
            # Revisa si aun falta tiempo para la apertura de mercado y espera
            # Si el mercado se encuentra abierto continua con el programa
            self._sleep_to_next_market_opening(sleep_in_market= False)
            
            # Se crea una lista que contendra a los objetos de las estrategias creadas
            strategies = []
            
            
            #region creación de estrategias
                        
            #region HardHedge
            # Se crea el objeto de la estrategia HardHedge 
            hard_hedge_symbols = manager.list(symbols)
            hard_hedge_trading = HardHedgeTrading(
                symbol_data= manager.dict({}), 
                symbols= hard_hedge_symbols, 
                is_on=manager.Value("b", True), 
                orders_time=60
            )
            hard_hedge_trading._preparing_symbols_data()
            strategies.append(hard_hedge_trading)
            # Se crea el proceso que administra la estrategia
            hard_hedge_process = multiprocessing.Process(target=hard_hedge_trading.start)
            hard_hedge_process.start()
            #endregion
            
            #endregion
            
                            
            # Inicia el proceso que administrara todas las posiciones de todas las estrategias agregadas en tiempo real
            manage_positions_process = multiprocessing.Process(target=self.manage_positions, args=(strategies,))
            manage_positions_process.start()
            # Espera a que termine el proceso
            manage_positions_process.join()
            
            self._sleep_to_next_market_opening(sleep_in_market= True)

    #endregion

#-------------------------------------------------------------------------------------------------------------------------------------

class HardHedgeTrading:
    def __init__(self, symbol_data:DictProxy, symbols: ListProxy, is_on:ValueProxy[bool], orders_time: int = 60) -> None:
        # Lista de symbolos para administar dentro de la estrategia
        self.symbols = symbols
        
        # Tiempo de espera en segundos que habra entre cada compra
        self.orders_time = orders_time
        
        # Diccionario que contendra la data necesaria para ejecutar la estrategia cada symbolo
        self.symbol_data = symbol_data
        
        # El numero que identificara las ordenes de esta estrategia
        self.magic = 33
        
        # True para que la estrategia siga ejecutandose y False para detenerse
        self.is_on = is_on
        
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
        for position in positions:
            # Obtiene los datos relacionados con el símbolo de la posición
            data = self.symbol_data[position.symbol]
            submit_changes = False
            if position.type == OrderType.MARKET_BUY: # Compra
                new_stop_loss = position.tp - data['recovery_range']
                new_take_profit = position.tp + data['recovery_range']
                if position.price_current > new_stop_loss:
                    submit_changes = True
                    
            else: # Venta
                new_stop_loss = position.tp + data['recovery_range']
                new_take_profit = position.tp - data['recovery_range']
                if position.price_current < new_stop_loss:
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
        current_time = datetime.now(pytz.utc)
        
        # Establece el periodo de tiempo para calcular el rango
        start_time = current_time.replace(hour=self._market_opening_time['hour'], minute=0, second=0, microsecond=0)
        end_time = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'], second=0, microsecond=0)
        
        # Variable auxiliar
        symbol_data = {}
        
        # Obtener la informacion necesaria para cada symbolo
        for symbol in self.symbols:
            rates_in_range = MT5Api.get_rates_range(symbol, TimeFrame.MINUTE_1, start_time, end_time)
            info = MT5Api.get_symbol_info(symbol)
            
            # Obtiene la cantidad de decimales que debe teber una orden en su volumen
            digits = info.digits

            high = np.max(rates_in_range['high'])
            low = np.min(rates_in_range['low'])
            range_value = abs(high - low)
            dividing_price = round(((high + low)/2), digits)
            recovery_range = round((range_value/3), digits)
            
            current_time = datetime.now(pytz.utc)
                        
            symbol_data[symbol] = {
                'symbol': symbol,
                'digits': digits,
                'recovery_range': recovery_range,
                'dividing_price': dividing_price,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max
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
        if account_info.margin_free > minimun_margin:
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
                
                if current_price > data['dividing_price']:
                    recovery_high = current_price
                    order['order_type'] = OrderType.MARKET_BUY
                    order['take_profit'] = recovery_high + radius
                    order['stop_loss'] = recovery_high - radius
                    
                else:
                    recovery_low = current_price
                    order['order_type'] = OrderType.MARKET_SELL
                    order['take_profit'] = recovery_low - radius
                    order['stop_loss'] = recovery_low + radius
                
                # El comment representara al numero de veces que se ha apliacado el HardHedge
                order['comment'] = str(0)
                
                # Envía la orden a MetaTrader 5
                MT5Api.send_order(**order)
            
        # Espera el tiempo establecido para volver a realizar las ordenes
        time.sleep(self.orders_time)
        
    def _hedge_strategy(self):
        """
        Ejecuta la estrategia a las posiciones abiertas.
        """
        while self.is_on:
            # Se obtienen las posiciones abiertas
            positions = MT5Api.get_positions(magic=self.magic)
            for position in positions:
                # Si la posicion tiene un take profit igual a cero, significa que ya tiene ganancias y se ignora
                if self.find_position_in_txt(position.ticket):
                    continue
                data = self.symbol_data[position.symbol]
                
                if position.type == OrderType.MARKET_BUY: # Long
                    recovery_low = position.sl + (data["recovery_range"]*2)
                    if position.price_current < recovery_low:
                        self._hedge_order(position, data, recovery_low)
                else: # Short
                    recovery_high = position.sl - (data["recovery_range"]*2)
                    if position.price_current > recovery_high:
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
        comment = str(next_hedge)
        new_volume = data['volume_min'] * (2 ** (next_hedge))
        radius = data['recovery_range']*3
        
        if position.type == OrderType.MARKET_BUY:
            new_order_type = OrderType.MARKET_SELL
            tp = recovery_price - radius
            sl = recovery_price + radius
        else:
            new_order_type = OrderType.MARKET_BUY
            tp = recovery_price + radius
            sl = recovery_price - radius
                    
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
        if MT5Api.send_order(**order):
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
        while True:
            # Salir del bucle si no quedan símbolos
            if not self.symbols:
                print("HardHedge: No hay símbolos por analizar.")
                self.is_on.value = False
                break
            
            # Salir del bucle si termino el mercado
            if not self._is_in_market_hours():
                print("HardHedge: Finalizo el horario de mercado.")
                self.is_on.value = False
                break
            
            self._hedge_buyer()
        
        strategy_process.join()
        
        # Limpiamos el archivo txt para la proxima iteración
        self.clean_positions_in_txt()
        
        # Fin del ciclo
        print("HardHedge: Finalizando estrategia...")
          
    #endregion
         


