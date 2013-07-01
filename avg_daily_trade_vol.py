#!/usr/bin/env python

"""
Compute average daily trade volume of Indian NSE securities.

Notes
-----
Assumes that the trade data for a specific firm XXX is stored in a file
named XXX-trades.csv.

"""

import glob
import pandas
import re

file_name_list = glob.glob('*-trades.csv')
avg_daily_vol_dict = {}
for file_name in file_name_list:

    # Get security name from file name:
    security = re.search('(\w+)-trades\.csv', file_name).group(1)

    # Column 3 contains the day, column 11 contains the volume:
    df = pandas.read_csv(file_name, header=None)

    avg_daily_vol = df.groupby(3)[11].sum().mean()
    avg_daily_vol_dict[security] = avg_daily_vol

# Print securities with highest volume first:
for security in sorted(avg_daily_vol_dict, key=avg_daily_vol_dict.get, reverse=True):
    print '{:<15s} {:>12.2f}'.format(security, avg_daily_vol_dict[security])
