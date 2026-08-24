from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="教师=用户名，学生=姓名")
    password: str = Field(..., min_length=1, description="密码")
    class_id: Optional[int] = Field(None, description="学生登录时的班级 ID")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="学生姓名（作为用户名）")
    password: str = Field("123456", min_length=6, max_length=50, description="密码，默认 123456")
    class_id: Optional[int] = Field(None, description="班级 ID")


class PasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=50)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    class_id: Optional[int] = None
    class_name: Optional[str] = None
