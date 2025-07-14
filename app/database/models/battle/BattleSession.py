from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.Base import Base


class BattleSession(Base):
  __tablename__ = 'battle_sessions'

  id: Mapped[int] = mapped_column(primary_key=True)
  host_user_id: Mapped[int] = mapped_column()
  rating: Mapped[int] = mapped_column()
  # second_player: Mapped[int] = mapped_column(default=0)
  # started: Mapped[bool] = mapped_column(default=False)
  # ended: Mapped[bool] = mapped_column(default=False)
