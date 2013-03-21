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

import datetime
import logging
import odict
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

        # Counter used to assign unique identifiers to generated trades:
        self._trade_counter = 1
        
        # Trades performed as orders arrive are recorded in this data
        # structure:
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
            order = row[1].to_dict()
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
                # XXX It seems that a few market orders are listed as modify orders;
                # temporarily treat them as add operations XXX                  
                if order['mkt_flag'] == 'Y':
                    self.add(order)
                else:    
                    self.modify(order)
            else:
                raise ValueError('unrecognized activity type %i' % order['activity_type'])

    def create_level(self, indicator, price):
        """
        Create a new empty price level queue.

        Parameters
        ----------
        indicator : str
            Indicate whether to create a new buy ('B') or sell ('S') price
            level.
        price : float
            Price associated with new level.

        Returns
        -------
        od : odict
            New price level queue.
        
        """

        od = odict.odict()
        self._book_data[indicator][price] = od
        self.logger.info('created new price level: %s, %f' % (indicator, price))
        return od
    
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

    def delete_order(self, indicator, price, order_number):
        """
        Delete an order from a price level queue.

        Parameters
        ----------
        indicator : str
            Indicate whether to create a new buy ('B') or sell ('S') price
            level.
        price : float
            Price associated with level.
        order_number : str
            Number of order to delete.

        Notes
        -----
        If the price level queue containing the specified order is empty after
        the order is deleted, it is removed from the limit order book.
        
        """

        book = self._book_data[indicator]
        od = book[price]
        od.pop(order_number)
        self.logger.info('deleted order %s from price level: %s, %f' % \
                         (order_number, indicator, price))
        if not od:
            self.delete_level(indicator, price)
            
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
            best_price = max(prices)
            if not self._book_data[BID][best_price]:
                raise RuntimeError('empty price level detected')
            return best_price

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
            best_price = min(prices)
            if not self._book_data[ASK][best_price]:
                raise RuntimeError('empty price level detected')
            return best_price
            
    def price_level(self, indicator, price):
        """
        Find a specified price level in the limit order book.
        
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
            raise ValueError('invalid buy/sell indicator')

        # Look for price level queue:
        try:
            od = book[price]
        except KeyError:
            self.logger.info('price level not found: %s, %f' % (indicator, price))
            return None
        else:
            self.logger.info('price level found: %s, %f' % (indicator, price))
            return od

    def record_trade(self, trade_date, trade_time, trade_price, trade_quantity,
                     buy_order_number, sell_order_number):
        """
        Record a trade.

        Parameters
        ----------
        trade_date : str
        trade_time : str
        trade_price : str
        trade_quantity : str
        buy_order_number : str
        sell_order_number : str
        
        """
        
        trade = {'trade_time': trade_time,
                 'trade_price': trade_price,
                 'trade_quantity': trade_quantity,
                 'buy_order_number': buy_order_number,
                 'sell_order_number': sell_order_number}
        trade_number = '%08i' % self._trade_counter
        self._trades[trade_number] = trade
        self._trade_counter += 1
        self.logger.info('recording trade %s; price: %f, quantity: %f' % \
                 (trade_number, trade_price, trade_quantity))
        
    def add(self, new_order):
        """
        Add the specified order to the LOB.
        
        Parameters
        ----------
        new_order : dict
            Order to add.

        Notes
        -----        
        New orders are implicitly appended onto the end of each ordered dict.
        One can obtain the oldest order by popping the first entry in the dict.
        
        """

        indicator = new_order['buy_sell_indicator']
        volume_original = new_order['volume_original']
        volume_disclosed = new_order['volume_disclosed']           

        # If the buy/sell order is a market order, check whether there is a
        # corresponding limit order in the book at the best ask/bid price:
        if new_order['mkt_flag'] == 'Y':
            while volume_original > 0:
                if indicator == BUY:
                    buy_order = new_order
                    best_price = self.best_ask_price()

                    # Sell/buy market orders cannot be processed until there is at least
                    # one bid/ask limit order in the book:
                    if best_price is None:
                        self.logger.info('no sell limit orders in book yet')
                    od = self.price_level(ASK, best_price) 
                elif indicator == SELL:
                    sell_order = new_order
                    best_price = self.best_bid_price()

                    # Sell/buy market orders cannot be processed until there is at least
                    # one bid/ask limit order in the book:
                    if best_price is None:
                        self.logger.info('no buy limit orders in book yet')                    
                    od = self.price_level(BID, best_price)
                else:
                    RuntimeError('invalid buy/sell indicator')

                # Move through the limit orders in the price level queue from oldest
                # to newest:
                for order_number in od.keys():
                    curr_order = od[order_number]
                    if curr_order['buy_sell_indicator'] == BUY:
                        buy_order = curr_order
                    elif curr_order['buy_sell_indicator'] == SELL:
                        sell_order = curr_order
                    else:
                        RuntimeError('invalid buy/sell indicator')

                    # If a bid/ask limit order in the book has the same volume as
                    # that requested in the sell/buy market order, record a
                    # transaction and remove the limit order from the queue:
                    if curr_order['volume_original'] == volume_original:
                        self.record_trade(new_order['trans_date'],
                                          new_order['trans_time'],
                                          best_price,
                                          volume_original,
                                          buy_order['order_number'],
                                          sell_order['order_number']) 
                        self.delete_order(curr_order['buy_sell_indicator'],
                                          best_price, order_number)
                        volume_original = 0.0                 
                        break

                    # If a bid/ask limit order in the book has a greater volume than that
                    # requested in the sell/buy market order, record a transaction
                    # and decrement its volume accordingly:
                    elif curr_order['volume_original'] > volume_original:
                        self.record_trade(new_order['trans_date'],
                                          new_order['trans_time'],
                                          best_price,
                                          curr_order['volume_original']-volume_original,
                                          buy_order['order_number'],
                                          sell_order['order_number'])
                        curr_order['volume_original'] -= volume_original
                        volume_original = 0.0
                        break

                    # If the bid/ask limit order in the book has a volume that is
                    # below the requested sell/buy market order volume, continue
                    # removing orders from the queue until the entire requested
                    # volume has been satisfied:
                    elif curr_order['volume_original'] < volume_original:
                        self.record_trade(new_order['trans_date'],
                                          new_order['trans_time'],
                                          best_price,
                                          curr_order['volume_original'],
                                          buy_order['order_number'],
                                          sell_order['order_number'])
                        volume_original -= curr_order['volume_original']
                        self.delete_order(curr_order['buy_sell_indicator'],
                                          best_price, order_number)
                    else:

                        # This should never be reached:
                        pass

        elif new_order['mkt_flag'] == 'N':

            # Check whether the limit order is marketable:
            price = new_order['limit_price']
            marketable = True
            if indicator == BUY and self.best_ask_price() is not None and price >= self.best_ask_price():
                self.logger.info('buy order is marketable')
                best_price = self.best_ask_price();
            elif indicator == SELL and self.best_bid_price() is not None and price <= self.best_bid_price():
                self.logger.info('sell order is marketable')
                best_price = self.best_bid_price();
            else:
                marketable = False

            # If the limit order is not marketable, add it to the appropriate
            # price level queue in the limit order book:
            if not marketable:
                self.logger.info('order is not marketable')
                od = self.price_level(indicator, price)

                # Create a new price level queue if none exists for the order's
                # limit price:
                if od is None:
                    self.logger.info('no matching price level found')
                    od = self.create_level(indicator, price)

                od[new_order['order_number']] = new_order

            # Try to match marketable orders with orders that are already in the
            # book:
            else:

                # If the requested volume in the order isn't completely
                # satisfied at the best price, recompute the best price and
                # try to satisfy the remainder:
                while volume_original > 0.0:
                    if indicator == BUY:
                        buy_order = new_order                    
                        best_price = self.best_ask_price()
                        od = self.price_level(ASK, best_price) 
                    elif indicator == SELL:
                        sell_order = new_order
                        best_price = self.best_bid_price()                
                        od = self.price_level(BID, best_price)
                    else:
                        RuntimeError('invalid buy/sell indicator')

                    # Move through the limit orders in the price level queue from
                    # oldest to newest:
                    for order_number in od.keys():                    
                        curr_order = od[order_number]
                        if curr_order['buy_sell_indicator'] == BUY:
                            buy_order = curr_order
                        elif curr_order['buy_sell_indicator'] == SELL:
                            sell_order = curr_order
                        else:
                            RuntimeError('invalid buy/sell indicator')

                        # If a bid/ask limit order in the book has the same volume
                        # as that requested in the sell/buy limit order, record a
                        # transaction and remove the limit order from the queue:
                        if curr_order['volume_original'] == volume_original:
                            self.record_trade(new_order['trans_date'],
                                              new_order['trans_time'],
                                              best_price,
                                              volume_original,
                                              buy_order['order_number'],
                                              sell_order['order_number'])
                            self.delete_order(curr_order['buy_sell_indicator'],
                                              best_price, order_number)
                            volume_original = 0.0
                            break
                        
                        # If a bid/ask limit order in the book has a greater volume
                        # than that requested in the sell/buy limit order, record a
                        # transaction and decrement its volume accordingly:
                        elif curr_order['volume_original'] > volume_original:
                            self.record_trade(new_order['trans_date'],
                                              new_order['trans_time'],
                                              best_price,
                                              curr_order['volume_original']-volume_original,
                                              buy_order['order_number'],
                                              sell_order['order_number'])
                            curr_order['volume_original'] -= volume_original
                            volume_original = 0.0
                            break

                        # If the bid/ask limit order in the book has a volume that is
                        # below the requested sell/buy market order volume, continue
                        # removing orders from the queue until the entire requested
                        # volume has been satisfied:
                        elif curr_order['volume_original'] < volume_original:
                            self.record_trade(new_order['trans_date'],
                                              new_order['trans_time'],
                                              best_price,
                                              curr_order['volume_original'],
                                              buy_order['order_number'],
                                              sell_order['order_number'])
                            volume_original -= curr_order['volume_original']
                            self.delete_order(curr_order['buy_sell_indicator'],
                                              best_price, order_number)
                        else:

                            # This should never be reached:
                            pass
                    
                        
        else:
            raise RuntimeError('invalid market order flag')
        
    def modify(self, new_order):
        """
        Modify the order with matching order number in the LOB.
        """

        # This exception should never be thrown:
        if new_order['mkt_flag'] == 'Y':
            raise ValueError('cannot modify market order')
        
        od = self.price_level(new_order['buy_sell_indicator'],
                              new_order['limit_price'])
        order_number = new_order['order_number']
        if od is not None:
            self.logger.info('matching price level found: %s' % \
                             new_order['limit_price'])

            # Find the old order to modify:
            try:
                old_order = od[order_number]
            except:
                self.logger.info('order number %i not found' % order_number)
            else:

                # If the modify changes the price of an order, remove it and
                # then add the modified order to the appropriate price level queue:
                if new_order['limit_price'] != old_order['limit_price']:
                    self.logger.info('modified order %i price from %f to %f: ' % \
                                     (order_number,
                                      old_order['limit_price'],
                                      new_order['limit_price']))
                    self.delete_order(old_order['buy_sell_indicator'],
                                      old_order['limit_price'],
                                      order_number)
                    self.add(new_order)
                    
                # If the modify reduces the original or disclosed volume of an
                # order, update it without altering where it is in the queue:
                elif new_order['volume_original'] < old_order['volume_original']:
                    self.logger.info('modified order %i original volume from %f to %f: ' % \
                                     (order_number,
                                      old_order['volume_original'],
                                      new_order['volume_original']))
                    od[order_number] = new_order
                elif new_order['volume_disclosed'] < old_order['volume_disclosed']:
                    self.logger.info('modified order %i disclosed volume from %f to %f: ' % \
                                     (order_number,
                                      old_order['volume_disclosed'],
                                      new_order['volume_disclosed']))
                    od[order_number] = new_order
                    
                # If the modify increases the original or disclosed volume of an
                # order, remove it and resubmit it to the queue:
                elif new_order['volume_original'] > old_order['volume_original']:
                    self.logger.info('modified order %i original volume from %f to %f: ' % \
                                     (order_number,
                                      old_order['volume_original'],
                                      new_order['volume_original']))
                    self.delete_order(old_order['buy_sell_indicator'],
                                      old_order['limit_price'],
                                      order_number)
                    self.add(new_order)
                elif new_order['volume_disclosed'] > old_order['volume_disclosed']:
                    self.logger.info('modified order %i disclosed volume from %f to %f: ' % \
                                     (order_number,
                                      old_order['volume_disclosed'],
                                      new_order['volume_disclosed']))
                    self.delete_order(old_order['buy_sell_indicator'],
                                      old_order['limit_price'],
                                      order_number)
                    self.add(new_order)
                else:
                    self.logger.info('undefined modify scenario')
        else:
            self.logger.info('no matching price level found')
                
    def cancel(self, order):
        """
        Remove the order with matching order number from the LOB.

        Parameters
        ----------
        order : dict
            Order to cancel.

        """

        # This exception should never be thrown:
        if order['mkt_flag'] == 'Y':
            raise ValueError('cannot cancel market order')

        indicator = order['buy_sell_indicator']
        price = order['limit_price']
        order_number = order['order_number']
        od = self.price_level(indicator, price)
        if od is not None:
            self.logger.info('matching price level found: %s, %f' % \
                             (indicator, price))
            try:
                old_order = od[order_number]            
            except:
                self.logger.info('order number %i not found' % order_number)
            else:
                self.delete_order(indicator, price, order_number)          
                self.logger.info('canceled order %i' % order_number)
        else:
            self.logger.info('no matching price level found')
                    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(levelname)s [%(funcName)s] %(message)s')    
    file_name = 'AXISBANK-orders.csv'

    df = pandas.read_csv(file_name,
                         names=col_names,
                         nrows=10000)
    lob = LimitOrderBook()
    lob.process(df)
