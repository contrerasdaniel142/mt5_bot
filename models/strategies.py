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
    

class HedgeTrailing:
    def __init__(self, symbol: str) -> None:
        # Indica si el programa debe seguir activo
        self.is_on = None
        
        # Lista de symbolos para administar dentro de la estrategia
        self.symbol = symbol
        
        # Variable que contiene informaciond el symbolo para la estrategia
        self.symbol_data = {}
        
        # Numero de desfase
        self.number_outdated = 0
        
        # El numero que identificara las ordenes de esta estrategia
        self.magic = 63
                                
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
        
        # Comienza el administrador de posiciones
        # Variables del rango
        high = self.symbol_data['high_outdated'].value
        low = self.symbol_data['low_outdated'].value
        range = self.symbol_data['range']
        hedge_range = (range * 0.625)
        number_trailing = 1
        in_hedge = False
        trailing_stop = False
        
        while self.is_on.value:
            # Se obtienen las posiciones y la información del símbolo de MetaTrader 5
            while True:
                positions = MT5Api.get_positions(magic=self.magic, symbol=self.symbol)
                info = MT5Api.get_symbol_info(self.symbol)
                if positions is not None and info is not None:
                    break
                        
            # Reinicia las variables en caso de que ya no haya posiciones abiertas
            if not positions:                
                number_trailing = 1
                in_hedge = False
                trailing_stop = False
                continue
            
            current_price = info.bid
            high = self.symbol_data['high_outdated'].value
            low = self.symbol_data['low_outdated'].value
            
            if high == 0 or low == 0:
                continue
                        
            if not trailing_stop and positions:
                # Determina el número de lotes y el tipo de última posición
                number_batchs = int(positions[-1].comment)
                type = positions[-1].type
                
                if number_batchs == 1 or number_batchs == 2:
                    if type == OrderType.MARKET_BUY:
                        limit_price = high + range
                        if current_price >= limit_price:
                            # Vende la mitad de las posiciones abiertas
                            completed = True
                            for position in positions:
                                new_volume = round((position.volume/2), self.symbol_data['digits'])
                                result = MT5Api.send_sell_partial_order(position, new_volume, "0")
                                completed = completed and result
                            if not completed:
                                continue
                            print("HedgeTrailing: Comenzando trailing stop")
                            trailing_stop = True
                    else:
                        limit_price = low - range
                        if current_price <= limit_price:
                            # Vende la mitad de las posiciones abiertas
                            completed = True
                            for position in positions:
                                new_volume = round((position.volume/2), self.symbol_data['digits'])
                                result = MT5Api.send_sell_partial_order(position, new_volume, "0")
                                completed = completed and result
                            if not completed:
                                continue
                            print("HedgeTrailing: Comenzando trailing stop")
                            trailing_stop = True
                else:
                    if type == OrderType.MARKET_BUY:
                        limit_price = high + hedge_range
                        if current_price > limit_price:
                            # Cierra posiciones con pérdidas
                            completed = True
                            for position in positions:
                                if position.profit < 0:
                                    result = MT5Api.send_close_position(position)
                                    completed = completed and result
                            if not completed:
                                continue
                            print("HedgeTrailing: Comenzando trailing stop")
                            in_hedge = True
                            trailing_stop = True
                    else:
                        limit_price = low - hedge_range
                        if current_price < limit_price:
                            # Cierra posiciones con pérdidas
                            completed = True
                            for position in positions:
                                if position.profit < 0:
                                    result = MT5Api.send_close_position(position)
                                    completed = completed and result
                            if not completed:
                                continue
                            print("HedgeTrailing: Comenzando trailing stop")
                            in_hedge = True
                            trailing_stop = True
            
            if trailing_stop and positions:
                type = positions[-1].type
                # Establece el stop loss móvil si se activa el trailing stop
                trailing_range = (range * (number_trailing/2))
                next_trailing_range = (range * ((number_trailing + 1)/2))
                next_stop_price_range = (range * ((number_trailing + 2)/2))
                if type == OrderType.MARKET_BUY:
                    stop_loss = high + trailing_range
                    next_stop_loss = high + next_trailing_range
                    next_stop_price = high + next_stop_price_range
                    # Cierra todas las posiciones si el precio cae por debajo del stop loss
                    if current_price <= stop_loss:
                        print(f"HedgeTrailing: stop loss alcanzado {stop_loss}")
                        MT5Api.send_close_all_position()
                    elif current_price >= next_stop_price:
                        print(f"HedgeTrailing: stop loss en {next_stop_loss}")
                        number_trailing += 1
                        
                
                else:
                    stop_loss = low - trailing_range
                    next_stop_loss = low - next_trailing_range
                    next_stop_price = low - next_stop_price_range
                    # Cierra todas las posiciones si el precio cae por debajo del stop loss
                    if current_price >= stop_loss:
                        print(f"HedgeTrailing: stop loss alcanzado {stop_loss}")
                        MT5Api.send_close_all_position()
                    elif current_price <= next_stop_price:
                        print(f"HedgeTrailing: stop loss en {next_stop_loss}")
                        number_trailing += 1
                
            if in_hedge and positions:
                type = positions[-1].type             
                # Realiza acciones de hedge si se encuentra en modo hedge
                if type == OrderType.MARKET_BUY:
                    limit_price = high + range
                    if current_price >= limit_price:
                        # Vende la mitad de las posiciones abiertas
                        completed = True
                        for position in positions:
                            new_volume = round((position.volume/2), self.symbol_data['digits'])
                            result = MT5Api.send_sell_partial_order(position, new_volume, "0")
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
                            new_volume = round((position.volume/2), self.symbol_data['digits'])
                            result = MT5Api.send_sell_partial_order(position, new_volume, "0")
                            completed = completed and result
                        if not completed:
                            continue
                        in_hedge = False

    
    #endregion                 
    
    #region HedgeTrailing strategy 
        
    def _hedge_buyer(self):
        """
        Prepara órdenes para ser enviadas a MetaTrader 5 en función de los datos y las condicionales establecidas.
        """
        print("HedgeTrailing: Iniciando administrador de compras")
        
        current_time = datetime.now(pytz.utc)   # Hora actual
        market_close = current_time.replace(hour=self._market_closed_time['hour'], minute=self._market_closed_time['minute'], second=0)
        
        
        # Variables del rango
        high = self.symbol_data['high_outdated'].value
        low = self.symbol_data['low_outdated'].value
        range = self.symbol_data['range']
        volume = self.symbol_data['volume']
        
        # Condicionales de estados
        false_rupture= False
        rupture = False
        counter_hedge = False
        
        while self.is_on.value:
            # Se obtiene las variables de mt5
            while True:
                info = MT5Api.get_symbol_info(self.symbol)
                positions = MT5Api.get_positions(magic=self.magic)
                last_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 0, 1)
                finished_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 1)
                if info is not None and positions is not None and last_bar is not None and finished_bar is not None:
                    break
            
            current_time = datetime.now(pytz.utc)   # Hora actual
            if current_time > market_close:
                MT5Api.send_close_all_position()
                continue 
                                      
            if len(positions) == 0:
                # Hora para cerrar el programa antes
                pre_closing_time = current_time + timedelta(hours=1, minutes=0)
                # Si el programa no se encuentra aun horario de pre cierre puede seguir comprando
                if pre_closing_time > market_close:
                    self.is_on.value = False
                    continue
                                
                # Se reinicia los estados
                false_rupture = False
                rupture = False
                counter_hedge = False       
                # Establece las variables
                current_price = last_bar['close']
                open = last_bar['open']
                
                # Encuentra el desfase
                self._check_outdated(self.symbol_data['high'], self.symbol_data['low'], range, last_bar['open'])
                
                # Si el desfase esta dentro del rango se calcula el high y low
                if 6 > self.number_outdated.value or self.number_outdated.value < -6:
                    outdated = round((range * self.number_outdated.value), self.symbol_data['digits'])
                    new_high = self.symbol_data['high'] + outdated
                    new_low = self.symbol_data['low'] + outdated
                    if new_high != high:
                        print(f"HedgeTrailing: high establecido en {new_high}")
                        high = new_high
                        self.symbol_data['high_outdated'].value = new_high
                    if new_low != low:
                        print(f"HedgeTrailing: low establecido en {new_low}")
                        low = new_low
                        self.symbol_data['low_outdated'].value = new_low
                
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
                        print("HedgeTrailing: Primer trade")
                        result =MT5Api.send_order(
                            symbol= self.symbol, 
                            order_type= order_type, 
                            volume=volume,
                            magic=self.magic,
                            comment= "1"
                        )
                        
                        if result is not None:
                            # Espera a que la vela termine y la obtiene
                            rupture = True
                            self._sleep_to_next_minute()
                            finished_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 1)
                            send_buyback = False
                            
                            # Si no se logro obtener la ultima barra continua con otra iteracion
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
                                print("HedgeTrailing: Primer trade, recompra")
                                result =MT5Api.send_order(
                                    symbol= self.symbol, 
                                    order_type= order_type, 
                                    volume=volume,
                                    magic=self.magic,
                                    comment= "2"
                                )
                                continue

            if rupture and positions and not counter_hedge and int(positions[-1].comment) != 0:
                # Establece las variables
                open = last_bar['open']
                current_price = last_bar['close']
                last_type = positions[-1].type
                send_order = False
                # Verifica si despues del falso rompimiento vuelve a existir una ruptura en la misma direccion
                if last_type == OrderType.MARKET_BUY:
                    if current_price < low:
                        order_type = OrderType.MARKET_SELL
                        send_order = True
                elif last_type == OrderType.MARKET_SELL:
                    if current_price > high:
                        order_type =  OrderType.MARKET_BUY
                        send_order = True
                
                if send_order:
                    print("HedgeTrailing: Hedge trade")
                    last_batch = int(positions[-1].comment)
                    next_batch = last_batch * 3
                    next_volume = volume * next_batch
                    next_profit = range * next_volume
                    if next_profit > 2500:
                        print("HedgeTrailing: Counter Hedge trade")
                        next_volume = self._get_counter_volume(positions)
                            
                    result =MT5Api.send_order(  
                        symbol= self.symbol, 
                        order_type= order_type, 
                        volume=next_volume,
                        magic=self.magic,
                        comment= str(next_batch)
                    )
                    if result:
                        if next_profit > 2500:
                            counter_hedge = True
                        false_rupture = False
                        continue
            
            if false_rupture and positions and int(positions[-1].comment) != 0:
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
                    print("HedgeTrailing: Falsa ruptura trade")
                    result =MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= last_type, 
                        volume=volume,
                        magic=self.magic,
                        comment= "2"
                    )
                    if result:
                        false_rupture = False
                        continue

    def _check_outdated(self, high:float, low:float, range:float, current_price:float):
        if current_price > high:
            price_diff = current_price - high
            count = int(price_diff // range) + 1
        elif current_price < low:
            price_diff = low - current_price
            count = (-int(price_diff // range)) - 1
        else:
            count = 0
        self.number_outdated.value = count
    
    def _get_counter_volume(self, positions: List[TradePosition])->float:
        
        buys = [position for position in positions if position.type == OrderType.MARKET_BUY]
        sells = [position for position in positions if position.type == OrderType.MARKET_SELL]

        total_buys = sum(position.volume for position in buys)
        total_sells = sum(position.volume for position in sells)

        difference = abs(total_sells - total_buys)
        
        return difference
    
    def _get_optimal_range_size(self, rates: np.ndarray, atr_timeperiod=14):
        brick_size = 0.0
        df = pd.DataFrame(rates)
        # Si tenemos suficientes datos
        if len(rates) > atr_timeperiod:
            atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=atr_timeperiod)
            brick_size = np.median(atr[atr_timeperiod:])
        return brick_size
    
    def _preparing_symbols_data(self):
        """
        Prepara la data que se usara en la estrategia de HedgeTrailing.
        """
        print("HedgeTrailing: Preparando la data...")
                
        while True:
            info = MT5Api.get_symbol_info(self.symbol)
            account_info = MT5Api.get_account_info()
            # Obtiene las barras de 30 minutos de 7 dias
            rates_in_range = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_5, 1, 10080)
            
            if info is not None and rates_in_range is not None and account_info is not None:
                break
        
        # Obtiene el nuemro de digitos en el symbolo
        digits = info.digits
        # Establece el rango
        range = self._get_optimal_range_size(rates_in_range)
                
        # Obtiene el cierre de la ultima barra
        last_close = rates_in_range[-1]['close']
        
        # Establece el high y el low con respecto al rango
        quantity_high = int(last_close/range) + 1
        quantity_low = int(last_close/range)
                
        # Establece el high
        high = quantity_high * range
        high = round(high,digits)
        # Establece el low
        low = quantity_low * range
        low = round(low,digits)
        
        volume = (account_info.balance * 0.001) / range
        volume = round(volume, digits)
        
        if volume < (info.volume_min * 2):
            volume = info.volume_min * 2

        symbol_data= {
            'symbol': self.symbol,
            'digits': digits,
            'high': high,
            'low': low,
            'range': range,
            'volume': volume,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
        }
        
        print(symbol_data)
            
        
        # Actualiza la variable compartida
        self.symbol_data = symbol_data
        
    
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
        
        self._preparing_symbols_data()
        
        # Se crea las variables compartidas
        manager = multiprocessing.Manager()
        self.is_on = manager.Value("b", True)
        self.number_outdated = manager.Value("i", 0)
        self.symbol_data['high_outdated'] = manager.Value("f", 0.0)
        self.symbol_data['low_outdated'] = manager.Value("f", 0.0)
                
        # Crea los procesos y los inicia
        manage_positions_process = multiprocessing.Process(target= self._manage_positions)
        manage_positions_process.start()
        hedge_buyer_process = multiprocessing.Process(target=self._hedge_buyer)
        hedge_buyer_process.start()
        
        # Espera a que termine para continuar
        manage_positions_process.join()
                    
        # Fin del ciclo
        print("HedgeTrailing: Finalizando estrategia...")
          
    #endregion