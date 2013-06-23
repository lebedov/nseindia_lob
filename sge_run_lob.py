#!/usr/bin/env python

"""
Script to run LOB implementation on a cluster
managed by Sun Grid Engine using Python bindings for DRMAA.
"""

import drmaa
import glob
import os

def main():

    # Directory in which output data should be written:
    output_dir = '/user/user2/lgivon/india_limit_order_book'

    # Location of LOB implementation:
    lob_app = os.path.join(output_dir, 'lob.py')

    s = drmaa.Session()
    s.initialize()
    jt = s.createJobTemplate()
    jt.remoteCommand = 'python'
    jt.nativeSpecification = '-v PATH=$PATH:/user/user2/lgivon/PYTHON/bin'
    for n in [1,2]:
        file_name = 'AXISBANK-test-%s.csv.gz' % n
        jt.jobName = 'AXISBANK-test-%s' % n
        print 'submitted job: ' + jt.jobName
        jt.args = [lob_app, 'AXISBANK', output_dir] + \
                  glob.glob(os.path.join(output_dir, file_name))
        jid = s.runJob(jt)
    s.synchronize([s.JOB_IDS_SESSION_ALL], s.TIMEOUT_WAIT_FOREVER, False)
    s.deleteJobTemplate(jt)
    s.exit()

if __name__ == '__main__':
    main()
    
