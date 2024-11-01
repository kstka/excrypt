from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class SymbolInfo:
    symbol: str = None
    original_symbol: str = None
    base_asset: str = None
    quote_asset: str = None
    price_precision: int = None
    price_tick_size: float = None
    price_tick_size_str: str = None
    min_quantity: float = None
    min_quantity_str: str = None
    quantity_step_size: float = None
    quantity_step_size_str: str = None
    quantity_precision: int = None
    min_order_size: float = None
    min_order_size_str: str = None
    status: str = None
    response: dict = None
    

@dataclass
class Balance:
    asset: str = None
    free: float = None
    free_str: str = None
    locked: float = None
    locked_str: str = None
    total: float = None
    total_str: str = None
    timestamp: int = None
    datetime: datetime = None
    response: dict = None
    

@dataclass
class Ticker:
    symbol: str = None
    price: float = None
    price_str: str = None
    timestamp: int = None
    datetime: datetime = None
    response: dict = None


@dataclass
class Order:
    symbol: str = None
    order_id: str = None
    price: float = None
    price_str: str = None
    stop_price: float = None
    stop_price_str: str = None
    qty: float = None
    qty_str: str = None
    orig_qty: float = None
    orig_qty_str: str = None
    quote_qty: float = None
    quote_qty_str: str = None
    status: str = None
    type: str = None
    side: str = None
    timestamp: int = None
    datetime: datetime = None
    response: dict = None


@dataclass
class Trade:
    symbol: str = None
    order_id: str = None
    trade_id: str = None
    price: float = None
    price_str: str = None
    qty: float = None
    qty_str: str = None
    quote_qty: float = None
    quote_qty_str: str = None
    comm: float = None
    comm_str: str = None
    comm_asset: str = None
    pnl: float = None
    pnl_str: str = None
    position: str = None
    status: str = None
    type: str = None
    side: str = None
    buyer: bool = None
    maker: bool = None
    timestamp: int = None
    datetime: datetime = None
    response: dict = None
