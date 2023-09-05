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
        self._alpaca_api = AlpacaApi()
            
    def _get_business_hours_today(self):
        """
        Obtiene las horas de apertura y cierre del mercado para el día de hoy.

        Returns:
            dict: Un diccionario con las horas de apertura y cierre ajustadas a mt5. 
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
            # Convierte el open y close al tiempo manejado en mt5
            business_hours['open'] = calendar_today[0].open.astimezone(pytz.utc)
            business_hours['close'] = calendar_today[0].close.astimezone(pytz.utc)
            return business_hours
        return business_hours   
    
    def _send_order(self, send_order_queue:Queue):
        # Inicializa metatrader 5
        MT5Api.initialize()
        while True:
            order: Dict[str, Any] = send_order_queue.get()
            MT5Api.send_order(**order)
        
    def _prepare_hedge_order(self, hedge_strategy_queue:Queue, send_order_queue:Queue):
        # Inicializa metatrader 5
        MT5Api.initialize()
        while True:
            data = hedge_strategy_queue.get()
            # Pre establece los datos de la orden que se enviara
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
            
            # Consultamos el numero de ordenes realizadas para el symbolo
            start_time = datetime.now().replace(hour=9,minute=0,second=0,microsecond=0).astimezone(pytz.utc)
            current_time = datetime.now().astimezone(pytz.utc)
            orders_placed = MT5Api.get_history_orders(start_time, current_time, order['symbol'])
            # size = 2^(orders_placed) cuando orders_placed = 0 size = 1, 
            # cuando orders_placed = 1 size = 2, cuando orders_placed = 2 size = 4 ...
            size = 2 ** (len(orders_placed))
            order['volume'] = 0.01 * size
            # El tipo de compra que se realizara
            
            # Se establece los demas campos de la orden
            if data['type'] == 'buy':
                order['order_type'] = OrderType.MARKET_BUY
                order['take_profit'] = data['high'] + (data['size']*2)
                order['stop_loss'] = data['low']
            else:
                order['order_type'] = OrderType.MARKET_SELL
                order['take_profit'] = data['low'] - (data['size']*2)
                order['stop_loss'] = data['high']
                
            order['comment'] = "Mt5_bot: Hedge -> " + str(size)
            
            # Se envia la orden por la cola de comunicación
            send_order_queue.put(order)    
            
    def _hedge_strategy(self, symbols: List[str], hedge_strategy_queue: Queue):
        """
        Función para verificar los símbolos y tomar decisiones de compra/venta para la estrategia .

        Esta función se encarga de verificar los símbolos proporcionados y tomar decisiones
        de compra o venta basadas en ciertas condiciones. Se ejecuta en un bucle infinito.

        Args:
            self: La instancia de la clase que llama a esta función.
            symbols (List[str]): Una lista de símbolos a verificar.
            hedge_strategy_queue (Queue): Cola de comunicación para enviar datos de compra/venta.

        Returns:
            None
        """
        # Inicializa metatrader 5
        MT5Api.initialize()
        # Obtener la hora actual en la zona horaria de Nueva York
        ny_timezone = pytz.timezone('America/New_York')
        current_time_in_ny = datetime.now(ny_timezone)
        # Establecer el horario de inicio y finalización en Nueva York
        start_time = current_time_in_ny.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = current_time_in_ny.replace(hour=9, minute=30, second=0, microsecond=0)
        # Convierte las horas de inicio y finalización a UTC
        start_time = start_time.astimezone(pytz.utc)
        end_time = end_time.astimezone(pytz.utc)
        
        # Diccionario para almacenar rangos de precios de símbolos
        ranges: Dict[str, Dict[str, float]] = {}
        
        # Obtener el máximo y mínimo en el rango de precio para cada símbolo
        for symbol in symbols:
            rates_in_range = MT5Api.get_rates_range(symbol, TimeFrame.MINUTE_1, start_time, end_time)
            ranges[symbol] = {}
            ranges[symbol]['high'] = np.max(rates_in_range['high'])
            ranges[symbol]['low'] = np.min(rates_in_range['low'])
            ranges[symbol]['size'] = ranges[symbol]['high'] - ranges[symbol]['low']
        
        while True:
            # Salir del bucle si no quedan símbolos en el diccionario de rangos
            if not ranges:
                break
            
            # Esperar hasta que termine el minuto actual para tomar una decision
            current_time = datetime.now()
            next_minute = current_time.replace(second=1, microsecond=0) + timedelta(minutes=1)
            segundos_faltantes = (next_minute - current_time).total_seconds()
            time.sleep(segundos_faltantes)
            
            # Volver a calcular el tiempo actual
            current_time = datetime.now().astimezone(pytz.utc)
            
            # Copia del diccionario de rangos para poder eliminar símbolos
            copy_ranges = ranges.copy()
            
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
                close = penultimate_bar['close']
                if close < data['low'] and (type == 0 or type is None):
                    data_to_send = {
                        'symbol': symbol,
                        'high': data['high'],
                        'low': data['low'],
                        'size': data['size'],
                        'type': 'sell',
                    }
                    # Enviar datos de venta a la cola de comunicación
                    hedge_strategy_queue.put(data_to_send)
                elif close > data['high'] and (type == 1 or type is None):
                    data_to_send = {
                        'symbol': symbol,
                        'threshold': data['high'],
                        'size': data['size'],
                        'type': 'buy',
                    }
                    # Enviar datos de compra a la cola de comunicación
                    hedge_strategy_queue.put(data_to_send)
            
    def _get_seconds_before_next_start()->int:
        return
        
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
        business_hours = self._get_business_hours_today()
        if True:
            # Establece los symbolos
            symbols= ["US30.cash"]
            
            # Crea el administrador
            manager = multiprocessing.Manager()
            
            # Se crean las colas de comunicacion
            hedge_strategy_queue = manager.Queue()
            send_order_queue = manager.Queue()
            
            # Se crean los procesos
            hedge_strategy_process = multiprocessing.Process(target=self._hedge_strategy, args=(symbols, hedge_strategy_queue,))
            send_order_process = multiprocessing.Process(target=self._send_order, args=(send_order_queue,))
            prepare_hedge_order_process = multiprocessing.Process(target=self._prepare_hedge_order, args=(hedge_strategy_queue, send_order_queue,))

            # Se inician los procesos
            hedge_strategy_process.start()
            prepare_hedge_order_process.start()
            send_order_process.start
            
            # Espera a que termine el proceso
            hedge_strategy_process.join()
            
            # Termina los procesos
            prepare_hedge_order_process.terminate()
            send_order_process.terminate()
            

