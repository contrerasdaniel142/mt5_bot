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

# Importacion de los clientes de las apis para hacer solicitudes
from .mt5.client import MT5Api

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
import pytz, time

# Importaciones de indicatores técnicos
import pandas_ta as ta
from .technical_indicators import vRenko


#endregion


class StateTr3nd:
    unassigned = 0
    bullish = 1
    bearish = -1

class StateSymbol:
    no_trades = 0
    bullish = 1
    bearish = -1
    balanced = 2

class TradeState:
    on = 0
    ready = 1
    start = 3

class Tr3nd:
    def __init__(self, symbol: str, volume: float = None, size_renko:float = 40, atr_period:int = 10, multiplier:int = 3) -> None:
        # Numero identificador de la estretegia
        self.magic = 40
        # Indica si la estrategia esta activa
        self.is_on = None
        # Activo a tradear
        self.symbol = symbol
        # Volumen de las ordenes
        self.volume = volume
        # Estado el activo
        self.state = StateSymbol.balanced
        # Tamaño del ladrillo del renko principal
        self.size_renko = size_renko
        # Periodo del atr usado para el supertrend
        self.atr_period = atr_period
        # Multiplicador usado en el supertrend
        self.multiplier = multiplier
        # Inicializa las variables que tendran la tendencia
        self.main_trend = StateTr3nd.unassigned
        self.intermediate_trend = StateTr3nd.unassigned
        self.fast_trend = StateTr3nd.unassigned
        # Horario de apertura y cierre del mercado
        self._market_opening_time = {'hour':13, 'minute':30}
        self._market_closed_time = {'hour':19, 'minute':45}
        
    
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
        
    
    def _manage_positions(self):
        positions = MT5Api.get_positions(magic = self.magic)
        # Si se vuelve a iniciar el programa y tiene posiciones abiertas les continua haciendo seguimiento
        if positions:
            if len(positions) % 2 == 0:
                self._balaced_state()
            else:
                self._unbalanced_state()
        # Comienza el administrador de posiciones
        while self.is_on.value:
            if self.state.value == StateSymbol.no_trades:
                self._no_trade_state()
            elif self.state.value == StateSymbol.bullish or self.state.value == StateSymbol.bearish:
                self._unbalanced_state()
            else:
                self._balaced_state()
    
    def _goal_profit(self)->bool:
        positions = MT5Api.get_positions(magic = self.magic)
        account_info = MT5Api.get_account_info()
        profit = account_info.profit
        for position in positions:
            profit += position.profit
        if profit >= (account_info.balance*0.03):
            self.is_on.value = False
            MT5Api.send_close_all_position()
            return True
        
        # Revisa si esta en horario de mercado para salir del bot
        if not self._is_in_market_hours():
            self.is_on.value = False
            return True
        return False
            
    def _no_trade_state(self):
        no_trade_state = TradeState.on
        is_unbalanced = False
        while self.is_on.value:
            if self.main_trend.value != StateTr3nd.unassigned:
                is_unbalanced, no_trade_state = self._trade_to_unbalance(no_trade_state)
                if is_unbalanced:
                    break
                
    def _trade_to_unbalance(self, trade_state:TradeState):
        if trade_state == TradeState.on and self.main_trend.value == self.intermediate_trend.value and self.main_trend.value == self.fast_trend.value:
            trade_state = TradeState.ready
                
        if trade_state == TradeState.ready and self.fast_trend.value != self.main_trend.value:
            trade_state = TradeState.start
        
        if trade_state == TradeState.start and self.fast_trend.value == self.main_trend.value:
            if self.main_trend == StateTr3nd.bullish:
                result = MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= OrderType.MARKET_BUY, 
                        volume=self.volume,
                        comment="+1"
                        )
                self.state.value = StateSymbol.bullish
            else:
                result = MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= OrderType.MARKET_SELL, 
                        volume=self.volume,
                        comment="-1"
                        )
                self.state.value = StateSymbol.bearish
                
            if result is None:
                trade_state = TradeState.on
                self.state.value = StateSymbol.no_trades
            else:
                return True, trade_state
        return False, trade_state
        
    def _unbalanced_state(self):
        while self.is_on.value:
            if self.main_trend.value == self.intermediate_trend.value and self.main_trend.value != self.fast_trend.value:
                positions = MT5Api.get_positions(magic = self.magic)
                if self.main_trend.value == StateTr3nd.bullish:
                    positions = [position for position in positions if position.type == OrderType.MARKET_BUY]
                else:
                    positions = [position for position in positions if position.type == OrderType.MARKET_SELL]
                last_profit = 0
                ticket = 0
                symbol = self.symbol
                for position in positions:
                    if position.profit > last_profit:
                        last_profit = position.profit
                        ticket = position.ticket
                if ticket != 0:
                    result = MT5Api.send_close_position(symbol, ticket)
                    if result:
                        if (len(positions) - 1) == 0:
                            self.state.value = StateSymbol.no_trades
                        else:
                            self.state.value = StateSymbol.balanced
                        break
                    
            if self.main_trend.value != self.intermediate_trend.value and self.intermediate_trend.value == self.fast_trend.value:
                if self.state.value == StateSymbol.bullish:
                    result = MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= OrderType.MARKET_SELL, 
                        volume=self.volume,
                        comment="-1"
                        )
                else:
                    result = MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= OrderType.MARKET_BUY, 
                        volume=self.volume,
                        comment="+1"
                        )
                if result is not None:
                    self.state.value = StateSymbol.balanced
                    break
                    
    def _balaced_state(self):
        unbalanced_trade_state = TradeState.on
        is_unbalanced = False
        while self.is_on.value:
            if self.main_trend.value == self.fast_trend.value:
                positions = MT5Api.get_positions(magic = self.magic)
                if self.main_trend.value == StateTr3nd.bullish:
                    positions = [position for position in positions if position.type == OrderType.MARKET_SELL]
                    state = StateSymbol.bullish
                    order_type = OrderType.MARKET_BUY
                else:
                    positions = [position for position in positions if position.type == OrderType.MARKET_BUY]
                    state = StateSymbol.bearish
                    order_type = OrderType.MARKET_SELL

                last_profit = 0
                ticket = 0
                symbol = self.symbol
                for position in positions:
                    if position.profit > last_profit:
                        last_profit = position.profit
                        ticket = position.ticket
                if ticket != 0:
                    result = MT5Api.send_close_position(symbol, ticket)
                    if result:
                        if (len(positions) - 1) == 0:
                            self.state.value = StateSymbol.no_trades
                        else:
                            self.state.value = state
                        break
                else:
                    result = MT5Api.send_order(
                        symbol= self.symbol, 
                        order_type= order_type, 
                        volume=self.volume,
                        comment="1" if order_type == OrderType.MARKET_BUY else "-1"
                        )
                    if result is not None:
                        self.state.value = StateSymbol.bullish if self.main_trend == StateTr3nd.bullish else StateSymbol.bearish
                        break
            
            is_unbalanced, unbalanced_trade_state = self._trade_to_unbalance(unbalanced_trade_state)
            if is_unbalanced:
                break   
    
        
    def _update_trends(self):
        # Symbolo a encontrar los trends
        symbol = self.symbol
        # Se establecen las variables para el supertrend
        atr_period = self.atr_period
        multiplier = self.multiplier
        # Obtiene las barras desde mt5
        symbol_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 0, 7200)
        # Establece el tamaño de los ladrillos de los renkos
        main_size = self.size_renko
        intermediate_size = main_size/2
        fast_size = intermediate_size/2
        # Establece y calcula los renkos
        main_renko = vRenko(main_size)
        main_renko.calculate_renko(symbol_rates)
        intermediate_renko = vRenko(intermediate_size)
        intermediate_renko.calculate_renko(symbol_rates)
        fast_renko = vRenko(fast_size)
        fast_renko.calculate_renko(symbol_rates)
        while self.is_on.value:
            # Se cerciora que alcance el profit diario para terminar el programa
            if self._goal_profit():
                break
            # Agrega la ultima barra (es la barra en formación)
            last_bar = MT5Api.get_last_bar(symbol)
            if main_renko.update_renko(last_bar):
                df = pd.DataFrame(main_renko.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier)['SUPERT_10_3.0']
                last_renko = df.iloc[-1]
                if last_renko['close'] > last_renko['supertrend']:
                    self.main_trend.value = StateTr3nd.bullish
                elif last_renko['close'] < last_renko['supertrend']:
                    self.main_trend.value = StateTr3nd.bearish
                else:
                    self.main_trend.value = StateTr3nd.unassigned
                
            if intermediate_renko.update_renko(last_bar):
                df = pd.DataFrame(intermediate_renko.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier)['SUPERT_10_3.0']
                last_renko = df.iloc[-1]
                if last_renko['close'] > last_renko['supertrend']:
                    self.main_trend.value = StateTr3nd.bullish
                elif last_renko['close'] < last_renko['supertrend']:
                    self.main_trend.value = StateTr3nd.bearish
                else:
                    self.main_trend.value = StateTr3nd.unassigned
                
            if fast_renko.update_renko(last_bar):
                df = pd.DataFrame(fast_renko.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier)['SUPERT_10_3.0']
                last_renko = df.iloc[-1]
                if last_renko['close'] > last_renko['supertrend']:
                    self.main_trend.value = StateTr3nd.bullish
                elif last_renko['close'] < last_renko['supertrend']:
                    self.main_trend.value = StateTr3nd.bearish
                else:
                    self.main_trend.value = StateTr3nd.unassigned
                
    
    def start(self):
        print(f"Tr3nd: Iniciando estrategia para {self.symbol}...")
        # Establece el volumen para las ordenes
        account_info = MT5Api.get_account_info()
        symbol_info = MT5Api.get_symbol_info(self.symbol)
        max_volume = round((account_info.balance * 0.01 * symbol_info.point), symbol_info.digits)
        if self.volume is None:
            self.volume = max_volume
        else:
            self.volume = round(self.volume, symbol_info.digits)
            if self.volume > max_volume:
                self.volume = max_volume
        # Crea un administrador para multiprocessing
        manager = multiprocessing.Manager()
        # Crea las variables que se administraran entre procesos
        self.is_on = manager.Value("b", True)
        self.state = manager.Value("i", StateSymbol.balanced)
        self.main_trend = manager.Value("i", StateTr3nd.unassigned)
        self.intermediate_trend = manager.Value("i", StateTr3nd.unassigned)
        self.fast_trend = manager.Value("i", StateTr3nd.unassigned)
        
        # Crea los procesos y los inicia
        manage_positions_process = multiprocessing.Process(target= self._manage_positions)
        manage_positions_process.start()
        update_trends_process = multiprocessing.Process(target=self._update_trends)
        update_trends_process.start()
        
        # Espera a que termine para continuar
        update_trends_process.join()
        
        # Fin del ciclo
        print("HardHedge: Finalizando estrategia...")
        
