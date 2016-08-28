# -*- coding: utf-8 -*-

import collections


__all__ = [
    'RouteError',
    'Routes',
    'RouteResolved']


class RouteError(Exception):
    """Base error for any exception raised by Kua"""


def depth_of(parts):
    """
    Calculate the depth of URL parts

    :param list parts: A list of URL parts
    :return: Depth of the list
    :rtype: int

    :private:
    """
    return len(parts) - 1


def normalize_url(url):
    """
    Remove leading and trailing slashes from a URL

    :param str url: URL
    :return: URL with no leading and trailing slashes
    :rtype: str

    :private:
    """
    if url.startswith('/'):
        url = url[1:]

    if url.endswith('/'):
        url = url[:-1]

    return url


def make_params(key_parts, variable_parts):
    """
    Map keys to variables. This map\
    URL-pattern variables to\
    a URL related parts

    :param tuple key_parts: A list of URL parts
    :param tuple variable_parts: A list of URL parts
    :return: The param dict with the values\
    assigned to the keys
    :rtype: dict

    :private:
    """
    assert len(key_parts) == len(variable_parts)

    return dict(zip(key_parts, variable_parts))


_Route = collections.namedtuple(
    '_Route',
    ['key_parts', 'anything'])


RouteResolved = collections.namedtuple(
    'RouteResolved',
    ['params', 'anything'])
RouteResolved.__doc__ = (
    """
    Resolved route

    :param dict params: Pattern variables\
    to URL parts
    :param object anything: Literally anything.\
    This is attached to the URL pattern when\
    registering it
    """)


class Routes:
    """
    Route URLs to registered URL patterns.

    Thread safety: adding routes is not thread-safe,\
    it should be done on import time, everything else is.

    Usage::

        routes_ = routes.Routes()
        routes_.add('api/:foo', {'GET': my_get_controller})
        route = routes_.match('api/hello-world')
        route.params
        # {'foo': 'hello-world'}
        route.anything
        # {'GET': my_get_controller}

    """

    _VAR_NODE = ':var'
    _ROUTE_NODE = ':route'

    def __init__(self):
        """
        :ivar _routes: \
        Contain a graph with the parts of\
        each URL pattern. This is referred as\
        "partial route" later in the docs.
        :vartype _routes: dict
        :ivar _max_depth: Depth of the deepest\
        registered pattern
        :vartype _max_depth: int

        :private-vars:
        """
        # Routes graph format for 'foo/:foobar/bar':
        # {
        #   'foo': {
        #       ':var': {
        #           'bar': {
        #               ':route': _Route(),
        #               ...
        #           },
        #           ...
        #        }
        #        ...
        #   },
        #   ...
        # }
        self._routes = {}
        self._max_depth = 0

    def _deconstruct_url(self, url):
        """
        Split a regular URL into parts

        :param str url: A normalized URL
        :return: Parts of the URL
        :rtype: list
        :raises kua.routes.RouteError: \
        If the depth of the URL exceeds\
        the max depth of the deepest\
        registered pattern

        :private:
        """
        parts = url.split('/', self._max_depth + 1)
        total_depth = depth_of(parts)

        if total_depth > self._max_depth:
            raise RouteError('No match')

        return parts

    def _match(self, parts):
        """
        Match URL parts to a registered pattern.

        Return `None` if there is no match.

        This function is basically where all\
        the CPU-heavy work is done.

        :param list parts: URL parts
        :return: Matched route
        :rtype: :py:class:`.RouteResolved` or None

        :private:
        """
        route_match = None
        route_variable_parts = tuple()
        to_visit = [(self._routes, tuple(), 0)]  # (route_partial, variable_parts, depth)

        # Walk through the graph,
        # keep track of all possible
        # matching branches and do
        # backtracking if needed
        while to_visit:
            curr, curr_variable_parts, depth = to_visit.pop()

            try:
                part = parts[depth]
            except IndexError:
                if self._ROUTE_NODE in curr:
                    route_match = curr[self._ROUTE_NODE]
                    route_variable_parts = curr_variable_parts
                    break
                else:
                    continue

            if self._VAR_NODE in curr:
                to_visit.append((
                    curr[self._VAR_NODE],
                    (*curr_variable_parts, part),
                    depth + 1))

            if part in curr:
                to_visit.append((
                    curr[part],
                    curr_variable_parts,
                    depth + 1))

        if not route_match:
            return None
        else:
            return RouteResolved(
                params=make_params(
                    key_parts=route_match.key_parts,
                    variable_parts=route_variable_parts),
                anything=route_match.anything)

    def match(self, url):
        """
        Match a URL to a registered pattern.

        :param str url: URL
        :return: Matched route
        :rtype: :py:class:`.RouteResolved`
        :raises kua.routes.RouteError: If there is no match
        """
        url = normalize_url(url)
        parts = self._deconstruct_url(url)
        route = self._match(parts)

        if not route:
            raise RouteError('No match')

        return route

    def add(self, url, anything):
        """
        Register a URL pattern into\
        the routes for later matching.

        It's possible to attach any kind of\
        object to the pattern for later\
        retrieving. A dict with methods and callbacks,\
        for example. Anything really.

        Registration order does not matter.\
        Adding a URL first or last makes no difference.

        :param str url: URL
        :param object anything: Literally anything.
        """
        url = normalize_url(url)
        parts = url.split('/')
        curr_partial_routes = self._routes
        curr_key_parts = []

        for depth, part in enumerate(parts):
            if part.startswith(':'):
                curr_key_parts.append(part[1:])
                part = self._VAR_NODE

            curr_partial_routes = (curr_partial_routes
                                   .setdefault(part, {}))

        curr_partial_routes[self._ROUTE_NODE] = _Route(
            key_parts=curr_key_parts,
            anything=anything)

        self._max_depth = max(self._max_depth, depth_of(parts))
