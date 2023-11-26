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
    unassigned = 0
    bullish = 1
    bearish = -1

class TrendSignal:
    anticipating = 0
    rady_main = 1
    ready_mid = 2
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
        
        # La temporalidad de las barras que se usara
        self.time_frame = TimeFrame.MINUTE_30
                
        # Horario de apertura y cierre del mercado
        self._market_opening_time = {'hour':14, 'minute':0}
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
        
        # Variables del rango
        volume_decimals = self.symbol_data['volume_decimals']
        price_range = self.symbol_data['fast_range']
        hedge_range = price_range
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
                        
            # Reinicia las variables en caso de que ya no haya posiciones abiertas
            if not positions:
                # Comienza el administrador de posiciones
                number_trailing = 1
                in_hedge = False
                trailing_stop = False
                continue        
            
            last_position = max(positions, key=lambda position: int(position.comment))
            
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
                if number_step == 1:
                    send_partial_order = False
                                        
                    # Para longs
                    if type == OrderType.MARKET_BUY:
                        limit_high = last_position.price_open + price_range
                        if info.bid > limit_high:
                            send_partial_order = True
                                            
                    # Para shorts
                    else:
                        limit_low = last_position.price_open - price_range
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
                        limit_high_hedge = last_position.price_open + hedge_range
                        if info.bid > limit_high_hedge:
                            positions_to_close = [position for position in positions if position.type == OrderType.MARKET_SELL]
                            send_close_order = True
                    # Para shorts
                    else:
                        limit_low_hedge = last_position.price_open - hedge_range
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
                    limit_high = last_position.price_open + price_range
                    if info.bid > limit_high:
                        send_partial_order = True
                                        
                # Para shorts
                else:
                    limit_low = last_position.price_open - price_range
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
                        stop_loss = last_position.price_open + hedge_range
                    else:
                        stop_loss = last_position.price_open + trailing_range
                    next_stop_loss = last_position.price_open + next_trailing_range
                    next_stop_price = last_position.price_open + next_stop_price_range
                    # Cierra todas las posiciones si el precio cae por debajo del stop loss
                    if info.bid <= stop_loss:
                        print(f"HedgeTrailing: stop loss alcanzado {stop_loss}")
                        MT5Api.send_close_all_position()
                    elif info.ask >= next_stop_price:
                        print(f"HedgeTrailing: stop loss en {next_stop_loss}")
                        number_trailing += 1
                else:
                    if in_hedge and number_trailing == 1:
                        stop_loss = last_position.price_open - hedge_range
                    else:
                        stop_loss = last_position.price_open - trailing_range
                    next_stop_loss = last_position.price_open - next_trailing_range
                    next_stop_price = last_position.price_open - next_stop_price_range
                    # Cierra todas las posiciones si el precio cae por debajo del stop loss
                    if info.ask >= stop_loss:
                        print(f"HedgeTrailing: stop loss alcanzado {stop_loss}")
                        MT5Api.send_close_all_position()
                    elif info.bid <= next_stop_price:
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
        pre_closing_time = market_close - timedelta(hours= 1)
        
        # Variables del rango
        price_range = self.symbol_data['mid_range']
        volume = self.symbol_data['volume']
        volume_max = self.symbol_data['volume_max']
        volume_decimals = self.symbol_data['volume_decimals']
        spread = self.symbol_data['spread']
        
        # Condicionales de estados
        rupture = False
        first_trade = True
        
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
            if not positions and current_time > pre_closing_time:
                try:
                    self.is_on.value = False
                    continue
                except BrokenPipeError as e:
                    print(f"Se produjo un error de tubería rota: {e}")         
            elif positions and current_time > market_close:
                MT5Api.send_close_all_position()
                continue
            
            if self.trade_signal.value != TrendSignal.buy:
                first_trade = True
            
            if first_trade and self.trade_signal.value == TrendSignal.buy:
                # Condicionales de estados
                rupture = False
                
                if self.fast_trend.value == StateTrend.bullish:
                    order_type = OrderType.MARKET_BUY
                    
                else:
                    order_type = OrderType.MARKET_SELL

                print("HedgeTrailing: Primer trade")
                result =MT5Api.send_order(
                    symbol= self.symbol, 
                    order_type= order_type, 
                    volume=volume,
                    magic=self.magic,
                    comment= "1"
                )
                
                if result is not None:
                    rupture = True
                    first_trade = False
                    first_type = order_type
                        
            
            if rupture and positions:
                last_position = max(positions, key=lambda position: position.time)
                if float(last_position.comment) != 0:
                    # Establece las variables
                    last_type = last_position.type
                    send_order = False
                    
                    if last_type == OrderType.MARKET_BUY and self.mid_trend.value == StateTrend.bearish:
                        order_type = OrderType.MARKET_SELL
                        send_order = True
                    elif last_type == OrderType.MARKET_SELL and self.mid_trend.value == StateTrend.bullish:
                        order_type =  OrderType.MARKET_BUY
                        send_order = True
                                        
                    if send_order:
                        print("HedgeTrailing: Close trade")
                        for position in positions:
                            MT5Api.send_close_position(position)
                        
                        # print("HedgeTrailing: Hedge trade")
                        # profit = abs(sum(position.profit for position in positions))
                        # volume_to_even = ((profit/info.trade_contract_size) / ((price_range/2) - (spread * 1))) + volume
                        # next_step = int(last_position.comment) + 1
                        
                        # parts = int(volume_to_even // volume_max) + 1
                        # volume_part = round(volume_to_even/parts, volume_decimals)
                        # for _ in range(parts):
                        #     result =MT5Api.send_order(
                        #         symbol= self.symbol, 
                        #         order_type= order_type, 
                        #         volume=volume_part,
                        #         magic=self.magic,
                        #         comment= str(next_step)
                        #     )
                        #     if not result:
                        #         MT5Api.send_close_all_position()
                        #         continue

    def _preparing_symbols_data(self):
        """
        Prepara la data que se usara en la estrategia de HedgeTrailing.
        """
        #print("HedgeTrailing: Preparando la data...")
        
        # Variable auxiliar
        symbol_data = {}
                
        while True:
            info = MT5Api.get_symbol_info(self.symbol)
            account_info = MT5Api.get_account_info()
            number_bars = 5040
            range_rates = MT5Api.get_rates_from_pos(self.symbol, self.time_frame, 1, number_bars)
            last_minute_bar = MT5Api.get_rates_from_pos(self.symbol, TimeFrame.MINUTE_1, 0, 1)
            if info is not None and range_rates is not None and account_info is not None and last_minute_bar is not None:
                break
        
        # Establece variables             
        symbol_data = {}
        symbol_data['symbol'] = self.symbol
        symbol_data['volume_decimals'] = self.count_decimal_places(info.volume_min)
        symbol_data['volume_min'] = info.volume_min
        symbol_data['volume_max'] = info.volume_max
        symbol_data['spread'] = info.spread * info.point
        symbol_data['price_decimals'] = info.digits
        symbol_data['initial_balance'] = account_info.balance
        
        # Encuentra el rango optimo
        atr_timeperiod = 14
        df = pd.DataFrame(range_rates)
        atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=atr_timeperiod)
        main_range = np.median(atr[atr_timeperiod:])
        
        # Establece los rangos
        symbol_data['main_range'] = main_range
        symbol_data['mid_range'] = main_range/2
        symbol_data['fast_range'] = main_range/4
        
        # Establece el volumen
        if self.user_risk == 0:
            volume = info.volume_min * 2
        else:
            user_risk = account_info.balance * self.user_risk
            user_risk = user_risk/info.trade_contract_size
            volume = user_risk / symbol_data['mid_range']
            volume = round(volume, symbol_data['volume_decimals'])
        
        if volume < (info.volume_min * 2):
            volume = info.volume_min * 2
        
        symbol_data['volume'] = volume
                
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
        # Symbolo a encontrar los trends
        symbol = self.symbol

        # Se establecen las variables para el supertrend
        first_time = True
        
        # Obtiene las barras desde mt5
        while True:
            minute_1_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1,  1440)
            if minute_1_rates is not None:
                break
        
        main_size = self.symbol_data['main_range']
        mid_size = self.symbol_data['mid_range']
        fast_size = self.symbol_data['fast_range']
        
        renko_main = vRenko(minute_1_rates, main_size, False)
        renko_mid = vRenko(minute_1_rates, mid_size, False)
        renko_fast = vRenko(minute_1_rates, fast_size, False)
                                    
        while self.is_on.value:       
            while True:
                minute_last_bar = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 0, 1)
                if minute_last_bar is not None:
                    break
            
            if first_time or renko_fast.update_renko(minute_last_bar):
                last_bar_renko = renko_fast.renko_data[-1]
                type = 1 if last_bar_renko['type'] == 'up' else -1
                if self.fast_trend.value != type:
                    try:
                        self.fast_trend.value = type
                        print(f"Tr3nd: Main {self.main_trend.value} mid {self.mid_trend.value} Fast {self.fast_trend.value}")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
            
            if first_time or renko_mid.update_renko(minute_last_bar):
                last_bar_renko = renko_mid.renko_data[-1]
                type = 1 if last_bar_renko['type'] == 'up' else -1
                if self.mid_trend.value != type:
                    try:
                        self.mid_trend.value = type
                        print(f"Tr3nd: Main {self.main_trend.value} mid {self.mid_trend.value} Fast {self.fast_trend.value}")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
            
            if first_time or renko_main.update_renko(minute_last_bar):
                last_bar_renko = renko_main.renko_data[-1]
                type = 1 if last_bar_renko['type'] == 'up' else -1
                if self.main_trend.value != type:
                    try:
                        self.main_trend.value = type
                        print(f"Tr3nd: Main {self.main_trend.value} mid {self.mid_trend.value} Fast {self.fast_trend.value}")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
            
            if first_time:
                first_time = False
            
    def _trade_signal(self):
        while self.is_on.value:
            
            if self.main_trend.value == StateTrend.unassigned or self.mid_trend.value == StateTrend.unassigned or self.fast_trend.value == StateTrend.unassigned:
                continue

            if self.trade_signal.value == TrendSignal.anticipating:
                if self.main_trend.value == self.mid_trend.value and self.main_trend.value != self.fast_trend.value:
                    try:
                        self.trade_signal.value = TrendSignal.ready_fast
                        print(f"Tr3nd: Estado para nueva orden [ready_fast]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                elif self.mid_trend.value != self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                    try:
                        self.trade_signal.value = TrendSignal.ready_mid
                        print(f"Tr3nd: Estado para nueva orden [ready_mid]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                            
            if self.trade_signal.value == TrendSignal.ready_fast:
                if self.mid_trend.value != self.main_trend.value:
                    try:
                        self.trade_signal.value = TrendSignal.anticipating
                        print(f"Tr3nd: Estado para nueva orden [anticipating]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
                elif self.fast_trend.value == self.main_trend.value:
                    try:
                        self.trade_signal.value = TrendSignal.buy
                        print(f"Tr3nd: Estado para nueva orden [buy]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
            
            elif self.trade_signal.value == TrendSignal.ready_mid:
                if self.mid_trend.value == self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                    try:
                        self.trade_signal.value = TrendSignal.buy
                        print(f"Tr3nd: Estado para nueva orden [buy]")
                    except BrokenPipeError as e:
                        print(f"Se produjo un error de tubería rota: {e}")
            
            if self.trade_signal.value == TrendSignal.buy:               
                # Mantiene un tiempo determinado la señal de compra
                time.sleep(10)
                try:
                    self.trade_signal.value = TrendSignal.anticipating
                    print(f"Tr3nd: Estado para nueva orden [anticipating]")
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
        self.main_trend = manager.Value("i", StateTrend.unassigned)
        self.mid_trend = manager.Value("i", StateTrend.unassigned)
        self.fast_trend = manager.Value("i", StateTrend.unassigned)
        self.trade_signal = manager.Value("i", TrendSignal.anticipating)

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