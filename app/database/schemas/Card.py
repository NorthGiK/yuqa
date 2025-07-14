from pydantic import BaseModel, Field


class CardSchema(BaseModel):
  card_name:        str
  card_rarity:      str
  card_university:  str
  card_image:       str
  card_description: str = Field(max_length=1000)
  card_base_health: int = Field(gt=0)
  card_base_damage: int = Field(gt=0)
  # card_abilities: Mapped[list['CardAbility']] = 
  # card_buffs: Mapped[List['CardBuff']]
  # card_debuffs: Mapped[List['CardBuff']]
