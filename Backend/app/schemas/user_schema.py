import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def validate_username(value: str) -> str:
    if len(value) < 3 or len(value) > 20:
        raise ValueError("Username must be between 3 and 20 characters")
    return value.lower()

def validate_email(value: str) -> str:
    if "@" not in value:
        raise ValueError("The email should contain an @ symbol.")
    if "." not in value.split("@")[-1]:
        raise ValueError("The email should have a period after the @ symbol.")
    return value.lower()


def validate_password(value: str) -> str:
    if len(value) < 8 or len(value) > 64:
        raise ValueError("Password must be between 8 and 64 characters")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must include at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must include at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must include at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValueError("Password must include at least one special character.")
    return value


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: str = Field(..., min_length=5, max_length=50)
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return validate_username(v) if v else v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password(v)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=20)
    email: Optional[str] = Field(None, min_length=5, max_length=50)
    current_password: Optional[str] = Field(None, min_length=8, max_length=64)
    new_password: Optional[str] = Field(None, min_length=8, max_length=64)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        return validate_username(v) if v else v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        return validate_email(v) if v else v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: Optional[str]) -> Optional[str]:
        return validate_password(v) if v else v

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True
class UserCreateResponse(BaseModel):
    msg: str
    user_id: str


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8, max_length=64)

class LoginResponse(BaseModel):
    username: str
    role: str

class LoginConfirm(BaseModel):
    username: str
