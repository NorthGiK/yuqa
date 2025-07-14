from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.battle.get_battle_data import ActiveBattle, process_battle
from app.api.battle.start_battle import join_to_battle
from app.database.database import AsyncSessionLocal
from app.database.models import User
from app.database.models.battle.BattleSession import BattleSession
from app.database.schemas.BattleQuery import BattleQeury


router = APIRouter()

@router.post('/start_battle__')
async def start_battle_handler(user_id: int, user_rating: int):
  await join_to_battle(user_id=user_id, user_rating=user_rating)
  return {'ok': True}

#TODO:
#@router.post('/battle_processing__/{')
async def process_data_handler(user1_id: int, user2_id: int, battle_query: BattleQeury):
  battle: ActiveBattle = ActiveBattle(
    user1_id = user1_id,
    user2_id = user2_id,
  )

  while ActiveBattle.what_user_win is None:
    process_battle(
      battle_query
    )
