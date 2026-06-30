import inspect
from contextvars import ContextVar
from typing import Any, Callable, Dict, Type, TypeVar, Optional
from fastapi import Depends

T = TypeVar("T")
_current_scope_id: ContextVar[Optional[str]] = ContextVar("scope_id", default=None)

class IoCContainer:
    def __init__(self) -> None:
        self._singletons: Dict[Type[Any], Any] = {}
        self._scoped_definitions: Dict[Type[Any], Callable[..., Any]] = {}
        self._scoped_instances: Dict[str, Dict[Type[Any], Any]] = {}
        self._factories: Dict[Type[Any], Callable[..., Any]] = {}

    def register_singleton(self, interface: Type[Any], instance: Any) -> None:
        self._singletons[interface] = instance

    def register_scoped(self, interface: Type[Any], implementation: Type[Any]) -> None:
        self._scoped_definitions[interface] = lambda: self._auto_wire(implementation)

    def register_transient(self, interface: Type[Any], implementation: Type[Any]) -> None:
        self._factories[interface] = lambda: self._auto_wire(implementation)

    def resolve(self, interface: Type[T]) -> T:
        if interface in self._singletons:
            return self._singletons[interface]

        scope_id = _current_scope_id.get()
        if scope_id and interface in self._scoped_definitions:
            if scope_id not in self._scoped_instances:
                self._scoped_instances[scope_id] = {}
            if interface not in self._scoped_instances[scope_id]:
                self._scoped_instances[scope_id][interface] = self._scoped_definitions[interface]()
            return self._scoped_instances[scope_id][interface]

        if interface in self._factories:
            return self._factories[interface]()

        return self._auto_wire(interface)

    def _auto_wire(self, target_class: Type[T]) -> T:
        if not inspect.isclass(target_class):
            return target_class
        constructor = getattr(target_class, "__init__", None)
        if constructor is None or constructor is object.__init__:
            return target_class()
        sig = inspect.signature(constructor)
        resolved = []
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            resolved.append(self.resolve(param.annotation))
        return target_class(*resolved)

    def clear_scope(self, scope_id: str) -> None:
        if scope_id in self._scoped_instances:
            del self._scoped_instances[scope_id]

container = IoCContainer()

class Injector:
    def __init__(self, interface: Type[Any]):
        self.interface = interface
    def __call__(self) -> Any:
        return container.resolve(self.interface)

def Inject(interface: Type[T]) -> Any:
    return Depends(Injector(interface))