import MetaTrader5 as mt5
from numpy import dtype


class TimeFrame:
    """
    Enum de los marcos de tiempo disponibles en MetaTrader 5.

    Los valores enumerados representan los diferentes marcos de tiempo utilizados en el análisis técnico y en la programación de estrategias de trading.

    Valores:
    - MINUTE_1: Marco de tiempo de 1 minuto.
    - MINUTE_2: Marco de tiempo de 2 minutos.
    - MINUTE_3: Marco de tiempo de 3 minutos.
    - ...
    - HOUR_1: Marco de tiempo de 1 hora.
    - ...
    - DAY_1: Marco de tiempo de 1 día.
    - WEEK_1: Marco de tiempo de 1 semana.
    - MONTHLY_1: Marco de tiempo de 1 mes.
    """
    MINUTE_1                            = 1
    MINUTE_2                            = 2
    MINUTE_3                            = 3
    MINUTE_4                            = 4
    MINUTE_5                            = 5
    MINUTE_6                            = 6
    MINUTE_10                           = 10
    MINUTE_12                           = 12
    MINUTE_15                           = 15
    MINUTE_20                           = 20
    MINUTE_30                           = 30
    HOUR_1                              = 1  | 0x4000
    HOUR_2                              = 2  | 0x4000
    HOUR_3                              = 3  | 0x4000
    HOUR_4                              = 4  | 0x4000
    HOUR_6                              = 6  | 0x4000
    HOUR_8                              = 8  | 0x4000
    HOUR_12                             = 12 | 0x4000
    DAY_1                               = 24 | 0x4000
    WEEK_1                              = 1  | 0x8000
    MONTHLY_1                           = 1  | 0xC000
    
class CopyTicks:
    """
    Enum de las opciones disponibles para la copia de ticks en MetaTrader 5.

    Valores:
    - COPY_TICKS_ALL: Copiar todos los ticks disponibles.
    - COPY_TICKS_INFO: Copiar solo información sobre los ticks.
    - COPY_TICKS_TRADE: Copiar solo los ticks de trading.
    """
    COPY_TICKS_ALL                      = -1
    COPY_TICKS_INFO                     = 1
    COPY_TICKS_TRADE                    = 2
    
class TickFlag:
    """
    Enum de las banderas de ticks en MetaTrader 5.

    Estas banderas se utilizan para identificar diferentes tipos de datos de ticks en un flujo de datos de ticks.

    Valores:
    - TICK_FLAG_BID: Indica un tick de oferta (bid).
    - TICK_FLAG_ASK: Indica un tick de demanda (ask).
    - TICK_FLAG_LAST: Indica el último tick (precio de cierre).
    - TICK_FLAG_VOLUME: Indica un tick de volumen.
    - TICK_FLAG_BUY: Indica un tick de compra.
    - TICK_FLAG_SELL: Indica un tick de venta.
    """
    TICK_FLAG_BID                       = 0x02
    TICK_FLAG_ASK                       = 0x04
    TICK_FLAG_LAST                      = 0x08
    TICK_FLAG_VOLUME                    = 0x10
    TICK_FLAG_BUY                       = 0x20
    TICK_FLAG_SELL                      = 0x40
    
class TradeActions:
    """
    Enum de las acciones de trading en MetaTrader 5.

    Estas acciones representan los tipos de operaciones que se pueden realizar en una plataforma de trading.

    Valores:
    - TRADE_ACTION_DEAL: Realizar una orden de mercado inmediata con los parámetros especificados.
    - TRADE_ACTION_PENDING: Colocar una orden pendiente que se ejecutará bajo condiciones especificadas.
    - TRADE_ACTION_SLTP: Modificar Stop Loss y Take Profit de una posición abierta.
    - TRADE_ACTION_MODIFY: Modificar los parámetros de una orden colocada previamente.
    - TRADE_ACTION_REMOVE: Eliminar una orden pendiente colocada previamente.
    - TRADE_ACTION_CLOSE_BY: Cerrar una posición ejecutando una operación opuesta.
    """
    TRADE_ACTION_DEAL                   = 1  # Realizar una orden de mercado inmediata con los parámetros especificados
    TRADE_ACTION_PENDING                = 5  # Colocar una orden pendiente que se ejecutará bajo condiciones especificadas
    TRADE_ACTION_SLTP                   = 6  # Modificar Stop Loss y Take Profit de una posición abierta
    TRADE_ACTION_MODIFY                 = 7  # Modificar los parámetros de una orden colocada previamente
    TRADE_ACTION_REMOVE                 = 8  # Eliminar una orden pendiente colocada previamente
    TRADE_ACTION_CLOSE_BY               = 10  # Cerrar una posición ejecutando una operación opuesta

class OrderType:
    """
    Enumeración de los tipos de órdenes en MetaTrader 5.

    Los valores enumerados representan los diferentes tipos de órdenes utilizados en el trading en MetaTrader 5.

    Valores:
    - MARKET_BUY: Orden de compra de mercado.
    - MARKET_SELL: Orden de venta de mercado.
    - BUY_LIMIT: Orden pendiente de compra (Buy Limit).
    - SELL_LIMIT: Orden pendiente de venta (Sell Limit).
    - BUY_STOP: Orden pendiente de compra (Buy Stop).
    - SELL_STOP: Orden pendiente de venta (Sell Stop).
    - BUY_STOP_LIMIT: Orden pendiente de compra con límite (Buy Stop Limit).
    - SELL_STOP_LIMIT: Orden pendiente de venta con límite (Sell Stop Limit).
    - CLOSE_BY: Orden para cerrar una posición mediante una operación opuesta.
    """
    MARKET_BUY                          = 0
    MARKET_SELL                         = 1
    BUY_LIMIT                           = 2
    SELL_LIMIT                          = 3
    BUY_STOP                            = 4
    SELL_STOP                           = 5
    BUY_STOP_LIMIT                      = 6
    SELL_STOP_LIMIT                     = 7
    CLOSE_BY                            = 8

class FieldType:
    """
    Clase que define los tipos de datos de campos utilizados en MetaTrader 5 para información de precios y ticks.

    Los tipos de datos definidos aquí son utilizados en la estructura de datos de precios y ticks en MetaTrader 5.

    Atributos:
    - rates_dtype: Tipo de datos para información de precios (OHLCV).
    - ticks_dtype: Tipo de datos para datos de ticks (bid, ask, last, volumen, etc.).
    """
    rates_dtype = dtype([
        ('time', float),
        ('open', float),
        ('high', float),
        ('low', float),
        ('close', float),
        ('tick_volume', int),
        ('spread', int),
        ('real_volume', int)
    ])
    ticks_dtype = dtype([
        ('time', 'datetime64[s]'),
        ('bid', 'f8'),
        ('ask', 'f8'),
        ('last', 'f8'),
        ('volume', 'i4'),
        ('time_msc', 'i8'),
        ('flags', 'i4'),
        ('volume_real', 'f8')
    ])
    
