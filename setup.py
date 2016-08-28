#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

BASE_DIR = os.path.join(os.path.dirname(__file__))

with open(os.path.join(BASE_DIR, 'requirements.txt')) as f:
    REQUIREMENTS = f.read()

URL = 'https://github.com/nitely/kua'
README = "For more info, go to: {}".format(URL)
VERSION = __import__('kua').__version__


setup(
    name='kua',
    version=VERSION,
    description='Lightning fast URL routing.',
    author='Esteban Castro Borsani',
    author_email='ecastroborsani@gmail.com',
    long_description=README,
    url=URL,
    packages=find_packages(exclude=[]),
    test_suite="runtests.start",
    zip_safe=False,
    include_package_data=True,
    install_requires=REQUIREMENTS,
    setup_requires=REQUIREMENTS,
    license='MIT License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content'])
