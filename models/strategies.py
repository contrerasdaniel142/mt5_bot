#region Descripción:
# Componente esencial en el sistema de trading automatizado basado en MetaTrader 5 (MT5). 
# Su función principal es contener y definir las estrategias específicas de trading que 
# desean implementar y ejecutar en la plataforma MT5.
#endregion

#region Importaciones
# Importaciones necesarias para definir tipos de datos
from typing import List, Dict, Any, Tuple
from decimal import Decimal
# importaciones para realizar operaciones numéricas eficientes
import numpy as np
from numpy import ndarray
import pandas as pd

# Para trabajo en paralelo
import multiprocessing

# Importacion de los clientes de las apis para hacer solicitudes
from .mt5.enums import TimeFrame, OrderType
from .mt5.client import MT5Api
from .telegram.client import TelegramApi

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz, time

# Importaciones de indicatores técnicos
import pandas_ta as ta
from .technical_indicators import HeikenAshi


#endregion


class StateTr3nd:
    unassigned = 0
    bullish = 1
    bearish = -1

class StateSymbol:
    no_trades = 0
    unbalanced = 1
    balanced = 2

class TrendSignal:
    anticipating = 0
    rady_main = 1
    ready_intermediate = 2
    ready_fast = 3
    buy = 4
    
    

class Tr3nd:
    def __init__(self, symbol: str, volume: float = None, atr_period:int = 10, multiplier:float = 3.0) -> None:
        # Numero identificador de la estretegia
        self.magic = 40
        # Indica si la estrategia esta activa
        self.is_on = True
        # Activo a tradear
        self.symbol = symbol
        # Maximo intentos de desbalance permitidos en la estregia
        self.max_positions = 6
        # Volumen de las ordenes
        self.volume = float(volume)
        # Estado el activo
        self.state = StateSymbol.no_trades
        # Periodo del atr usado para el supertrend
        self.atr_period = atr_period
        # Multiplicador usado en el supertrend
        self.multiplier = multiplier
        # Inicializa las variables que tendran la tendencia
        self.main_trend = StateTr3nd.unassigned
        self.intermediate_trend = StateTr3nd.unassigned
        self.fast_trend = StateTr3nd.unassigned
        # Horario de apertura y cierre del mercado
        self._market_opening_time = {'day':1,'hour':0, 'minute':0}
        self._market_closed_time = {'hour':19, 'minute':45}
        self.opening_balance_account = 0
        
    def _is_in_market_hours_synthetic(self):
        """
        Comprueba si el momento actual se encuentra en horario de mercado.

        Returns:
            bool: True si se encuentra en horario de mercado, False si no lo está.
        """
        # Obtener la hora y minutos actuales en UTC
        current_time = datetime.now(pytz.utc)

        # Crear objetos time para el horario de apertura y cierre del mercado
        market_close = current_time.replace(hour=23, minute=45, second=0, microsecond=0)

        # Verificar si la hora actual está dentro del horario de mercado
        if current_time < market_close:
            return True
        else:
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

        # Calcular el momento en que comienza el próximo minuto 
        next_minute = current_time.replace(second=1, microsecond=200000) + timedelta(minutes=1)

        # Calcular la cantidad de segundos que faltan hasta el próximo minuto
        seconds = (next_minute - current_time).total_seconds()

        # Dormir durante la cantidad de segundos necesarios
        time.sleep(seconds)
    
    def _manage_positions(self):
        TelegramApi.send_text("tr3nd: Iniciando administrador de posiciones")
        # Comienza el administrador de posiciones
        while self.is_on.value:
            if self.main_trend.value != StateTr3nd.unassigned and self.intermediate_trend.value != StateTr3nd.unassigned and self.fast_trend.value != StateTr3nd.unassigned:
                if self.state.value == StateSymbol.no_trades:
                    self._no_trade_state()
                elif self.state.value == StateSymbol.unbalanced:
                    self._unbalanced_state()
                else:
                    self._balaced_state()
    
    def _goal_profit(self)->bool:
        positions = MT5Api.get_positions(magic = self.magic)
        account_info = MT5Api.get_account_info()
        if positions is not None and account_info is not None:
            profit_account = account_info.profit
            profit_positions = 0
            for position in positions:
                profit_positions += position.profit
                
            # if profit_positions > (self.opening_balance_account*0.005):
            #     TelegramApi.send_text(f"Tr3nd: Meta de profit en las posiciones abiertas alcanzado {profit_positions}")
            #     self.state.value = StateSymbol.no_trades
            #     MT5Api.send_close_all_position()
            
            total_profit = profit_positions+profit_account
            if total_profit >= (self.opening_balance_account*0.03):
                TelegramApi.send_text(f"Tr3nd: Meta de profit total alcanzado {total_profit}")
                self.is_on.value = False
                MT5Api.send_close_all_position()
            
    def _no_trade_state(self):
        TelegramApi.send_text("Tr3nd: Estado sin Trade")
        trend_signal = TrendSignal.anticipating
        #TelegramApi.send_message(f"Tr3nd: [Estado para nueva orden {no_trade_state}]")
        while self.is_on.value:
            # Se cerciora que alcance el profit diario para terminar el programa
            self._goal_profit()
            
            if self._is_in_market_hours_synthetic():
                trend_signal = self._trade_to_unbalance(trend_signal)

            if self.state.value == StateSymbol.unbalanced:
                break
                
    def _trade_to_unbalance(self, trend_signal:TrendSignal):
        
        if trend_signal == TrendSignal.anticipating:
            if self.main_trend.value == self.intermediate_trend.value and self.main_trend.value != self.fast_trend.value and self.state.value == StateSymbol.no_trades:
                trend_signal = TrendSignal.ready_fast
                TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
            elif self.intermediate_trend.value != self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                trend_signal = TrendSignal.ready_intermediate
                TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
        
        if self.intermediate_trend.value == self.main_trend.value and self.main_trend.value == self.fast_trend.value and self.state.value != StateSymbol.no_trades:
            trend_signal = TrendSignal.buy
            TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
        
        if trend_signal == TrendSignal.ready_fast:
            if self.intermediate_trend.value != self.main_trend.value:
                trend_signal = TrendSignal.anticipating
                TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
            elif self.fast_trend.value == self.main_trend.value:
                trend_signal = TrendSignal.buy
                TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
        
        elif trend_signal == TrendSignal.ready_intermediate:
            if self.intermediate_trend.value != self.main_trend.value and self.main_trend.value != self.fast_trend.value:
                trend_signal = TrendSignal.anticipating
                TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
            elif self.intermediate_trend.value == self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                trend_signal = TrendSignal.buy
                TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
                            
        if trend_signal == TrendSignal.buy:
            TelegramApi.send_text(f"Tr3nd: Creando orden nueva")
            if self.main_trend.value == StateTr3nd.bullish:
                result = MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= OrderType.MARKET_BUY, 
                        volume=self.volume,
                        comment="+1",
                        magic=self.magic
                        )
            else:
                result = MT5Api.send_order(
                        symbol= self.symbol,
                        order_type= OrderType.MARKET_SELL, 
                        volume=self.volume,
                        comment="-1",
                        magic=self.magic
                        )
            
            self.state.value = StateSymbol.unbalanced
                
            if result is None:
                trend_signal = TrendSignal.anticipating
                self.state.value = StateSymbol.no_trades
            else:
                return trend_signal
            TelegramApi.send_text(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
        
        return trend_signal
               
    def _unbalanced_state(self):
        TelegramApi.send_text("Tr3nd: Estado desbalanceado")
        take_profit = False
        while self.is_on.value:
            # Se cerciora que alcance el profit diario para terminar el programa
            self._goal_profit()
            
            if self.state.value != StateSymbol.unbalanced:
                break
            
            positions = MT5Api.get_positions(magic = self.magic)
            
            if positions is not None:
                if self.main_trend.value == self.intermediate_trend.value and self.main_trend.value != self.fast_trend.value:
                    take_profit = True
                                
                if take_profit:
                    if self.main_trend.value == StateTr3nd.bullish:
                        positions_in_favor = [position for position in positions if position.type == OrderType.MARKET_BUY]
                    else:
                        positions_in_favor = [position for position in positions if position.type == OrderType.MARKET_SELL]
                    last_profit = 0
                    ticket = 0
                    symbol = self.symbol
                    for position in positions_in_favor:
                        if position.profit > last_profit:
                            last_profit = position.profit
                            ticket = position.ticket
                    if ticket != 0:
                        TelegramApi.send_text("Tr3nd: Cerrando posicion a favor con profit")
                        result = MT5Api.send_close_position(symbol, ticket)
                        if result:
                            if (len(positions) - 1) == 0:
                                self.state.value = StateSymbol.no_trades
                            else:
                                self.state.value = StateSymbol.balanced
                            break
                    
                if len(positions) < self.max_positions and self._is_in_market_hours_synthetic():
                    if self.main_trend.value != self.intermediate_trend.value and self.intermediate_trend.value == self.fast_trend.value :
                        TelegramApi.send_text("Tr3nd: Creando orden Hedge")
                        if self.main_trend.value == StateTr3nd.bullish:
                            result = MT5Api.send_order(
                                symbol= self.symbol, 
                                order_type= OrderType.MARKET_SELL, 
                                volume=self.volume,
                                comment="-1",
                                magic=self.magic
                                )
                        else:
                            result = MT5Api.send_order(
                                symbol= self.symbol, 
                                order_type= OrderType.MARKET_BUY, 
                                volume=self.volume,
                                comment="+1",
                                magic=self.magic
                                )
                        if result is not None:
                            self.state.value = StateSymbol.balanced
                            break
                    
    def _balaced_state(self):
        TelegramApi.send_text("Tr3nd: Estado balanceado")
        trend_signal = TrendSignal.anticipating
        #TelegramApi.send_message(f"Tr3nd: [Estado para nueva orden {no_trade_state}]")
        while self.is_on.value:
            # Se cerciora que alcance el profit diario para terminar el programa
            self._goal_profit()
            
            if self.state.value != StateSymbol.balanced:
                break
            
            positions = MT5Api.get_positions(magic = self.magic)
            if positions is not None:
                if self.main_trend.value != self.intermediate_trend.value and self.main_trend.value == self.fast_trend.value:
                    positions = MT5Api.get_positions(magic = self.magic)
                    if self.main_trend.value == StateTr3nd.bullish:
                        hedge_positions = [position for position in positions if position.type == OrderType.MARKET_SELL]
                    else:
                        hedge_positions = [position for position in positions if position.type == OrderType.MARKET_BUY]

                    last_profit = 0
                    ticket = 0
                    symbol = self.symbol
                    for position in hedge_positions:
                        if position.profit > last_profit:
                            last_profit = position.profit
                            ticket = position.ticket
                    if ticket != 0:
                        TelegramApi.send_text("Tr3nd: Cerrando posicion contraria con profit")
                        result = MT5Api.send_close_position(symbol, ticket)
                        if result:
                            if (len(positions) - 1) == 0:
                                self.state.value = StateSymbol.no_trades
                            else:
                                self.state.value = StateSymbol.unbalanced
                            break
                        
                if len(positions) < self.max_positions and self._is_in_market_hours_synthetic():
                    trend_signal = self._trade_to_unbalance(trend_signal)
                    if self.state.value == StateSymbol.unbalanced:
                        break 
                
    def _get_optimal_brick_size(self, rates: np.ndarray, atr_timeperiod=14):
        brick_size = 0.0
        df = pd.DataFrame(rates)
        # Si tenemos suficientes datos
        if len(rates) > atr_timeperiod:
            atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=atr_timeperiod)
            brick_size = np.median(atr[atr_timeperiod:])
        return round(brick_size)
    
    def _update_trends(self):
        TelegramApi.send_text("Tr3nd: Update iniciado")
        # Indica si es la primera vez que inicia el metodo
        first_time = True
        
        # Symbolo a encontrar los trends
        symbol = self.symbol

        # Se establecen las variables para el supertrend
        atr_period = self.atr_period
        multiplier = self.multiplier
        
        # Obtiene las barras desde mt5
        while True:
            minute_15_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_15, 1,  10080)
            hour_1_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.HOUR_1, 1,  10080)
            hour_4_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.HOUR_4, 1,  10080)
            if minute_15_rates is not None and hour_1_rates is not None and hour_4_rates is not None:
                break
        
        ha_main = HeikenAshi(MT5Api.get_rates_from_pos(symbol, TimeFrame.HOUR_4, 1,  10080))
        ha_intermediate = HeikenAshi(MT5Api.get_rates_from_pos(symbol, TimeFrame.HOUR_1, 1,  10080))
        ha_fast = HeikenAshi(MT5Api.get_rates_from_pos(symbol, TimeFrame.HOUR_1, 1,  10080))
                                    
        while self.is_on.value:           
            fast_bar = None
            intermediate_bar = None
            main_bar = None
                                               
            if not first_time:
                self._sleep_to_next_minute()
                
                while True:
                    fast_bar = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_15, 1, 1)
                    intermediate_bar = MT5Api.get_rates_from_pos(symbol, TimeFrame.HOUR_1, 1, 1)
                    main_bar = MT5Api.get_rates_from_pos(symbol, TimeFrame.HOUR_4, 1, 1)
                    if fast_bar is not None and intermediate_bar is not None and main_bar is not None:
                        break
                    
                if ha_main.rates[-1]['time'] < main_bar['time']:
                    ha_main.update_HeikenAshi(main_bar)
                    
                if ha_intermediate.rates[-1]['time'] < intermediate_bar['time']:
                    ha_intermediate.update_HeikenAshi(intermediate_bar)
                
                if ha_fast.rates[-1]['time'] < fast_bar['time']:
                    ha_fast.update_HeikenAshi(fast_bar)
            
            
            if first_time or ha_main.rates[-1]['time'] < main_bar['time']:
                ha_main.update_HeikenAshi(main_bar)
                df = pd.DataFrame(ha_main.heiken_ashi)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.main_trend.value != last_bar_renko['supertrend']:
                    self.main_trend.value = last_bar_renko['supertrend']
                    TelegramApi.send_text(f"Tr3nd: [Main {self.main_trend.value}] [Intermediate {self.intermediate_trend.value}] [Fast {self.fast_trend.value}]")
                
            if first_time or ha_intermediate.rates[-1]['time'] < intermediate_bar['time']:
                ha_intermediate.update_HeikenAshi(intermediate_bar)
                df = pd.DataFrame(ha_intermediate.heiken_ashi)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.intermediate_trend.value != last_bar_renko['supertrend']:
                    self.intermediate_trend.value = last_bar_renko['supertrend']
                    TelegramApi.send_text(f"Tr3nd: [Main {self.main_trend.value}] [Intermediate {self.intermediate_trend.value}] [Fast {self.fast_trend.value}]")
                
            if first_time or ha_fast.rates[-1]['time'] < fast_bar['time']:
                ha_fast.update_HeikenAshi(fast_bar)
                df = pd.DataFrame(ha_fast.heiken_ashi)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.fast_trend.value != last_bar_renko['supertrend']:
                    self.fast_trend.value = last_bar_renko['supertrend']
                    TelegramApi.send_text(f"Tr3nd: [Main {self.main_trend.value}] [Intermediate {self.intermediate_trend.value}] [Fast {self.fast_trend.value}]")
                    
            if first_time:
                first_time = False
                
    
    def start(self):
        TelegramApi.send_text(f"Tr3nd: Iniciando estrategia para {self.symbol}...")
        TelegramApi.send_text(f"Tr3nd: Periodo atr: {self.atr_period}")
        TelegramApi.send_text(f"Tr3nd: Multiplicador: {self.multiplier}")
        # Establece el volumen para las ordenes
        while True:
            account_info = MT5Api.get_account_info()
            if account_info is not None:
                break
            
        self.opening_balance_account = account_info.balance
        TelegramApi.send_text(f"Tr3nd: Balance de apertura {self.opening_balance_account}")
        
        #symbol_info = MT5Api.get_symbol_info(self.symbol)
        # max_volume = round((account_info.balance * 0.01 * symbol_info.point), symbol_info.digits)
        # if self.volume is None:
        #     self.volume = max_volume
        # else:
        #     self.volume = round(self.volume, symbol_info.digits)
        #     if self.volume > max_volume:
        #         self.volume = max_volume
        # Crea un administrador para multiprocessing
        
        manager = multiprocessing.Manager()
        # Crea las variables que se administraran entre procesos
        self.is_on = manager.Value("b", True)
        self.state = manager.Value("i", StateSymbol.no_trades)
        self.main_trend = manager.Value("i", StateTr3nd.unassigned)
        self.intermediate_trend = manager.Value("i", StateTr3nd.unassigned)
        self.fast_trend = manager.Value("i", StateTr3nd.unassigned)
        
        # Si se vuelve a iniciar el programa y tiene posiciones abiertas les continua haciendo seguimiento
        while True:
            positions = MT5Api.get_positions(magic = self.magic)
            if positions is not None:
                break
        
        if positions:
            if len(positions) % 2 == 0:
                self.state.value = StateSymbol.balanced
            else:
                self.state.value = StateSymbol.unbalanced
        
        # Crea los procesos y los inicia
        manage_positions_process = multiprocessing.Process(target= self._manage_positions)
        manage_positions_process.start()
        update_trends_process = multiprocessing.Process(target=self._update_trends)
        update_trends_process.start()
        
        # Espera a que termine para continuar
        update_trends_process.join()
        
        # Fin del ciclo
        TelegramApi.send_text("Tr3nd: Finalizando estrategia...")
        

