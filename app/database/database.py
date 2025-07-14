from typing import Optional
import json

from pydantic import EmailStr
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models.cards.Card import Card
from .models.Base import Base
from .models.User import User


engine = create_async_engine(
  'sqlite+aiosqlite:///./db.sqlite',
  echo=True,
  json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.drop_all)
    await conn.run_sync(Base.metadata.create_all)
  

async def create_card(card: Card, db: AsyncSession = AsyncSessionLocal()):
  db.add(card)
  await db.commit()
  await db.refresh(card)

async def create_user(
  username: str,
  email: EmailStr,
  password: str,
) -> User:
  db: AsyncSession = AsyncSessionLocal()
  user = User(
    username=username,
    email=email,
    password=password,
    inventory='1,2',
  )

  db.add(user)
  await db.commit()
  await db.refresh(user)

  return user

async def get_user(
  username: str,
) -> Optional[User]:
  db: AsyncSession = AsyncSessionLocal()

  stmt = select(User).where(User.username == username)  
  result = await db.execute(stmt)
  user = result.scalar_one_or_none()
  return user

async def get_user_inventory(
  username: str
  ):
  user = await get_user(username)
  if user is None:
    raise HTTPException(404, 'user doesn\'t exist')

  return user.inventory

async def add_to_inventory(
    new_card: int,
    username: str,
) -> Optional[User]:
  db: AsyncSession = AsyncSessionLocal()
  user = await get_user(username=username)
  if user is None:
    return None
  
  user.inventory += f',{new_card}' #type:ignore
  await db.commit()
  await db.refresh(user)

  return user


async def delete_user(user_id: int) -> None:
  db: AsyncSession = AsyncSessionLocal()
  stmt_delete = delete(User).where(User.id == user_id)
  await db.execute(stmt_delete)
  await db.commit()


async def delete_card(card_id: int) -> None:
  db: AsyncSession = AsyncSessionLocal()
  stmt_delete = delete(Card).where(Card.card_id == card_id)
  await db.execute(stmt_delete)
  await db.commit()
