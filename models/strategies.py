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

class StateTr3nd:
    unassigned = 0
    bullish = 1
    bearish = -1

class TrendSignal:
    anticipating = 0
    rady_main = 1
    ready_intermediate = 2
    ready_fast = 3
    buy = 4
    

class HedgeTrailing:
    def __init__(self, symbol: str, user_risk: float = None) -> None:
        # Indica si el programa debe seguir activo
        self.is_on = None
        
        # Lista de symbolos para administar dentro de la estrategia
        self.symbol = symbol
                
        # Variable que contiene informaciond el symbolo para la estrategia
        self.symbol_data = {}
        
        # El numero que identificara las ordenes de esta estrategia
        self.magic = 63
                
        # El tamaño del lote
        self.user_risk = user_risk
                
        # Horario de apertura y cierre del mercado
        self._market_opening_time = {'hour':14, 'minute':30}
        self._market_closed_time = {'hour':20, 'minute':55}
    
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
                
        while self.is_on.value:
            # Se obtienen las posiciones y la información del símbolo de MetaTrader 5
            while True:
                positions = MT5Api.get_positions(magic=self.magic)
                info = MT5Api.get_symbol_info(self.symbol)
                if positions is not None and info is not None:
                    break
                        
            # Reinicia las variables en caso de que ya no haya posiciones abiertas
            if not positions:
                # Comienza el administrador de posiciones
                # Variables del rango
                high = self.symbol_data['high']
                low = self.symbol_data['low']
                volume_decimals = self.symbol_data['volume_decimals']
                price_range = self.symbol_data['price_range']
                hedge_range = price_range/2
                number_trailing = 1
                in_hedge = False
                trailing_stop = False
                continue              
            
            last_position = max(positions, key=lambda position: position.time)
            
            # Para el manejo de posiciones tendremos en cuenta como se maneja el cierre en mt5
            # Compras al precio ask.
            # Cierras una posición de compra al precio bid.
            # Vendes al precio bid.
            # Cierras una posición de venta al precio ask.         
            if not trailing_stop and positions:
                # Determina el número de lotes y el tipo de última posición
                number_step = float(last_position.comment)
                type = last_position.type
                
                # Para el caso del primer trade
                if number_step == 1 or number_step == 2:
                    send_partial_order = False
                                        
                    # Para longs
                    if type == OrderType.MARKET_BUY:
                        limit_high = high + price_range
                        if info.bid > limit_high:
                            send_partial_order = True
                                            
                    # Para shorts
                    else:
                        limit_low = low - price_range
                        if info.ask < limit_low:
                            send_partial_order = True
                    
                    if send_partial_order:
                        # Vende la mitad de las posiciones abiertas
                        completed = True
                        for position in positions:
                            partial_volume = round(position.volume/2, volume_decimals)
                            result = MT5Api.send_sell_partial_order(position, partial_volume, "0")
                            completed = completed and result
                        if not completed:
                            continue
                        trailing_stop = True
                        
                # Para el caso donde hallan hedges
                else:
                    send_close_order = False
                    positions_to_close = []
                    
                    # Para longs
                    if type == OrderType.MARKET_BUY:
                        limit_high_hedge = high + hedge_range
                        if info.bid > limit_high_hedge:
                            positions_to_close = [position for position in positions if position.type == OrderType.MARKET_SELL]
                            send_close_order = True
                    # Para shorts
                    else:
                        limit_low_hedge = low - hedge_range
                        if info.ask < limit_low_hedge:
                            positions_to_close = [position for position in positions if position.type == OrderType.MARKET_BUY]
                            send_close_order = True
                        
                    if send_close_order:
                        # Cierra posiciones con pérdidas
                        completed = True                            
                        for position in positions_to_close:
                            if position.profit < 0:
                                result = MT5Api.send_close_position(position)
                                completed = completed and result
                        if not completed:
                            continue
                        in_hedge = True
                        trailing_stop = True
                        continue
            
            # Cuando esta en Hedge revisa si llego al rango limite para hacer ventas parciales
            if in_hedge and positions and int(positions[-1].comment) > 0:
                type = last_position.type
                send_partial_order = False
                                        
                # Para longs
                if type == OrderType.MARKET_BUY:
                    limit_high = high + price_range
                    if info.bid > limit_high:
                        send_partial_order = True
                                        
                # Para shorts
                else:
                    limit_low = low - price_range
                    if info.ask < limit_low:
                        send_partial_order = True
                
                if send_partial_order:
                    # Vende la mitad de las posiciones abiertas
                    completed = True
                    for position in positions:
                        partial_volume = round(position.volume/2, volume_decimals)
                        result = MT5Api.send_sell_partial_order(position, partial_volume, "0")
                        completed = completed and result
                    if not completed:
                        continue
                            
            # Para el traling se manejara x/2 de distancia entre cada stop,
            # para el caso donde halla hedge se pondra el primer stop donde se hicieron las ventas negativas
            if trailing_stop and positions:
                type = last_position.type
                # Establece el stop loss móvil si se activa el trailing stop
                trailing_range = (price_range * (number_trailing/2))
                next_trailing_range = (price_range * ((number_trailing + 1)/2))
                next_stop_price_range = (price_range * ((number_trailing + 2)/2))                    
                if type == OrderType.MARKET_BUY:
                    if in_hedge and number_trailing == 1:
                        stop_loss = high + hedge_range
                    else:
                        stop_loss = high + trailing_range
                    next_stop_loss = high + next_trailing_range
                    next_stop_price = high + next_stop_price_range
                    # Cierra todas las posiciones si el precio cae por debajo del stop loss
                    if info.bid <= stop_loss:
                        print(f"HedgeTrailing: stop loss alcanzado {stop_loss}")
                        MT5Api.send_close_all_position()
                    elif info.bid >= next_stop_price:
                        print(f"HedgeTrailing: stop loss en {next_stop_loss}")
                        number_trailing += 1
                else:
                    if in_hedge and number_trailing == 1:
                        stop_loss = low - hedge_range
                    else:
                        stop_loss = low - trailing_range
                    next_stop_loss = low - next_trailing_range
                    next_stop_price = low - next_stop_price_range
                    # Cierra todas las posiciones si el precio cae por debajo del stop loss
                    if info.ask >= stop_loss:
                        print(f"HedgeTrailing: stop loss alcanzado {stop_loss}")
                        MT5Api.send_close_all_position()
                    elif info.ask <= next_stop_price:
                        print(f"HedgeTrailing: stop loss en {next_stop_loss}")
                        number_trailing += 1

    
    #endregion                 
    
    #region HedgeTrailing strategy 
    
    def _hedge_buyer(self):
        """
        Prepara órdenes para ser enviadas a MetaTrader 5 en función de los datos y las condicionales establecidas.
        """
        print("HedgeTrailing: Iniciando administrador de compras")
        
        # Horario de cierre
        current_time = datetime.now(pytz.utc)   # Hora actual
        market_close = current_time.replace(hour=self._market_closed_time['hour'], minute=self._market_closed_time['minute'], second=0)
        
        # Variables del rango
        high = self.symbol_data['high']
        low = self.symbol_data['low']
        price_range = self.symbol_data['price_range']
        hedge_range = price_range/2
        volume = self.symbol_data['volume']
        volume_max = self.symbol_data['volume_max']
        volume_decimals = self.symbol_data['volume_decimals']
        spread = self.symbol_data['spread']
        
        # Condicionales de estados
        false_rupture= False
        rupture = False
        number_hedge = 1
        updated_symbol_data = True
        
        while self.is_on.value:
            # Se obtiene las variables de mt5
            while True:
                info = MT5Api.get_symbol_info(self.symbol)
                positions = MT5Api.get_positions(magic=self.magic)
                last_bar = MT5Api.get_last_bar(self.symbol)
                finished_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 1)
                if info is not None and positions is not None and last_bar is not None and finished_bar is not None:
                    break
            
            # Hora actual
            current_time = datetime.now(pytz.utc)
            
            if not positions and current_time > market_close:
                MT5Api.send_close_all_position()
                continue
            
            # Se actualizan las variables
            if not positions and (not updated_symbol_data or (finished_bar['close'] > high or finished_bar['close'] < low )):
                self._preparing_symbols_data()
                updated_symbol_data = True
                
                # Variables del rango
                high = self.symbol_data['high']
                low = self.symbol_data['low']
                price_range = self.symbol_data['price_range']
                hedge_range = price_range/2
                volume = self.symbol_data['volume']
                volume_max = self.symbol_data['volume_max']
                volume_decimals = self.symbol_data['volume_decimals']
                spread = self.symbol_data['spread']
                
                # Condicionales de estados
                false_rupture= False
                rupture = False
                number_hedge = 1
            
            if not positions and self.trend_signal.value == TrendSignal.buy:
                # Hora para cerrar el programa antes
                pre_closing_time = current_time + timedelta(hours=1, minutes=0)
                # Si el programa no se encuentra aun en horario de pre cierre puede seguir operando
                if pre_closing_time > market_close:
                    try:
                        self.is_on.value = False
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                        
                    continue
                                
                # Establece las variables
                open = last_bar['open']       
                send_order = False
                buyback_range = (price_range * 0.2)
                
                # Comprueba si el precio supera el rango
                
                if info.ask > high and self.fast_trend.value == StateTr3nd.bullish:
                    send_order = True
                    order_type = OrderType.MARKET_BUY
                    range_limit = high + buyback_range
                    
                elif info.bid < low and self.fast_trend.value == StateTr3nd.bearish:
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
                        updated_symbol_data = False
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
        
            if rupture and positions:
                last_position = max(positions, key=lambda position: position.time)
                if float(last_position.comment) != 0:
                    # Establece las variables
                    open = last_bar['open']
                    last_type = last_position.type
                    send_order = False
                    # Verifica si despues del falso rompimiento vuelve a existir una ruptura en la misma direccion
                    if last_type == OrderType.MARKET_BUY:
                        if info.bid < low:
                            order_type = OrderType.MARKET_SELL
                            send_order = True
                    elif last_type == OrderType.MARKET_SELL:
                        if info.ask > high:
                            order_type =  OrderType.MARKET_BUY
                            send_order = True
                    
                    if send_order:
                        print("HedgeTrailing: Hedge trade")
                        counter_volume = self._get_counter_volume(positions)
                        profit = abs(sum(position.profit for position in positions))
                        volume_to_even = ((profit/info.trade_contract_size) / (hedge_range - (spread * 2))) + counter_volume
                        next_step = int(last_position.comment) + 1 if int(last_position.comment) != 1 else 3
                        
                        parts = int(volume_to_even // volume_max) + 1
                        volume_part = round(volume_to_even/parts, volume_decimals)
                        for _ in range(parts):
                            result =MT5Api.send_order(
                                symbol= self.symbol, 
                                order_type= order_type, 
                                volume=volume_part,
                                magic=self.magic,
                                comment= str(next_step)
                            )
                            if not result:
                                continue
                        if result:
                            number_hedge += 1
                            if number_hedge == 2:
                                part_range = (price_range * 0.2)
                                high = high + part_range
                                low = low - part_range
                                price_range = price_range - part_range
                                hedge_range = hedge_range - part_range
                            false_rupture = False
                            continue
            
            if false_rupture and positions:
                last_position = max(positions, key=lambda position: position.time)
                if float(last_position.comment) != 0:
                    # Establece las variables
                    open = finished_bar['open']
                    close = finished_bar['close']
                    last_type = last_position.type
                    send_buyback = False
                    buyback_range = (price_range * 0.2)
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
        
    def _get_counter_volume(self, positions: List[TradePosition])->float:
        
        buys = [position for position in positions if position.type == OrderType.MARKET_BUY]
        sells = [position for position in positions if position.type == OrderType.MARKET_SELL]

        total_buys = sum(position.volume for position in buys)
        total_sells = sum(position.volume for position in sells)

        difference = abs(total_sells - total_buys)
        
        return difference

    def _preparing_symbols_data(self):
        """
        Prepara la data que se usara en la estrategia de HedgeTrailing.
        """
        print("HedgeTrailing: Preparando la data...")
        
        # Variable auxiliar
        symbol_data = {}
        
        self._sleep_to_next_minute()
        
        while True:
            info = MT5Api.get_symbol_info(self.symbol)
            account_info = MT5Api.get_account_info()
            number_bars = 60
            rates = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_5, 1, number_bars)
            last_minute_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 1, 1)
            if info is not None and rates is not None and account_info is not None and last_minute_bar is not None:
                break
        
        # Establece variables             
        symbol_data = {}
        symbol_data['symbol'] = self.symbol
        symbol_data['volume_decimals'] = self.count_decimal_places(info.volume_min)
        symbol_data['volume_min'] = info.volume_min
        symbol_data['volume_max'] = info.volume_max
        symbol_data['spread'] = info.spread * info.point
        symbol_data['price_decimals'] = info.digits
        
        # Encuentra el rango optimo
        atr_timeperiod = 14
        df = pd.DataFrame(rates)
        atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=atr_timeperiod)
        price_range = np.median(atr[atr_timeperiod:])
        
        # Establece el high y low
        current_price = last_minute_bar[-1]['close']
        quantity = int(current_price/price_range)
        high = (quantity + 1) * price_range
        low = quantity * price_range
        
        # Establece el volumen
        user_risk = (account_info.balance * 0.01) if self.user_risk is None else self.user_risk
        user_risk = user_risk/info.trade_contract_size
        volume = user_risk / price_range
        volume = round(volume, symbol_data['volume_decimals'])
        
        if volume < (info.volume_min * 2):
            volume = info.volume_min * 2
        
        # Guarda las variables
        symbol_data['price_range'] = price_range
        symbol_data['volume'] = volume
        symbol_data['high'] = high
        symbol_data['low'] = low
                
        print(symbol_data)
        
        # Actualiza la variable compartida
        self.symbol_data.update(symbol_data)
  
    def count_decimal_places(self, number)-> int:
        if isinstance(number, float):
            if number == 1.0:
                return 0
            # Convierte el número a una cadena (string) para analizar los decimales
            number_str = str(number)
            # Divide la cadena en dos partes: la parte entera y la parte decimal
            integer_part, decimal_part = number_str.split(".")
            # Retorna la longitud de la parte decimal
            return len(decimal_part)
        else:
            # Si el número no es un float, retorna 0 decimales
            return 0
    
    def _update_trends(self):
        print("Tr3nd: Update iniciado")
        # Indica si es la primera vez que inicia el metodo
        first_time = True
        
        # Symbolo a encontrar los trends
        symbol = self.symbol

        # Se establecen las variables para el supertrend
        atr_period = 14
        multiplier = 1
        
        # Obtiene las barras desde mt5
        while True:
            minute_1_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1,  10080)
            minute_30_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_15, 1,  10080)
            if minute_1_rates is not None and minute_30_rates is not None:
                break
        
        # Encuentra el rango optimo
        df = pd.DataFrame(minute_30_rates)
        atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=atr_period)
        price_range = np.median(atr[atr_period:])
        
        main_size = price_range
        intermediate_size = main_size/2
        fast_size = intermediate_size/2
        
        print(f"Tr3nd: Main brick size: {main_size}")
        print(f"Tr3nd: Intermediate brick size: {intermediate_size}")
        print(f"Tr3nd: Fast brick size: {fast_size}")
        
        renko_main = vRenko(minute_1_rates, main_size, False)
        renko_intermediate = vRenko(minute_1_rates, intermediate_size, False)
        renko_fast = vRenko(minute_1_rates, fast_size, False)
                                    
        while self.is_on.value:           
             
            if not first_time:
                self._sleep_to_next_minute()
                
                while True:
                    minute_1_bar = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1, 1)
                    if minute_1_bar is not None:
                        break      
            
            if first_time or renko_main.update_renko(minute_1_bar):
                df = pd.DataFrame(renko_main.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.main_trend.value != last_bar_renko['supertrend']:
                    try:
                        self.main_trend.value = int(last_bar_renko['supertrend'])
                        print(f"Tr3nd: Main {self.main_trend.value} Intermediate {self.intermediate_trend.value} Fast {self.fast_trend.value}")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                        
            if first_time or renko_intermediate.update_renko(minute_1_bar):
                df = pd.DataFrame(renko_intermediate.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.intermediate_trend.value != last_bar_renko['supertrend']:
                    try:
                        self.intermediate_trend.value = int(last_bar_renko['supertrend'])
                        print(f"Tr3nd: Main {self.main_trend.value} Intermediate {self.intermediate_trend.value} Fast {self.fast_trend.value}")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                        
            if first_time or renko_fast.update_renko(minute_1_bar):
                df = pd.DataFrame(renko_fast.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.fast_trend.value != last_bar_renko['supertrend']:
                    try:
                        self.fast_trend.value = int(last_bar_renko['supertrend'])
                        print(f"Tr3nd: Main {self.main_trend.value} Intermediate {self.intermediate_trend.value} Fast {self.fast_trend.value}")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                        
            if first_time:
                first_time = False
    
    def _trade_signal(self):
        while self.is_on.value:
            
            if self.main_trend.value == StateTr3nd.unassigned or self.intermediate_trend.value == StateTr3nd.unassigned or self.fast_trend.value == StateTr3nd.unassigned:
                continue
            
            if self.trend_signal.value == TrendSignal.anticipating or self.trend_signal.value == TrendSignal.buy:
                if self.main_trend.value == self.intermediate_trend.value and self.main_trend.value != self.fast_trend.value:
                    try:
                        self.trend_signal.value = TrendSignal.ready_fast
                        print(f"Tr3nd: Estado para nueva orden [ready_fast]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                elif self.intermediate_trend.value != self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                    try:
                        self.trend_signal.value = TrendSignal.ready_intermediate
                        print(f"Tr3nd: Estado para nueva orden [ready_intermediate]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                elif self.trend_signal.value != TrendSignal.buy and self.intermediate_trend.value == self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                    try:
                        self.trend_signal.value = TrendSignal.buy
                        print(f"Tr3nd: Estado para nueva orden [buy]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
            
            if self.trend_signal.value == TrendSignal.ready_fast:
                if self.intermediate_trend.value != self.main_trend.value:
                    try:
                        self.trend_signal.value = TrendSignal.anticipating
                        print(f"Tr3nd: Estado para nueva orden [anticipating]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                elif self.fast_trend.value == self.main_trend.value:
                    try:
                        self.trend_signal.value = TrendSignal.buy
                        print(f"Tr3nd: Estado para nueva orden [buy]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
            
            elif self.trend_signal.value == TrendSignal.ready_intermediate:
                if self.intermediate_trend.value == self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                    try:
                        self.trend_signal.value = TrendSignal.buy
                        print(f"Tr3nd: Estado para nueva orden [buy]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")       

    
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
        self.symbol_data = manager.dict({})
        self.main_trend = manager.Value("i", StateTr3nd.unassigned)
        self.intermediate_trend = manager.Value("i", StateTr3nd.unassigned)
        self.fast_trend = manager.Value("i", StateTr3nd.unassigned)
        self.trend_signal = manager.Value("i", TrendSignal.anticipating)

        self._preparing_symbols_data()
        
        # Crea los procesos y los inicia
        update_trends_process = multiprocessing.Process(target=self._update_trends)
        update_trends_process.start()
        trade_signal_process = multiprocessing.Process(target=self._trade_signal)
        trade_signal_process.start()
        manage_positions_process = multiprocessing.Process(target= self._manage_positions)
        manage_positions_process.start()
        hedge_buyer_process = multiprocessing.Process(target=self._hedge_buyer)
        hedge_buyer_process.start()
        
        # Espera a que termine para continuar
        manage_positions_process.join()
                    
        # Fin del ciclo
        print("HedgeTrailing: Finalizando estrategia...")
          
    #endregion