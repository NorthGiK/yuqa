from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.Base import Base


class UserDeck(Base):
  __tablename__ = 'user_decks'

  id: Mapped[int] = mapped_column(primary_key=True)
  card_1: Mapped[int] = mapped_column(nullable=False, default=1)
  card_2: Mapped[int] = mapped_column(nullable=False, default=2)
  # card_3: Mapped[int] = mapped_column()
  # card_4: Mapped[int] = mapped_column()
  # card_5: Mapped[int] = mapped_column()
