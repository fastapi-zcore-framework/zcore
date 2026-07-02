import re
import uuid
import json

from datetime import datetime, date, time
from decimal import Decimal
from typing import Annotated, Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import HttpUrl, PlainSerializer

from zcore.db.setup import get_db


SessionDep = Annotated[AsyncSession, Depends(get_db)]
SafeUrl = Annotated[HttpUrl, PlainSerializer(lambda v: str(v), return_type=str)]

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

def json_dumps(obj: Any, **kwargs: Any) -> str:
    return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)

def json_loads(s: str | bytes, **kwargs: Any) -> Any:
    return json.loads(s, **kwargs)