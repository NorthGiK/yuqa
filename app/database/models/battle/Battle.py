from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.Base import Base


class Battle(Base):
  __tablename__ = 'battles'

  id:              Mapped[int]  = mapped_column(primary_key=True)
  first_player_id: Mapped[int]  = mapped_column(nullable=False)
  second_user_id:  Mapped[int]  = mapped_column(nullable=False)
  ended:           Mapped[bool] = mapped_column(default=False)
  