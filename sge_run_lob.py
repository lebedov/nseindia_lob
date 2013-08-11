#!/usr/bin/env python

"""
Script to run LOB implementation on a cluster
managed by Sun Grid Engine using Python bindings for DRMAA.
"""

import drmaa
import glob
import os
import os.path

# List of the 50 firms with the highest average daily volume of trade:
firm_name_list = ['TATAPOWER',
                  'IFCI',
                  'SUZLON',
                  'RCOM',
                  'JPASSOCIAT',
                  'UNITECH',
                  'HDIL',
                  'GVKPIL',
                  'LITL',
                  'RENUKA',
                  'TATAMOTORS',
                  'DLF',
                  'GMRINFRA',
                  'ALOKTEXT',
                  'HINDALCO',
                  'IVRCLINFRA',
                  'STER',
                  'IDFC',
                  'BHEL',
                  'NIFTY',
                  'MTNL',
                  'RPOWER',
                  'NHPC',
                  'PANTALOONR',
                  'IBREALEST',
                  'APOLLOTYRE',
                  'TATASTEEL',
                  'PUNJLLOYD',
                  'BHARTIARTL',
                  'SAIL',
                  'DENABANK',
                  'JISLJALEQS',
                  'ITC',
                  'SINTEX',
                  'ASHOKLEY',
                  'DISHTV',
                  'PFC',
                  'JSWENERGY',
                  'CAIRN',
                  'SESAGOA',
                  'KTKBANK',
                  'RELCAPITAL',
                  'IRB',
                  'N',
                  'RELIANCE',
                  'ICICIBANK',
                  'JINDALSTEL',
                  'IDBI',
                  'YESBANK',
                  'AUROPHARMA',
                  'TATAPOWER']

def main():

    # Base directory containing orders_* subdirectories with securities order
    # data:
    home_dir = os.path.expanduser('~')
    base_dir = home_dir + '/nseindia_lob'

    # Subdirectory in which output data should be written:
    output_dir = os.path.join(base_dir, 'output')

    # Location of LOB implementation:
    lob_app = os.path.join(base_dir, 'lob.py')

    # Set the PATH accordingly if using a virtualenv:
    s = drmaa.Session()
    s.initialize()
    jt = s.createJobTemplate()
    jt.remoteCommand = 'python'
    jt.nativeSpecification = '-q all.q -l virtual_free=2000000000,h_vmem=2000000000,h_stack=67208864 -v PATH=$PATH:%s/PYTHON/bin' % home_dir
    for firm_name in firm_name_list:
        file_name_list = sorted(glob.glob(os.path.join(base_dir, 'orders_*', '%s-orders.csv.gz' % firm_name)))
        jt.jobName = firm_name
        print 'submitted job: ' + jt.jobName
        jt.args = [lob_app, firm_name, output_dir] + file_name_list
        jid = s.runJob(jt)
    s.exit()

if __name__ == '__main__':
    main()
    
