#region Descripción
# El archivo "technical_indicators.py" es un componente en el sistema de trading 
# automatizado que contiene definiciones de indicadores técnicos comúnmente utilizados 
# en análisis técnico y trading algorítmico. Su función principal es proporcionar métodos 
# y funciones para calcular estos indicadores a partir de datos de mercado y utilizarlos en estrategias de trading.
#endregion

#region Importaciones
# Para realizar operaciones numéricas eficientes
import numpy as np 
import pandas as pd

# Importaciones para el manejo de datos
from .mt5.enums import FieldType
from numpy import ndarray

# Importaciones necesarias para definir tipos de datos
from typing import Dict, List, Tuple, Any

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta
from .utilities import convert_time_to_mt5

#endregion

class vRenko:
    def __init__(self, brick_size:float):
        """
        Inicializa una instancia de vRenko con un tamaño de ladrillo especificado.

        Args:
            brick_size (float): El tamaño de ladrillo para el gráfico Renko.
        """
        self.brick_size = brick_size
        self.dtype_renko = [('time', datetime), ('type', str), ('open', float), ('high', float), ('low', float), ('close', float)]
        self.renko_data = np.empty(0, dtype= self.dtype_renko)
    
    def calculate_renko(self, rates: ndarray[FieldType.rates_dtype]):
        """
        Calcula y genera datos de gráfico Renko basados en las tasas de precios proporcionadas.

        Args:
            rates (ndarray): Un array de barras de MT5 que incluye información de open, high, low, close, etc.
        """
        renko_bricks = []
        current_brick = None

        for rate in rates:
            if current_brick is None:
                close = rate['close']
                open = rate['open']
                quantity_high = int(rate['open']/self.brick_size)
                quantity_low = int(rate['close']/self.brick_size)
                if open > close:
                    open = (quantity_high * self.brick_size)
                    type = 'down'
                else:
                    open = (quantity_low + 1) * self.brick_size
                    type = 'up'
                current_brick = {
                    'type': type,
                    'open': open,
                    'close': open
                }
                self._add_bricks(rate, current_brick, renko_bricks)
                
            else:
                self._add_bricks(rate, current_brick, renko_bricks)

        self.renko_data = np.array(renko_bricks, dtype=self.dtype_renko)
        
    def _add_bricks(self, rate:Tuple, current_brick: Dict[str, Any], renko_bricks: List[Tuple] = None)-> bool:
        """
        Añade ladrillos Renko al gráfico.

        Args:
            rate (Tuple): Información de una barra de precios de MT5.
            current_brick (Dict[str, Any]): Ladrillo Renko actual.
            renko_bricks (List[Tuple], opcional): Lista de ladrillos Renko.
        Returns:
            bool: retorna verdadero si se agrego uno o mas ladrillos, en caso contrario False
        """
        price_diff = None
        type = None
        if current_brick['type'] == 'up':
            if current_brick['close'] < rate['close']:
                price_diff = rate['close'] - current_brick['close']
                type = 'up'
            elif current_brick['open'] > rate['close']:
                price_diff = current_brick['open'] - rate['close']
                type = 'down2'
        else:
            if current_brick['open'] < rate['close']:
                price_diff = rate['close'] - current_brick['open']
                type = 'up2'
            elif current_brick['close'] > rate['close']:
                price_diff = current_brick['close'] - rate['close']
                type = 'down'
                
        if price_diff is not None:
            brick_count = price_diff // self.brick_size
            for i in range(int(brick_count)):
                if 'up' in type:
                    current_brick['time'] = convert_time_to_mt5(datetime.fromtimestamp(rate['time']))
                    current_brick['type'] = 'up'
                    current_brick['open'] = current_brick['close'] if type == 'up' else current_brick['open']
                    current_brick['close'] = current_brick['open'] + self.brick_size
                    current_brick['high'] = current_brick['close']
                    current_brick['low'] = rate['low'] if i == 0 else current_brick['open']       
                    type = 'up'
                elif 'down' in type:
                    current_brick['time'] = convert_time_to_mt5(datetime.fromtimestamp(rate['time']))
                    current_brick['type'] = 'down'
                    current_brick['open'] = current_brick['close'] if type == 'down' else current_brick['open']
                    current_brick['close'] = current_brick['open'] - self.brick_size
                    current_brick['high'] = rate['high'] if i == 0 else current_brick['open']
                    current_brick['low'] = current_brick['close']
                    type = 'down'

                    
                brick = (current_brick['time'], current_brick['type'], current_brick['open'], current_brick['high'], current_brick['low'], current_brick['close'],)
                    
                if renko_bricks is None:
                    self.renko_data = np.append(self.renko_data, np.array([brick], dtype=self.dtype_renko))
                else:
                    renko_bricks.append(brick)
                return True
        
        return False         
            
    def update_renko(self, rate)-> bool:
        """
        Actualiza el gráfico Renko basado en la barra proporcionada de MT5.

        Args:
            rate (Tuple): Información de una barra de precios de MT5.
        Returns:
            bool: retorna verdadero si se agrego uno o mas ladrillos, en caso contrario False
        """
        result = False
        if self.renko_data.size != 0:
            last_brick = self.renko_data[-1].copy()
            result = self._add_bricks(rate, last_brick)
        return result
        
    def get_renko_data(self):
        """
        Obtiene los datos del gráfico Renko calculados.

        Returns:
            ndarray: Un array de datos del gráfico Renko.
        """
        return self.renko_data
