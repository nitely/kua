# -*- coding: utf-8 -*-

import collections
from typing import (
    Tuple,
    List,
    Sequence,
    Any)


__all__ = [
    'RouteError',
    'Routes',
    'RouteResolved']

# This is a nested structure similar to a linked-list
VariablePartsType = Tuple[tuple, Tuple[str, str]]


class RouteError(Exception):
    """Base error for any exception raised by Kua"""


def depth_of(parts: Sequence[str]):
    """
    Calculate the depth of URL parts

    :param list parts: A list of URL parts
    :return: Depth of the list
    :rtype: int

    :private:
    """
    return len(parts) - 1


def normalize_url(url: str):
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


def _unwrap(variable_parts: VariablePartsType):
    """
    Yield URL parts. The given parts are usually in reverse order.
    """
    curr_parts = variable_parts
    var_any = []

    while curr_parts:
        curr_parts, (var_type, part) = curr_parts

        if var_type == Routes._VAR_ANY_NODE:
            var_any.append(part)
            continue

        if var_any:
            yield tuple(reversed(var_any))
            yield part
            var_any.clear()
            continue

        yield part

    if var_any:
        yield tuple(reversed(var_any))


def make_params(key_parts: Sequence[str], variable_parts: VariablePartsType):
    """
    Map keys to variables. This map\
    URL-pattern variables to\
    a URL related parts

    :param tuple key_parts: A list of URL parts
    :param tuple variable_parts: A linked-list\
    (ala nested tuples) of URL parts
    :return: The param dict with the values\
    assigned to the keys
    :rtype: dict

    :private:
    """
    # The unwrapped variable parts are in reverse order.
    # Instead of reversing those we reverse the key parts
    # and avoid the O(n) space required for reversing the vars
    return dict(zip(reversed(key_parts), _unwrap(variable_parts)))


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

    URL matcher supports ``:var`` for matching dynamic\
    path parts and ``:*var`` for matching one or more parts.

    Path parts are matched in the following order: ``static > var > any-var``.

    Usage::

        routes = kua.Routes()
        routes.add('api/:foo', {'GET': my_get_controller})
        route = routes.match('api/hello-world')
        route.params
        # {'foo': 'hello-world'}
        route.anything
        # {'GET': my_get_controller}

        # Matching any path
        routes.add('assets/:*foo', {})
        route = routes.match('assets/user/profile/avatar.jpg')
        route.params
        # {'foo': ('user', 'profile', 'avatar.jpg')}

        # Error handling
        try:
            route = routes.match('bad-url/some')
        except kua.RouteError:
            raise ValueError('Not found 404')
        else:
            # Do something useful here
            pass

    """

    _VAR_NODE = ':var'
    _VAR_ANY_NODE = ':*var'
    _ROUTE_NODE = ':route'

    def __init__(self, depth_limit: int=40):
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
        self._depth_limit = depth_limit
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

    def _deconstruct_url(self, url: str):
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

        if depth_of(parts) > self._max_depth:
            raise RouteError('No match')

        return parts

    def _match(self, parts: Sequence[str]):
        """
        Match URL parts to a registered pattern.

        This function is basically where all\
        the CPU-heavy work is done.

        :param list parts: URL parts
        :return: Matched route
        :rtype: :py:class:`.RouteResolved`
        :raises kua.routes.RouteError: If there is no match

        :private:
        """
        route_match = None  # type: RouteResolved
        route_variable_parts = tuple()  # type: VariablePartsType
        # (route_partial, variable_parts, depth)
        to_visit = [(self._routes, tuple(), 0)]  # type: List[Tuple[dict, tuple, int]]

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

            if self._VAR_ANY_NODE in curr:
                to_visit.append((
                    {self._VAR_ANY_NODE: curr[self._VAR_ANY_NODE]},
                    (curr_variable_parts,
                     (self._VAR_ANY_NODE, part)),
                    depth + 1))
                to_visit.append((
                    curr[self._VAR_ANY_NODE],
                    (curr_variable_parts,
                     (self._VAR_ANY_NODE, part)),
                    depth + 1))

            if self._VAR_NODE in curr:
                to_visit.append((
                    curr[self._VAR_NODE],
                    (curr_variable_parts,
                     (self._VAR_NODE, part)),
                    depth + 1))

            if part in curr:
                to_visit.append((
                    curr[part],
                    curr_variable_parts,
                    depth + 1))

        if not route_match:
            raise RouteError('No match')

        return RouteResolved(
            params=make_params(
                key_parts=route_match.key_parts,
                variable_parts=route_variable_parts),
            anything=route_match.anything)

    def match(self, url: str):
        """
        Match a URL to a registered pattern.

        :param str url: URL
        :return: Matched route
        :rtype: :py:class:`.RouteResolved`
        :raises kua.RouteError: If there is no match
        """
        url = normalize_url(url)
        parts = self._deconstruct_url(url)
        return self._match(parts)

    def add(self, url: str, anything: Any):
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

        for part in parts:
            if part.startswith(':*'):
                curr_key_parts.append(part[2:])
                part = self._VAR_ANY_NODE

            elif part.startswith(':'):
                curr_key_parts.append(part[1:])
                part = self._VAR_NODE

            curr_partial_routes = (curr_partial_routes
                                   .setdefault(part, {}))

        curr_partial_routes[self._ROUTE_NODE] = _Route(
            key_parts=curr_key_parts,
            anything=anything)

        self._max_depth = max(self._max_depth, depth_of(parts))
