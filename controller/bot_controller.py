import os
import sys
import pandas as pd
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
from multiprocessing.managers import DictProxy, ListProxy

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
            all_positions = MT5Api.get_positions()
            
            # Iterar a través de las estrategias proporcionadas
            for strategy in strategies:
                # Revisa si la estrategia está activa aún
                if strategy.symbols:
                    number_of_active_strategies += 1
                
                # Usar una comprensión de lista para filtrar las posiciones que contienen el comentario
                positions = [position for position in all_positions if strategy.comment in position.comment]
                if positions:
                    number_of_active_positions += 1
                    # Llama al método 'manage_positions' de la estrategia para gestionar las posiciones
                    strategy.manage_positions(positions)

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
                
        # Establece el riesgo por operacion
        user_risk = 100
        
        # Se establece el riesgo maximo
        max_user_risk = 1000
        
        # Establece los symbolos
        symbols= ["US30.cash"] 
        
        # Crea un administrador
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
            
            # #region Real-time breakout
            # # Se crea el objeto de la estrategia breakout en tiempo real
            # symbols_rt_breakout = manager.list(symbols)
            # rt_breakoutTrading = BreakoutTrading(data= manager.dict({}), symbols=symbols_rt_breakout, number_stops= 4, in_real_time= True)
            # # Se agrega rt_breakout_symbols
            # strategies.append(rt_breakoutTrading)                      
            # # Se crea el proceso que incia la estrategia
            # rt_breakout_process = multiprocessing.Process(target=rt_breakoutTrading.start)
            # # Prepara la data de la estrategia antes de iniciar
            # rt_breakoutTrading._prepare_breakout_data(user_risk)    
            # # Se inicia el proceso, si no se desea que se ejecute solo comente rt_breakout_process.start()
            # rt_breakout_process.start()
            # #endregion
            
            # #region Every-minute breakout
            # # Se crea el objeto de la estrategia breakout cada minuto
            # symbols_em_breakout = manager.list(symbols)
            # em_breakoutTrading = BreakoutTrading(data= manager.dict({}), symbols=symbols_em_breakout, number_stops= 4, in_real_time= False)
            # # Se agrega rt_breakout_symbols
            # strategies.append(em_breakoutTrading)                      
            # # Se crea el proceso que incia la estrategia
            # em_breakout_process = multiprocessing.Process(target=em_breakoutTrading.start)
            # # Prepara la data de la estrategia antes de iniciar
            # em_breakoutTrading._prepare_breakout_data(user_risk)      
            # # Se inicia el proceso, si no se desea que se ejecute solo comente em_breakout_process.start()
            # em_breakout_process.start()
            # #endregion
            
            #region Hedge
            # Se crea el objeto de la estrategia hedge 
            symbols_hedge = manager.list(symbols)
            hedgeTrading = HedgeTrading(data= manager.dict({}), symbols=symbols_hedge)
            strategies.append(hedgeTrading)                      
            # Se crea el proceso que incia la estrategia
            hedge_process = multiprocessing.Process(target=hedgeTrading.start)
            # Prepara la data de la estrategia antes de iniciar
            hedgeTrading._prepare_hedge_data(user_risk= user_risk, max_user_risk= max_user_risk)    
            # Se inicia el proceso, si no se desea que se ejecute solo comente
            hedge_process.start()
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


class BreakoutTrading:
    def __init__(self, data:DictProxy, symbols: ListProxy, number_stops:int = 4, in_real_time: bool = False) -> None:
        # Estos horarios estan en utc
        self._in_real_time = in_real_time
        
        # Se guarda la lista de símbolos compartida
        self.symbols = symbols
        
        # Las veces que se fracionara el stop cuando se tomen ganancias con parciales
        self.number_stops = number_stops
        
        # Variable compartida que se acutalizara entre procesos
        self._data = data 
        
        # El numero de intentos de cada símbolo de enviar una orden
        self._purchase_attempts = {}
        
        # El comentario que identificara a los trades
        if in_real_time:
            self.comment = "Breakout:rt"
        else:
            self.comment = "Breakout:em"
        
        # Porcentaje
        self._percentage_piece = (100 / self.number_stops) / 100
        
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':19, 'minute':55}
    
    #region Senders
    def _send_order(self, order: Dict[str, Any]):
        """
        Procesa y envía órdenes a MetaTrader 5 desde una cola de órdenes.

        Esta función procesa continuamente órdenes que se encuentran en una cola y las envía a MetaTrader 5.
        Cada orden es enviada después de inicializar la conexión con MetaTrader 5 y se cierra la conexión 
        después de enviar la orden.

        Args:
            order (Dict[str, Any]): Un diccionario que contiene información de la orden a enviar a MetaTrader 5.

        Returns:
            None
        """
        request = MT5Api.send_order(**order)
        if request is None:
            self._purchase_attempts[order['symbol']] += 1
        else:
            self._purchase_attempts[order['symbol']] = 0
    #endregion
    
    #region Utilities
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
    
    def _counting_decimals(self, number:float):
        """
        Cuenta el número de decimales en un número de punto flotante.

        Args:
            number (float): El número de punto flotante del que deseas contar los decimales.

        Returns:
            int: El número de decimales en el número.
        """
        # Convierte el número a una cadena (string) y divide en partes usando el punto decimal
        partes = str(number).split('.')
        # Si hay una parte decimal, devuelve la longitud de esa parte; de lo contrario, devuelve 0
        return len(partes[1]) if len(partes) > 1 else 0
    
    def _is_in_market_hours(self):
        """
        Comprueba si el momento actual se encuentra en horario de mercado.

        Returns:
            bool: True si se encuentra en horario de mercado, False si no lo está.
        """
        # Obtener la hora y minutos actuales en UTC
        current_time = datetime.now(pytz.utc).time()

        # Crear objetos time para el horario de apertura y cierre del mercado
        market_open = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'])
        market_close = current_time.replace(hour=self._market_closed_time['hour'], minute=self._market_closed_time['minute'])

        # Verificar si la hora actual está dentro del horario de mercado
        if market_open <= current_time <= market_close:
            return True
        else:
            print("El mercado está cerrado.")
            return False
    
    def get_number_in_comment(self, comment:str)->int:
        """
        Extrae y devuelve el último número entero encontrado en la cadena de comentario dada.

        Args:
            comment (str): La cadena de comentario de entrada.
        Returns:
            int: El número entero extraído si se encuentra, o None si no se encuentra ningún número en el comentario.
        """
        parts = comment.split()

        if parts[-1].isdigit():
            return int(parts[-1])
        else:
            return None
    
    def get_decimal_part(number)->int:
        """
        Obtiene la parte decimal de un número como un entero.

        Args:
            number (float): El número del cual se quiere obtener la parte decimal.

        Returns:
            int: La parte decimal del número como un entero. Si no hay parte decimal, se devuelve un cero.
        """
        # Convierte el número a una cadena
        number_str = str(number)
        
        # Divide la cadena en partes usando el punto decimal como separador
        parts = number_str.split('.')
        
        # Si hay al menos dos partes (parte entera y parte decimal)
        if len(parts) > 1:
            # Devuelve la parte decimal como una cadena
            return int(parts[1])
        else:
            # Si no hay parte decimal, devuelve 0
            return 0
    #endregion
        
    #region Positions Management
    
    def manage_positions(self, positions: List[TradePosition]):
        """
        Gestiona las posiciones de breakout.

        Args:
            positions (List[TradePosition]): Lista de posiciones de operaciones.
        """
        # Itera sobre todas las posiciones en la lista proporcionada.
        for position in positions:
            # Obtiene el símbolo asociado a la posición actual.
            symbol = position.symbol
            
            # Comprueba si el símbolo ya está presente en el diccionario de datos.
            if symbol in self._data:
                # Verifica si el campo "tp" de la posición actual es igual a cero.
                if position.tp == 0:
                    # Si "tp" es cero, aplica una estrategia de trailing stop adicional.
                    self._trailing_stop(self._data[symbol]['range'], position)
                else:
                    # Si "tp" no es cero, llama a la función "_partial_position" para gestionar la posición parcial.
                    self._partial_position(position)

    def _partial_position(self, position: TradePosition):
        """
        Calcula y envía órdenes para gestionar una posición parcial.

        Args:
            position (TradePosition): La posición de trading actual.

        Returns:
            None
        """
        # Obtiene el símbolo asociado a la posición actual.
        symbol = position.symbol
        # Obtiene los datos relacionados con el símbolo de trading.
        symbol_data = self._data[symbol]
        # Obtiene el precio de apertura y el precio actual de la posición.
        price_open = position.price_open
        price_current = position.price_current
        # Obtiene el valor de "take_profit" de la posición.
        take_profit = position.tp
        # Calcula la diferencia de precio entre "take_profit" y el precio de apertura.
        profit_range = abs(take_profit - price_open)

        # Verifica si "first_volume" y "stop_level" no están presentes en los datos del símbolo y los inicializa si no lo están.
        if "first_volume" not in symbol_data and "stop_level" not in symbol_data:
            # Inicializa valores iniciales para la posición parcial.
            symbol_data['first_volume'] = position.volume
            # Calcula el valor de "take_profit" según el tipo de posición.
            if position.type == 0:
                symbol_data['previous_stop_level'] = abs((symbol_data['range'] * 2) - take_profit)
            else:
                symbol_data['previous_stop_level'] = abs((symbol_data['range'] * 2) + take_profit)
            # Actualiza los valores en el diccionario compartido self._data.
            self._data.update({symbol: symbol_data})

        # Obtiene el número de posición parcial desde el comentario de la posición.
        partial_position_number = self.get_number_in_comment(position.comment)

        # Calcula el porcentaje de volumen a vender para esta posición parcial.
        percentage = self._percentage_piece * partial_position_number
        # Calcula el siguiente rango parcial basado en el porcentaje de ganancia y el rango de ganancia.
        next_partial_range = percentage * profit_range

        # Calcula el nivel de stop loss basado en el tipo de posición y el rango parcial.
        if position.type == 0:
            stop_level = price_open + next_partial_range
            # Verifica si el nivel de stop es menor que el precio actual antes de enviar la orden.
            if stop_level < price_current:
                # Llama a la función para preparar y enviar una orden parcial.
                self._prepare_and_send_partial_order(symbol_data, position, stop_level, partial_position_number)
        else:
            stop_level = price_open - next_partial_range
            # Verifica si el nivel de stop es mayor que el precio actual antes de enviar la orden.
            if stop_level > price_current:
                # Llama a la función para preparar y enviar una orden parcial.
                self._prepare_and_send_partial_order(symbol_data, position, stop_level, partial_position_number)

    def _prepare_and_send_partial_order(self, symbol_data: Dict[str, Any], position: TradePosition, stop_level, partial_position_number: int):
        """
        Prepara y envía una orden para una posición parcial.

        Args:
            symbol_data (Dict[str, Any]): Datos relacionados con el símbolo de trading.
            position (TradePosition): La posición de trading actual.
            stop_level: Nivel de stop loss para la posición parcial.
            partial_position_number (int): Número de la posición parcial.

        Returns:
            None
        """
        # Obtiene el símbolo del diccionario de datos.
        symbol = symbol_data['symbol']
        # Calcula el número de la siguiente posición parcial.
        next_partial_position_number = partial_position_number + 1
        # Calcula el nuevo volumen para la venta parcial.
        new_volume = round(symbol_data['first_volume'] * self._percentage_piece, symbol_data['decimals'])
        # Crea un nuevo comentario para la orden con el número de la posición parcial.
        new_comment = self.comment + " " + str(next_partial_position_number)

        # Envía la orden de venta parcial.
        MT5Api.send_sell_partial_order(symbol, new_volume, position.ticket, new_comment)
        # Mueve el stop loss al nivel anterior.
        new_stop_loss = symbol_data['previous_stop_level']
        # Actualiza el stop loss en MT5.
        is_change_completed = MT5Api.send_change_stop_loss(symbol, new_stop_loss, position.ticket)
        # En caso de ser la última posición parcial, elimina el take profit para iniciar el trailing stop.
        if is_change_completed and next_partial_position_number == self.number_stops:
            # Elimina el take profit.
            MT5Api.send_change_take_profit(symbol, 0.0, position.ticket)
        # Actualiza el nuevo "previous_stop_level" con el "stop_level" actual.
        symbol_data['previous_stop_level'] = stop_level
        # Actualiza los valores en el diccionario compartido self._data.
        self._data.update({symbol: symbol_data})
        
    def _trailing_stop(self, range: float, position: TradePosition):
        """
        Aplica un trailing stop a una posición.

        Args:
            range (float): El rango para calcular el trailing stop.
            position (TradePosition): La posición de la operación.

        Esta función calcula y aplica un trailing stop a una posición en función del rango especificado.
        """
        # Se calcula la distancia del trailing stop con el rango especificado
        trailing_stop_distance = range  * 0.5

        # Calcula la diferencia entre el precio actual y el stop loss existente
        difference = abs(position.price_current - position.sl)

        # Si la diferencia es mayor que el rango especificado, se aplica el trailing stop
        if difference > range:
            # Calcula el nuevo stop loss
            if position.type == 0: 
                # Para una posición de compra (long)
                new_sl = position.price_current - trailing_stop_distance
            else:
                # Para una posición de venta (short)
                new_sl = position.price_current + trailing_stop_distance
            
            # Envia la orden para cambiar el stop loss en MT5
            MT5Api.send_change_stop_loss(position.symbol, new_sl, position.ticket)
    
    #endregion
    
    #region Breakout strategy
    def _breakout_order(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        Prepara órdenes para ser enviadas a MetaTrader 5. Cada orden se prepara en función de los datos recibidos.

        Args:
            symbol (str): El nombre del símbolo para el cual se creará la orden.
            data (Dict[str, Any]): Los datos necesarios para preparar la orden, como precios, volúmenes, etc.

        Returns:
            None
        """
        print("Breakout: Preparando orden ", str(data['symbol']))
        # Pre establece los datos de la orden que se enviará
        order = {
            "symbol": data['symbol'], 
            "order_type": None, 
            "volume": None,
            "price": None,
            "stop_loss": None,
            "take_profit": None,
            "ticket": None,
            "comment": None
        }
        
        # Consultar el número de órdenes realizadas para el símbolo
        positions = MT5Api.get_positions(symbol= symbol)
        
        # Filtra aquellos con el comentario de la estrategia
        positions = [position for position in positions if self.comment in position.comment]
        
        # Obtiene el numero de la ultima posicion realizada
        if positions:
            number = self.get_number_in_comment(positions[-1].comment)
        else:
            number = 0
                    
        order['volume'] = data['lot_size']
        
        # El volumen se remplaza con el maximo permitido en caso de ser mayor
        if order['volume'] > data['volume_max']:
            order['volume'] = data['volume_max']
        # El volumen se remplaza con el minimo permitido en caso de ser menor
        elif order['volume'] < data['volume_min']:
            order['volume'] = data['volume_min']
                        
        # El tipo de compra que se realizará y 
        # se establecen los demás campos de la orden
        if data['type'] == 'buy':
            order['order_type'] = OrderType.MARKET_BUY
            order['take_profit'] = data['high'] + (data['range']*2)
            order['stop_loss'] = data['low']
        else:
            order['order_type'] = OrderType.MARKET_SELL
            order['take_profit'] = data['low'] - (data['range']*2)
            order['stop_loss'] = data['high']
        
        
        order['comment'] = self.comment + " " + str(number + 1)
        
        # Se envía la orden por la cola de comunicación
        self._send_order(order)

    def _prepare_breakout_data(self, user_risk: float):
        """
        Prepara la data que se usara en la estrategia de breakout.

        Args:
            user_risk (float): Riesgo del usuario.
        """
        current_time = datetime.now(pytz.utc)
        
        # Establecer el horario de inicio y finalización del mercado
        start_time = current_time.replace(
            hour=self._market_opening_time['hour'],
            minute=0,
            second=0,
            microsecond=0
        )
        end_time = current_time.replace(
            hour=self._market_opening_time['hour'],
            minute=self._market_opening_time['minute'],
            second=0,
            microsecond=0
        )
        
        data = {}
        
        # Obtener la informacion necesaria para cada symbolo
        for symbol in self.symbols:
            rates_in_range = MT5Api.get_rates_range(symbol, TimeFrame.MINUTE_1, start_time, end_time)
            info = MT5Api.get_symbol_info(symbol)
            
            # Obtiene la cantidad de decimales que debe teber una orden en su volumen
            decimals = self._counting_decimals(info.volume_min)

            high = np.max(rates_in_range['high'])
            low = np.min(rates_in_range['low'])
            range_value = round(abs(high - low), decimals)
            trade_risk = round((user_risk / range_value), decimals)
            
            data[symbol] = {
                'symbol': symbol,
                'high': high,
                'low': low,
                'range': range_value,
                'lot_size': trade_risk,
                'decimals': decimals,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'partial_position': 1
            }
            
            # Establece el numero de intentos de comprar en 0
            self._purchase_attempts[symbol] = 0
            
        # Actualiza la variable compartida
        self._data.update(data)
    
    def _breakout_strategy(self):
        """
        Ejecuta la estrategia.

        Esta función verifica los símbolos proporcionados y toma decisiones de compra o venta basadas en ciertas condiciones.

        Returns:
            None
        """
        # Verifica que tipo de ejecucion es
        if self._in_real_time == False:
            # Espera que el minuto termine para iniciar
            self._sleep_to_next_minute()
        
        # Se crea una copia para evitar errores cuando se modifique la original
        copy_symbols = list(self.symbols)
        
        for symbol in copy_symbols:
            data = self._data[symbol]
            
            # Asegura un numero de intentos de compra maximos para evitar que el bot se estanque
            if self._purchase_attempts[symbol] > 5:
                print("Numero de intentos de compra para ", symbol, " excedidos, quitando símbolo de la lista.")
                self.symbols.remove(symbol)
                           
            # Se obtienen las posiciones abiertas
            positions = MT5Api.get_positions(symbol)
            # Usar una comprensión de lista para filtrar las posiciones que contienen el comentario
            positions = [position for position in positions if self.comment in position.comment]
            type = None
            # En caso de exisitr almenos una posicion abierta obtiene el tipo de esta
            if positions:
                type = positions[-1].type
                # Remueve los símbolos tradeados segun la estrategia
                self.symbols.remove(symbol)
                continue
            
            # Obtiene el precio actual
            current_price = MT5Api.get_last_price(symbol)
            
            # Precio ask (venta) como precio de compra
            if current_price < data['low'] and (type == 0 or type is None):
                # Se agrega el tipo de orden
                data['type'] = 'sell'
                # Crear orden y enviarla
                self._breakout_order(symbol, data)
                
            # Precio bid (oferta) como precio de venta
            elif current_price > data['high'] and (type == 1 or type is None):
                # Se agrega el tipo de orden
                data['type']= 'buy'
                # Crear orden y enviarla
                self._breakout_order(symbol, data)
                               
    #endregion
    
    #region start
    def start(self):
        """
        Inicia la estrategia de breakout trading para los símbolos especificados.

        Args:
            user_risk (int, opcional): El nivel de riesgo deseado para las operaciones. El valor predeterminado es 100.
        Returns:
            None
        """
        
        if self._in_real_time:
            print("Breakout: Iniciando estrategia (tiempo real)...")
            print("Breakout: Símbolos por analizar en tiempo real ", self.symbols)
        else:
            print("Breakout: Iniciando estrategia (cada minuto)...")
            print("Breakout: Símbolos por analizar cada minuto ", self.symbols)
               
        # Inicio del cilco
        while True:
            # Salir del bucle si no quedan símbolos
            if not self.symbols:
                print("Breakout: No hay símbolos por analizar.")
                break
            
            # Salir del bucle si termino el mercado
            if not self._is_in_market_hours():
                print("Breakout: Finalizo el horario de mercado.")
                break
            
            # Ejecuta la estrategia
            self._breakout_strategy()
        # Fin del ciclo
        
        if self._in_real_time:
            print("Breakout: Finalizando estrategia (tiempo real)...")
        else:
            print("Breakout: Finalizando estrategia (cada minuto)...")             
    #endregion
    

#-------------------------------------------------------------------------------------------------------------------------------------


class HedgeTrading:
    def __init__(self, data:DictProxy, symbols: ListProxy) -> None:
        # Se guarda la lista de símbolos compartida
        self.symbols = symbols
        
        # Variable compartida que se acutalizara entre procesos
        self._data = data 
        
        # El comentario que identificara a los trades
        self.comment = "Hedge"
                
        # El numero de intentos de cada símbolo de enviar una orden
        self._purchase_attempts = {}
        
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':19, 'minute':55}
    
    #region Senders
    def _send_order(self, order: Dict[str, Any]):
        """
        Procesa y envía órdenes a MetaTrader 5 desde una cola de órdenes.

        Esta función procesa continuamente órdenes que se encuentran en una cola y las envía a MetaTrader 5.
        Cada orden es enviada después de inicializar la conexión con MetaTrader 5 y se cierra la conexión 
        después de enviar la orden.

        Args:
            order (Dict[str, Any]): Un diccionario que contiene información de la orden a enviar a MetaTrader 5.

        Returns:
            None
        """
        # Envía la orden a MetaTrader 5
        request = MT5Api.send_order(**order)
        if request is None:
            self._purchase_attempts[order['symbol']] += 1
        else:
            self._purchase_attempts[order['symbol']] = 0
    #endregion
    
    #region Utilities
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
    
    def _counting_decimals(self, number:float):
        """
        Cuenta el número de decimales en un número de punto flotante.

        Args:
            number (float): El número de punto flotante del que deseas contar los decimales.

        Returns:
            int: El número de decimales en el número.
        """
        # Convierte el número a una cadena (string) y divide en partes usando el punto decimal
        partes = str(number).split('.')
        # Si hay una parte decimal, devuelve la longitud de esa parte; de lo contrario, devuelve 0
        return len(partes[1]) if len(partes) > 1 else 0
    
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
    
    def get_number_in_comment(self, comment:str)->int:
        """
        Extrae y devuelve el último número entero encontrado en la cadena de comentario dada.

        Args:
            comment (str): La cadena de comentario de entrada.
        Returns:
            int: El número entero extraído si se encuentra, o None si no se encuentra ningún número en el comentario.
        """
        parts = comment.split()

        if parts[-1].isdigit():
            return int(parts[-1])
        else:
            return None
    
    #endregion
    
    #region Positions Management
    
    def manage_positions(self, positions: List[TradePosition]):
        """
        Gestiona las posiciones de Hedge mediante la actualización del stop loss y el trailing stop.

        Args:
            positions (List[TradePosition]): Lista de posiciones de operaciones.
        """
        # Itera sobre todas las posiciones en la lista "positions"
        for position in positions:
            # Obtiene los datos relacionados con el símbolo de la posición
            data = self._data[position.symbol]
            
            # Si el take profit (tp) es igual a cero, ejecuta el trailing stop
            if position.tp == 0:
                self._trailing_stop(data['recovery_range'], position)
            else:               
                # Calcula la diferencia entre el precio actual y el take profit
                difference = abs(position.price_current - position.tp)
                
                # Si la diferencia es menor que el rango de recuperación
                if difference < data['recovery_range']:
                    # Calcula el nuevo valor del stop loss
                    if position.type == 0: # Para una posición de compra (long)
                        new_stop_loss = position.tp - data['recovery_range']
                    else: # Para una posición de venta (short)
                        new_stop_loss = position.tp + data['recovery_range']
                                        
                    # Actualiza el stop loss con el nuevo valor calculado
                    request = MT5Api.send_change_stop_loss(position.symbol, new_stop_loss, position.ticket)
                    
                    # Si el cambio de stopp loss se ejecuto con extito se quita el  take profit
                    if request is True:
                        # Elimina el take profit
                        MT5Api.send_change_take_profit(position.symbol, 0.0, position.ticket)
                        
    def _trailing_stop(self, range: float, position: TradePosition):
        """
        Aplica un trailing stop a una posición.

        Args:
            range (float): El rango para calcular el trailing stop.
            position (TradePosition): La posición de la operación.

        Esta función calcula y aplica un trailing stop a una posición en función del rango especificado.
        """
        # Se calcula la distancia del trailing stop con el rango especificado
        trailing_stop_distance = range 

        # Calcula la diferencia entre el precio actual y el stop loss existente
        difference = abs(position.price_current - position.sl)

        # Si la diferencia es mayor que el rango especificado, se aplica el trailing stop
        if difference > range:
            # Calcula el nuevo stop loss
            if position.type == 0: 
                # Para una posición de compra (long)
                new_sl = position.price_current - trailing_stop_distance
            else:
                # Para una posición de venta (short), se aumenta el stop loss
                new_sl = position.price_current + trailing_stop_distance
            
            # Envia la orden para cambiar el stop loss en MT5
            MT5Api.send_change_stop_loss(position.symbol, new_sl, position.ticket)
 
    #endregion
    
    #region Hedge strategy
    def _hedge_order(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        Prepara órdenes para ser enviadas a MetaTrader 5. Cada orden se prepara en función de los datos recibidos.

        Args:
            symbol (str): El nombre del símbolo para el cual se creará la orden.
            data (Dict[str, Any]): Los datos necesarios para preparar la orden, como precios, volúmenes, etc.

        Returns:
            None
        """
        order = {
            "symbol": symbol, 
            "order_type": None, 
            "volume": None,
            "price": None,
            "stop_loss": None,
            "take_profit": None,
            "ticket": None,
            "comment": None
        }
           
        # Consultar el número de órdenes realizadas para el símbolo
        positions = MT5Api.get_positions(symbol= symbol)
        
        # Filtra aquellos con el comentario de la estrategia
        positions = [position for position in positions if self.comment in position.comment]
        
        # Obtiene el numero de la ultima posicion realizada
        if positions:
            number = self.get_number_in_comment(positions[-1].comment)
        else:
            number = 0
            
        # size = 2^(number) con esta formula nos aseguramos que el size siempre sea el doble del anterior
        size = 2 ** (number)
        order['volume'] = (data['lot_size'] * size)
        
        # El volumen se remplaza con el maximo permitido en caso de ser mayor
        if order['volume'] > data['volume_max']:
            order['volume'] = data['volume_max']
        # El volumen se remplaza con el minimo permitido en caso de ser menor
        elif order['volume'] < data['volume_min']:
            order['volume'] = data['volume_min']
                
        # El tipo de compra que se realizará y 
        # se establecen los demás campos de la orden
        if data['type'] == 'buy':
            order['order_type'] = OrderType.MARKET_BUY
            order['take_profit'] = data['recovery_high'] + (data['recovery_range']*3)
            order['stop_loss'] = data['recovery_low'] - (data['recovery_range']*2)
            
        else:
            order['order_type'] = OrderType.MARKET_SELL
            order['take_profit'] = data['recovery_low'] - (data['recovery_range']*3)
            order['stop_loss'] = data['recovery_high'] + (data['recovery_range']*2)
        
        order['comment'] = self.comment + " " + str(number+1)
        
        # Se envía la orden por la cola de comunicación
        self._send_order(order)

    def _prepare_hedge_data(self, user_risk: float, max_user_risk: float):
        """
        Prepara la data que se usara en la estrategia de Hedge.

        Args:
            user_risk (float): Riesgo minimo del usuario.
            max_user_risk (float): Riesgo maximo del usuario.
        """
        print("Hedge: Preparando la data...")
        current_time = datetime.now(pytz.utc)
        
        # Establecer el horario de inicio y finalización del mercado
        start_time = current_time.replace(
            hour=self._market_opening_time['hour'],
            minute=0,
            second=0,
            microsecond=0
        )
        
        end_time = current_time.replace(
            hour=self._market_opening_time['hour'],
            minute=self._market_opening_time['minute'],
            second=0,
            microsecond=0
        )
        
        data = {}
        
        # Obtener la informacion necesaria para cada symbolo
        for symbol in self.symbols:
            rates_in_range = MT5Api.get_rates_range(symbol, TimeFrame.MINUTE_1, start_time, end_time)
            info = MT5Api.get_symbol_info(symbol)
            
            # Obtiene la cantidad de decimales que debe teber una orden en su volumen
            decimals = self._counting_decimals(info.volume_min)

            high = np.max(rates_in_range['high'])
            low = np.min(rates_in_range['low'])
            range_value = round(abs(high - low), decimals)
            recovery_range = round((range_value/3), decimals)
            min_trade_risk = round((user_risk / range_value), decimals)
            max_trade_risk = round((max_user_risk / range_value), decimals)
            
            current_time = datetime.now(pytz.utc)
            
            if current_time < (end_time + timedelta(seconds=10)):
                in_hedge = True
            else:
                in_hedge = False
            
            data[symbol] = {
                'symbol': symbol,
                'high': high,
                'decimals': decimals,
                'low': low,
                'range': range_value,
                'recovery_range': recovery_range,
                'recovery_high': None,
                'recovery_low': None,
                'lot_size': 1.95,   # Prueba
                'max_lot_size': max_trade_risk,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'in_hedge': in_hedge    # Indica si esta la estrategia activa
            }
            
            # Establece el numero de intentos de comprar en 0
            self._purchase_attempts[symbol] = 0
            
        # Actualiza la variable compartida
        self._data.update(data)
    
    def _hedge_strategy(self):
        """
        Ejecuta la estrategia.

        Esta función verifica los símbolos proporcionados y toma decisiones de compra o venta basadas en ciertas condiciones.

        Returns:
            None
        """
        # Se crea una copia para evitar errores cuando se modifique la original
        copy_symbols = list(self.symbols)
        
        for symbol in copy_symbols:
            data = self._data[symbol]
            
            # Asegura un numero de intentos de compra maximos para evitar que el bot se estanque
            if self._purchase_attempts[symbol] > 5:
                print("Numero de intentos de compra para ", symbol, " excedidos, quitando símbolo de la lista.")
                self.symbols.remove(symbol)
                
            # Se obtienen las posiciones abiertas
            positions = MT5Api.get_positions(symbol)
            # Usar una comprensión de lista para filtrar las posiciones que contienen el comentario
            positions = [position for position in positions if self.comment in position.comment]
            last_type = None
            # En caso de exisitr almenos una posicion abierta obtiene el tipo de esta
            if positions:
                last_position = positions[-1]
                last_type = last_position.type
                # Elimina los symbolos que ya consiguieron ganancias y estan en traling stop
                # Aquellos en trailing stop tendran take profit 0
                if last_position.tp == 0:
                    data['in_hedge'] = False
                    data['recovery_low'] = None
                    data['recovery_high'] = None
                    self._data.update({symbol: data})
                    continue
                
            # Obtiene la ultima barra
            last_bar = MT5Api.get_last_bar(symbol)
            # Obtiene el precio actual
            current_price = last_bar['close']
            
            # Si el precio vuelve a estar dentro del rango de recuperación, se habilita la cobertura y se actualiza el estado.
            if data['recovery_low'] is None and data['recovery_high'] is None:
                if data['in_hedge'] == False and data['recovery_high'] > current_price > data['recovery_low']:
                    data['in_hedge'] = True
                    self._data.update({symbol: data})
            
                        
            if last_type is None and data['in_hedge'] == True:
                if current_price < data['low']:
                    # Se establece el recovery zone
                    data['recovery_low'] = data['low']
                    data['recovery_high'] = data['low'] + data['recovery_range']
                    # Actualiza el diccionario compartido
                    self._data.update({symbol: data})
                
                elif current_price > data['high']:
                    # Se establece el recovery zone
                    data['recovery_low'] = data['high'] - data['recovery_range']
                    data['recovery_high'] = data['high']
                    # Actualiza el diccionario compartido
                    self._data.update({symbol: data})
            
            # Se asegura de tener la recovery zone establecida antes de  tomar una decision
            if data['recovery_low'] is not None and data['recovery_high'] is not None:
                
                if (last_type == 0 or last_type is None) and current_price < data['recovery_low']:
                    # Se agrega el tipo de orden
                        data['type'] = 'sell'
                        # Crear orden y enviarla
                        self._hedge_order(symbol, data)
                
                elif (last_type == 1 or last_type is None) and current_price > data['recovery_high']:
                        # Se agrega el tipo de orden
                        data['type']= 'buy'
                        # Crear orden y enviarla
                        self._hedge_order(symbol, data)
                    
    #endregion
    
    #region start
    def start(self):
        """
        Inicia la estrategia de Hedge trading para los símbolos especificados.
        Returns:
            None
        """

        print("Hedge: Iniciando estrategia...")
        
        # Inicio del cilco
        while True:
            # Salir del bucle si no quedan símbolos
            if not self.symbols:
                print("Hedge: No hay símbolos por analizar.")
                break
            
            # Salir del bucle si termino el mercado
            if not self._is_in_market_hours():
                print("Hedge: Finalizo el horario de mercado.")
                break
            
            # Ejecuta la estrategia
            self._hedge_strategy()
        # Fin del ciclo
        print("Hedge: Finalizando estrategia...")
          
    #endregion


