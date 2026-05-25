import re

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import HttpUrl, PlainSerializer

from app.core.db.setup import get_db


SessionDep = Annotated[AsyncSession, Depends(get_db)]

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text

SafeUrl = Annotated[HttpUrl, PlainSerializer(lambda v: str(v), return_type=str)]