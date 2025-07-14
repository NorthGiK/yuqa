from fastapi import APIRouter

from app.api.auth.auth import router as auth_router #type: ignore
from app.api.cards.get_cards import router as cards_router #type: ignore
from app.api.users.static.inventory_handler import router as inventory_router  #type: ignore
from app.api.battle.battle import router as battle_router


router = APIRouter()
router.include_router(auth_router, prefix='/auth')
router.include_router(cards_router, prefix='/cards')
router.include_router(inventory_router)
router.include_router(battle_router, prefix='/battle')
