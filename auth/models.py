import uuid
from typing import TYPE_CHECKING
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Boolean, String, func, Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Enum as SQLEnum

from app.core.database import Base

from app.core.auth.actions import UserActions

if TYPE_CHECKING:
    from app.modules.personnel import UserHRProfile
    from app.modules.crm import Contacts
    from app.modules.catalog import CatalogItems
    from app.modules.workflow import Stages 

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id",ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id",ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_stages = Table(
    "role_stages",
    Base.metadata, 
    Column("role_id",ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("stage_id",ForeignKey("stages.id", ondelete="CASCADE"), primary_key=True),
)

class Gender(str, Enum):
    Male = "Male"
    Female = "Female"

class Users(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    ) 
    
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    personnel_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(75))
    gender: Mapped[Gender] = mapped_column(SQLEnum(Gender, name="user_gender", native_enum=True), nullable=False)
    
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    
    last_login: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    contact: Mapped["Contacts | None"] = relationship("Contacts", foreign_keys=[contact_id], lazy="selectin")
    
    job_title_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalogitems.id"), nullable=True)
    job_title: Mapped["CatalogItems | None"] = relationship("CatalogItems", foreign_keys=[job_title_id], lazy="selectin")
    
    roles: Mapped[list["Roles"]] = relationship(secondary=user_roles, lazy="selectin", back_populates="users")
    hr_profile: Mapped["UserHRProfile | None"] = relationship("UserHRProfile", uselist=False, back_populates="user", lazy="selectin")
    
    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @full_name.expression
    def full_name(cls):
        return func.concat(cls.first_name, " ", cls.last_name)
    
    @property
    def all_scopes(self) -> set[str]:
        user_scope = set()
        for role in self.roles:
            for scope in role.scopes:
                user_scope.add(scope)
        return user_scope
    
    @classmethod
    def actions(cls) -> UserActions:
        return UserActions.actions(cls.__tablename__)
    
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
    
    stages: Mapped[list["Stages"] | None] = relationship(secondary=role_stages, back_populates="roles", lazy="selectin")
    users: Mapped[list["Users"]] = relationship(secondary=user_roles, back_populates="roles")