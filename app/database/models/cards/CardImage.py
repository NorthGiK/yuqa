from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from ..Base import Base


class CardImage(Base):
  __tablename__ = 'card_image'

  id: Mapped[int] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(String(50))
  data: Mapped[bytearray] = mapped_column(LargeBinary)
  mime_type: Mapped[str] = mapped_column(String)
