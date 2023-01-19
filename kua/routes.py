# -*- coding: utf-8 -*-

import re
import urllib.parse
import collections
from typing import (
    Tuple,
    List,
    Sequence,
    Any,
    Dict,
    Union,
    Callable,
    Iterator)


__all__ = [
    'RouteError',
    'Routes',
    'RouteResolved']

# This is a nested structure similar to a linked-list
WrappedVariablePartsType = Tuple[tuple, Tuple[str, str]]
VariablePartsType = Tuple[Union[str, Tuple[str]]]
VariablePartsIterType = Iterator[Union[str, Tuple[str]]]
ValidateType = Dict[str, Callable[[str], bool]]


class RouteError(Exception):
    """Base error for any exception raised by Kua"""


class MatchRouteError(RouteError):
    """No match found"""


class DecodeRouteError(RouteError):
    """Can't decode the URL"""


def depth_of(parts: Sequence[str]) -> int:
    """
    Calculate the depth of URL parts

    :param parts: A list of URL parts
    :return: Depth of the list

    :private:
    """
    return len(parts) - 1


def normalize_url(url: str) -> str:
    """
    Remove leading and trailing slashes from a URL

    :param url: URL
    :return: URL with no leading and trailing slashes

    :private:
    """
    if url.startswith('/'):
        url = url[1:]

    if url.endswith('/'):
        url = url[:-1]

    return url


def decode_parts(parts):
    try:
        return tuple(
            urllib.parse.unquote(
                part, encoding='utf-8', errors='strict')
            for part in parts)
    except UnicodeDecodeError:
        raise DecodeRouteError('Can\'t decode the URL')


def _unwrap(variable_parts: WrappedVariablePartsType) -> VariablePartsIterType:
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

        if var_type == Routes._VAR_ANY_BREAK:
            if var_any:
                yield tuple(reversed(var_any))
                var_any.clear()

            var_any.append(part)
            continue

        if var_any:
            yield tuple(reversed(var_any))
            var_any.clear()
            yield part
            continue

        yield part

    if var_any:
        yield tuple(reversed(var_any))


def unwrap(variable_parts: WrappedVariablePartsType) -> VariablePartsType:
    return tuple(reversed(tuple(_unwrap(variable_parts))))


def make_params(
        key_parts: Sequence[str],
        variable_parts: VariablePartsIterType) -> Dict[str, Union[str, Tuple[str]]]:
    """
    Map keys to variables. This map\
    URL-pattern variables to\
    a URL related parts

    :param key_parts: A list of URL parts
    :param variable_parts: A list of URL parts
    :return: The param dict with the values\
    assigned to the keys

    :private:
    """
    return dict(zip(key_parts, variable_parts))


_SAFE_COMPONENT = re.compile(r'[ \w\-_.]+')


def _is_safe(part: str) -> bool:
    if isinstance(part, tuple):  # /:*parts/
        return all(_is_safe(p) for p in part)

    return _SAFE_COMPONENT.fullmatch(part) is not None


def validate(
        key_parts: Sequence[str],
        variable_parts: VariablePartsIterType,
        params_validate: dict) -> bool:
    return all(
        params_validate.get(param, _is_safe)(value)
        for param, value in zip(key_parts, variable_parts))


_Route = collections.namedtuple(
    '_Route',
    ['key_parts', 'anything', 'validate'])
_Route.__doc__ = (
    """
    Route pattern state. Every pattern has one of this.

    :param tuple key_parts: Pattern variable names
    :param object anything: Literally anything. For retrieving later
    :param dict validate: A map of ``{var: validator}``

    :private:
    """)


def _route(key_parts: Sequence, anything: Any, validate: ValidateType) -> _Route:
    key_parts = tuple(key_parts)
    validate = validate or {}

    if not set(validate.keys()).issubset(set(key_parts)):
        raise RouteError(
            '{missing_vars} not found within the pattern'.format(
                missing_vars=set(validate.keys()).difference(set(key_parts))))

    return _Route(
        key_parts=key_parts,
        anything=anything,
        validate=validate)


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


def _resolve(
        variable_parts: VariablePartsType,
        routes: Sequence[_Route]) -> Union[RouteResolved, None]:
    for route in routes:
        if validate(
                route.key_parts,
                variable_parts,
                route.validate):
            return RouteResolved(
                params=make_params(
                    key_parts=route.key_parts,
                    variable_parts=variable_parts),
                anything=route.anything)

    return None


class Routes:
    """
    Route URLs to registered URL patterns.

    Thread safety: every method has a doc note about this

    URL matcher supports ``:var`` for matching dynamic\
    path parts and ``:*var`` for matching multiple parts.

    Path parts have precedence: ``static > var > *var``.

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
        except kua.MatchRouteError:
            raise Exception('Not Found 404')
        except kua.DecodeRouteError:
            raise Exception('Bad Request 400')
        except kua.RouteError:
            raise Exception('Internal Server Error 500')
        else:
            # Do something useful here
            pass

        # Typed vars
        is_num = lambda part: part.isdigit()
        routes.add('api/user/:id', {'GET': my_get_controller}, {'id': is_num})
        route = routes.match('api/user/123')
        route.params
        # {'id': '123'}

    :ivar max_depth: The maximum URL depth\
    (number of parts) willing to match. This only\
    takes effect when one or more URLs matcher\
    make use of any-var (i.e: ``:*var``), otherwise the\
    depth of the deepest URL is taken.
    """

    _VAR_NODE = ':var'
    _VAR_ANY_NODE = ':*var'
    _ROUTE_NODE = ':route'

    _VAR_ANY_BREAK = ':*var:break'

    def __init__(self, max_depth: int=10) -> None:
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
        self._max_depth_custom = max_depth
        # Routes graph format for 'foo/:foobar/bar':
        # {
        #   'foo': {
        #       ':var': {
        #           'bar': {
        #               ':route': [_Route(), ...],
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

    def _deconstruct_url(self, url: str) -> List[str]:
        """
        Split a regular URL into parts

        :param url: A normalized URL
        :return: Parts of the URL
        :raises kua.routes.RouteError: \
        If the depth of the URL exceeds\
        the max depth of the deepest\
        registered pattern

        :private:
        """
        parts = url.split('/', self._max_depth + 1)

        if depth_of(parts) > self._max_depth:
            raise MatchRouteError('No match')

        return parts

    def _match(self, parts: Sequence[str]) -> RouteResolved:
        """
        Match URL parts to a registered pattern.

        This function is basically where all\
        the CPU-heavy work is done.

        :param parts: URL parts
        :return: Matched route
        :raises kua.routes.RouteError: If there is no match

        :private:
        """
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
                if self._ROUTE_NODE not in curr:
                    continue

                route_resolved = _resolve(
                    variable_parts=unwrap(curr_variable_parts),
                    routes=curr[self._ROUTE_NODE])

                if not route_resolved:
                    continue

                return route_resolved

            if self._VAR_ANY_NODE in curr:
                to_visit.append((
                    {self._VAR_ANY_NODE: curr[self._VAR_ANY_NODE]},
                    (curr_variable_parts,
                     (self._VAR_ANY_NODE, part)),
                    depth + 1))
                to_visit.append((
                    curr[self._VAR_ANY_NODE],
                    (curr_variable_parts,
                     (self._VAR_ANY_BREAK, part)),
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

        raise MatchRouteError('No match')

    def match(self, url: str) -> RouteResolved:
        """
        Match a URL to a registered pattern.

        This method is thread-safe.

        :param url: URL
        :return: Matched route
        :raises kua.RouteError: If there is no match
        """
        url = normalize_url(url)
        parts = self._deconstruct_url(url)

        if '%' in url:
            parts = decode_parts(parts)

        return self._match(parts)

    def add(self, url: str, anything: Any, validate: ValidateType=None) -> None:
        """
        Register a URL pattern into\
        the routes for later matching.

        This method is not thread-safe.\
        It should be called on import time or with a lock.

        It's possible to attach any kind of\
        object to the pattern for later\
        retrieving. A dict with methods and callbacks,\
        for example. Anything really.

        Registration order does not matter.\
        Adding a URL first or last makes no difference.

        :param url: URL
        :param anything: Literally anything.
        :param validate: Map of ``{var: func}``\
        for validating matched vars
        """
        url = normalize_url(url)
        parts = url.split('/')
        curr_partial_routes = self._routes
        curr_key_parts = []

        for part in parts:
            if part.startswith(':*'):
                curr_key_parts.append(part[2:])
                part = self._VAR_ANY_NODE
                self._max_depth = self._max_depth_custom

            elif part.startswith(':'):
                curr_key_parts.append(part[1:])
                part = self._VAR_NODE

            curr_partial_routes = (
                curr_partial_routes.setdefault(part, {}))

        (curr_partial_routes
         .setdefault(self._ROUTE_NODE, [])
         .append(_route(
            key_parts=curr_key_parts,
            anything=anything,
            validate=validate)))

        self._max_depth = max(self._max_depth, depth_of(parts))
