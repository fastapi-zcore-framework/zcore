import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import DateTime, Boolean, String, func, Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.personnel import UserHRProfile

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id",ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id",ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

class Users(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    ) 
    
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    personnel_code: Mapped[int] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str|None] = mapped_column(String(100), default=None)
    job_title: Mapped[str|None] = mapped_column(String(50), default=None)
    avatar_url: Mapped[str|None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime|None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # contact_id: uuid.UUID
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    roles: Mapped[list["Roles"]] = relationship(secondary=user_roles, lazy="selectin", back_populates="users")
    hr_profile: Mapped["UserHRProfile | None"] = relationship("UserHRProfile", uselist=False, back_populates="user", lazy="selectin")
    
    @property
    def all_scopes(self) -> set[str]:
        user_scope = set()
        for role in self.roles:
            for scope in role.scopes:
                user_scope.add(scope)
        return user_scope
    
class Roles(Base):
    __tablename__ = "roles"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    ) 
    
    name: Mapped[str] = mapped_column(String(100), unique=True)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=[]) # "order:read", "order:create" , . . .
    ui_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str|None] = mapped_column(String(255), nullable=True)
    
    users: Mapped[list["Users"]] = relationship(secondary=user_roles, back_populates="roles")
    
    