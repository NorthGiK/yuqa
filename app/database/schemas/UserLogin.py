from pydantic import BaseModel, EmailStr


class UserLoginSchema(BaseModel):
  username: str
  email:    EmailStr
  password: str
