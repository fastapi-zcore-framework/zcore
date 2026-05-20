from dataclasses import dataclass

from app.core.database import Actions

@dataclass(frozen=True)
class UserActions(Actions):
    RESET_PASSWORD_OTP:str