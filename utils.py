from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.auth import Users

SessionDep = Annotated[AsyncSession, Depends(get_db)]