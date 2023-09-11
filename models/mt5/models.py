
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


class SymbolInfo:
    """
    Representa un objeto SymbolInfo de MetaTrader 5 (MT5).

    Attributes:
        custom (bool): Descripción de custom.
        chart_mode (int): Descripción de chart_mode.
        select (bool): Descripción de select.
        visible (bool): Descripción de visible.
        session_deals (int): Descripción de session_deals.
        session_buy_orders (int): Descripción de session_buy_orders.
        session_sell_orders (int): Descripción de session_sell_orders.
        volume (float): Descripción de volume.
        volumehigh (float): Descripción de volumehigh.
        volumelow (float): Descripción de volumelow.
        time (int): Descripción de time.
        digits (int): Descripción de digits.
        spread (int): Descripción de spread.
        spread_float (bool): Descripción de spread_float.
        ticks_bookdepth (int): Descripción de ticks_bookdepth.
        trade_calc_mode (int): Descripción de trade_calc_mode.
        trade_mode (int): Descripción de trade_mode.
        start_time (int): Descripción de start_time.
        expiration_time (int): Descripción de expiration_time.
        trade_stops_level (int): Descripción de trade_stops_level.
        trade_freeze_level (int): Descripción de trade_freeze_level.
        trade_exemode (int): Descripción de trade_exemode.
        swap_mode (int): Descripción de swap_mode.
        swap_rollover3days (int): Descripción de swap_rollover3days.
        margin_hedged_use_leg (bool): Descripción de margin_hedged_use_leg.
        expiration_mode (int): Descripción de expiration_mode.
        filling_mode (int): Descripción de filling_mode.
        order_mode (int): Descripción de order_mode.
        order_gtc_mode (int): Descripción de order_gtc_mode.
        option_mode (int): Descripción de option_mode.
        option_right (int): Descripción de option_right.
        bid (float): Descripción de bid.
        bidhigh (float): Descripción de bidhigh.
        bidlow (float): Descripción de bidlow.
        ask (float): Descripción de ask.
        askhigh (float): Descripción de askhigh.
        asklow (float): Descripción de asklow.
        last (float): Descripción de last.
        lasthigh (float): Descripción de lasthigh.
        lastlow (float): Descripción de lastlow.
        volume_real (float): Descripción de volume_real.
        volumehigh_real (float): Descripción de volumehigh_real.
        volumelow_real (float): Descripción de volumelow_real.
        option_strike (float): Descripción de option_strike.
        point (float): Descripción de point.
        trade_tick_value (float): Descripción de trade_tick_value.
        trade_tick_value_profit (float): Descripción de trade_tick_value_profit.
        trade_tick_value_loss (float): Descripción de trade_tick_value_loss.
        trade_tick_size (float): Descripción de trade_tick_size.
        trade_contract_size (float): Descripción de trade_contract_size.
        trade_accrued_interest (float): Descripción de trade_accrued_interest.
        trade_face_value (float): Descripción de trade_face_value.
        trade_liquidity_rate (float): Descripción de trade_liquidity_rate.
        volume_min (float): Descripción de volume_min.
        volume_max (float): Descripción de volume_max.
        volume_step (float): Descripción de volume_step.
        volume_limit (float): Descripción de volume_limit.
        swap_long (float): Descripción de swap_long.
        swap_short (float): Descripción de swap_short.
        margin_initial (float): Descripción de margin_initial.
        margin_maintenance (float): Descripción de margin_maintenance.
        session_volume (float): Descripción de session_volume.
        session_turnover (float): Descripción de session_turnover.
        session_interest (float): Descripción de session_interest.
        session_buy_orders_volume (float): Descripción de session_buy_orders_volume.
        session_sell_orders_volume (float): Descripción de session_sell_orders_volume.
        session_open (float): Descripción de session_open.
        session_close (float): Descripción de session_close.
        session_aw (float): Descripción de session_aw.
        session_price_settlement (float): Descripción de session_price_settlement.
        session_price_limit_min (float): Descripción de session_price_limit_min.
        session_price_limit_max (float): Descripción de session_price_limit_max.
        margin_hedged (float): Descripción de margin_hedged.
        price_change (float): Descripción de price_change.
        price_volatility (float): Descripción de price_volatility.
        price_theoretical (float): Descripción de price_theoretical.
        price_greeks_delta (float): Descripción de price_greeks_delta.
        price_greeks_theta (float): Descripción de price_greeks_theta.
        price_greeks_gamma (float): Descripción de price_greeks_gamma.
        price_greeks_vega (float): Descripción de price_greeks_vega.
        price_greeks_rho (float): Descripción de price_greeks_rho.
        price_greeks_omega (float): Descripción de price_greeks_omega.
        price_sensitivity (float): Descripción de price_sensitivity.
        basis (str): Descripción de basis.
        category (str): Descripción de category.
        currency_base (str): Descripción de currency_base.
        currency_profit (str): Descripción de currency_profit.
        currency_margin (str): Descripción de currency_margin.
        bank (str): Descripción de bank.
        description (str): Descripción de description.
        exchange (str): Descripción de exchange.
        formula (str): Descripción de formula.
        isin (str): Descripción de isin.
        name (str): Descripción de name.
        page (str): Descripción de page.
        path (str): Descripción de path.

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