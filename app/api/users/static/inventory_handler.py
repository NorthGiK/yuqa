from typing import Annotated, List, Optional, Union
from fastapi import APIRouter, HTTPException

from app.database.database import AsyncSessionLocal, add_to_inventory, get_user
from app.database.schemas.AddCardsToUser import AddCardsToUserSchema
from app.database.models.User import User


router = APIRouter()

@router.get('/get_user/{username_or_id}')
async def get_user_handler(username_or_id: int):
  if user := await get_user(db=AsyncSessionLocal(), user_id=username_or_id):
    return user
  raise HTTPException(404, 'user doesn\'t exist')

@router.post('/add_cards')
async def add_cards(creds: AddCardsToUserSchema):
  for card_id in creds.new_cards:
    await add_to_inventory(card_id, creds.user_id)

  return {'successfuly updated': True}

@router.get('/my_inventory')
async def get_my_inventory(username: str):
  user: Optional[User] = await get_user(username)
  if user:
    return {user.id: user.inventory}
  raise HTTPException(404, 'user doesn\'t exist')
