import os
import sys
# Obtiene la ruta absoluta del directorio actual
current_file = os.path.abspath(os.getcwd())
# Agrega el directorio actual al sys.path para poder ejecutar el programa
sys.path.append(current_file)

# Importaciones necesarias para definir tipos de datos
from typing import List, Dict, Any

# importaciones para realizar operaciones numéricas eficientes
import numpy as np

# Importacion de los clientes de las apis para hacer solicitudes
from models.alpaca.client import AlpacaApi
from models.mt5.client import MT5Api
from models.mt5.enums import TimeFrame, OrderType

# Para trabajo en paralelo
import multiprocessing
from multiprocessing import Queue

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz
import time

class BotController:
    def __init__(self) -> None:
        # Estos horarios estan en utc
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':20, 'minute':0}
        self._alpaca_api = AlpacaApi()

#region hedge_strategy
    def _send_order(self, send_order_queue: Queue):
        """
        Procesa y envía órdenes a MetaTrader 5 desde una cola de órdenes.

        Esta función procesa continuamente órdenes que se encuentran en una cola y las envía a MetaTrader 5.
        Cada orden es enviada después de inicializar la conexión con MetaTrader 5 y se cierra la conexión 
        después de enviar la orden.

        Args:
            send_order_queue (Queue): Una cola de órdenes que contiene diccionarios con información de las órdenes a enviar.

        Returns:
            None
        """
        while True:
            # Espera la orden
            order: Dict[str, Any] = send_order_queue.get()
            print("Enviando orden")
            
            # Abre la conexión con MetaTrader 5
            MT5Api.initialize()
            
            # Envía la orden a MetaTrader 5
            MT5Api.send_order(**order)
            
            # Cierra la conexión con MetaTrader 5
            MT5Api.shutdown()
        
    def _prepare_hedge_order(self, hedge_strategy_queue: Queue, send_order_queue: Queue):
        """
        Prepara órdenes para una estrategia de cobertura (hedge) a partir de datos en una cola de estrategias de cobertura.

        Esta función procesa continuamente datos de estrategias de cobertura que se encuentran en una cola y prepara órdenes para
        enviarlas a MetaTrader 5. Cada orden se prepara en función de los datos recibidos y se coloca en una cola de órdenes 
        listas para ser enviadas.

        Args:
            hedge_strategy_queue (Queue): Una cola de estrategias de cobertura que contiene datos relevantes para preparar órdenes.
            send_order_queue (Queue): Una cola de órdenes donde se colocarán las órdenes preparadas para ser enviadas.

        Returns:
            None
        """
        while True:
            data = hedge_strategy_queue.get()

            print("Preparando orden ", str(data['symbol']))
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
            
            # Obtener la hora actual en la zona horaria de Nueva York
            ny_timezone = pytz.timezone('America/New_York')
            current_time_in_ny = datetime.now(ny_timezone)

            # Establecer el horario de inicio y finalización en Nueva York y convertirlo a UTC
            start_time = current_time_in_ny.replace(hour=9, minute=30, second=0, microsecond=0).astimezone(pytz.utc)
            end_time = current_time_in_ny.astimezone(pytz.utc)

            # Abre la conexión con MetaTrader 5
            MT5Api.initialize()

            # Consultar el número de órdenes realizadas para el símbolo
            orders_placed = MT5Api.get_history_orders(start_time, end_time, order['symbol'])
            
            # Cierra la conexión con MetaTrader 5
            MT5Api.shutdown()
            
            # size = 2^(orders_placed) con esta formula nos aseguramos que el size siempre sea el doble del anterior
            # 0 orden = 1       3 orden = 8
            # 1 orden = 2       4 orden = 16
            # 2 orden = 4       .......
            size = 2 ** (len(orders_placed))
            order['volume'] = round((data['trade_risk'] * size),2)
            
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
                
            order['comment'] = "Mt5_bot: Hedge -> " + str(size)
            
            # Se envía la orden por la cola de comunicación
            send_order_queue.put(order)
             
    def _hedging_strategy_every_minute(self, user_risk:float, symbols: List[str], hedge_strategy_queue: Queue):
        """
        Función para verificar los símbolos y tomar decisiones de compra/venta para la estrategia.

        Esta función se encarga de verificar los símbolos proporcionados y tomar decisiones
        de compra o venta basadas en ciertas condiciones. Se ejecuta en un bucle infinito
        y toma decisiones al inicio de cada minuto durante el horario de mercado, antes de finalizar.

        Args:
            self: La instancia de la clase que llama a esta función.
            user_risk (float): El nivel de riesgo del usuario.
            symbols (List[str]): Una lista de símbolos a verificar.
            hedge_strategy_queue (Queue): Cola de comunicación para enviar datos de compra/venta.

        Returns:
            None
        """

        current_time = datetime.now(pytz.utc)
        
        # Establecer el horario de inicio y finalización del mercado
        start_time = current_time.replace(hour=self._market_opening_time['hour'], minute=0, second=0, microsecond=0)
        end_time = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'], second=0, microsecond=0)
                
        # Diccionario para almacenar rangos de precios de símbolos
        ranges: Dict[str, Dict[str, float]] = {}
        
        # Abre conexion con metatrader 5
        MT5Api.initialize()
        
        # Obtener el máximo y mínimo en el rango de precio para cada símbolo
        for symbol in symbols:
            rates_in_range = MT5Api.get_rates_range(symbol, TimeFrame.MINUTE_1, start_time, end_time)
            ranges[symbol] = {}
            ranges[symbol]['symbol'] = symbol
            ranges[symbol]['high'] = np.max(rates_in_range['high'])
            ranges[symbol]['low'] = np.min(rates_in_range['low'])
            ranges[symbol]['range'] = abs(ranges[symbol]['high'] - ranges[symbol]['low'])
            ranges[symbol]['trade_risk'] =  user_risk / ranges[symbol]['range']
        
        # cierra conexion con metatrader 5
        MT5Api.shutdown()
        
        while True:
            # Salir del bucle si no quedan símbolos en el diccionario de rangos
            if not ranges:
                print("No hay mas símbolos por analizar.")
                break
            
            if not self.is_in_market_hours():
                print("Finalizo el horario de mercado.")
                break
            
            # Espera que el minuto termine para iniciar
            self.sleep_to_next_minute()
            
            print("Símbolos por analizar ", str(symbols))
            
            # Volver a calcular el tiempo actual
            current_time = datetime.now().astimezone(pytz.utc)
            
            # Copia del diccionario de rangos para poder eliminar símbolos que alcancen el profit
            copy_ranges = ranges.copy()
            
            # Abre conexion con metatrader 5
            MT5Api.initialize()
            
            for symbol, data in copy_ranges.items():
                # Se obtienen los deals realizados desde la apertura
                deals = MT5Api.get_history_deals(start_time, current_time, symbol)
                if deals:
                    # En caso de hallar, se revisa si tuvo un profit positivo (significa que alcanzo el take profit)
                    last_deal = deals[-1]
                    if last_deal.profit > 0:
                        # Se alcanzó la meta, eliminar el símbolo de la lista
                        del ranges[symbol]
                        break
                # Se obtienen las posiciones abiertas
                positions = MT5Api.get_positions(symbol)
                type = None
                if positions:
                    # En caso de exisitr almenos una posicion abierta obtiene el tipo de esta
                    type = positions[-1].type
                penultimate_bar = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1, 1)
                close = penultimate_bar['close'][0]
                if close < data['low'] and (type == 0 or type is None):
                    # Se agrega el tipo de orden
                    data['type'] = 'sell'
                    # Enviar datos de venta a la cola de comunicación
                    hedge_strategy_queue.put(data)
                    
                elif close > data['high'] and (type == 1 or type is None):
                    # Se agrega el tipo de orden
                    data['type']= 'buy'
                    # Enviar datos de compra a la cola de comunicación
                    hedge_strategy_queue.put(data)
            
            # cierra conexion con metatrader 5
            MT5Api.shutdown()
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
    
    def sleep_to_next_minute(self):
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

    def sleep_to_next_market_opening(self):
        """
        Espera hasta la próxima apertura del mercado.

        La función calcula el tiempo restante hasta la próxima apertura del mercado en el día actual
        y pausa la ejecución del programa durante ese tiempo, a menos que la apertura ya haya ocurrido
        y el tiempo actual se encuentra fuera del horario de mercado, en cuyo caso no se realizará ninguna pausa.

        Args:
            None

        Returns:
            None
        """
        
        # Obtener la hora actual en UTC
        current_time = datetime.now(pytz.utc)
        
        # Crear un objeto datetime para la hora de apertura del mercado hoy
        market_open_today = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'])
        
        # Calcular la cantidad de segundos que faltan hasta la apertura
        seconds = (market_open_today - current_time).total_seconds()
        
        # Si segundos es positivo, significa que la apertura del día de hoy aún no ha ocurrido, por lo tanto, esperamos
        if seconds > 0:
            time.sleep(seconds)
        elif not self.is_in_market_hours():
            market_open_tomorrow = market_open_today + timedelta(days=1)
            # Calcular la cantidad de segundos que faltan hasta la apertura
            seconds = (market_open_tomorrow - current_time).total_seconds()
            time.sleep(seconds)        
    
    def is_in_market_hours(self):
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
            return False

#endregion
        
    def start(self):
        """
        Inicia el programa principal.

        Esta función se encarga de comenzar la ejecución del programa principal. 
        Realiza las siguientes tareas:
        1. Obtiene el horario comercial del día actual.
        2. Verifica si el horario comercial está disponible.
        3. Si está disponible, crea colas de comunicación y procesos para realizar operaciones.

        Returns:
            None
        """
        while True:
            business_hours_utc = self._get_business_hours_today()
            if business_hours_utc:
                # Revisa si aun falta tiempo para la apertura de mercado y espera
                self.sleep_to_next_market_opening()
                
                # Abre mt5 y espera 4 segundos
                MT5Api.initialize(sleep=4)
                
                # Establece los symbolos
                symbols= ["US30.cash"]
                
                # Establece el riesgo por operacion
                user_risk = 100 
                
                # Crea el administrador
                manager = multiprocessing.Manager()
                
                # Se crean las colas de comunicacion
                hedge_strategy_queue = manager.Queue()
                send_order_queue = manager.Queue()
                
                # Se crean los procesos
                hedge_strategy_process = multiprocessing.Process(target=self._hedging_strategy_every_minute, args=(user_risk, symbols, hedge_strategy_queue,))
                prepare_hedge_order_process = multiprocessing.Process(target=self._prepare_hedge_order, args=(hedge_strategy_queue, send_order_queue,))
                send_order_process = multiprocessing.Process(target=self._send_order, args=(send_order_queue,))
                
                # Se inician los procesos
                hedge_strategy_process.start()
                prepare_hedge_order_process.start()
                send_order_process.start()
                
                # Espera a que termine el proceso
                hedge_strategy_process.join()
                
                # Termina los procesos
                prepare_hedge_order_process.terminate()
                send_order_process.terminate()
                
                # Cierra conexion con metatrader
                MT5Api.shutdown(sleep=2)
            
            # Al finalizar la ejecución del programa o si no hay mercado hoy, 
            # se pausará el programa hasta el próximo día laborable para volver a comprobar.
            self.sleep_to_next_market_opening()
                
                
            

