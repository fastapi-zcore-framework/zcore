from typing import Protocol, runtime_checkable
from fastapi import FastAPI

from zcore.kernel.events import EventDispatcher

@runtime_checkable
class Plugin(Protocol):
    name: str
    version: str
    dependencies: list[str]

    def setup(self, app: FastAPI, dispatcher: EventDispatcher) -> None: ...
    async def on_startup(self) -> None: ...
    async def on_shutdown(self) -> None: ...