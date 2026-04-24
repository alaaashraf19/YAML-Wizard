import re
from pydantic import BaseModel, Field, field_validator

# class User(BaseModel):
#     username: str
#     email: EmailStr
#     password : str
#     hashed_password: str = ""
#     role: str = "user" #default role is "user", can be overridden to "admin" during signup if needed


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: str = Field(..., min_length=5, max_length=50)
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("email")
    def validate_email(cls, value):
        if "@" not in value:
            raise ValueError("The email should contain an @ symbol.")
        if "." not in value.split("@")[-1]:
            raise ValueError("The email should have a period after the @ symbol.")
        return value

    @field_validator("password")
    def validate_password(cls, value):
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must include at least one lowercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must include at least one number.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must include at least one special character.")
        return value
    
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