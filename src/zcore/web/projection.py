"""JSON Response Projection Utility.

This module provides a pruning engine (`ResponseProjector`) designed to remove 
unauthorized fields dynamically from serialized JSON payloads before they are returned 
to the client, ensuring data confidentiality.
"""

from typing import Any, Union
from zcore.utils.helpers import json_dumps, json_loads


class ResponseProjector:
    """Pruning utility removing restricted attributes recursively from dictionary/list trees.

    Walks JSON-serializable models and deletes fields matching configured dot-path 
    restriction definitions.
    """

    @staticmethod
    def project(data: Any, restricted_fields: Union[set[str], frozenset[str]]) -> Any:
        """Prune unauthorized attributes from the provided data payload.

        Serializes and deserializes the data payload to parse standard Pydantic or 
        SQLAlchemy model attributes, resolves data envelopes, and removes key nodes 
        matching restricted dot-paths.

        Args:
            data: The raw data payload (typically a dictionary or sequence of objects).
            restricted_fields: Set of blocked dot-path strings (e.g., "owner.email").

        Returns:
            The sanitized JSON-compatible data payload.
        """
        if not data or not restricted_fields:
            return data
            
        json_data = json_loads(json_dumps(data))
        
        if isinstance(json_data, dict) and "data" in json_data:
            data_field = json_data["data"]
            if isinstance(data_field, list):
                for item in data_field:
                    for path in restricted_fields:
                        parts = path.split(".")
                        if parts[0] == "resource" and len(parts) > 1:
                            parts = parts[1:]
                        ResponseProjector._prune_nested(item, parts)
            elif isinstance(data_field, dict):
                for path in restricted_fields:
                    parts = path.split(".")
                    if parts[0] == "resource" and len(parts) > 1:
                        parts = parts[1:]
                    ResponseProjector._prune_nested(data_field, parts)
        else:
            for path in restricted_fields:
                parts = path.split(".")
                if parts[0] == "resource" and len(parts) > 1:
                    parts = parts[1:]
                ResponseProjector._prune_nested(json_data, parts)
                
        return json_data

    @staticmethod
    def _prune_nested(node: Any, path_parts: list[str]) -> None:
        """Recursively traverse a JSON node and delete target key-value nodes.

        Args:
            node: The current tree node (typically a list or dictionary) to process.
            path_parts: Remaining segments of the restricted dot-path.
        """
        if not path_parts or node is None:
            return
            
        field = path_parts[0]
        
        if len(path_parts) == 1:
            if isinstance(node, dict):
                node.pop(field, None)
            elif isinstance(node, list):
                for item in node:
                    ResponseProjector._prune_nested(item, path_parts)
            return

        if isinstance(node, dict):
            next_node = node.get(field)
            if next_node is not None:
                ResponseProjector._prune_nested(next_node, path_parts[1:])
        elif isinstance(node, list):
            for item in node:
                ResponseProjector._prune_nested(item, path_parts)