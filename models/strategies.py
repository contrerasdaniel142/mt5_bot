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
from .technical_indicators import vRenko


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
    def __init__(self, telegram_api: TelegramApi, symbol: str, volume: float = None, size_renko:float = 40, atr_period:int = 10, multiplier:float = 3.0) -> None:
        # Api de telegram para enviar mensajes
        self._telegram_api = telegram_api
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
        self._market_opening_time = {'day':1,'hour':0, 'minute':0}
        self._market_closed_time = {'hour':19, 'minute':45}
        self.opening_balance_account = 0
        
    def _is_in_market_hours(self):
        """
        Comprueba si el momento actual se encuentra en horario de mercado.

        Returns:
            bool: True si se encuentra en horario de mercado, False si no lo está.
        """
        # Obtener la hora y minutos actuales en UTC
        current_time = datetime.now(pytz.utc) #+ timedelta(days=self._market_opening_time['day'])

        # Crear objetos time para el horario de apertura y cierre del mercado
        market_open = current_time.replace(hour=self._market_opening_time['hour'], minute=self._market_opening_time['minute'], second=0)
        market_close = current_time.replace(hour=self._market_closed_time['hour'], minute=self._market_closed_time['minute'], second=0)

        # Verificar si la hora actual está dentro del horario de mercado
        if market_open <= current_time <= market_close:
            return True
        else:
            self._telegram_api.send_message("El mercado está cerrado.")
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
        next_minute = current_time.replace(second=1, microsecond=0) + timedelta(minutes=1)

        # Calcular la cantidad de segundos que faltan hasta el próximo minuto
        seconds = (next_minute - current_time).total_seconds()

        # Dormir durante la cantidad de segundos necesarios
        time.sleep(seconds)
    
    def _manage_positions(self):
        self._telegram_api.send_message("tr3nd: Iniciacion administrador de posiciones")
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
        profit = account_info.profit
        for position in positions:
            profit += position.profit
        if profit >= (self.opening_balance_account*0.03):
            self.is_on.value = False
            MT5Api.send_close_all_position()
            return True
        
        # Revisa si esta en horario de mercado para salir del bot
        if not self._is_in_market_hours():
            self.is_on.value = False
            return True
        return False
            
    def _no_trade_state(self):
        self._telegram_api.send_message("Tr3nd: Estado sin Trade")
        trend_signal = TrendSignal.anticipating
        #self._telegram_api.send_message(f"Tr3nd: [Estado para nueva orden {no_trade_state}]")
        while self.is_on.value:
            trend_signal = self._trade_to_unbalance(trend_signal)
            if self.state.value == StateSymbol.unbalanced:
                break
                
    def _trade_to_unbalance(self, trend_signal:TrendSignal):
               
        if trend_signal == TrendSignal.anticipating:
            if self.main_trend.value == self.intermediate_trend.value and self.main_trend.value != self.fast_trend.value:
                 trend_signal = TrendSignal.ready_fast
            elif self.intermediate_trend.value != self.main_trend.value and self.main_trend.value == self.fast_trend.value:
                trend_signal = TrendSignal.ready_intermediate
            # elif self.main_trend.value == self.intermediate_trend.value and self.main_trend.value == self.fast_trend.value:
            #     trend_signal = TrendSignal.buy
        
        if trend_signal == TrendSignal.ready_fast:
            if self.intermediate_trend.value != self.main_trend.value and self.intermediate_trend.value == self.fast_trend.value:
                trend_signal = TrendSignal.anticipating
            elif self.fast_trend.value == self.main_trend.value:
                trend_signal = TrendSignal.buy
        
        elif trend_signal == TrendSignal.ready_intermediate:
            if self.intermediate_trend.value == self.main_trend.value and self.intermediate_trend.value == self.fast_trend.value:
                trend_signal = TrendSignal.buy
                            
        if trend_signal == TrendSignal.buy:
            self._telegram_api.send_message(f"Tr3nd: Creando orden nueva")
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
            self._telegram_api.send_message(f"Tr3nd: [Estado para nueva orden {trend_signal}]")
        
        return trend_signal
               
    def _unbalanced_state(self):
        self._telegram_api.send_message("Tr3nd: Estado desbalanceado")
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
                    self._telegram_api.send_message("Tr3nd: Cerrando posicion a favor con profit")
                    result = MT5Api.send_close_position(symbol, ticket)
                    if result:
                        if (len(positions) - 1) == 0:
                            self.state.value = StateSymbol.no_trades
                        else:
                            self.state.value = StateSymbol.balanced
                        break
                
            positions = MT5Api.get_positions(magic = self.magic)
            if positions is not None and len(positions) < self.max_positions:
                if self.main_trend.value != self.intermediate_trend.value and self.intermediate_trend.value == self.fast_trend.value :
                    self._telegram_api.send_message("Tr3nd: Creando orden Hedge")
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
        self._telegram_api.send_message("Tr3nd: Estado balanceado")
        trend_signal = TrendSignal.anticipating
        #self._telegram_api.send_message(f"Tr3nd: [Estado para nueva orden {no_trade_state}]")
        while self.is_on.value:
            positions = MT5Api.get_positions(magic = self.magic)
            if self.main_trend.value != self.intermediate_trend.value and self.main_trend.value == self.fast_trend.value:
                positions = MT5Api.get_positions(magic = self.magic)
                if self.main_trend.value == StateTr3nd.bullish:
                    positions = [position for position in positions if position.type == OrderType.MARKET_SELL]
                else:
                    positions = [position for position in positions if position.type == OrderType.MARKET_BUY]

                last_profit = 0
                ticket = 0
                symbol = self.symbol
                for position in positions:
                    if position.profit > last_profit:
                        last_profit = position.profit
                        ticket = position.ticket
                if ticket != 0:
                    self._telegram_api.send_message("Tr3nd: Cerrando posicion contraria con profit")
                    result = MT5Api.send_close_position(symbol, ticket)
                    if result:
                        if (len(positions) - 1) == 0:
                            self.state.value = StateSymbol.no_trades
                        else:
                            self.state.value = StateSymbol.unbalanced
                        break
                        
            if positions is not None and len(positions) < self.max_positions:
                trend_signal = self._trade_to_unbalance(trend_signal)
                if self.state.value == StateSymbol.unbalanced:
                    break 
    
    def _update_trends(self):
        self._telegram_api.send_message("Tr3nd: Update iniciado")
        # Indica si es la primera vez que inicia el metodo
        first_time = True
        # Symbolo a encontrar los trends
        symbol = self.symbol
        # Se establecen las variables para el supertrend
        atr_period = self.atr_period
        multiplier = self.multiplier
        # Obtiene las barras desde mt5
        symbol_rates = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1,  10080)
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
            # if self._goal_profit():
            #     break
            # Agrega la ultima barra (es la barra en formación)
            if not first_time:
                self._sleep_to_next_minute()
            last_bar = MT5Api.get_rates_from_pos(symbol, TimeFrame.MINUTE_1, 1, 1)
            if first_time or main_renko.update_renko(last_bar):
                df = pd.DataFrame(main_renko.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.main_trend.value != last_bar_renko['supertrend']:
                    self.main_trend.value = last_bar_renko['supertrend']
                    self._telegram_api.send_message(f"Tr3nd: [Main {self.main_trend.value}] [Intermediate {self.intermediate_trend.value}] [Fast {self.fast_trend.value}]")
                    self._telegram_api.send_message("")
                
            if first_time or intermediate_renko.update_renko(last_bar):
                df = pd.DataFrame(intermediate_renko.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.intermediate_trend.value != last_bar_renko['supertrend']:
                    self.intermediate_trend.value = last_bar_renko['supertrend']
                    self._telegram_api.send_message(f"Tr3nd: [Main {self.main_trend.value}] [Intermediate {self.intermediate_trend.value}] [Fast {self.fast_trend.value}]")
                    self._telegram_api.send_message("")
                
            if first_time or fast_renko.update_renko(last_bar):
                df = pd.DataFrame(fast_renko.renko_data)
                df['supertrend'] = ta.supertrend(df['high'], df['low'], df['close'], length=atr_period, multiplier=multiplier).iloc[:, 1]
                last_bar_renko = df.iloc[-1]
                if self.fast_trend.value != last_bar_renko['supertrend']:
                    self.fast_trend.value = last_bar_renko['supertrend']
                    self._telegram_api.send_message(f"Tr3nd: [Main {self.main_trend.value}] [Intermediate {self.intermediate_trend.value}] [Fast {self.fast_trend.value}]")
                    self._telegram_api.send_message("")
                    
            if first_time:
                first_time = False
                
    
    def start(self):
        self._telegram_api.send_message(f"Tr3nd: Iniciando estrategia para {self.symbol}...")
        # Establece el volumen para las ordenes
        account_info = MT5Api.get_account_info()
        self.opening_balance_account = account_info.balance
        symbol_info = MT5Api.get_symbol_info(self.symbol)
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
        positions = MT5Api.get_positions(magic = self.magic)
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
        self._telegram_api.send_message("HardHedge: Finalizando estrategia...")
        

