import datetime as dt

from .exchange import Exchange
from .exceptions import *
from .dataclasses import *


class Binance(Exchange):
    """
    https://binance-docs.github.io/apidocs/spot/en/
    https://binance-docs.github.io/apidocs/futures/en/
    """

    _FUTURES_API_URL = "https://fapi.binance.com"
    _SPOT_API_URL = "https://api.binance.com"

    _spot_quote_assets = ['BTC', 'PLN', 'NGN', 'RON', 'TUSD', 'USDT', 'PAX', 'JPY', 'FDUSD', 'UST', 'USDS', 'ZAR', 'USDC', 'RUB', 'BUSD', 'BNB', 'TRY', 'BKRW', 'DOGE', 'AEUR', 'DAI', 'ARS', 'GBP', 'ETH', 'BVND', 'IDRT', 'EUR', 'TRX', 'DOT', 'VAI', 'USDP', 'BIDR', 'UAH', 'AUD', 'XRP', 'BRL']
    _futures_quote_assets = ['BTC', 'PLN', 'NGN', 'RON', 'TUSD', 'USDT', 'PAX', 'JPY', 'FDUSD', 'UST', 'USDS', 'ZAR', 'USDC', 'RUB', 'BUSD', 'BNB', 'TRY', 'BKRW', 'DOGE', 'AEUR', 'DAI', 'ARS', 'GBP', 'ETH', 'BVND', 'IDRT', 'EUR', 'TRX', 'DOT', 'VAI', 'USDP', 'BIDR', 'UAH', 'AUD', 'XRP', 'BRL']

    _EXCHANGE_SYMBOL_SEPARATOR = ''

    def _initialize(self):
        if self._FUTURES:
            self._API_URL = self._FUTURES_API_URL
        else:
            self._API_URL = self._SPOT_API_URL

        if self._API_KEY:
            self.update_headers({'X-MBX-APIKEY': self._API_KEY})

    def _handle_request_kwargs(self, kwargs, method, timestamp, endpoint, signed):
        if signed:
            kwargs['params'].update({'timestamp': timestamp})
            signature = self._generate_signature(method, timestamp, endpoint, kwargs['params'])
            kwargs['params'].update({'signature': signature})

        return kwargs

    def _convert_symbol_to_global(self, symbol):
        """
        In case of Bianance symbol does not contain separator.
        So it is required to guess base and quote assets.
        For this case Binance quote assets will be kept in a variable inside this class
        """
        symbol_in_global_format = None
        for symbol_info in self.symbols_info.values():
            if symbol == symbol_info.original_symbol:
                symbol_in_global_format = symbol_info.base_asset + self._GLOBAL_SYMBOL_SEPARATOR + symbol_info.quote_asset

        if symbol_in_global_format:
            return symbol_in_global_format

        quote_assets = self._futures_quote_assets if self._FUTURES else self._spot_quote_assets
        for quote_asset in quote_assets:
            if symbol.endswith(quote_asset):
                base_asset = symbol.replace(quote_asset, '')
                symbol_in_global_format = base_asset + self._GLOBAL_SYMBOL_SEPARATOR + quote_asset
        return symbol_in_global_format

    def get_exchange_info(self):
        if self._FUTURES:
            endpoint = '/fapi/v1/exchangeInfo'
        else:
            endpoint = '/api/v3/exchangeInfo'

        response = self._request(endpoint=endpoint)

        # parse symbols info
        for info in response['symbols']:
            symbol_info = SymbolInfo

            symbol_info.response = info

            # symbol and original symbol
            symbol_info.symbol = info['baseAsset'] + self._GLOBAL_SYMBOL_SEPARATOR + info['quoteAsset']
            symbol_info.original_symbol = info['symbol']

            # assets
            symbol_info.base_asset = info['baseAsset']
            symbol_info.quote_asset = info['quoteAsset']

            # status
            symbol_info.status = info['status']

            # filters
            for f in info['filters']:
                if f['filterType'] == 'PRICE_FILTER':
                    symbol_info.price_tick_size = float(f['tickSize'])
                    symbol_info.price_tick_size_str = f['tickSize']
                    symbol_info.price_precision = self.get_precision(f['tickSize'])
                elif f['filterType'] == 'LOT_SIZE':
                    symbol_info.min_quantity = float(f['minQty'])
                    symbol_info.min_quantity_str = f['minQty']
                    symbol_info.quantity_step_size = float(f['stepSize'])
                    symbol_info.quantity_step_size_str = f['stepSize']
                    symbol_info.quantity_precision = self.get_precision(f['stepSize'])
                elif f['filterType'] == 'MIN_NOTIONAL' and self._FUTURES:
                    symbol_info.min_order_size = float(f['notional'])
                    symbol_info.min_order_size_str = f['notional']
                elif f['filterType'] == 'NOTIONAL':
                    symbol_info.min_order_size = float(f['minNotional'])
                    symbol_info.min_order_size_str = f['minNotional']

            self.symbols_info[symbol_info.symbol] = symbol_info

        # update quote assets
        # so far usefull for Binance only because it's symbols do not contain separator
        quote_assets = set()
        for info in response['symbols']:
            quote_assets.add(info['quoteAsset'])
        if self._FUTURES:
            self._futures_quote_assets = list(quote_assets)
        else:
            self._spot_quote_assets = list(quote_assets)

        return self.symbols_info

    def get_balances(self):
        if self._FUTURES:
            endpoint = '/fapi/v2/account'
        else:
            endpoint = '/api/v3/account'

        response = self._get(endpoint, signed=True)

        if self._FUTURES:
            for item in response['assets']:
                balance = Balance
                balance.asset = item['asset']
                balance.free = float(item['walletBalance'])
                balance.free_str = item['walletBalance']
                balance.locked = float(item['unrealizedProfit'])
                balance.locked_str = item['unrealizedProfit']
                balance.total = balance.free + balance.locked
                balance.total_str = '{:0.8f}'.format(balance.total)
                balance.response = item

                self.balances[balance.asset] = balance
        else:
            for item in response['balances']:
                balance = Balance
                balance.asset = item['asset']
                balance.free = float(item['free'])
                balance.free_str = item['free']
                balance.locked = float(item['locked'])
                balance.locked_str = item['locked']
                balance.total = balance.free + balance.locked
                balance.total_str = '{:0.8f}'.format(balance.total)
                balance.response = item

                self.balances[balance.asset] = balance

        return self.balances

    def get_tickers(self):
        if self._FUTURES:
            endpoint = '/fapi/v2/ticker/price'
        else:
            endpoint = '/api/v3/ticker/price'

        # [{'symbol': 'ZRXUSDT', 'price': '1.2234', 'time': 1710931501565},
        # {'symbol': 'REEFUSDT', 'price': '0.002789', 'time': 1710931501281},]
        response = self._request(endpoint=endpoint)
        for item in response:
            symbol = self._convert_symbol_to_global(item['symbol'])
            ticker = Ticker
            ticker.symbol = symbol
            ticker.price = float(item['price'])
            ticker.price_str = item['price']
            ticker.timestamp = int(item['time'])
            ticker.date_time = dt.datetime.fromtimestamp(ticker.timestamp / 1000)
            ticker.response = item
            self.tickers[symbol] = ticker

        return self.tickers

    def get_ticker(self, symbol):
        if self._FUTURES:
            endpoint = '/fapi/v2/ticker/price'
        else:
            endpoint = '/api/v3/ticker/price'

        symbol = self._convert_symbol_to_local(symbol)
        params = {
            'symbol': symbol,
            }
        # {'symbol': 'YGGUSDT', 'price': '0.7399000', 'time': 1710931387892}
        response = self._request(endpoint=endpoint, params=params)

        ticker = Ticker
        ticker.symbol = self._convert_symbol_to_global(symbol)
        ticker.price = float(response['price'])
        ticker.price_str = response['price']
        ticker.timestamp = int(response['time'])
        ticker.date_time = dt.datetime.fromtimestamp(ticker.timestamp / 1000)
        ticker.response = response

        # update tickers
        self.tickers[ticker.symbol] = ticker

        return ticker

    def create_order(self, symbol, side, quantity, price=None, stop_price=None, type='LIMIT', time_in_force=None):
        symbol = self._convert_symbol_to_local(symbol)
        side = side.upper()
        type = type.upper()

        if self._FUTURES:
            endpoint = '/fapi/v1/order'
        else:
            endpoint = '/api/v3/order'

        if type == 'LIMIT':
            if not time_in_force:
                time_in_force = self.TIME_IN_FORCE_GTC
            params = {
                'symbol': symbol,
                'side': side,
                'type': type,
                'quantity': quantity,
                'timeInForce': time_in_force,
                'price': price,
            }

        elif type == 'MARKET':
            params = {
                'symbol': symbol,
                'side': side,
                'type': type,
                'quantity': quantity,
            }
        elif type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
            params = {
                'symbol': symbol,
                'side': side,
                'type': type,
                'quantity': quantity,
                'stopPrice': stop_price,
            }
        else:
            raise ExchangeException('Unknown order type: %s' % type)

        response = self._request(endpoint=endpoint, params=params, method='post', signed=True)
        return self._parse_order(response)

    def _parse_order(self, raw_order):
        order = Order()
        order.response = raw_order
        order.symbol = self._convert_symbol_to_global(raw_order['symbol'])
        order.base_asset, order.quote_asset = self.get_symbol_assets(order.symbol)
        order.order_id = str(raw_order['orderId'])
        order.price = float(raw_order['price'])
        order.price_str = raw_order['price']
        order.qty = float(raw_order['executedQty'])
        order.qty_str = raw_order['executedQty']
        order.orig_qty = float(raw_order['origQty'])
        order.orig_qty_str = raw_order['origQty']
        order.status = raw_order['status'].lower()
        order.type = raw_order['type'].lower()
        order.side = raw_order['side'].lower()
        if 'time' in raw_order:
            order.timestamp = int(raw_order['time'])
            order.datetime = dt.datetime.utcfromtimestamp(order.timestamp // 1000)
        if 'cummulativeQuoteQty' in raw_order:  # в фьючерсах есть cumQuote, может это оно
            order.quote_qty = float(raw_order['cummulativeQuoteQty'])
            order.quote_qty_str = raw_order['cummulativeQuoteQty']
        else:
            order.quote_qty = round(order.price * order.qty, 8)
            order.quote_qty_str = '{:0.0{}f}'.format(order.quote_qty, 8)
        # partially_filled status
        if order.qty and order.status == 'canceled':
            order.status = 'partially_filled'
        # stop price
        if 'stopPrice' in raw_order:
            order.stop_price = float(raw_order['stopPrice'])
            order.stop_price_str = raw_order['stopPrice']
        return order

def _parse_trade(self, raw_trade):
    trade = Trade()
    trade.response = raw_trade
    trade.symbol = self._convert_symbol_to_global(raw_trade['symbol'])
    trade.trade_id = str(raw_trade['id'])
    trade.order_id = str(raw_trade['orderId'])
    trade.price = float(raw_trade['price'])
    trade.price_str = raw_trade['price']
    trade.qty = float(raw_trade['qty'])
    trade.qty_str = raw_trade['qty']
    trade.quote_qty = float(raw_trade['quoteQty'])
    trade.quote_qty_str = raw_trade['quoteQty']
    trade.comm = float(raw_trade['commission'])
    trade.comm_str = raw_trade['commission']
    trade.comm_asset = raw_trade['commissionAsset']
    trade.timestamp = int(raw_trade['time'])
    trade.datetime = datetime.utcfromtimestamp(trade.timestamp // 1000)
    trade.buyer = raw_trade['isBuyer']
    trade.maker = raw_trade['isMaker']
    trade.status = raw_trade.get('status', None)
    trade.type = raw_trade.get('type', None)
    trade.side = raw_trade.get('side', None)
    trade.pnl = raw_trade.get('pnl', None)
    trade.pnl_str = raw_trade.get('pnl_str', None)
    trade.position = raw_trade.get('position', None)
    return trade

    def get_position_info(self, symbol):
        if self._FUTURES:
            endpoint = '/fapi/v2/positionRisk'
        else:
            raise ExchangeException('get_position_info is not supported for spot exchange')

        params = {
            'symbol': self._convert_symbol_to_local(symbol),
        }

        response = self._request(endpoint=endpoint, signed=True, params=params)
        return self._parse_position_info(response[0])

    def get_positions_info(self):
        if self._FUTURES:
            endpoint = '/fapi/v2/positionRisk'
        else:
            raise ExchangeException('get_positions_info is not supported for spot exchange')

        response = self._request(endpoint=endpoint, signed=True)
        result = {}
        for item in response:
            result[self._convert_symbol_to_global(item['symbol'])] = self._parse_position_info(item)
        return result

    @staticmethod
    def _parse_position_info(position_info):
        """
        {
            'symbol': 'YGGUSDT',
            'positionAmt': '0',
            'entryPrice': '0.0',
            'breakEvenPrice': '0.0',
            'markPrice': '0.73743796',
            'unRealizedProfit': '0.00000000',
            'liquidationPrice': '0',
            'leverage': '20',
            'maxNotionalValue': '25000',
            'marginType': 'cross',
            'isolatedMargin': '0.00000000',
            'isAutoAddMargin': 'false',
            'positionSide': 'BOTH',
            'notional': '0',
            'isolatedWallet': '0',
            'updateTime': 1710945588354,
            'isolated': False,
            'adlQuantile': 0
        }
        """
        return {
                'amount': float(position_info['positionAmt']),
                'entry_price': float(position_info['entryPrice']),
                'mark_price': float(position_info['markPrice']),
                'unrealized_profit': float(position_info['unRealizedProfit']),
                'liquidation_price': float(position_info['liquidationPrice']),
                'leverage': float(position_info['leverage']),
                'margin_type': position_info['marginType'],
                'isolated_margin': float(position_info['isolatedMargin']),
                'is_auto_add_margin': position_info['isAutoAddMargin'],
                'position_side': position_info['positionSide'],
                'notional': float(position_info['notional']),
                'isolated_wallet': float(position_info['isolatedWallet']),
                }

    def set_margin_type(self, symbol, margin_type):
        if self._FUTURES:
            endpoint = '/fapi/v1/marginType'
        else:
            raise ExchangeException('change_margin_type is not supported for spot exchange')

        params = {
            'symbol': self._convert_symbol_to_local(symbol),
            'marginType': margin_type.upper(),
        }

        response = self._request(endpoint=endpoint, signed=True, method='post', params=params)
        return response

    def set_leverage(self, symbol, leverage):
        if self._FUTURES:
            endpoint = '/fapi/v1/leverage'
        else:
            raise ExchangeException('change_leverage is not supported for spot exchange')

        params = {
            'symbol': self._convert_symbol_to_local(symbol),
            'leverage': leverage,
        }

        response = self._request(endpoint=endpoint, signed=True, method='post', params=params)
        return response

    def cancel_order(self, symbol=None, order_id=None):
        if not symbol:
            raise ExchangeException('symbol must be specified to cancel order')

        if self._FUTURES:
            endpoint = '/fapi/v1/order'
        else:
            endpoint = '/api/v3/order'

        params = {
            'symbol': self._convert_symbol_to_local(symbol),
        }

        if order_id:
            params['orderId'] = order_id

        response = self._request(endpoint=endpoint, signed=True, method='delete', params=params)
        return self._parse_order(response)

    def get_order(self, order_id=None, symbol=None, parse=True):
        if not symbol or not order_id:
            raise ExchangeException('symbol and order_id must be specified to get order')

        if self._FUTURES:
            endpoint = '/fapi/v1/order'
        else:
            endpoint = '/api/v3/order'

        params = {
            'symbol': self._convert_symbol_to_local(symbol),
            'orderId': order_id
        }

        response = self._request(endpoint=endpoint, signed=True, params=params)
        if parse:
            return self._parse_order(response)
        else:
            return response


    def get_orders(self, symbol: str, from_timestamp=None, from_order_id=None, parse=True):
        # https://binance-docs.github.io/apidocs/spot/en/#all-orders-user_data

        if self._FUTURES:
            raise NotImplementedException('get_orders is not implemented for futures')
        else:
            endpoint = '/api/v3/allOrders'

        params = {
            'symbol': self._convert_symbol_to_local(symbol),
        }

        orders = []

        # go into infinite loop if from_timestamp is specified
        if from_timestamp:
            params['startTime'] = from_timestamp * 1000
            orders = self._get_paginated_data(endpoint, 'get', True, params, 'startTime', 'time')
        elif from_order_id:
            params['orderId'] = from_order_id
            orders = self._get_paginated_data(endpoint, 'get', True, params, 'orderId', 'time')
        # request single time
        else:
            response = self._request(endpoint=endpoint, signed=True, params=params)
            orders = response

        if parse:
            return [self._parse_order(order) for order in orders]
        else:
            return orders

    def get_trades(self, symbol, from_timestamp=None, from_order_id=None, parse=True):
        # https://binance-docs.github.io/apidocs/spot/en/#account-trade-list-user_data

        if self._FUTURES:
            raise NotImplementedException('get_trades is not implemented for futures')
        else:
            endpoint = '/api/v3/myTrades'

        params = {
            'symbol': self._convert_symbol_to_local(symbol),
        }

        trades = []

        # go into infinite loop if from_timestamp is specified
        if from_timestamp:
            params['startTime'] = from_timestamp * 1000
            trades = self._get_paginated_data(endpoint, 'get', True, params, 'startTime', 'time')
        # same for order_id
        elif from_order_id:
            params['orderId'] = from_order_id
            trades = self._get_paginated_data(endpoint, 'get', True, params, 'orderId', 'time')
        # request single time
        else:
            response = self._request(endpoint=endpoint, signed=True, params=params)
            trades = response

        if parse:
            return [self._parse_trade(trade) for trade in trades]
        else:
            return orders

    def get_symbols(self, all=None):
        if not self.symbols_info:
            self.get_exchange_info()

        symbols = []
        for symbol in self.symbols_info:
            if all:
                symbols.append(symbol)
            else:
                if self.symbols_info[symbol]['status'] == 'TRADING':
                    symbols.append(symbol)

        return symbols