from typing import List

from pydantic import BaseModel


class AddCardsToUserSchema(BaseModel):
  user_id: int
  new_cards: List[int]
