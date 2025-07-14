from pydantic import BaseModel, Field


class BattleQeury(BaseModel):
  user_step: int = Field(ge=1, le=2)
  battle_id: int = Field(gt=0)
  hits_count: int
  shield_count: int
  bonus_count: int
