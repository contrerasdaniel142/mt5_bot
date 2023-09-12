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
        self._market_opening_time = {'hour':13, 'minute':29}
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

            # Si no hay posiciones abiertas ni estrategias activas, sal del bucle
            if number_of_active_positions == 0 and number_of_active_strategies == 0:
                print("Sin posiciones abiertas ni estrategias activas.")
                break

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
        if market_open <= current_time <= market_close:
            return True
        else:
            print("El mercado está cerrado.")
            return False

    def _sleep_to_next_market_opening(self, sleep_to_tomorrow:bool = False):
        """
        Espera hasta la próxima apertura del mercado.

        Esta función calcula el tiempo restante hasta la próxima apertura del mercado. Si la apertura ya ha ocurrido o si se especifica
        `sleep_to_tomorrow` como True, el programa esperará hasta la apertura del próximo día.

        Args:
            sleep_to_tomorrow (bool, optional): Si es True, el programa esperará hasta la apertura del mercado del día siguiente.
                Por defecto, es False.

        Returns:
            None
        """
        if not self._is_in_market_hours() or sleep_to_tomorrow == True:
            
            print("Iniciando esperar hasta la proxima apertura de mercado...")
            
            # Obtener la hora actual en UTC
            current_time = datetime.now(pytz.utc)
            
            print("Hora actual utc: ", current_time)
        
            # Crear un objeto datetime para la hora de apertura del mercado hoy
            market_open = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'], second=0)
            
            # Si se quiere que el programa espere hasta el dia de mañana se aumentara un dia
            if sleep_to_tomorrow and current_time > market_open:
                print("Esperar hasta la apertura de mañana.")
                market_open = market_open + timedelta(days=1)
            
            print("Apertura del mercado utc: ", market_open)
            
            # Calcular la cantidad de segundos que faltan hasta la apertura
            seconds = (market_open - current_time).total_seconds()
            
            print("Esperando la apertura...")
                        
            time.sleep(seconds)
            
            # Obtener la hora actual en UTC
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
        
        # Establece los symbolos
        symbols= ["US30.cash"] 
        
        # Crea un administrador
        manager = multiprocessing.Manager()
                
        while True:
            print("Comprobando mercado...")
            business_hours_utc = self._get_business_hours_today()
            
            # Abre mt5 y espera 4 segundos
            MT5Api.initialize(sleep=4)
                        
            if business_hours_utc:
                # Revisa si aun falta tiempo para la apertura de mercado y espera
                self._sleep_to_next_market_opening()
                
                # Se crea una lista que contendra a los objetos de las estrategias creadas
                strategies = []
                
                
                #region creación de estrategias
                
                #region Real-time breakout
                # Se crea el objeto de la estrategia breakout en tiempo real
                symbols_rt_breakout = manager.list(symbols)
                rt_breakoutTrading = BreakoutTrading(data= manager.dict({}), symbols=symbols_rt_breakout, number_stops= 4, in_real_time= True)
                # Se agrega rt_breakout_symbols
                strategies.append(rt_breakoutTrading)                      
                # Se crea el proceso que incia la estrategia
                rt_breakout_process = multiprocessing.Process(target=rt_breakoutTrading.start, args=(user_risk,))
                # Prepara la data de la estrategia antes de iniciar
                rt_breakoutTrading._prepare_breakout_data(user_risk)    
                # Se inicia el proceso, si no se desea que se ejecute solo comente rt_breakout_process.start()
                rt_breakout_process.start()
                #endregion
                
                #region Every-minute breakout
                # Se crea el objeto de la estrategia breakout cada minuto
                symbols_em_breakout = manager.list(symbols)
                em_breakoutTrading = BreakoutTrading(data= manager.dict({}), symbols=symbols_em_breakout, number_stops= 4, in_real_time= False)
                # Se agrega rt_breakout_symbols
                strategies.append(em_breakoutTrading)                      
                # Se crea el proceso que incia la estrategia
                em_breakout_process = multiprocessing.Process(target=em_breakoutTrading.start, args=(user_risk,))
                # Prepara la data de la estrategia antes de iniciar
                em_breakoutTrading._prepare_breakout_data(user_risk)      
                # Se inicia el proceso, si no se desea que se ejecute solo comente em_breakout_process.start()
                em_breakout_process.start()
                #endregion
                
                #endregion
                
                                
                # Inicia el proceso que administrara todas las posiciones de todas las estrategias agregadas en tiempo real
                manage_positions_process = multiprocessing.Process(target=self.manage_positions, args=(strategies,))
                manage_positions_process.start()
                                
                # Espera a que termine el proceso
                manage_positions_process.join()
            
            # Al finalizar la ejecución del programa o si no hay mercado hoy, 
            # se pausará el programa hasta el próximo día laborable para volver a comprobar.
            print("")
            self._sleep_to_next_market_opening(sleep_to_tomorrow=True)                
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
        
        # El comentario que identificara a los trades
        if in_real_time:
            self.comment = "Breakout:rt"
        else:
            self.comment = "Breakout:em"
            
        self._market_opening_time = {'hour':13, 'minute':29}
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
        print("Breakout: Enviando orden")
        # Envía la orden a MetaTrader 5
        MT5Api.send_order(**order)
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
    #endregion
    
    #region Breakout strategy Management
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
                    
        order['volume'] = data['lote_size']
        
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
        
        order['comment'] = self.comment
        
        # Se envía la orden por la cola de comunicación
        self._send_order(order)

    def _prepare_breakout_data(self, user_risk: float):
        """
        Prepara la data que se usara en la estrategia de breakout.

        Args:
            user_risk (float): Riesgo del usuario.
        """
        print("Breakout: Preparando la data...")
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
            range_value = abs(high - low)
            trade_risk = round((user_risk / range_value), decimals)
            
            data[symbol] = {
                'symbol': symbol,
                'high': high,
                'low': low,
                'range': range_value,
                'lote_size': trade_risk,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'partial_position': 1
            }
            
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
        if self._in_real_time:
            # Espera que el minuto termine para iniciar
            self._sleep_to_next_minute()
        
        # Se crea una copia para evitar errores cuando se modifique la original
        copy_symbols = list(self.symbols)
        
        for symbol in copy_symbols:
            data = self._data[symbol]            
            # Se obtienen las posiciones abiertas
            positions = MT5Api.get_positions(symbol)
            type = None
            # En caso de exisitr almenos una posicion abierta obtiene el tipo de esta
            if positions:
                type = positions[-1].type
            
            # Obtenemos la ultima informacion actualizada del symbolo
            info_tick = MT5Api.get_symbol_info_tick(symbol)
            
            # Precio ask (venta) como precio de compra
            if info_tick.bid < data['low'] and (type == 0 or type is None):
                # Se agrega el tipo de orden
                data['type'] = 'sell'
                # Crear orden y enviarla
                self._breakout_order(symbol, data)
                # Remueve los símbolos tradeados segun la estrategia
                self.symbols.remove(symbol)
            
            # Precio bid (oferta) como precio de venta
            elif info_tick.ask >data['high'] and (type == 1 or type is None):
                # Se agrega el tipo de orden
                data['type']= 'buy'
                # Crear orden y enviarla
                self._breakout_order(symbol, data)
                # Remueve los símbolos tradeados segun la estrategia
                self.symbols.remove(symbol)
                
            # En caso de no superar alguna de las condiciones ignfica que los precios estan alejados de su rango
            # por lo tanto hay que quitar el símbolo
            if symbol in self.symbols:
                self.symbols.remove(symbol)
               
    #endregion
    
    #region Positions Management
    def manage_positions(self, positions: List[TradePosition]):
        """
        Gestiona las posiciones de breakout.

        Args:
            positions (List[TradePosition]): Lista de posiciones de operaciones.
        """
        for position in positions:
            self._trailing_strategy(position)

    def _trailing_strategy(self, position: TradePosition):
        """
        Estrategia de seguimiento para una posición.

        Args:
            position (TradePosition): La posición de la operación.

        Esta función implementa una estrategia de trailing stop basada en ciertas condiciones.
        """
        symbol = position.symbol
        symbol_data = self._data[symbol]  # Datos relacionados con el símbolo
        partial_position = symbol_data['partial_position']
        
        if partial_position == 1:
            # Inicializa valores iniciales para la posición parcial
            symbol_data['first_volume'] = position.volume
            symbol_data['previous_stop_level'] = position.price_open
            # Actualiza los valores en el diccionario compartido self._data
            self._data.update({symbol: symbol_data})

        # Calcula el porcentaje de cambio de precio
        price_change_percentage = ((position.price_current - position.price_open) / (position.tp - position.price_current))
        percentage_piece = (100 / self.number_stops) / 100

        # Calcula el porcentaje para la próxima posición parcial y el umbral donde comienza el trailing stop
        next_partial_percentage = percentage_piece * partial_position

        if price_change_percentage > next_partial_percentage and symbol_data['partial_position'] < self.number_stops:
            # Calcula el nuevo volumen para la venta parcial
            new_volume = symbol_data['first_volume'] * next_partial_percentage
            # Envia la orden para la venta parcial
            MT5Api.send_sell_partial_position(symbol, new_volume, position.ticket)
            # Actualiza la posición parcial
            symbol_data['partial_position'] += 1
            # Mueve el stop loss al nivel anterior
            new_stop_loss = symbol_data['previous_stop_level']
            # Actualiza el stop loss en MT5
            MT5Api.send_change_stop_loss(symbol, new_stop_loss, position.ticket)
            # Actualiza el nuevo previous_stop_level con el precio actual
            symbol_data['previous_stop_level'] = position.price_current
            
            # Actualiza los valores en el diccionario compartido self._data
            self._data.update({symbol: symbol_data})
            
        else:
            # Aplica una estrategia de trailing stop adicional
            self._trailing_stop(symbol_data['range'], position)

    def _trailing_stop(self, range: float, position: TradePosition):
        """
        Aplica un trailing stop a una posición.

        Args:
            range (float): El rango para calcular el trailing stop.
            position (TradePosition): La posición de la operación.

        Esta función calcula y aplica un trailing stop a una posición en función del rango especificado.
        """
        # Se calcula la distancia con el rango
        trailing_stop_distance = range * 0.5
        
        if position.type == 0:
            # Calcula el nuevo stop loss para posiciones de compra
            new_sl = position.price_current - trailing_stop_distance
            if new_sl > position.sl:
                # Envia la orden para cambiar el stop loss en MT5
                MT5Api.send_change_stop_loss(position.symbol, new_sl, position.ticket)
        else:
            # Calcula el nuevo stop loss para posiciones de venta
            new_sl = position.price_current + trailing_stop_distance
            if new_sl < position.sl:
                # Envia la orden para cambiar el stop loss en MT5
                MT5Api.send_change_stop_loss(position.symbol, new_sl, position.ticket)
    #endregion
    
    #region start
    def start(self, user_risk: int = 100):
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
    def __init__(self, data:DictProxy, symbols: ListProxy, number_stops:int = 4, in_real_time: bool = False) -> None:
        # Estos horarios estan en utc
        self._in_real_time = in_real_time
        
        # Se guarda la lista de símbolos compartida
        self.symbols = symbols
        
        # Las veces que se fracionara el stop cuando se tomen ganancias con parciales
        self.number_stops = number_stops
        
        # Variable compartida que se acutalizara entre procesos
        self._data = data 
        
        # El comentario que identificara a los trades
        if in_real_time:
            self.comment = "Hedge: real-time order"
        else:
            self.comment = "Hedge: every-minute order"
            
        self._market_opening_time = {'hour':13, 'minute':29}
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
        print("Hedge: Enviando orden")
        # Envía la orden a MetaTrader 5
        MT5Api.send_order(**order)
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
    #endregion
    
    #region Hedge strategy Management
    def _hedge_order(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        Prepara órdenes para ser enviadas a MetaTrader 5. Cada orden se prepara en función de los datos recibidos.

        Args:
            symbol (str): El nombre del símbolo para el cual se creará la orden.
            data (Dict[str, Any]): Los datos necesarios para preparar la orden, como precios, volúmenes, etc.

        Returns:
            None
        """
        print("Hedge: Preparando orden ", str(data['symbol']))
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
                    
        order['volume'] = data['lote_size']
        
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
        
        order['comment'] = self.comment
        
        # Se envía la orden por la cola de comunicación
        self._send_order(order)

    def _prepare_hedge_data(self, user_risk: float):
        """
        Prepara la data que se usara en la estrategia de Hedge.

        Args:
            user_risk (float): Riesgo del usuario.
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
            range_value = abs(high - low)
            recovery_range = range_value/3
            trade_risk = round((user_risk / range_value), decimals)
            
            data[symbol] = {
                'symbol': symbol,
                'high': high,
                'low': low,
                'range': range_value,
                'recovery_range': recovery_range,
                'recovery_zone': 0,
                'lote_size': trade_risk,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'partial_position': 1
            }
            
        # Actualiza la variable compartida
        self._data.update(data)
    
    def _hedge_strategy(self):
        """
        Ejecuta la estrategia.

        Esta función verifica los símbolos proporcionados y toma decisiones de compra o venta basadas en ciertas condiciones.

        Returns:
            None
        """
        # Verifica que tipo de ejecucion es
        if self._in_real_time:
            # Espera que el minuto termine para iniciar
            self._sleep_to_next_minute()
        
        # Se crea una copia para evitar errores cuando se modifique la original
        copy_symbols = list(self.symbols)
        
        for symbol in copy_symbols:
            data = self._data[symbol]            
            # Se obtienen las posiciones abiertas
            positions = MT5Api.get_positions(symbol)
            type = None
            # En caso de exisitr almenos una posicion abierta obtiene el tipo de esta
            if positions:
                type = positions[-1].type
            
            # Obtenemos la ultima informacion actualizada del symbolo
            info_tick = MT5Api.get_symbol_info_tick(symbol)
            
            if type is None:
                # Precio ask (venta) como precio de compra
                if info_tick.bid < data['low']:
                    # Se agrega el tipo de orden
                    data['type'] = 'sell'
                    # Se establece el recovery zone
                    data['recovery_zone'] = data['low'] + data['recovery_range']
                    # Crear orden y enviarla
                    self._hedge_order(symbol, data)
                
                # Precio bid (oferta) como precio de venta
                elif info_tick.ask >data['high']:
                    # Se agrega el tipo de orden
                    data['type']= 'buy'
                    # Se establece el recovery zone
                    data['recovery_zone'] = data['low'] + data['recovery_range']
                    # Crear orden y enviarla
                    self._hedge_order(symbol, data)
            
            elif type == 0 and info_tick.bid < (data['high'] - data['recovery_zone']):
                # Se agrega el tipo de orden
                    data['type'] = 'sell'
                    # Crear orden y enviarla
                    self._hedge_order(symbol, data)
            
            elif type == 1 and info_tick.ask > (data['low'] + data['recovery_zone']):
                # Se agrega el tipo de orden
                    data['type'] = 'sell'
                    # Crear orden y enviarla
                    self._hedge_order(symbol, data)
            
                
            
            # Precio ask (venta) como precio de compra
            if info_tick.bid < data['low'] and (type == 0 or type is None):
                # Se agrega el tipo de orden
                data['type'] = 'sell'
                # Crear orden y enviarla
                self._hedge_order(symbol, data)
                # Remueve los símbolos tradeados segun la estrategia
                self.symbols.remove(symbol)
            
            # Precio bid (oferta) como precio de venta
            elif info_tick.ask >data['high'] and (type == 1 or type is None):
                # Se agrega el tipo de orden
                data['type']= 'buy'
                # Crear orden y enviarla
                self._hedge_order(symbol, data)
                # Remueve los símbolos tradeados segun la estrategia
                self.symbols.remove(symbol)
                
            # En caso de no superar alguna de las condiciones ignfica que los precios estan alejados de su rango
            # por lo tanto hay que quitar el símbolo
            if symbol in self.symbols:
                self.symbols.remove(symbol)
            
            
    #endregion
    
    #region Positions Management
    def manage_positions(self, positions: List[TradePosition]):
        """
        Gestiona las posiciones de Hedge.

        Args:
            positions (List[TradePosition]): Lista de posiciones de operaciones.
        """
        for position in positions:
            self._trailing_strategy(position)

    def _trailing_strategy(self, position: TradePosition):
        """
        Estrategia de seguimiento para una posición.

        Args:
            position (TradePosition): La posición de la operación.

        Esta función implementa una estrategia de trailing stop basada en ciertas condiciones.
        """
        symbol = position.symbol
        symbol_data = self._data[symbol]  # Datos relacionados con el símbolo
        partial_position = symbol_data['partial_position']
        
        if partial_position == 1:
            # Inicializa valores iniciales para la posición parcial
            symbol_data['first_volume'] = position.volume
            symbol_data['previous_stop_level'] = position.price_open
            # Actualiza los valores en el diccionario compartido self._data
            self._data.update({symbol: symbol_data})

        # Calcula el porcentaje de cambio de precio
        price_change_percentage = ((position.price_current - position.price_open) / (position.tp - position.price_current))
        percentage_piece = (100 / self.number_stops) / 100

        # Calcula el porcentaje para la próxima posición parcial y el umbral donde comienza el trailing stop
        next_partial_percentage = percentage_piece * partial_position
        trailing_stop_threshold = percentage_piece * (self.number_stops - 1)

        if price_change_percentage > next_partial_percentage and price_change_percentage < trailing_stop_threshold:
            # Calcula el nuevo volumen para la venta parcial
            new_volume = symbol_data['first_volume'] * next_partial_percentage
            # Envia la orden para la venta parcial
            MT5Api.send_sell_partial_position(symbol, new_volume, position.ticket)
            # Actualiza la posición parcial
            symbol_data['partial_position'] += 1
            # Mueve el stop loss al nivel anterior
            new_stop_loss = symbol_data['previous_stop_level']
            # Actualiza el stop loss en MT5
            MT5Api.send_change_stop_loss(symbol, new_stop_loss, position.ticket)
            # Actualiza el nuevo previous_stop_level con el precio actual
            symbol_data['previous_stop_level'] = position.price_current
            
            # Actualiza los valores en el diccionario compartido self._data
            self._data.update({symbol: symbol_data})
            
        elif price_change_percentage > trailing_stop_threshold:
            # Aplica una estrategia de trailing stop adicional
            self._trailing_stop(symbol_data['range'], position)

    def _trailing_stop(self, range: float, position: TradePosition):
        """
        Aplica un trailing stop a una posición.

        Args:
            range (float): El rango para calcular el trailing stop.
            position (TradePosition): La posición de la operación.

        Esta función calcula y aplica un trailing stop a una posición en función del rango especificado.
        """
        # Se calcula la distancia con el rango
        trailing_stop_distance = range * 0.5
        
        if position.type == 0:
            # Calcula el nuevo stop loss para posiciones de compra
            new_sl = position.price_current - trailing_stop_distance
            if new_sl > position.sl:
                # Envia la orden para cambiar el stop loss en MT5
                MT5Api.send_change_stop_loss(position.symbol, new_sl, position.ticket)
        else:
            # Calcula el nuevo stop loss para posiciones de venta
            new_sl = position.price_current + trailing_stop_distance
            if new_sl < position.sl:
                # Envia la orden para cambiar el stop loss en MT5
                MT5Api.send_change_stop_loss(position.symbol, new_sl, position.ticket)
    #endregion
    
    #region start
    def start(self, user_risk: int = 100):
        """
        Inicia la estrategia de Hedge trading para los símbolos especificados.

        Args:
            user_risk (int, opcional): El nivel de riesgo deseado para las operaciones. El valor predeterminado es 100.
        Returns:
            None
        """

        print("Hedge: Iniciando estrategia...")
        # Prepara la data de la estrategia antes de iniciar
        self._prepare_hedge_data(user_risk)            
        
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


    #region hedge_strategy   
    
            # size = 2^(orders_placed) con esta formula nos aseguramos que el size siempre sea el doble del anterior
            # 0 orden = 1       3 orden = 8
            # 1 orden = 2       4 orden = 16
            # 2 orden = 4       .......
            # size = 2 ** (len(orders_placed))
            # order['volume'] = (data['trade_risk'] * size)
        
    #endregion
    
    
    