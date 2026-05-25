from typing import Protocol, runtime_checkable

@runtime_checkable
class Plugin(Protocol):
    name: str
    version: str
    dependencies: list[str] = []

    async def on_init(self) -> None: ...
    async def on_startup(self) -> None: ...
    async def on_ready(self) -> None: ...
    async def on_shutdown(self) -> None: ...

class Kernel:
    def __init__(self):
        self.plugins: dict[str, Plugin] = {}

    def add_plugin(self, plugin: Plugin):
        self.plugins[plugin.name] = plugin

    async def startup(self):
        for plugin in self.plugins.values():
            await plugin.on_init()
            await plugin.on_startup()
        
        for plugin in self.plugins.values():
            await plugin.on_ready()

    async def shutdown(self):
        for plugin in reversed(list(self.plugins.values())):
            await plugin.on_shutdown()