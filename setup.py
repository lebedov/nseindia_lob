import os

try:
    import setuptools
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
 
from setuptools import setup, Extension
#from distutils.core import setup
#from distutils.extension import Extension
from Cython.Distutils import build_ext

NAME =                 'nseindia_lob'
VERSION =              '0.01'
AUTHOR =               'Lev Givon'
AUTHOR_EMAIL =         'lev@columbia.edu'
URL =                  'https://github.com/lebedov/nseindia_lob/'
MAINTAINER =           AUTHOR
MAINTAINER_EMAIL =     AUTHOR_EMAIL
DESCRIPTION =          'National Stock Exchange of India Limit Order Book Simulation'
LICENSE =              'BSD'
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Financial and Insurance Industry',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python']

ext_modules = [Extension('_lob', ['_lob.pyx'])]

if __name__ == '__main__':
    if os.path.exists('MANIFEST'):
        os.remove('MANIFEST')

    setup(name = NAME,
          version = VERSION,
          author = AUTHOR,
          author_email = AUTHOR_EMAIL,
          url = URL,
          maintainer = MAINTAINER,
          maintainer_email =MAINTAINER_EMAIL,
          description = DESCRIPTION,
          license = LICENSE,
          classifiers = CLASSIFIERS,
          install_requires = ['numpy >= 1.7.0',
                              'odict >= 1.5.0',
                              'pandas >= 0.10',
                              'rbtree >= 0.9.0'],
          ext_modules = ext_modules,
          cmdclass = {'build_ext': build_ext},
    )
