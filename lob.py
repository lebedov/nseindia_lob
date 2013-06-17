#!/usr/bin/env python

"""
Limit order book simulation for Indian security exchange.
"""

import _lob as lob

import logging
import pandas
import time

if __name__ == '__main__':
    start = time.time()

    format = '%(asctime)s %(name)s %(levelname)s [%(funcName)s] %(message)s'
    logging.basicConfig(level=logging.WARNING, format=format)

    # Remove root log handlers:
    for h in logging.root.handlers:
        logging.root.removeHandler(h)

    #root_dir = '/user/user2/lgivon/india_limit_order_book/'
    root_dir = './'

    lob_obj = lob.LimitOrderBook(show_output=False, sparse_events=True,
                                 events_log_file=root_dir+'events.log',
                                 stats_log_file=None,
                                 daily_stats_log_file=root_dir+'daily_stats.log')
    fh = logging.FileHandler(root_dir+'lob.log', 'w')
    fh.setFormatter(logging.Formatter(format))
    lob_obj.logger.addHandler(fh)

    file_name = root_dir+'AXISBANK-orders.csv'
    tp = pandas.read_csv(file_name,
                         names=lob.col_names,
                         iterator=True)
    # for i in xrange(50):
    #     data = tp.get_chunk(200)
    #     lob.process(data)

    # Process orders that occurred before a certain cutoff time:
    while True:
        try:
            data = tp.get_chunk(500)
        except StopIteration:
            break
        else:
            if data.irow(0)['trans_time'] > '09:25:00.000000':
                break        
            lob_obj.process(data)

    lob_obj.print_daily_stats()
    print 'Processing time:              ', (time.time()-start)
