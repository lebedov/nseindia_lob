#!/usr/bin/env python

"""
Script to run LOB implementation on a cluster
managed by Sun Grid Engine using Python bindings for DRMAA.
"""

import drmaa
import glob
import os

# List of the 50 firms with the highest average daily volume of trade:
firm_name_list = ['TATAPOWER']
firm_name_list_x = ['IFCI',
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

    # Directory in which output data should be written:
    output_dir = '/user/user2/lgivon/india_limit_order_book'

    # Location of LOB implementation:
    lob_app = os.path.join(output_dir, 'lob.py')

    s = drmaa.Session()
    s.initialize()
    jt = s.createJobTemplate()
    jt.remoteCommand = 'python'
    jt.nativeSpecification = '-q all.q -l virtual_free=2000000000,h_vmem=2000000000,h_stack=67208864 -v PATH=$PATH:/user/user2/lgivon/PYTHON/bin'
    for firm_name in firm_name_list:
        file_name_list = sorted(glob.glob(os.path.join(output_dir, 'orders_*', '%s-orders.csv.gz' % firm_name)))
        jt.jobName = firm_name
        print 'submitted job: ' + jt.jobName
        jt.args = [lob_app, firm_name, output_dir] + file_name_list
        jid = s.runJob(jt)
    #s.synchronize([s.JOB_IDS_SESSION_ALL], s.TIMEOUT_WAIT_FOREVER, False)
    #s.deleteJobTemplate(jt)
    s.exit()

if __name__ == '__main__':
    main()
    
