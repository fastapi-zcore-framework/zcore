from fastapi import APIRouter, Depends

from app.core.db.setup import Base
from app.core.web.response import ResponseWrapper
from app.core.exception.exceptions import ForbiddenError

from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/system", tags=["System Metadata"])

