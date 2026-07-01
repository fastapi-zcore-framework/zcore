from typing import Any, Union
from pydantic import BaseModel

class ResponseProjector:
    @staticmethod
    def project(data: Any, restricted_fields: Union[set[str], frozenset[str]]) -> Any:
        if not data or not restricted_fields:
            return data
            
        for path in restricted_fields:
            parts = path.split(".")
            if parts[0] == "resource" and len(parts) > 1:
                parts = parts[1:]
            ResponseProjector._prune_nested(data, parts)
        return data

    @staticmethod
    def _prune_nested(node: Any, path_parts: list[str]) -> None:
        if not path_parts or node is None:
            return
            
        field = path_parts[0]
        
        if len(path_parts) == 1:
            if isinstance(node, dict):
                node.pop(field, None)
            elif isinstance(node, BaseModel):
                if hasattr(node, field):
                    delattr(node, field)
            elif hasattr(node, "__dict__"):
                if field in node.__dict__:
                    node.__dict__.pop(field, None)
                elif hasattr(node, field):
                    setattr(node, field, None)
            elif isinstance(node, list):
                for item in node:
                    ResponseProjector._prune_nested(item, path_parts)
            return

        # Recursive step for nested navigation
        if isinstance(node, dict):
            next_node = node.get(field)
            if next_node is not None:
                ResponseProjector._prune_nested(next_node, path_parts[1:])
        elif isinstance(node, BaseModel):
            if hasattr(node, field):
                ResponseProjector._prune_nested(getattr(node, field), path_parts[1:])
        elif hasattr(node, "__dict__"):
            if hasattr(node, field):
                ResponseProjector._prune_nested(getattr(node, field), path_parts[1:])
        elif isinstance(node, list):
            for item in node:
                ResponseProjector._prune_nested(item, path_parts)