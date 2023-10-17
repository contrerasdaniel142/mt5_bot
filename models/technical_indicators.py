#region Descripción
# El archivo "technical_indicators.py" es un componente en el sistema de trading 
# automatizado que contiene definiciones de indicadores técnicos comúnmente utilizados 
# en análisis técnico y trading algorítmico. Su función principal es proporcionar métodos 
# y funciones para calcular estos indicadores a partir de datos de mercado y utilizarlos en estrategias de trading.
#endregion

#region Importaciones
# Para realizar operaciones numéricas eficientes
import numpy as np
import pandas_ta as ta 

# Importaciones para el manejo de datos
from .mt5.enums import FieldType
from numpy import ndarray

# Importaciones necesarias para definir tipos de datos
from typing import Dict, List, Tuple, Any

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime
from .utilities import convert_time_to_mt5


#endregion

class vRenko:
    def __init__(self, rates: ndarray[FieldType.rates_dtype], brick_size:float, wicks:bool = False):
        """
        Inicializa una instancia de vRenko con un tamaño de ladrillo especificado.

        Args:
            brick_size (float): El tamaño de ladrillo para el gráfico Renko.
        """
        self.brick_size = brick_size
        self.wicks = wicks
        self.dtype_renko = [('time', datetime), ('type', 'U4'), ('open', float), ('high', float), ('low', float), ('close', float)]
        self.renko_data = np.empty(0, dtype= self.dtype_renko)
        self._current_brick: Dict[str, Any]= None
        self._calculate_renko(rates)
    
    def _calculate_renko(self, rates: ndarray[FieldType.rates_dtype]):
        """
        Calcula y genera datos de gráfico Renko basados en las tasas de precios proporcionadas.

        Args:
            rates (ndarray): Un array de barras de MT5 que incluye información de open, high, low, close, etc.
        """
        renko_bricks = []
        self._current_brick = None

        for rate in rates:
            if self._current_brick is None:
                close = rate['close']
                open = rate['open']
                
                quantity_high = int(rate['open']/self.brick_size)
                quantity_low = int(rate['close']/self.brick_size)
                
                if open > close:
                    close = (quantity_high * self.brick_size)
                    type = 'down'
                else:
                    close = (quantity_low + 1) * self.brick_size
                    type = 'up'
                    
                self._current_brick = {
                    'type': type,
                    'open': close,
                    'close': close,
                    'last_high': None,
                    'last_low': None
                }
                self._add_bricks(rate, renko_bricks)
                
            else:
                self._add_bricks(rate, renko_bricks)

        self.renko_data = np.array(renko_bricks, dtype=self.dtype_renko)
        
    def _add_bricks(self, rate:Tuple, renko_bricks: List[Tuple] = None)-> bool:
        """
        Añade ladrillos Renko al gráfico.

        Args:
            rate (Tuple): Información de una barra de precios de MT5.
            renko_bricks (List[Tuple], opcional): Lista de ladrillos Renko.
        Returns:
            bool: retorna verdadero si se agrego uno o mas ladrillos, en caso contrario False
        """
        current_type = self._current_brick['type']
        current_open = self._current_brick['open']
        current_close = self._current_brick['close']
        new_type = None

        if current_close < rate['close']:
            price_diff = rate['close'] - current_close
            new_type = 'up'
        # elif current_type == 'up' and current_open > rate['close']:
        #     price_diff = current_open - rate['close']
        #     new_type = 'down2'
        # elif current_type == 'down' and current_open < rate['close']:
        #     price_diff = rate['close'] - current_open
        #     new_type = 'up2'
        elif current_close > rate['close']:
            price_diff = current_close - rate['close']
            new_type = 'down'
        
        if self.wicks:
            if self._current_brick['last_high'] is None or self._current_brick['last_high'] < rate['high']:
                self._current_brick['last_high'] = rate['high']
            if self._current_brick['last_low'] is None or self._current_brick['last_low'] > rate['low']:
                self._current_brick['last_high'] = rate['low']
        
        if new_type is None:
            return False

        brick_count = int(price_diff // self.brick_size)
        
        if brick_count == 0:
            return False
        
        for i in range(int(brick_count)):
            
            unix = rate['time']
            time = datetime.fromtimestamp(unix)
            convert_time = convert_time_to_mt5(time)
            self._current_brick['time'] = convert_time
            
            if 'up' in new_type:
                self._current_brick['type'] = 'up'
                self._current_brick['open'] = self._current_brick['close'] if new_type == 'up' else self._current_brick['open']
                self._current_brick['close'] = self._current_brick['open'] + self.brick_size
                self._current_brick['high'] = self._current_brick['close']
                self._current_brick['low'] = self._current_brick['open'] if self._current_brick['last_low'] is None else self._current_brick['last_low']
                self._current_brick['last_low'] = None
                new_type = 'up'
            elif 'down' in new_type:
                self._current_brick['type'] = 'down'
                self._current_brick['open'] = self._current_brick['close'] if new_type == 'down' else self._current_brick['open']
                self._current_brick['close'] = self._current_brick['open'] - self.brick_size
                self._current_brick['high'] = self._current_brick['open'] if self._current_brick['last_high'] is None else self._current_brick['last_high']
                self._current_brick['low'] = self._current_brick['close']
                self._current_brick['last_high'] = None
                new_type = 'down'

                
            brick = (
                self._current_brick['time'],
                self._current_brick['type'],
                self._current_brick['open'],
                self._current_brick['high'],
                self._current_brick['low'],
                self._current_brick['close'],
            )

            if renko_bricks is None:
                self.renko_data = np.append(self.renko_data, np.array([brick], dtype=self.dtype_renko))
            else:
                renko_bricks.append(brick)
        
        return True
            
    def update_renko(self, rates)-> bool:
        """
        Actualiza el gráfico Renko basado en la barras proporcionada de MT5.

        Args:
            rates (ndarray): Información de una o varias barra de precios de MT5.
        Returns:
            bool: retorna verdadero si se agrego uno o mas ladrillos, en caso contrario False
        """
        is_update = False
        if self.renko_data.size != 0:
            for rate in rates:
                result = self._add_bricks(rate)
                if result:
                    is_update = True
        return is_update
        
    def get_renko_data(self):
        """
        Obtiene los datos del gráfico Renko calculados.

        Returns:
            ndarray: Un array de datos del gráfico Renko.
        """
        return self.renko_data

class HeikenAshi:
    def __init__(self, rates):
        self.rates = rates
        self.dtype_ha = [('time', datetime), ('open', float), ('high', float), ('low', float), ('close', float)]
        self.heiken_ashi = np.empty(0, dtype=self.dtype_ha)
        self._calculate_heiken_ashi()
        
    def _calculate_heiken_ashi(self):
        for i in range(1, len(self.rates)):
            current_rate = self.rates[i]
            self._add_ha_bar(current_rate)
        
    def update_HeikenAshi(self, new_rate: ndarray):
        self.rates = np.append(self.rates, new_rate)
        for current_rate in new_rate:
            self._add_ha_bar(current_rate)
    
    def _add_ha_bar(self, current_rate: Tuple):
        previous_ha = self.heiken_ashi[-1] if len(self.heiken_ashi) > 0 else self.rates[-1]
        ha_open = (previous_ha['open'] + previous_ha['close']) / 2
        ha_close = (current_rate['open'] + current_rate['high'] + current_rate['low'] + current_rate['close']) / 4
        ha_high = np.max([current_rate['high'], ha_open, ha_close])
        ha_low = np.min([current_rate['low'], ha_open, ha_close])
        
        new_ha_bar = (current_rate['time'], ha_open, ha_high, ha_low, ha_close)
        self.heiken_ashi = np.append(self.heiken_ashi, np.array([new_ha_bar], dtype=self.dtype_ha))
    
    def get_heiken_ashi(self):
        return self.heiken_ashi

    def get_heiken_ashi(self):
        return self.heiken_ashi
    