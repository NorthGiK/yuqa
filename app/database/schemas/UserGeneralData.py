from pydantic import BaseModel, Field


class UserGeneralDataSchema(BaseModel):
  name: str = Field('')
  id:   int = Field(0, ge=1)
