#!/usr/bin/env python

"""
Limit order book 

Notes
-----
* Market orders are immediately executed at best buy and best ask values; if the
  book is empty (i.e., no limit orders have been placed yet), the market order
  is automatically canceled.
* All outstanding limit orders expire at the end of the day.
* Attempting to execute a buy/sell market order prior to the arrival of any
  sell/buy limit orders that can satisfy it (both in terms of quantity and price).
* When a limit order arrives that can satisfy an outstanding limit order, it is
  executed and the corresponding order is removed from the book.
* More information re LOBs can be found at 
  http://iopscience.iop.org/0295-5075/75/3/510/fulltext/
"""

import logging
import collections as coll

import odict
import onctuous as onc
import pandas

col_names = \
  ['record_indicator',
   'segment',
   'order_number',
   'trans_date',
   'trans_time',
   'buy_sell_indicator',
   'activity_type',
   'symbol',
   'instrument',
   'expiry_date',
   'strike_price',
   'option_type',
   'volume_disclosed',
   'volume_original',
   'limit_price',
   'trigger_price',
   'mkt_flag',
   'on_stop_flag',
   'io_flag',
   'spread_comb_type',
   'algo_ind',
   'client_id_flag']

# Some aliases for bids and asks:
BID = BUY = 'B'
ASK = SELL = 'S'

class LimitOrderBook(object):
    """
    Limit order book.

    Parameters    
    ----------

    Notes
    -----
    Orders at each price level are stored in an ordered dict keyed by order
    number; new orders are implicitly appended whenever they are added to the dict.

    """
    
    def __init__(self, tick_size=0.05):
        self.logger = logging.getLogger('lob')

        # All limit prices are a multiple of the tick size:
        self.tick_size = tick_size

        # The order data in the book is stored in two dictionaries of ordered
        # dicts; the keys of each dictionary correspond to the price levels of
        # each ordered dict. The ordered dicts are used as
        # queues; adding a new entry with a key corresponding to the order
        # number is equivalent to pushing it into the queue, and the ordered
        # dict permits one to "pop" its first entry:
        self._book_data = {}
        self._book_data[BID] = {}
        self._book_data[ASK] = {}
        
        # Trades performed as orders arrive are recorded in this data
        # structure:
        self._trade_counter = 1
        self._trades = {}

    def clear_book(self):
        """
        Clear all outstanding limit orders from the book

        Notes
        -----
        The trade counter is reset to 1, but all previously
        recorded trades are not erased.
        
        """

        self.logger.info('clearing outstanding limit orders')
        for d in self._book_data.keys():
            self._book_data[d].clear()
        self._trade_counter = 1
        
    def process(self, df):
        """
        Process order data

        Parameters
        ----------
        df : pandas.DataFrame
           Each row of this DataFrame instance contains a single order.

        """

        day = None
        for row in df.iterrows():
            order = row.to_dict()
            self.logger.info('processing order %i' % order['order_number'])

            # Reset the limit order book when a new day of orders begins:
            trans_date = datetime.datetime.strptime(order['trans_date'], '%m/%d/%Y')
            if day is None:
                day = trans_date.day
                self.logger.info('day set to %s' % day)
            elif day != trans_date.day:
                self.logger.info('new day - resetting book')
                self.clear_book()
                
            if order['activity_type'] == 1:
                self.add(order)
            elif order['activity_type'] == 3:
                self.cancel(order)
            elif order['activity_type'] == 4:
                self.modify(order)
            else:
                raise ValueError('unrecognized activity type %i' % order['activity_type'])

    def create_level(self, indicator, price):
        """
        Create a new price level queue.

        Parameters
        ----------
        indicator : str
            Indicate whether to create a new buy ('B') or sell ('S') price
            level.
        price : float
            Price associated with new level.
       
        """
        
        self._book_data[indicator][price] = odict.odict()
        self.logger.info('created new price level: %s, %f' % (indicator, price))
        
    def delete_level(self, indicator, price):
        """
        Delete an existing price level.

        Parameters
        ----------
        indicator : str
            Indicate whether to delete a buy ('B') or sell ('S') price level.
        price : float
            Price associated with level.

        """
        
        self._book_data[indicator].pop(price)
        self.logger.info('deleted price level: %s, %f' % (indicator, price))
                    
    def best_bid_price(self):
        """
        Return the best bid price defined in the book.

        Returns
        -------
        order : dict
            Limit order with best (highest) bid price.

        Notes
        -----
        Assumes that there are no empty price levels in the book.
        
        """

        prices = self._book_data[BID].keys()
        if prices == []:
            return None
        else:
            return max(prices)

    def best_ask_price(self):
        """
        Return the best ask price defined in the book.

        Returns
        -------
        order : dict
            Limit order with best (lowest) ask price.

        Notes
        -----
        Assumes that there are no empty price levels in the book.
        
        """

        prices = self._book_data[ASK].keys()
        if prices == []:
            return None
        else:
            return min(prices)

    def find_best_bid_order(self):
        """
        Return the oldest best bid limit order in the book.

        Returns
        -------
        order : dict
            Limit order with best (highest) bid price.
            
        """

        od = self._book_data[BID][self.best_bid_price()]
        return od[od.firstkey()]
    
    def find_best_ask_order(self):
        pass
    
    def find_price_level(self, indicator, price):
        """
        Find a matching price level in the limit order book.

        Parameters
        ----------
        indicator : str
            Indicate whether to find a buy ('B') or sell ('S') price level.
        price : float
            Price associated with level.
        
        Returns
        -------
        od : odict.odict
            Ordered dict with matching price level.

        """

        # Validate buy/sell indicator:
        try:
            book = self._book_data[indicator]
        except KeyError:
            raise ValueError('unrecognized buy_sell_indicator value')

        # Look for price level queue:
        try:
            od = book[price]
        except KeyError:
            self.logger.info('%s price level not found: %f' % (indicator, price))
            return None
        else:
            self.logger.info('%s price level found: %f' % (indicator, price))
            return od

    def save_trade(self, trade_time, trade_price, trade_quantity,
                    buy_order_number, sell_order_number):
        """
        Record a trade.
        
        """
        
        trade = {'trade_time': trade_time,
                 'trade_price': trade_price,
                 'trade_quantity': trade_quantity,
                 'buy_order_number': buy_order_number,
                 'sell_order_number': sell_order_number}
        trade_number = '%08i' % trade
        self._trades[self._trades_counter] = trade_number
        self._trades_counter += 1
        self.logger.info('recording trade %s' % trade_number)
        
    def add(self, order):
        """
        Add the specified order to the LOB.
        
        Parameters
        ----------
        order : dict
            Order data.

        Notes
        -----        
        New orders are implicitly appended onto the end of each ordered dict.
        One can obtain the oldest order by popping the first entry in the dict.
        
        """

        # If the bid/ask order is a market order, check whether there is a
        # corresponding limit order in the book at the best ask/bid price:
        if order['mkt_flag'] == 'Y':
            volume_original = order['volume_original']
            volume_disclosed = order['volume_disclosed']
            if order['buy_sell_indicator'] == BID:

                # Find order with best ask price:
                od = self.find_price_level(ASK, self.best_ask_price())
                for order_number in od.keys():

                    # If an ask order has the same volume as that requested in
                    # the bid, remove it from the queue and record a
                    # transaction:
                    if od[order_number]['volume_original'] == volume_original:
                        pass
                    # If an ask order has a greater volume than that requested
                    # in the bid, decrement its volume accordingly and record a
                    # transaction:
                    elif od[order_number]['volume_original'] > volume_original:
                        pass
                    # XXX What if the ask volume is below the requested bid volume?
                    else
                        self.logger.info('undefined behavior for best ask '
                                         'volume < bid volume')
                        
            elif order['buy_sell_indicator'] == ASK:

                # Find order with best bid price:
                od = self.find_price_level(BID, self.best_ask_price())
                pass

        elif order['mkt_flag'] == 'N':
            
            od = self.find_price_level(order['buy_sell_indicator'], order['limit_price'])
            if od is not None:
                self.logger.info('matching price level found: %s' % order['limit_price'])                        

                # Check whether the bid/ask order matches a corresponding ask/bid
                # limit order already in the book:
                for k in od.keys():
                    if od[k]['limit_price'] == order['limit_price']:
                        self.logger.info('')


            else:

                # Check whether the bid/ask order matches a corresponding ask/bid
                # limit order already in the book:

                #Create a new price level and add it:
                self.logger.info('no matching price level found')
        

    def modify(self, order):
        """
        Modify the order with matching order number in the LOB.
        """

        # This exception should never be thrown:
        if order['mkt_flag'] == 'Y':
            raise ValueError('cannot modify market order')
        
        od = self.find_price_level(order['buy_sell_indicator'], order['limit_price'])
        order_number = order['order_number']
        if od is not None:
            self.logger.info('matching price level found: %s' % order['limit_price'])
            try:
                old_order = od[order_number]
            except:
                self.logger.info('order number %i not found' % order_number)
            else:

                # If the modify changes the volume of an order, remove it and
                # resubmit it to the queue:
                if order['limit_price'] != old_order['limit_price']:
                    self.logger.info('modified order %i price from %f to %f: ' % \
                                     (order_number,
                                      old_order['limit_price'],
                                      order['limit_price']))
                    od.pop(order_number)
                    od.push(order)
                    
                # If the modify changes the price of an order, update it
                # without alterning where it is in the queue:
                elif order['original_volume'] != old_order['original_volume']:
                    self.logger.info('modified order %i volume from %f to %f: ' % \
                                     (order_number,
                                      old_order['original_volume'],
                                      order['original_volume']))
                    od[order_number] = order
                else:
                    self.logger.info('undefined modify scenario')
        else:
            self.logger.info('no matching price level found')
                
    def cancel(self, order):
        """
        Remove the order with matching order number from the LOB.
        """

        # This exception should never be thrown:
        if order['mkt_flag'] == 'Y':
            raise ValueError('cannot cancel market order')
        
        od = self.find_price_level(order['buy_sell_indicator'], order['limit_price'])
        order_number = order['order_number']
        if od is not None:
            self.logger.info('matching price level found: %s, %f' % \
                             (order['buy_sell_indicator'], order['limit_price']))
            try:
                # XXX Do we need to check that the price and volume match too?
                old_order = od[order_number]                
            except:
                self.logger.info('order number %i not found' % order_number)
            else:
                od.pop(order_number)
                self.logger.info('canceled order %i' % order_number)

                if not od:
                    pass
        else:
            self.logger.info('no matching price level found')
                    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(levelname)s %(funcName) %(message)s')    
    file_name = 'AXISBANK-orders.csv'

    df = pandas.read_csv(file_name,
                         names=col_names,
                         nrows=10000)

