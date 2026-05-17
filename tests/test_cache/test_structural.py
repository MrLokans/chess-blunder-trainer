from __future__ import annotations

import ast
import importlib
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.routing import APIRouter

import blunder_tutor.web.api as api_pkg
from blunder_tutor.cache.invalidation import CACHE_TAGS
from blunder_tutor.web.dependencies import set_request_scope

_API_DIR = Path(next(iter(api_pkg.__path__)))
_ROUTE_METHODS = frozenset(("get", "post", "put", "patch", "delete"))


@dataclass(frozen=True)
class _CachedRoute:
    module: str
    func: str
    tag: str | None
    router_name: str | None
    has_request_param: bool


def _tag_kw(call: ast.Call) -> str | None:
    for kw in call.keywords:
        if kw.arg == "tag" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _router_name(decorator: ast.expr) -> str | None:
    if (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr in _ROUTE_METHODS
        and isinstance(decorator.func.value, ast.Name)
    ):
        return decorator.func.value.id
    return None


def _has_request_param(func: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    a = func.args
    return any(arg.arg == "request" for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs))


def _cached_call(node: ast.AsyncFunctionDef | ast.FunctionDef) -> ast.Call | None:
    for dec in node.decorator_list:
        if (
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Name)
            and dec.func.id == "cached"
        ):
            return dec
    return None


def _route_from_node(
    node: ast.AsyncFunctionDef | ast.FunctionDef, module: str
) -> _CachedRoute | None:
    call = _cached_call(node)
    if call is None:
        return None
    router = next(
        (name for d in node.decorator_list if (name := _router_name(d))), None
    )
    return _CachedRoute(
        module=module,
        func=node.name,
        tag=_tag_kw(call),
        router_name=router,
        has_request_param=_has_request_param(node),
    )


def _collect_cached_routes() -> list[_CachedRoute]:
    routes: list[_CachedRoute] = []
    for path in sorted(_API_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        module = f"{api_pkg.__name__}.{path.stem}"
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                route = _route_from_node(node, module)
                if route is not None:
                    routes.append(route)
    return routes


_CACHED_ROUTES = _collect_cached_routes()


def test_scanner_found_cached_routes() -> None:
    # Guard against a false green: a broken scanner that finds nothing
    # would make every parametrized check below vacuously pass.
    assert len(_CACHED_ROUTES) >= 3


@pytest.mark.parametrize(
    "route", _CACHED_ROUTES, ids=lambda r: f"{r.module.split('.')[-1]}.{r.func}"
)
class TestCachedRouteContract:
    def test_tag_is_in_registry(self, route: _CachedRoute) -> None:
        assert route.tag in CACHE_TAGS

    def test_handler_accepts_request(self, route: _CachedRoute) -> None:
        # @cached fails closed without a Request; a route missing it
        # would 500 on first call instead of caching.
        assert route.has_request_param

    def test_router_carries_scope_dependency(self, route: _CachedRoute) -> None:
        assert route.router_name is not None
        module = importlib.import_module(route.module)
        router = getattr(module, route.router_name)
        assert isinstance(router, APIRouter)
        assert any(
            getattr(dep, "dependency", None) is set_request_scope
            for dep in router.dependencies
        )
