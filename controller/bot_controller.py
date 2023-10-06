#region Descripción:
# Componente central de mt5_bot, su función principal es administrar múltiples estrategias de trading de forma 
# concurrente utilizando el módulo de multiprocesamiento de Python. Este controlador permite la ejecución 
# simultánea y el monitoreo de diferentes estrategias en cuentas de trading separadas en la plataforma MT5.
#endregion

#region Importaciones

# Importaciones necesarias para definir tipos de datos
from typing import List

# Importacion de los clientes de las apis para hacer solicitudes
from models.alpaca.client import AlpacaApi
from models.mt5.client import MT5Api

# Importacion de las estrategias a usar en controlador
from models.strategies import HardHedgeTrading

# Para trabajo en paralelo
import multiprocessing
from multiprocessing.managers import ValueProxy

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime
import pytz
import time

#endregion

class BotController:
    def __init__(self) -> None:
        # Estos horarios estan en utc
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':19, 'minute':55}
        self._alpaca_api = AlpacaApi()

    #region Positions Management
    def manage_positions(self, is_on:ValueProxy[bool], strategy: object):
        """
        Administra las posiciones abiertas según las estrategias proporcionadas.

        Este método revisa las estrategias proporcionadas y gestiona las posiciones abiertas de acuerdo con ellas.
        
        Args:
            strategies (List[object]): Una lista de objetos que representan las estrategias a seguir.

        Returns:
            None
        """
        print("Iniciando administrador de posiciones abiertas.")
        while is_on.value:
            account_info = MT5Api.get_account_info()
            margin_free = account_info.margin_free
            profit = account_info.profit
            balance = account_info.balance
            if profit > 1:
                MT5Api.send_close_all_position()
            else:
                # Obtiene las posiciones para la estrategia con su identificador magic
                positions = MT5Api.get_positions(magic=strategy.magic)
                # Llama al método 'manage_positions' de la estrategia para gestionar las posiciones
                strategy.manage_positions(positions)
            
        MT5Api.send_close_all_position()
            
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
    
    def sleep_until_market_closes(self,):
        """Espera hasta el cierre del mercado.

        Returns:
            None
        """
    
        # Obtener la hora actual en UTC
        current_time = datetime.now(pytz.utc)
                
        market_close = current_time.replace(hour=self._market_closed_time['hour'], minute=self._market_closed_time['minute'], second=0)

        # Calcular la cantidad de segundos que faltan hasta la apertura
        seconds_until_close = (market_close - current_time).total_seconds()
        
        if seconds_until_close > 0:
            time.sleep(seconds_until_close)
        
        # Obtener la hora actual en UTC después de esperar
        current_time = datetime.now(pytz.utc)
        print("Hora actual utc: ", current_time)
        print("El Mercado esta cerrado")
    
    
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
            
            self._sleep_to_next_market_opening(False)
                
            # Establece una variable globarl compartida que le indicara al programa cuando parar
            is_on=manager.Value("b", True)
            
            #region creación de estrategias
                        
            #region HardHedge
            # Se crea el objeto de la estrategia HardHedge 
            hard_hedge_symbols = manager.list(symbols)
            hard_hedge_trading = HardHedgeTrading(
                symbol_data= manager.dict({}), 
                symbols= hard_hedge_symbols, 
                is_on=is_on, 
                volume_size= None,
                max_hedge= 10
            )
            hard_hedge_trading._preparing_symbols_data()
            
            # Se crea el proceso que administra la estrategia
            hard_hedge_process = multiprocessing.Process(target=hard_hedge_trading.start)
            hard_hedge_process.start()
            #endregion
            
            #endregion
            
                            
            # Inicia el proceso que administrara la estrategia
            manage_positions_process = multiprocessing.Process(target=self.manage_positions, args=(is_on, hard_hedge_trading,))
            manage_positions_process.start()
            
            self.sleep_until_market_closes()
            
            # Termina las estrategias
            is_on.value = False
                
            # Se espera a que terminen los procesos de las estrategias, se debe agregar manualmente
            manage_positions_process.join()   

    #endregion
