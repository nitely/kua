#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys


def start():
    argv = ['kua', 'discover']

    if len(sys.argv) > 1:
        argv = sys.argv

    unittest.main(module=None, argv=argv)


if __name__ == '__main__':
    start()
