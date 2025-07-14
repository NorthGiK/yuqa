# from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column#, relationship

from ..Base import Base
#from .CardImage import CardImage
# from .CardAbility import CardAbility
# from .CardBuff import CardBuff


class Card(Base):
  __tablename__ = 'cards'

  card_id:          Mapped[int] = mapped_column(primary_key=True)
  card_name:        Mapped[str] = mapped_column(String(100))
  card_rarity:      Mapped[str] = mapped_column(String())
  card_university:  Mapped[str] = mapped_column(String())
  card_image:       Mapped[str] = mapped_column(String())
  card_description: Mapped[str] = mapped_column(String(1000))
  card_base_health: Mapped[int] = mapped_column()
  card_base_damage: Mapped[int] = mapped_column()
  # card_abilities: Mapped[list['CardAbility']] = 
  # card_buffs: Mapped[List['CardBuff']]
  # card_debuffs: Mapped[List['CardBuff']]
