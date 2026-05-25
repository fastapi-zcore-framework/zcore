from typing import Callable, List
from enum import Enum

class DBEvent(Enum):
    BEFORE_FLUSH = "before_flush"
    AFTER_COMMIT = "after_commit"

class HookRegistry:
    def __init__(self):
        self._db_hooks: dict[DBEvent, List[Callable]] = {e: [] for e in DBEvent}

    def subscribe_db(self, event: DBEvent, handler: Callable):
        self._db_hooks[event].append(handler)

    def get_db_handlers(self, event: DBEvent):
        return self._db_hooks[event]

hook_registry = HookRegistry()