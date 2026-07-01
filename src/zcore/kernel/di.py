import inspect
from contextvars import ContextVar
from typing import Any, Callable, Dict, Type, TypeVar, Optional, Set, List, get_type_hints
from fastapi import Depends

T = TypeVar("T")

# Safe context storage for active scoped instances
_current_scope_id: ContextVar[Optional[str]] = ContextVar("scope_id", default=None)
_scoped_instances: ContextVar[Dict[Type[Any], Any]] = ContextVar("scoped_instances", default={})

class DIException(Exception):
    """Base exception for Dependency Injection errors in ZCore."""
    pass

class CircularDependencyError(DIException):
    """Raised when a circular dependency loop is detected during resolution."""
    pass

class IoCContainer:
    def __init__(self) -> None:
        self._singletons: Dict[Type[Any], Any] = {}
        self._scoped_definitions: Dict[Type[Any], Callable[..., Any]] = {}
        self._factories: Dict[Type[Any], Callable[..., Any]] = {}
        
        # High-performance caching for resolved type hints and constructors
        self._constructor_cache: Dict[Type[Any], Optional[Callable[..., Any]]] = {}
        self._dependency_signature_cache: Dict[Type[Any], List[Type[Any]]] = {}

    def register_singleton(self, interface: Type[Any], instance: Any) -> None:
        self._singletons[interface] = instance

    def register_scoped(self, interface: Type[Any], implementation: Type[Any]) -> None:
        self._scoped_definitions[interface] = lambda stack=None: self._auto_wire(implementation, stack)

    def register_transient(self, interface: Type[Any], implementation: Type[Any]) -> None:
        self._factories[interface] = lambda stack=None: self._auto_wire(implementation, stack)

    def resolve(self, interface: Type[T], _stack: Optional[Set[Type[Any]]] = None) -> T:
        if interface in self._singletons:
            return self._singletons[interface]

        scope_id = _current_scope_id.get()
        if scope_id and interface in self._scoped_definitions:
            current_instances = _scoped_instances.get()
            if interface not in current_instances:
                # Resolve with circular dependency detection stack
                resolved_instance = self._scoped_definitions[interface](_stack)
                # Store in ContextVar dict (thread/coroutine safe)
                new_instances = dict(current_instances)
                new_instances[interface] = resolved_instance
                _scoped_instances.set(new_instances)
                return resolved_instance
            return current_instances[interface]

        if interface in self._factories:
            return self._factories[interface](_stack)

        return self._auto_wire(interface, _stack)

    def _auto_wire(self, target_class: Type[T], _stack: Optional[Set[Type[Any]]] = None) -> T:
        if not inspect.isclass(target_class):
            return target_class

        # Initialize recursion verification stack
        _stack = _stack or set()
        if target_class in _stack:
            chain = " -> ".join([c.__name__ for c in _stack]) + f" -> {target_class.__name__}"
            raise CircularDependencyError(f"Circular dependency detected: {chain}")

        _stack.add(target_class)

        try:
            # High-Performance Signature Caching Lookup
            if target_class in self._dependency_signature_cache:
                dependencies = self._dependency_signature_cache[target_class]
                resolved_args = [self.resolve(dep, _stack.copy()) for dep in dependencies]
                return target_class(*resolved_args)

            # Retrieve constructor safely
            if target_class not in self._constructor_cache:
                constructor = getattr(target_class, "__init__", None)
                self._constructor_cache[target_class] = constructor
            else:
                constructor = self._constructor_cache[target_class]

            if constructor is None or constructor is object.__init__:
                self._dependency_signature_cache[target_class] = []
                return target_class()

            # Using typing.get_type_hints to perfectly resolve forward references (even if stringified)
            try:
                type_hints = get_type_hints(constructor)
            except Exception:
                type_hints = {}

            sig = inspect.signature(constructor)
            dependencies = []

            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                # Resolve the annotation type, checking get_type_hints first for forward references
                annotation = type_hints.get(name, param.annotation)
                if annotation is inspect.Parameter.empty:
                    continue
                dependencies.append(annotation)

            # Warm cache for subsequent requests (drastically reduces reflection time to O(1))
            self._dependency_signature_cache[target_class] = dependencies

            resolved_args = [self.resolve(dep, _stack.copy()) for dep in dependencies]
            return target_class(*resolved_args)
            
        finally:
            _stack.remove(target_class)

    def clear_scope(self, scope_id: str) -> None:
        """Explicit clearing hook. In ContextVar-approach, garbage collection handles this, 
        but we maintain compatibility with your middleware."""
        _scoped_instances.set({})

container = IoCContainer()

class Injector:
    def __init__(self, interface: Type[Any]):
        self.interface = interface
    def __call__(self) -> Any:
        return container.resolve(self.interface)

def Inject(interface: Type[T]) -> Any:
    return Depends(Injector(interface))