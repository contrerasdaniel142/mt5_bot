import numpy as np          # Para realizar operaciones numéricas eficientes

# Importaciones para el manejo de datos
from .mt5.enums import FieldType
from numpy import ndarray


class vRenko:
    def __init__(self, brick_size:float, rates: ndarray[FieldType.rates_dtype]) -> None:
        self.brick_size = brick_size
        self.bricks: ndarray = np.empty(shape=(0,))
        
    
    