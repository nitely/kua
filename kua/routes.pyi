from _typeshed import Incomplete
from typing import Any, NamedTuple, Tuple

VariablePartsType = Tuple[tuple, Tuple[str, str]]

class RouteError(Exception): ...

class _Route(NamedTuple):
    key_parts: Incomplete
    anything: Incomplete

class RouteResolved(NamedTuple):
    params: Incomplete
    anything: Incomplete

class Routes:
    def __init__(self, max_depth: int = ...) -> None: ...
    def match(self, url: str) -> RouteResolved: ...
    def add(self, url: str, anything: Any) -> None: ...

# Names in __all__ with no definition:
#   RouteResolved
