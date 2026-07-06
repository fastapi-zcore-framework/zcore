import asyncio
import uuid
from typing import Any, Generator
from fastapi import FastAPI
import pytest

from zcore.kernel.engine import Kernel

class TrackedPlugin:
    def __init__(self, name: str, dependencies: list[str], log: list[str]) -> None:
        self.name = name
        self.version = f"1.0.{uuid.uuid4().hex[:4]}"
        self.dependencies = dependencies
        self.log = log

    def setup(self, app: FastAPI) -> None:
        self.log.append(f"{self.name}:setup")

    async def before_startup(self) -> None:
        self.log.append(f"{self.name}:before_startup")

    async def on_startup(self) -> None:
        self.log.append(f"{self.name}:on_startup")

    async def after_startup(self) -> None:
        self.log.append(f"{self.name}:after_startup")

    async def on_shutdown(self) -> None:
        self.log.append(f"{self.name}:on_shutdown")

@pytest.mark.parametrize(
    "graph",
    [
        {"C": ["B"], "B": ["A"], "A": []},
        {"D": ["B", "C"], "C": ["A"], "B": ["A"], "A": []},
    ]
)
def test_topological_sort_order(graph: dict[str, list[str]]) -> None:
    kernel = Kernel()
    log: list[str] = []
    for name, deps in graph.items():
        kernel.add_plugin(TrackedPlugin(name, deps, log))
    
    resolved = kernel._resolve_dependencies()
    resolved_names = [p.name for p in resolved]
    
    for name, deps in graph.items():
        name_idx = resolved_names.index(name)
        for dep in deps:
            assert resolved_names.index(dep) < name_idx

@pytest.mark.parametrize(
    "graph",
    [
        {"A": ["B"], "B": ["A"]},
        {"A": ["B"], "B": ["C"], "C": ["A"]},
    ]
)
def test_cycle_dependency_error(graph: dict[str, list[str]]) -> None:
    kernel = Kernel()
    log: list[str] = []
    for name, deps in graph.items():
        kernel.add_plugin(TrackedPlugin(name, deps, log))
    
    with pytest.raises(RuntimeError) as exc_info:
        kernel._resolve_dependencies()
    assert "Cyclic dependency" in str(exc_info.value)

@pytest.mark.parametrize(
    "graph",
    [
        {"A": ["B"]},
        {"A": ["B"], "B": ["C"]},
    ]
)
def test_missing_dependency_error(graph: dict[str, list[str]]) -> None:
    kernel = Kernel()
    log: list[str] = []
    for name, deps in graph.items():
        kernel.add_plugin(TrackedPlugin(name, deps, log))
    
    with pytest.raises(RuntimeError) as exc_info:
        kernel._resolve_dependencies()
    assert "Missing dependency" in str(exc_info.value)

@pytest.mark.anyio
@pytest.mark.parametrize(
    "graph",
    [
        {"C": ["B"], "B": ["A"], "A": []},
    ]
)
async def test_plugin_lifespan_lifecycle(graph: dict[str, list[str]]) -> None:
    kernel = Kernel()
    log: list[str] = []
    app = FastAPI()
    
    for name, deps in graph.items():
        kernel.add_plugin(TrackedPlugin(name, deps, log))
        
    kernel.setup(app)
    
    assert log == ["A:setup", "B:setup", "C:setup"]
    log.clear()
    
    async with kernel.lifespan(app):
        assert log == [
            "A:before_startup", "B:before_startup", "C:before_startup",
            "A:on_startup", "B:on_startup", "C:on_startup",
            "A:after_startup", "B:after_startup", "C:after_startup",
        ]
        log.clear()
        
    assert log == [
        "C:on_shutdown", "B:on_shutdown", "A:on_shutdown"
    ]