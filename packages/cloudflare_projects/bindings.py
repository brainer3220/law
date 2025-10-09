from __future__ import annotations

from typing import Any, Awaitable, Dict, Iterable, Optional, Protocol, runtime_checkable


@runtime_checkable
class D1PreparedStatement(Protocol):
    """Minimal subset of the Cloudflare D1 prepared statement API."""

    def bind(self, *args: Any) -> "D1PreparedStatement":
        ...

    def first(self) -> Awaitable[Optional[Dict[str, Any]]]:
        ...

    def all(self) -> Awaitable[Dict[str, Any]]:
        ...

    def raw(self) -> Awaitable[Iterable[Iterable[Any]]]:
        ...

    def run(self) -> Awaitable[Dict[str, Any]]:
        ...


@runtime_checkable
class D1Binding(Protocol):
    """Interface expected from env.DB bindings inside Workers."""

    def prepare(self, sql: str) -> D1PreparedStatement:
        ...

    def batch(self, statements: Iterable[Any]) -> Awaitable[Iterable[Any]]:
        ...


@runtime_checkable
class R2Object(Protocol):
    """Subset of an R2 object returned from get/head operations."""

    body: Any
    http_metadata: Dict[str, Any]

    async def array_buffer(self) -> bytes:
        ...


@runtime_checkable
class R2Binding(Protocol):
    async def get(self, key: str) -> Optional[R2Object]:
        ...

    async def put(
        self,
        key: str,
        value: Any,
        *,
        http_metadata: Optional[Dict[str, Any]] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...


@runtime_checkable
class QueueBinding(Protocol):
    async def send(self, body: Dict[str, Any], *, delay_seconds: Optional[int] = None) -> None:
        ...


@runtime_checkable
class DurableObjectStub(Protocol):
    async def fetch(self, path: str, *, method: str = "POST", body: Any = None) -> Any:
        ...


@runtime_checkable
class DurableObjectNamespace(Protocol):
    def id_from_name(self, name: str) -> Any:
        ...

    def get(self, id_: Any) -> DurableObjectStub:
        ...


@runtime_checkable
class CacheBinding(Protocol):
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...

    async def put(self, key: str, value: Dict[str, Any], *, ttl_seconds: int) -> None:
        ...


@runtime_checkable
class AIGatewayBinding(Protocol):
    async def rerank(self, *, model: str, query: str, documents: Iterable[str]) -> Dict[str, Any]:
        ...

    async def complete(self, *, model: str, messages: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        ...


__all__ = [
    "AIGatewayBinding",
    "CacheBinding",
    "D1Binding",
    "D1PreparedStatement",
    "DurableObjectNamespace",
    "DurableObjectStub",
    "QueueBinding",
    "R2Binding",
    "R2Object",
]
