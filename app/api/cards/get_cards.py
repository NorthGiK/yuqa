from typing import Any, Optional, Sequence

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.database.models.cards.Card import Card
from app.database.models.cards import *  # noqa: F403
from app.database.database import AsyncSessionLocal, delete_card
from app.database.schemas.Card import CardSchema


router = APIRouter()

all_cards: tuple[Card, ...] = (
    IndaKarane,  # noqa: F405
    HanozoHakari,  # noqa: F405
)

async def get_card_by_id(card_id: int, db: AsyncSession = AsyncSessionLocal()) -> Optional[Card]:
  card: Optional[Card] = await db.get(Card, card_id)
  return card


@router.get('/card/{card_id}')
async def get_card_by_id_handler(card_id: int):
  card: Optional[Card] = await get_card_by_id(card_id)
  if card is None:
    raise HTTPException(404, 'card doesn\'t exist')
  return card


async def create_card(card: Card) -> Card:
  db = AsyncSessionLocal()
  db.add(card)
  await db.commit()
  await db.refresh(card)
  return card


@router.post('/create_card')
async def create_card_handler(card: CardSchema) -> dict[str, bool]:
  card_ = Card(
    card_name = card.card_name,
    card_rarity = card.card_rarity,
    card_university = card.card_university,
    card_image = card.card_image,
    card_description = card.card_description,
    card_base_health = card.card_base_health,
    card_base_damage = card.card_base_damage,
  )
  await create_card(card_)
  return {'added_card': True}


@router.delete('/delete_card')
async def delete_card_handler(card_id: int, bg_task: BackgroundTasks):
  bg_task.add_task(delete_card, card_id)
  return {'delete': 'success'}

async def create_all_cards():
  for card in all_cards:
    await create_card(card=card)
  return {'ok': True}


@router.get('/all_cards')
async def get_all_cards_handler():
  db: AsyncSession = AsyncSessionLocal()
  query = select(Card)
  raw_result = await db.execute(query)
  cards = raw_result.scalars().all()
  return {'data': cards}
