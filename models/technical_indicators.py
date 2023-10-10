#region Descripción
# El archivo "technical_indicators.py" es un componente en el sistema de trading 
# automatizado que contiene definiciones de indicadores técnicos comúnmente utilizados 
# en análisis técnico y trading algorítmico. Su función principal es proporcionar métodos 
# y funciones para calcular estos indicadores a partir de datos de mercado y utilizarlos en estrategias de trading.
#endregion

#region Importaciones
# Para realizar operaciones numéricas eficientes
import numpy as np 

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
    def __init__(self, brick_size:float):
        """
        Inicializa una instancia de vRenko con un tamaño de ladrillo especificado.

        Args:
            brick_size (float): El tamaño de ladrillo para el gráfico Renko.
        """
        self.brick_size = brick_size
        self.dtype_renko = [('time', datetime), ('type', 'U4'), ('open', float), ('high', float), ('low', float), ('close', float)]
        self.renko_data = np.empty(0, dtype= self.dtype_renko)
        self._current_brick: Dict[str, Any]= None
    
    def calculate_renko(self, rates: ndarray[FieldType.rates_dtype]):
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
                    open = (quantity_high * self.brick_size)
                    type = 'down'
                else:
                    open = (quantity_low + 1) * self.brick_size
                    type = 'up'
                    
                self._current_brick = {
                    'type': type,
                    'open': open,
                    'close': open,
                    'last_high': rate['high'],
                    'last_low': rate['low']
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
        price_diff = None
        type = None
        if self._current_brick['type'] == 'up':
            if self._current_brick['close'] < rate['close']:
                price_diff = rate['close'] - self._current_brick['close']
                type = 'up'
            elif self._current_brick['open'] > rate['close']:
                price_diff = self._current_brick['open'] - rate['close']
                type = 'down2'
        else:
            if self._current_brick['open'] < rate['close']:
                price_diff = rate['close'] - self._current_brick['open']
                type = 'up2'
            elif self._current_brick['close'] > rate['close']:
                price_diff = self._current_brick['close'] - rate['close']
                type = 'down'
        
        
        if self._current_brick['last_high'] is None or self._current_brick['last_high'] < rate['high']:
            self._current_brick['last_high'] = rate['high']
            
        if self._current_brick['last_low'] is None or self._current_brick['last_low'] > rate['low']:
            self._current_brick['last_low'] = rate['low']
                
        if price_diff is not None:
            brick_count = price_diff // self.brick_size
                    
            for i in range(int(brick_count)):
                if 'up' in type:
                    self._current_brick['time'] = convert_time_to_mt5(datetime.fromtimestamp(rate['time']))
                    self._current_brick['type'] = 'up'
                    self._current_brick['open'] = self._current_brick['close'] if type == 'up' else self._current_brick['open']
                    self._current_brick['close'] = self._current_brick['open'] + self.brick_size
                    self._current_brick['high'] = self._current_brick['close']
                    self._current_brick['low'] = self._current_brick['open'] if self._current_brick['last_low'] is None else self._current_brick['last_low']
                    self._current_brick['last_low'] = None
                    type = 'up'
                elif 'down' in type:
                    self._current_brick['time'] = convert_time_to_mt5(datetime.fromtimestamp(rate['time']))
                    self._current_brick['type'] = 'down'
                    self._current_brick['open'] = self._current_brick['close'] if type == 'down' else self._current_brick['open']
                    self._current_brick['close'] = self._current_brick['open'] - self.brick_size
                    self._current_brick['high'] = self._current_brick['open'] if self._current_brick['last_high'] is None else self._current_brick['last_high']
                    self._current_brick['low'] = self._current_brick['close']
                    self._current_brick['last_high'] = None
                    type = 'down'

                    
                brick = (self._current_brick['time'], self._current_brick['type'], self._current_brick['open'], self._current_brick['high'], self._current_brick['low'], self._current_brick['close'],)
                    
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
            result = self._add_bricks(rate)
        return result
        
    def get_renko_data(self):
        """
        Obtiene los datos del gráfico Renko calculados.

        Returns:
            ndarray: Un array de datos del gráfico Renko.
        """
        return self.renko_data
