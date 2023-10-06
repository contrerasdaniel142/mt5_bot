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
from mt5.enums import FieldType
from numpy import ndarray

# Importaciones necesarias para definir tipos de datos
from typing import Dict, List, Tuple, Any

# Importaciones necesarias para manejar fechas y tiempo
from datetime import datetime, timedelta

#endregion

class vRenko:
    def __init__(self, brick_size):
        """
        Inicializa una instancia de vRenko con un tamaño de ladrillo especificado.

        Args:
            brick_size (float): El tamaño de ladrillo para el gráfico Renko.
        """
        self.brick_size = brick_size
        self.dtype_renko = [('time', 'datetime64[s]'), ('type', '<U4'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8')]
        self.renko_rates = np.empty(0, dtype= self.dtype_renko)

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
                else:
                    open = (quantity_low + 1) * self.brick_size
                current_brick = {
                    'open': open,
                    'close': open
                }
                self._add_bricks(rate, current_brick, renko_bricks)
                
            else:
                self._add_bricks(rate, current_brick, renko_bricks)

        self.renko_rates = np.array(renko_bricks, dtype=self.dtype_renko)
        
    def _add_bricks(self, rate:Tuple, current_brick: Dict[str, Any], renko_bricks: List[Tuple] = None):
        """
        Añade ladrillos Renko al gráfico.

        Args:
            rate (Tuple): Información de una barra de precios de MT5.
            current_brick (Dict[str, Any]): Ladrillo Renko actual.
            renko_bricks (List[Tuple], opcional): Lista de ladrillos Renko.
        """
        price_diff = rate['close'] - current_brick['open']
        brick_count = abs(price_diff) // self.brick_size
        for i in range(int(brick_count)):
            if price_diff > 0:
                current_brick['time'] = self._convert_time_to_mt5(datetime.fromtimestamp(rate['time']))
                current_brick['type'] = 'up'
                current_brick['close'] += self.brick_size
                current_brick['high'] = current_brick['close']
                current_brick['low'] = rate['low'] if i == 0 else current_brick['open']
            else:
                current_brick['time'] = self._convert_time_to_mt5(datetime.fromtimestamp(rate['time']))
                current_brick['type'] = 'down'
                current_brick['close'] -= self.brick_size
                current_brick['high'] = rate['high'] if i == 0 else current_brick['open']
                current_brick['low'] = current_brick['close']
            
            brick = (current_brick['time'], current_brick['type'], current_brick['open'], current_brick['high'], current_brick['low'], current_brick['close'],)
                
            if renko_bricks is None:
                self.renko_rates = np.append(self.renko_rates, np.array([brick], dtype=self.dtype_renko))
            else:
                renko_bricks.append(brick)
                current_brick.update({
                        'open': current_brick['close'], 'close': current_brick['close']
                    })
            
    def _convert_time_to_mt5(self, date: datetime) -> datetime:
        """
        Suma 5 horas a la fecha y hora proporcionada.

        Args:
            date (datetime): Fecha y hora en formato UTC.

        Returns:
            datetime: La fecha y hora resultante después de sumar 5 horas.
        """
        # Suma 5 horas a la fecha y hora original
        dt_mt5 = date + timedelta(hours=5)
        
        return dt_mt5
    
    def update_renko(self, rate):
        """
        Actualiza el gráfico Renko basado en la barra proporcionada de MT5.

        Args:
            rate (Tuple): Información de una barra de precios de MT5.
        """
        if self.renko_rates.size != 0:
            last_brick = self.renko_rates[-1].copy()
            self._add_bricks(rate, last_brick)
  
    def get_renko_data(self):
        """
        Obtiene los datos del gráfico Renko calculados.

        Returns:
            ndarray: Un array de datos del gráfico Renko.
        """
        return self.renko_rates

