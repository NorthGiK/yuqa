from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.database.database import AsyncSessionLocal
from app.database.models.User import User
from app.database.models.battle.Battle import Battle
from app.database.models.battle.BattleSession import BattleSession


async def create_battle_session(user_id: int, user_rating: int, db: AsyncSession = AsyncSessionLocal()) -> None:
  new_session: BattleSession = BattleSession(host_user_id=user_id, rating=user_rating)
  db.add(new_session)
  await db.commit()
  await db.refresh(new_session)


async def join_to_battle(user_id: int, user_rating: int, db: AsyncSession = AsyncSessionLocal()) -> None:
  user = await db.get(User, user_id)
  if user is None:
    raise HTTPException(404, "user not found")
  stmt = select(BattleSession).where(
    (BattleSession.rating - 1 == user.rating) or
    (BattleSession.rating == user.rating)     or
    (BattleSession.rating + 1 == user.rating)
    )
  not_started_sessions_stmt = await db.execute(stmt)
  not_started_sessions = not_started_sessions_stmt.scalar_one_or_none()
  if not_started_sessions is None:
    await create_battle_session(user_id=user_id, user_rating=user_rating)
    return

  host_user_id: int = not_started_sessions.host_user_id
  battle = Battle(
    first_user_id=host_user_id,
    second_user_id=user.id,
  )
  await db.delete(not_started_sessions)
  db.add(battle)
  await db.refresh(battle)
  await db.commit()
