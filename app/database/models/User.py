from typing import List
from sqlalchemy import JSON, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import Mapped, mapped_column


from .Base import Base


class User(AsyncAttrs, Base):
  __tablename__ = 'users'

  id:        Mapped[int]       = mapped_column(primary_key=True, index=True)
  username:  Mapped[str]       = mapped_column(String(30))
  email:     Mapped[str]       = mapped_column()
  password:  Mapped[str]       = mapped_column(String(40))
  rating:    Mapped[int]       = mapped_column(default=1)
  inventory: Mapped[List[int]] = mapped_column(JSON, default=list)
