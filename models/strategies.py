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

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz, time

# Importaciones de indicatores técnicos
import pandas_ta as ta
from .technical_indicators import HeikenAshi, vRenko

#endregion

class StateTrend:
    """
    Clase que representa estados de tendencia.

    Atributos:
    - UNASSIGNED: Estado no asignado, con valor 0.
    - BULLISH: Estado alcista, con valor 1.
    - BEARISH: Estado bajista, con valor -1.
    """

    UNASSIGNED = 0
    BULLISH = 1
    BEARISH = -1

class Multipliers:
    N1 = 2
    N2 = 1.5
    N3 = 1.7
    N4 = 1.5
    

class HedgeTrailing2:
    def __init__(self, symbol: str, volume_size: int = 1) -> None:
        # Indica si el programa debe seguir activo
        self.is_on = None
        
        # Lista de symbolos para administar dentro de la estrategia
        self.symbol = symbol
        
        # Variable para indicar el estado del supertrend
        self.trend_state = StateTrend.UNASSIGNED
        
        # Variable que contiene informaciond el symbolo para la estrategia
        self.symbol_data = {}
        
        # El numero que identificara las ordenes de esta estrategia
        self.magic = 63
                
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
    
    #endregion
    
    #region Manage Profit
    
    def _manage_positions(self):
        """
        Esta función administra las posiciones en el contexto de trading.
        """
        
        # Envía un mensaje de inicio al canal de Telegram
        print("HedgeTrailing: Iniciando administrador de posiciones")
        
        # Horario de cierre
        current_time = datetime.now(pytz.utc)   # Hora actual
        market_close = current_time.replace(hour=self._market_closed_time['hour'], minute=self._market_closed_time['minute'], second=0)
        
        # Comienza el administrador de posiciones
        # Variables del rango
        high = self.symbol_data['high']
        low = self.symbol_data['low']
        range = self.symbol_data['range']
        number_trailing = 1
        in_hedge = False
        trailing_stop = False
        
        while self.is_on.value:
            # Se obtienen las posiciones y la información del símbolo de MetaTrader 5
            while True:
                positions = MT5Api.get_positions(magic=self.magic)
                info = MT5Api.get_symbol_info(self.symbol)
                if positions is not None and info is not None:
                    break
            
            current_time = datetime.now(pytz.utc)   # Hora actual
            if current_time > market_close:
                MT5Api.send_close_all_position()
                if not positions:
                    self.is_on.value = False
                continue
            
            # Reinicia las variables en caso de que ya no haya posiciones abiertas
            if not positions:
                pre_closing_time = current_time + timedelta(hours=1, minutes=0)    # Hora para cerrar el programa antes
                # Si el programa no se encuentra aun horario de pre cierre puede seguir comprando
                if pre_closing_time > market_close:
                    self.is_on.value = False
                    continue

                number_trailing = 1
                in_hedge = False
                trailing_stop = False
                continue
            
            current_price = info.bid
                        
            if not trailing_stop and positions:
                # Determina el número de lotes y el tipo de última posición
                number_batchs = int(positions[-1].comment)
                type = positions[-1].type
                
                if number_batchs < 3:
                    if type == OrderType.MARKET_BUY:
                        limit_price = high + range
                        if current_price >= limit_price:
                            # Vende la mitad de las posiciones abiertas
                            completed = True
                            for position in positions:
                                result = MT5Api.send_sell_partial_order(self.symbol, (position.volume/2), position.ticket, "0")
                                completed = completed and result
                            if not completed:
                                continue
                            trailing_stop = True
                    else:
                        limit_price = low - range
                        if current_price <= limit_price:
                            # Vende la mitad de las posiciones abiertas
                            completed = True
                            for position in positions:
                                result = MT5Api.send_sell_partial_order(self.symbol, (position.volume/2), position.ticket, "0")
                                completed = completed and result
                            if not completed:
                                continue
                            trailing_stop = True
                else:
                    in_hedge = True
                    if type == OrderType.MARKET_BUY:
                        limit_price = high + (range * 0.625)
                        if current_price >= limit_price:
                            # Cierra posiciones con pérdidas
                            completed = True
                            for position in positions:
                                if position.profit < 0:
                                    result = MT5Api.send_close_position(self.symbol, position.ticket)
                                    completed = completed and result
                            if not completed:
                                continue
                            trailing_stop = True
                    else:
                        limit_price = low - (range * 0.625)
                        if current_price <= limit_price:
                            # Cierra posiciones con pérdidas
                            completed = True
                            for position in positions:
                                if position.profit < 0:
                                    result = MT5Api.send_close_position(self.symbol, position.ticket)
                                    completed = completed and result
                            if not completed:
                                continue
                            trailing_stop = True
            
            if trailing_stop:
                type = positions[-1].type
                if in_hedge:
                    if type == OrderType.MARKET_BUY:
                        stop_loss = high + (range * 0.625)                 
                        # Cierra todas las posiciones si el precio cae por debajo del stop loss
                        if current_price < stop_loss:
                            MT5Api.send_close_all_position()
                    else:
                        stop_loss = low - (range * 0.625)
                        # Cierra todas las posiciones si el precio cae por debajo del stop loss
                        if current_price > stop_loss:
                            MT5Api.send_close_all_position()
                            
                elif number_trailing < 3:
                    # Establece el stop loss móvil si se activa el trailing stop
                    trailing_range = (range * (number_trailing/2))
                    next_trailing_range = (range * ((number_trailing + 2)/2))
                    if type == OrderType.MARKET_BUY:
                        stop_loss = high + trailing_range             
                        # Cierra todas las posiciones si el precio cae por debajo del stop loss
                        if current_price <= stop_loss:
                            MT5Api.send_close_all_position()
                        elif current_price > next_trailing_range:
                            number_trailing += 1
                    
                    else:
                        stop_loss = low - trailing_range
                        # Cierra todas las posici24ones si el precio cae por debajo del stop loss
                        if current_price >= stop_loss:
                            MT5Api.send_close_all_position()
                        elif current_price < next_trailing_range:
                            number_trailing += 1
                
                else:
                    if type == OrderType.MARKET_BUY and self.trend_state.value == StateTrend.BEARISH:
                        MT5Api.send_close_all_position()
                    elif type == OrderType.MARKET_SELL and self.trend_state.value == StateTrend.BULLISH:
                        MT5Api.send_close_all_position()
            
            if in_hedge:
                # Realiza acciones de hedge si se encuentra en modo hedge
                type = positions[-1].type
                if type == OrderType.MARKET_BUY:
                    limit_price = high + range
                    if current_price >= limit_price:
                        # Vende la mitad de las posiciones abiertas
                        completed = True
                        for position in positions:
                            result = MT5Api.send_sell_partial_order(self.symbol, (position.volume/2), position.ticket, "0")
                            completed = completed and result
                        if not completed:
                            continue
                        in_hedge = False
                else:
                    limit_price = low - range
                    if current_price <= limit_price:
                        # Vende la mitad de las posiciones abiertas
                        completed = True
                        for position in positions:
                            result = MT5Api.send_sell_partial_order(self.symbol, (position.volume/2), position.ticket, "0")
                            completed = completed and result
                        if not completed:
                            continue
                        in_hedge = False

    
    #endregion                 
    
    #region HedgeTrailing strategy 
    def _preparing_symbols_data(self):
        """
        Prepara la data que se usara en la estrategia de HedgeTrailing.
        """
        print("HedgeTrailing: Preparando la data...")
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
        range = abs(high - low)
                
        if self.volume_size is None:
            self.volume_size = info.volume_min
  
        symbol_data= {
            'symbol': self.symbol,
            'digits': digits,
            'high': high,
            'low': low,
            'range': range,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
        }
        
        print(symbol_data)
            
            
        # Actualiza la variable compartida
        self.symbol_data = symbol_data
    
    def _hedge_buyer(self):
        """
        Prepara órdenes para ser enviadas a MetaTrader 5 en función de los datos y las condicionales establecidas.
        """
        print("HedgeTrailing: Iniciando administrador de compras")
        
        # Variables del rango
        high = self.symbol_data['high']
        low = self.symbol_data['low']
        range = self.symbol_data['range']
        
        # Condicionales de estados
        false_rupture= False
        rupture = False
        number_hedge = 1
        
        while self.is_on.value:
            # Se obtiene las variables de mt5
            while True:
                info = MT5Api.get_symbol_info(self.symbol)
                positions = MT5Api.get_positions(magic=self.magic)
                last_bar = MT5Api.get_last_bar(self.symbol)
                finished_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 1)
                if info is not None and positions is not None and last_bar is not None and finished_bar is not None:
                    break
            
            current_price = last_bar['close']
                                         
            if len(positions) == 0:
                # Variables del rango
                high = self.symbol_data['high']
                low = self.symbol_data['low']
                range = self.symbol_data['range']
                
                # Se reinicia los estados
                false_rupture = False
                rupture = False
                number_hedge = 1
                
                # Establece las variables
                open = last_bar['open']
                # Comprueba si la apertura de la barra esta en el rango
                if open <= high and open >= low:
                    # Comprueba si el cierre (precio actual de la barra en formacion) esta fuera del rango
                    send_order = False
                    buyback_range = (range * 0.2)
                    
                    # Comprueba si el precio supera el rango
                    
                    if current_price > high:
                        send_order = True
                        order_type = OrderType.MARKET_BUY
                        range_limit = high + buyback_range
                        
                    elif current_price < low:
                        send_order = True
                        order_type = OrderType.MARKET_SELL
                        range_limit = low - buyback_range
                        
                    # Envia la primera orden
                    if send_order: 
                        result =MT5Api.send_order(
                            symbol= self.symbol, 
                            order_type= order_type, 
                            volume=self.volume_size,
                            magic=self.magic,
                            comment= "1"
                        )
                        
                        if result:
                            # Espera a que la vela termine y la obtiene
                            rupture = True
                            self._sleep_to_next_minute()
                            finished_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 1)
                            send_buyback = False
                            
                            # Si no se logro obtener la ultima barra continua
                            if finished_bar is None:
                                continue
                            
                            close = finished_bar['close']
                            
                            # Establece el estado de la estrategia
                            if order_type == OrderType.MARKET_BUY:
                                if close < high:
                                    false_rupture = True
                                    continue
                                elif close < range_limit:
                                    send_buyback = True
                            else:
                                if close > low:
                                    false_rupture = True
                                    continue
                                elif close > range_limit:
                                    send_buyback = True
                            
                            # Se hace recompra en caso de que la barra se encuentre en el rango limite
                            if send_buyback:
                                result =MT5Api.send_order(
                                    symbol= self.symbol, 
                                    order_type= order_type, 
                                    volume=self.volume_size,
                                    magic=self.magic,
                                    comment= "2"
                                )
                                continue
                
            if false_rupture and len(positions) > 0:
                # Establece las variables
                open = finished_bar['open']
                close = finished_bar['close']
                last_type = positions[-1].type
                send_buyback = False
                buyback_range = (range * 0.2)
                # Verifica si despues del falso rompimiento vuelve a existir una ruptura en la misma direccion
                if last_type == OrderType.MARKET_BUY:
                    if open <= high and close > high:
                        range_limit = high + buyback_range
                        if close < range_limit:
                            send_buyback = True
                elif last_type == OrderType.MARKET_SELL:
                    if open >= low and close < low:
                        range_limit = low - buyback_range
                        if close > range_limit:
                            send_buyback = True
                
                if send_buyback:
                    result =MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= last_type, 
                        volume=self.volume_size,
                        magic=self.magic,
                        comment= "2"
                    )
                    if result:
                        false_rupture = False
                        continue
            
            if rupture and len(positions) > 0:
                # Establece las variables
                open = last_bar['open']
                current_price = last_bar['close']
                last_type = positions[-1].type
                send_order = False
                # Verifica si despues del falso rompimiento vuelve a existir una ruptura en la misma direccion
                if last_type == OrderType.MARKET_BUY:
                    if open >= low and current_price < low:
                        order_type = OrderType.MARKET_SELL
                        send_order = True
                elif last_type == OrderType.MARKET_SELL:
                    if open <= high and current_price > high:
                        order_type =  OrderType.MARKET_BUY
                        send_order = True
                
                if send_order:
                    multiplier = getattr(Multipliers, "N" + str(number_hedge), 1.5)
                    last_batch = int(positions[-1].comment)
                    next_batch = last_batch * multiplier
                    next_volume = self.volume_size * next_batch
                    result =MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= order_type, 
                        volume=next_volume,
                        magic=self.magic,
                        comment= str(next_batch)
                    )
                    if result == True:
                        number_hedge += 1
                        if number_hedge == 4:
                            high = high - (range * 0.2)
                            low = low + (range * 0.2)
   
                        false_rupture = False
                        continue
       
    def _get_counter_volume(self, positions: List[TradePosition])->float:
        
        buys = [position for position in positions if position.type == OrderType.MARKET_BUY]
        sells = [position for position in positions if position.type == OrderType.MARKET_SELL]

        total_buys = sum(position.volume for position in buys)
        total_sells = sum(position.volume for position in sells)

        difference = abs(total_sells - total_buys)
        
        return difference

    def _update_trend(self):
        """
        Actualiza el estado de la tendencia utilizando el indicador SuperTrend.

        Este método actualiza continuamente el estado de la tendencia utilizando el indicador SuperTrend
        con los parámetros atr_period y multiplier. Monitorea las tasas de precios en un marco de tiempo
        de 1 minuto y ajusta el estado de la tendencia en consecuencia.

        Retorna:
            None
        """
        print("HedgeTrailing: Iniciando administrador de tendencia")
        atr_period = 5  # Período para el cálculo del ATR
        multiplier = 2  # Multiplicador para el cálculo del SuperTrend
        first_time = True

        # Obtener los datos de la tasa de 1 minuto iniciales
        while True:
            minute_1_rates = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 10080)
            if minute_1_rates is not None:
                break

        while self.is_on.value:
            if not first_time:
                self._sleep_to_next_minute()
                
                # Obtener la última barra de 1 minuto
                minute_1_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 1)
                
                # En caso de que exista un error, intentara actualizar todo el trend
                if minute_1_bar is None:
                    while True:
                        minute_1_rates = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 10080)
                        if minute_1_rates is not None:
                            break
                else:
                    minute_1_rates = np.append(minute_1_rates, minute_1_bar,)

            # Crear un DataFrame con los datos de la tasa de 1 minuto
            df = pd.DataFrame(minute_1_rates)
            
            # Calcular el indicador SuperTrend y agregarlo al DataFrame
            df['direction'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
            direction = int(df.iloc[-1]['direction'])

            # Actualizar el estado de la tendencia si ha cambiado
            if direction != self.trend_state.value:
                self.trend_state.value = direction
                print(f"HedgeTrailing: Actualizando tendencia: {direction}")

    #endregion
    
    #region start
    def start(self):
        """
        Inicia la estrategia de HedgeTrailing trading para los símbolos especificados.
        """

        print("HedgeTrailing: Iniciando estrategia...")
        
        while True:
            positions = MT5Api.get_positions(magic=self.magic)
            if positions is not None:
                break
        
        # Se crea las variables compartidas
        manager = multiprocessing.Manager()
        self.is_on = manager.Value("b", True)
        self.trend_state = manager.Value("i", StateTrend.UNASSIGNED)

        self._preparing_symbols_data()
        
        # Crea los procesos y los inicia
        update_trend_process = multiprocessing.Process(target=self._update_trend)
        update_trend_process.start()
        manage_positions_process = multiprocessing.Process(target= self._manage_positions)
        manage_positions_process.start()
        hedge_buyer_process = multiprocessing.Process(target=self._hedge_buyer)
        hedge_buyer_process.start()
        
        # Espera a que termine para continuar
        manage_positions_process.join()
                    
        # Fin del ciclo
        print("HedgeTrailing: Finalizando estrategia...")
          
    #endregion