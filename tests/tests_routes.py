# -*- coding: utf-8 -*-

import unittest
import logging

from kua import routes


logging.disable(logging.CRITICAL)


class ReactTest(unittest.TestCase):

    def setUp(self):
        self.routes = routes.Routes()

    def tearDown(self):
        pass

    def test_match(self):
        """
        Should match an url to a registered pattern
        """
        self.routes.add(':foo/:bar/api/:baz', 'foo')
        params, anything = self.routes.match('foo/bar/api/baz')
        self.assertDictEqual(
            params,
            {'foo': 'foo', 'bar': 'bar', 'baz': 'baz'})
        self.assertEqual(anything, 'foo')

    def test_match_nested(self):
        """
        Should support nested patterns
        """
        self.routes.add(':foo/:bar/api/:baz', 'foo')
        self.routes.add(':foo/:bar/api/:baz/books/:id', 'bar')
        params, anything = self.routes.match('foo/bar/api/baz')
        params_b, anything_b = self.routes.match('foo/bar/api/baz/books/id')
        self.assertDictEqual(
            params,
            {'foo': 'foo', 'bar': 'bar', 'baz': 'baz'})
        self.assertDictEqual(
            params_b,
            {'foo': 'foo', 'bar': 'bar', 'baz': 'baz', 'id': 'id'})
        self.assertEqual(anything, 'foo')
        self.assertEqual(anything_b, 'bar')

    def test_match_clashing(self):
        """
        Should resolve clashing
        """
        self.routes.add(':foo/:bar/:baz', 'foo')
        self.routes.add(':foo/api/:baz', 'bar')
        _, anything = self.routes.match('foo/bar/baz')
        _, anything_b = self.routes.match('foo/api/baz')
        self.assertEqual(anything, 'foo')
        self.assertEqual(anything_b, 'bar')

    def test_match_clashing_backtraking(self):
        """
        Should resolve clashing by doing backtracking
        """
        # match will walk up to the "api" part then realize
        # it needs one more part and then fallback to the previous
        # matched path (ie: all variables)
        self.routes.add(':bar/:baz', 'foo')
        self.routes.add('api', 'bar')
        params, anything = self.routes.match('bar/baz')
        params_b, anything_b = self.routes.match('api/baz')
        self.assertDictEqual(
            params,
            {'bar': 'bar', 'baz': 'baz'})
        self.assertDictEqual(
            params_b,
            {'bar': 'api', 'baz': 'baz'})
        self.assertEqual(anything, 'foo')
        self.assertEqual(anything_b, 'foo')

    def test_match_clashing_backtraking_deeper(self):
        """
        Should resolve clashing by doing backtracking
        """
        self.routes.add(':foo/:bar/:baz', 'foo')
        self.routes.add('api/:bar/:baz', 'bar')
        self.routes.add('api/id', 'baz')
        params, anything = self.routes.match('api/id/baz')
        self.assertDictEqual(
            params,
            {'bar': 'id', 'baz': 'baz'})
        self.assertEqual(anything, 'bar')

    def test_match_clashing_last_part(self):
        """
        Should resolve clashing by doing backtracking
        """
        self.routes.add(':foo/last', 'foo')
        self.routes.add('api', 'baz')
        params, anything = self.routes.match('api/last')
        self.assertDictEqual(
            params,
            {'foo': 'api'})
        self.assertEqual(anything, 'foo')

    def test_match_not_found(self):
        """
        Should raise match error if there is no match
        """
        self.assertRaises(routes.RouteError, self.routes.match, 'foo')

    def test_match_case_sensitive(self):
        """
        Should be case sensitive (see HTTP URL spec)
        """
        self.routes.add('API', 'foo')
        params, anything = self.routes.match('API')
        self.assertDictEqual(params, {})
        self.assertEqual(anything, 'foo')
        self.assertRaises(routes.RouteError, self.routes.match, 'api')

    def test_match_bail_early_on_deeper_urls(self):
        """
        Should not bother matching URLs larger than the largest registered URL
        """
        self.routes.add('foo/bar/baz', 'foo')
        self.routes.match('foo/bar/baz')
        self.routes._max_depth = 0
        self.assertRaises(routes.RouteError, self.routes.match, 'foo/bar/baz')
        self.routes._max_depth = 1
        self.assertRaises(routes.RouteError, self.routes.match, 'foo/bar/baz')
        self.routes._max_depth = 10
        self.routes.match('foo/bar/baz')
