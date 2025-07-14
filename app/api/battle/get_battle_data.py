#TODO:

from typing import Optional
from random import randint

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import AsyncSessionLocal
from app.database.models.User import User
from app.database.models.cards.Card import Card
from app.database.models.battle.BattleSession import BattleSession
from app.database.models.battle.UserDeck import UserDeck


router = APIRouter()


class ActiveBattle:
  async def __init__(
    self,
    user1_id: int,
    user2_id: int,
    db: AsyncSession = AsyncSessionLocal(),
  ) -> None:
    self.first_step: int = randint(1, 2)

    self.what_user_win: Optional[int] = None

    user1: User = await db.get(User, user1_id) #type:ignore
    user2: User = await db.get(User, user2_id) #type:ignore
    deck1: UserDeck = await db.get(UserDeck, user1_id) #type:ignore
    deck2: UserDeck = await db.get(UserDeck, user2_id) #type:ignore

    user1_card1: Card = await db.get(Card, deck1.card_1) #type:ignore
    user1_card2: Card = await db.get(Card, deck1.card_2) #type:ignore
    user2_card1: Card = await db.get(Card, deck2.card_1) #type:ignore 
    user2_card2: Card = await db.get(Card, deck2.card_2) #type:ignore 

    self.user1 = user1
    self.user2 = user2

    self.user1_rating: int = user1.rating #type:ignore
    self.user2_rating: int = user2.rating #type:ignore

    self.user1_card1_hp: int = user1_card1.health#type:ignore
    self.user1_card2_hp: int = user1_card2.health#type:ignore
    self.user2_card1_hp: int = user2_card1.health#type:ignore
    self.user2_card2_hp: int = user2_card2.health#type:ignore

    self.user1_card1_dmg: int = user1_card1.damage#type:ignore
    self.user1_card2_dmg: int = user1_card2.damage #type:ignore
    self.user2_card1_dmg: int = user2_card1.damage#type:ignore
    self.user2_card2_dmg: int = user1_card2.damage#type:ignore

  async def procces_end(self, db: AsyncSession = AsyncSessionLocal()) -> None:
    if any((
      self.user1_card1_hp,
      self.user1_card2_hp,
    )):
      self.what_user_win = 1
      rating1: int = self.user1_rating
      rating2: int = self.user2.rating
      rating1 = rating1 + 1 if rating1 < 10 else 10
      rating2 = rating2 - 1 if rating2 > 1 else 1
      await db.refresh(User, ('rating',), rating1)
    else:
      self.what_user_win = 2

async def process_battle(
  hit: int,
  block: int,
  bonus: int,
  battle: ActiveBattle
  ) -> None:
  battle.
