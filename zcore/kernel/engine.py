import graphlib
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from zcore.kernel.events import EventDispatcher
from zcore.kernel.plugins import Plugin

class Kernel:
    def __init__(self) -> None:
        self.plugins: dict[str, Plugin] = {}
        self.dispatcher = EventDispatcher()
        self._sorted_plugins: list[Plugin] = []

    def add_plugin(self, plugin: Plugin) -> None:
        self.plugins[plugin.name] = plugin

    def _resolve_dependencies(self) -> list[Plugin]:
        graph: dict[str, list[str]] = {}
        
        for name, plugin in self.plugins.items():
            graph[name] = plugin.dependencies

        sorter = graphlib.TopologicalSorter(graph)
        
        try:
            order = list(sorter.static_order())
        except graphlib.CycleError as e:
            raise RuntimeError(f"Cyclic dependency detected among plugins: {e}")

        resolved: list[Plugin] = []
        for name in order:
            if name in self.plugins:
                resolved.append(self.plugins[name])
            else:
                for p in self.plugins.values():
                    if name in p.dependencies:
                        raise RuntimeError(f"Missing dependency: '{name}' required by plugin '{p.name}'")
        
        return resolved

    def setup(self, app: FastAPI) -> None:
        self._sorted_plugins = self._resolve_dependencies()
        for plugin in self._sorted_plugins:
            plugin.setup(app, self.dispatcher)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        if not self._sorted_plugins:
            self._sorted_plugins = self._resolve_dependencies()

        for plugin in self._sorted_plugins:
            await plugin.on_startup()
            
        try:
            yield
        finally:
            for plugin in reversed(self._sorted_plugins):
                await plugin.on_shutdown()