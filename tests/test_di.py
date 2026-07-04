import asyncio
import uuid
from contextlib import contextmanager
from typing import Any, Generator, Type
import pytest

from zcore.kernel.di import (
    container,
    _current_scope_id,
    _scoped_instances,
    CircularDependencyError,
)

class IService:
    pass

class ServiceImpl(IService):
    def __init__(self) -> None:
        self.id = uuid.uuid4()

class AnotherServiceImpl(IService):
    def __init__(self) -> None:
        self.id = uuid.uuid4()

class ForwardA:
    def __init__(self, b: "ForwardB") -> None:
        self.b = b

class ForwardB:
    def __init__(self) -> None:
        self.id = uuid.uuid4()

class CircA:
    def __init__(self, b: "CircB") -> None:
        self.b = b

class CircB:
    def __init__(self, a: "CircA") -> None:
        self.a = a

@contextmanager
def di_scope(scope_id: str) -> Generator[None, None, None]:
    token_id = _current_scope_id.set(scope_id)
    token_instances = _scoped_instances.set({})
    try:
        yield
    finally:
        _current_scope_id.reset(token_id)
        _scoped_instances.reset(token_instances)

@pytest.mark.parametrize(
    "interface, implementation",
    [
        (IService, ServiceImpl),
        (ForwardB, ForwardB),
    ]
)
def test_resolve_singleton(interface: Type[Any], implementation: Type[Any]) -> None:
    instance = implementation()
    container.register_singleton(interface, instance)
    
    res1 = container.resolve(interface)
    res2 = container.resolve(interface)
    
    assert res1 is instance
    assert res2 is instance
    assert res1.id == res2.id

@pytest.mark.parametrize(
    "interface, implementation, scope_1, scope_2",
    [
        (IService, ServiceImpl, "scope-a", "scope-b"),
        (ForwardB, ForwardB, "scope-x", "scope-y"),
    ]
)
def test_resolve_scoped(
    interface: Type[Any],
    implementation: Type[Any],
    scope_1: str,
    scope_2: str
) -> None:
    container.register_scoped(interface, implementation)
    
    with di_scope(scope_1):
        res1 = container.resolve(interface)
        res2 = container.resolve(interface)
        assert res1 is res2
        
    with di_scope(scope_2):
        res3 = container.resolve(interface)
        assert res3 is not res1

@pytest.mark.parametrize(
    "interface, implementation",
    [
        (IService, ServiceImpl),
        (ForwardB, ForwardB),
    ]
)
def test_resolve_transient(interface: Type[Any], implementation: Type[Any]) -> None:
    container.register_transient(interface, implementation)
    
    res1 = container.resolve(interface)
    res2 = container.resolve(interface)
    
    assert res1 is not res2
    assert isinstance(res1, implementation)
    assert isinstance(res2, implementation)

@pytest.mark.parametrize(
    "registrations",
    [
        {"A": CircA, "B": CircB},
    ]
)
def test_circular_dependency(registrations: dict[str, Type[Any]]) -> None:
    container.register_transient(CircA, registrations["A"])
    container.register_transient(CircB, registrations["B"])
    
    with pytest.raises(CircularDependencyError) as exc_info:
        container.resolve(CircA)
        
    assert "Circular dependency detected" in str(exc_info.value)
    assert "CircA" in str(exc_info.value)
    assert "CircB" in str(exc_info.value)

@pytest.mark.parametrize(
    "target, dep",
    [
        (ForwardA, ForwardB),
    ]
)
def test_forward_reference_resolution(target: Type[Any], dep: Type[Any]) -> None:
    container.register_transient(dep, dep)
    container.register_transient(target, target)
    
    resolved = container.resolve(target)
    assert isinstance(resolved, target)
    assert isinstance(resolved.b, dep)

@pytest.mark.anyio
@pytest.mark.parametrize("num_tasks", [10, 50])
async def test_di_concurrency_isolation(num_tasks: int) -> None:
    container.register_scoped(IService, ServiceImpl)
    
    async def run_task(task_id: str) -> tuple[str, Any]:
        with di_scope(task_id):
            res1 = container.resolve(IService)
            await asyncio.sleep(0.001)
            res2 = container.resolve(IService)
            assert res1 is res2
            return task_id, res1
            
    tasks = [run_task(f"scope-{uuid.uuid4()}") for _ in range(num_tasks)]
    results = await asyncio.gather(*tasks)
    
    seen_ids = set()
    for task_id, instance in results:
        assert instance.id not in seen_ids
        seen_ids.add(instance.id)
    assert len(seen_ids) == num_tasks