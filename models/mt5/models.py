
class Tick:
    """
    Representa un objeto Tick de MetaTrader 5 (MT5).

    Attributes:
        time (int): Marca de tiempo del tick en formato Unix timestamp.
        bid (float): Precio de oferta (el precio al cual los compradores están dispuestos a comprar).
        ask (float): Precio de venta (el precio al cual los vendedores están dispuestos a vender).
        last (float): Último precio negociado en el mercado.
        volume (int): Volumen de operaciones para ese tick.
        time_msc (int): Marca de tiempo del tick con milisegundos.
        volume_real (float): Volumen real del tick.
        flags (int): Indicador de flags para el tick.
        n_fields (int): Número total de campos.
        n_sequence_fields (int): Número total de campos de secuencia.
        n_unnamed_fields (int): Número total de campos sin nombre.

    """
    time: int = None
    bid: float = None
    ask: float = None
    last: float = None
    volume: int = None
    time_msc: int = None
    volume_real: float = None
    flags: int = None
    n_fields: int = None
    n_sequence_fields: int = None
    n_unnamed_fields: int = None
    
class MqlTradeResult:
    """
    Representa la estructura MqlTradeResult.

    Attributes:
        retcode (int): Código del resultado de operación.
        deal (int): Ticket de transacción, si está concluida.
        order (int): Ticket de la orden, si está colocada.
        volume (float): Volumen de la transacción confirmado por el corredor.
        price (float): Precio en la transacción confirmada por el corredor.
        bid (float): Precio actual de la oferta en el mercado (precios de recuota).
        ask (float): Precio actual de la demanda en el mercado (precios de recuota).
        comment (str): Comentarios del corredor acerca de la operación.
        request_id (int): Identificador de la solicitud.
        retcode_external (int): Código de respuesta del sistema de comercio exterior.

    """
    retcode: int = None
    deal: int = None
    order: int = None
    volume: float = None
    price: float = None
    bid: float = None
    ask: float = None
    comment: str = None
    request_id: int = None
    retcode_external: int = None

class TradeDeal:
    """
    Representa un objeto TradeDeal en MetaTrader 5 (MT5).

    Attributes:
        comment (str): Comentario de la operación.
        commission (float): Comisión de la operación.
        entry (int): Entrada de la operación.
        external_id (str): ID externo de la operación.
        fee (float): Tarifa de la operación.
        magic (int): Identificador mágico.
        n_fields (int): Número total de campos.
        n_sequence_fields (int): Número total de campos de secuencia.
        n_unnamed_fields (int): Número total de campos sin nombre.
        order (int): Ticket de la orden asociada.
        position_id (int): ID de la posición.
        price (float): Precio de la operación.
        profit (float): Ganancia de la operación.
        reason (int): Razón de la operación.
        swap (float): Swap de la operación.
        symbol (str): Símbolo del instrumento financiero.
        ticket (int): Ticket de la operación.
        time (int): Marca de tiempo de la operación en formato Unix timestamp.
        time_msc (int): Marca de tiempo de la operación con milisegundos.
        type (int): Tipo de operación (e.g., compra o venta).
        volume (float): Volumen de la operación.
    """
    comment: str = None
    commission: float = None
    entry: int = None
    external_id: str = None
    fee: float = None
    magic: int = None
    n_fields: int = None
    n_sequence_fields: int = None
    n_unnamed_fields: int = None
    order: int = None
    position_id: int = None
    price: float = None
    profit: float = None
    reason: int = None
    swap: float = None
    symbol: str = None
    ticket: int = None
    time: int = None
    time_msc: int = None
    type: int = None
    volume: float = None

class TradeOrder:
    """
    Representa un objeto TradeOrder en MetaTrader 5 (MT5).

    Attributes:
        comment (str): Comentario de la orden.
        external_id (str): ID externo de la orden.
        magic (int): Identificador mágico de la orden.
        n_fields (int): Número total de campos.
        n_sequence_fields (int): Número total de campos de secuencia.
        n_unnamed_fields (int): Número total de campos sin nombre.
        position_by_id (int): Posición por ID.
        position_id (int): ID de la posición.
        price_current (float): Precio actual de la orden.
        price_open (float): Precio de apertura de la orden.
        price_stoplimit (float): Precio de stop/limit de la orden.
        reason (int): Razón de la orden.
        sl (float): Stop Loss de la orden.
        state (int): Estado de la orden.
        symbol (str): Símbolo del instrumento financiero.
        ticket (int): Ticket de la orden.
        time_done (int): Marca de tiempo de la orden completada en formato Unix timestamp.
        time_done_msc (int): Marca de tiempo de la orden completada con milisegundos.
        time_expiration (int): Marca de tiempo de caducidad de la orden.
        time_setup (int): Marca de tiempo de configuración de la orden en formato Unix timestamp.
        time_setup_msc (int): Marca de tiempo de configuración de la orden con milisegundos.
        tp (float): Take Profit de la orden.
        type (int): Tipo de orden.
        type_filling (int): Tipo de llenado de la orden.
        type_time (int): Tipo de tiempo de la orden.
        volume_current (float): Volumen actual de la orden.
        volume_initial (float): Volumen inicial de la orden.
    """
    comment: str = None
    external_id: str = None
    magic: int = None
    n_fields: int = None
    n_sequence_fields: int = None
    n_unnamed_fields: int = None
    position_by_id: int = None
    position_id: int = None
    price_current: float = None
    price_open: float = None
    price_stoplimit: float = None
    reason: int = None
    sl: float = None
    state: int = None
    symbol: str = None
    ticket: int = None
    time_done: int = None
    time_done_msc: int = None
    time_expiration: int = None
    time_setup: int = None
    time_setup_msc: int = None
    tp: float = None
    type: int = None
    type_filling: int = None
    type_time: int = None
    volume_current: float = None
    volume_initial: float = None

class TradePosition:
    """
    Representa un objeto TradePosition en MetaTrader 5 (MT5).

    Attributes:
        ticket (int): Ticket de la posición.
        time (int): Marca de tiempo de la posición en formato Unix timestamp.
        type (int): Tipo de posición.
        magic (int): Identificador mágico de la posición.
        identifier (int): Identificador de la posición.
        reason (int): Razón de la posición.
        volume (float): Volumen de la posición.
        price_open (float): Precio de apertura de la posición.
        sl (float): Stop Loss de la posición.
        tp (float): Take Profit de la posición.
        price_current (float): Precio actual de la posición.
        swap (float): Swap de la posición.
        profit (float): Ganancia de la posición.
        symbol (str): Símbolo del instrumento financiero.
        comment (str): Comentario de la posición.
        time_expiration (int): Marca de tiempo de caducidad de la posición.
        type_time (int): Tipo de tiempo de la posición.
        state (int): Estado de la posición.
        position_by_id (int): Posición por ID.
        volume_current (float): Volumen actual de la posición.
        price_stoplimit (float): Precio de stop/limit de la posición.
    """
    ticket: int = None
    time: int = None
    type: int = None
    magic: int = None
    identifier: int = None
    reason: int = None
    volume: float = None
    price_open: float = None
    sl: float = None
    tp: float = None
    price_current: float = None
    swap: float = None
    profit: float = None
    symbol: str = None
    comment: str = None
    time_expiration: int = None
    type_time: int = None
    state: int = None
    position_by_id: int = None
    volume_current: float = None
    price_stoplimit: float = None

class AccountInfo:
    """
    Representa un objeto AccountInfo en MetaTrader 5 (MT5).

    Attributes:
        assets (float): Activos.
        balance (float): Saldo.
        commission_blocked (float): Comisión bloqueada.
        company (str): Nombre de la compañía.
        credit (float): Crédito.
        currency (str): Moneda.
        currency_digits (int): Dígitos de la moneda.
        equity (float): Patrimonio.
        fifo_close (bool): Cierre FIFO.
        leverage (int): Apalancamiento.
        liabilities (float): Pasivos.
        limit_orders (int): Órdenes límite.
        login (int): Inicio de sesión.
        margin (float): Margen.
        margin_free (float): Margen libre.
        margin_initial (float): Margen inicial.
        margin_level (float): Nivel de margen.
        margin_maintenance (float): Margen de mantenimiento.
        margin_mode (int): Modo de margen.
        margin_so_call (float): Margen de llamada de margen.
        margin_so_mode (int): Modo de llamada de margen.
        margin_so_so (float): Llamada de margen de margen.
        n_fields (int): Número de campos.
        n_sequence_fields (int): Número de campos de secuencia.
        n_unnamed_fields (int): Número de campos sin nombre.
        name (str): Nombre de la cuenta.
        profit (float): Ganancia.
        server (str): Servidor.
        trade_allowed (bool): Comercio permitido.
        trade_expert (bool): Comercio experto.
        trade_mode (int): Modo de comercio.
    """
    assets: float = None
    balance: float = None
    commission_blocked: float = None
    company: str = None
    credit: float = None
    currency: str = None
    currency_digits: int = None
    equity: float = None
    fifo_close: bool = None
    leverage: int = None
    liabilities: float = None
    limit_orders: int = None
    login: int = None
    margin: float = None
    margin_free: float = None
    margin_initial: float = None
    margin_level: float = None
    margin_maintenance: float = None
    margin_mode: int = None
    margin_so_call: float = None
    margin_so_mode: int = None
    margin_so_so: float = None
    n_fields: int = None
    n_sequence_fields: int = None
    n_unnamed_fields: int = None
    name: str = None
    profit: float = None
    server: str = None
    trade_allowed: bool = None
    trade_expert: bool = None
    trade_mode: int = None

class SymbolInfo:
    """
    Representa un objeto SymbolInfo de MetaTrader 5 (MT5), que almacena información sobre un símbolo financiero.

    Attributes:
        custom (bool): Indica si el símbolo es personalizado.
        chart_mode (int): El modo de gráfico asociado al símbolo.
        select (bool): Indica si el símbolo está seleccionado.
        visible (bool): Indica si el símbolo es visible en el mercado.
        session_deals (int): El número de operaciones durante la sesión.
        session_buy_orders (int): El número de órdenes de compra durante la sesión.
        session_sell_orders (int): El número de órdenes de venta durante la sesión.
        volume (float): El volumen de operaciones del símbolo.
        volumehigh (float): El volumen más alto del símbolo durante la sesión.
        volumelow (float): El volumen más bajo del símbolo durante la sesión.
        time (int): El tiempo del último cambio en el símbolo.
        digits (int): La cantidad de dígitos en el precio del símbolo.
        spread (int): El spread actual del símbolo en puntos.
        spread_float (bool): Indica si el spread del símbolo es flotante.
        ticks_bookdepth (int): La profundidad de libro de órdenes del símbolo en ticks.
        trade_calc_mode (int): El modo de cálculo de las operaciones del símbolo.
        trade_mode (int): El modo de operación del símbolo.
        start_time (int): El tiempo de inicio de las cotizaciones del símbolo.
        expiration_time (int): El tiempo de vencimiento del símbolo.
        trade_stops_level (int): El nivel mínimo de Stop Loss (SL) para el símbolo.
        trade_freeze_level (int): El nivel mínimo de congelación de operaciones para el símbolo.
        trade_exemode (int): El modo de ejecución de las operaciones del símbolo.
        swap_mode (int): El modo de cálculo de swaps para el símbolo.
        swap_rollover3days (int): Indica si el rollover de swaps es triple durante tres días.
        margin_hedged_use_leg (bool): Indica si se utiliza la pernera (hedged) para el cálculo de margen.
        expiration_mode (int): El modo de cálculo de la fecha de vencimiento del símbolo.
        filling_mode (int): El modo de llenado de órdenes del símbolo.
        order_mode (int): El modo de apertura de órdenes del símbolo.
        order_gtc_mode (int): El modo de órdenes pendientes GTC (bueno hasta cancelar) del símbolo.
        option_mode (int): El modo de opción para el símbolo.
        option_right (int): El derecho de opción del símbolo.
        bid (float): El precio de oferta (bid) actual del símbolo.
        bidhigh (float): El precio de oferta más alto del símbolo durante la sesión.
        bidlow (float): El precio de oferta más bajo del símbolo durante la sesión.
        ask (float): El precio de demanda (ask) actual del símbolo.
        askhigh (float): El precio de demanda más alto del símbolo durante la sesión.
        asklow (float): El precio de demanda más bajo del símbolo durante la sesión.
        last (float): El último precio negociado del símbolo.
        lasthigh (float): El precio más alto negociado del símbolo durante la sesión.
        lastlow (float): El precio más bajo negociado del símbolo durante la sesión.
        volume_real (float): El volumen real del símbolo en el mercado.
        volumehigh_real (float): El volumen más alto real del símbolo durante la sesión.
        volumelow_real (float): El volumen más bajo real del símbolo durante la sesión.
        option_strike (float): El precio de ejercicio de la opción.
        point (float): El valor de un punto en el precio del símbolo.
        trade_tick_value (float): El valor de un tick en la moneda de la cuenta para el símbolo.
        trade_tick_value_profit (float): El valor de un tick para el cálculo de ganancias.
        trade_tick_value_loss (float): El valor de un tick para el cálculo de pérdidas.
        trade_tick_size (float): El tamaño de un tick en el símbolo.
        trade_contract_size (float): El tamaño del contrato del símbolo.
        trade_accrued_interest (float): El interés acumulado para el símbolo.
        trade_face_value (float): El valor nominal del contrato del símbolo.
        trade_liquidity_rate (float): La tasa de liquidez del símbolo.
        volume_min (float): El volumen mínimo permitido para operaciones del símbolo.
        volume_max (float): El volumen máximo permitido para operaciones del símbolo.
        volume_step (float): El incremento mínimo del volumen para operaciones del símbolo.
        volume_limit (float): El límite máximo del volumen para operaciones del símbolo.
        swap_long (float): El valor del swap largo del símbolo.
        swap_short (float): El valor del swap corto del símbolo.
        margin_initial (float): El margen inicial requerido para operaciones del símbolo.
        margin_maintenance (float): El margen de mantenimiento requerido para operaciones del símbolo.
        session_volume (float): El volumen de operaciones durante la sesión actual.
        session_turnover (float): El volumen de negociación durante la sesión actual.
        session_interest (float): El interés acumulado durante la sesión actual.
        session_buy_orders_volume (float): El volumen de órdenes de compra durante la sesión actual.
        session_sell_orders_volume (float): El volumen de órdenes de venta durante la sesión actual.
        session_open (float): El precio de apertura de la sesión actual.
        session_close (float): El precio de cierre de la sesión actual.
        session_aw (float): El precio promedio ponderado durante la sesión actual.
        session_price_settlement (float): El precio de liquidación de la sesión actual.
        session_price_limit_min (float): El límite mínimo de precio de la sesión actual.
        session_price_limit_max (float): El límite máximo de precio de la sesión actual.
        margin_hedged (float): El margen de cobertura para operaciones del símbolo.
        price_change (float): El cambio de precio del símbolo.
        price_volatility (float): La volatilidad del precio del símbolo.
        price_theoretical (float): El precio teórico del símbolo.
        price_greeks_delta (float): La sensibilidad delta del precio del símbolo.
        price_greeks_theta (float): La sensibilidad theta del precio del símbolo.
        price_greeks_gamma (float): La sensibilidad gamma del precio del símbolo.
        price_greeks_vega (float): La sensibilidad vega del precio del símbolo.
        price_greeks_rho (float): La sensibilidad rho del precio del símbolo.
        price_greeks_omega (float): La sensibilidad omega del precio del símbolo.
        price_sensitivity (float): La sensibilidad del precio del símbolo.
        basis (str): La base del símbolo.
        category (str): La categoría del símbolo.
        currency_base (str): La moneda base del símbolo.
        currency_profit (str): La moneda de ganancia del símbolo.
        currency_margin (str): La moneda de margen del símbolo.
        bank (str): El banco asociado al símbolo.
        description (str): La descripción del símbolo.
        exchange (str): El intercambio al que pertenece el símbolo.
        formula (str): La fórmula de cálculo del símbolo.
        isin (str): El código ISIN del símbolo.
        name (str): El nombre del símbolo.
        page (str): La página asociada al símbolo.
        path (str): La ruta del símbolo.

    """

    custom: bool = None
    chart_mode: int = None
    select: bool = None
    visible: bool = None
    session_deals: int = None
    session_buy_orders: int = None
    session_sell_orders: int = None
    volume: float = None
    volumehigh: float = None
    volumelow: float = None
    time: int = None
    digits: int = None
    spread: int = None
    spread_float: bool = None
    ticks_bookdepth: int = None
    trade_calc_mode: int = None
    trade_mode: int = None
    start_time: int = None
    expiration_time: int = None
    trade_stops_level: int = None
    trade_freeze_level: int = None
    trade_exemode: int = None
    swap_mode: int = None
    swap_rollover3days: int = None
    margin_hedged_use_leg: bool = None
    expiration_mode: int = None
    filling_mode: int = None
    order_mode: int = None
    order_gtc_mode: int = None
    option_mode: int = None
    option_right: int = None
    bid: float = None
    bidhigh: float = None
    bidlow: float = None
    ask: float = None
    askhigh: float = None
    asklow: float = None
    last: float = None
    lasthigh: float = None
    lastlow: float = None
    volume_real: float = None
    volumehigh_real: float = None
    volumelow_real: float = None
    option_strike: float = None
    point: float = None
    trade_tick_value: float = None
    trade_tick_value_profit: float = None
    trade_tick_value_loss: float = None
    trade_tick_size: float = None
    trade_contract_size: float = None
    trade_accrued_interest: float = None
    trade_face_value: float = None
    trade_liquidity_rate: float = None
    volume_min: float = None
    volume_max: float = None
    volume_step: float = None
    volume_limit: float = None
    swap_long: float = None
    swap_short: float = None
    margin_initial: float = None
    margin_maintenance: float = None
    session_volume: float = None
    session_turnover: float = None
    session_interest: float = None
    session_buy_orders_volume: float = None
    session_sell_orders_volume: float = None
    session_open: float = None
    session_close: float = None
    session_aw: float = None
    session_price_settlement: float = None
    session_price_limit_min: float = None
    session_price_limit_max: float = None
    margin_hedged: float = None
    price_change: float = None
    price_volatility: float = None
    price_theoretical: float = None
    price_greeks_delta: float = None
    price_greeks_theta: float = None
    price_greeks_gamma: float = None
    price_greeks_vega: float = None
    price_greeks_rho: float = None
    price_greeks_omega: float = None
    price_sensitivity: float = None
    basis: str = None
    category: str = None
    currency_base: str = None
    currency_profit: str = None
    currency_margin: str = None
    bank: str = None
    description: str = None
    exchange: str = None
    formula: str = None
    isin: str = None
    name: str = None
    page: str = None
    path: str = None