#!/usr/bin/env python

"""
Limit order book simulation for Indian security exchange.
"""

import _lob

import glob
import gzip
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

    root_dir = '/user/user2/lgivon/india_limit_order_book/'
    #root_dir = './'

    lob = _lob.LimitOrderBook(show_output=False, sparse_events=True,
                              events_log_file=root_dir+'events.log.gz',
                              stats_log_file=None,
                              daily_stats_log_file=root_dir+'daily_stats.log.gz')
    fh = logging.FileHandler(root_dir+'lob.log', 'w')
    fh.setFormatter(logging.Formatter(format))
    lob.logger.addHandler(fh)

    # Process all available files; assumes that the files are named in
    # a way such that their sort order corresponds to the
    # chronological order of their respective contents:    
    for file_name in sorted(glob.glob(root_dir+'AXISBANK-orders*.csv.gz')):

        # Check whether input file is compressed:
        with gzip.open(file_name, 'rb') as f:
            try:
                f.read(1)
            except IOError:
                compression = None
            else:
                compression = 'gzip'
                
        tp = pandas.read_csv(file_name,
                             names=_lob.col_names,
                             iterator=True,
                             compression=compression)
        while True:
            try:
                data = tp.get_chunk(500)
            except StopIteration:
                break
            else:
                # Process orders that occurred before a certain cutoff time:
                #if data.irow(0)['trans_time'] > '09:25:00.000000':
                #    break        
                lob.process(data)

    lob.print_daily_stats()
    print 'Processing time:              ', (time.time()-start)
