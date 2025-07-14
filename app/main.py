from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import run

from app.api.auth.auth import auth
from app.api.cards.get_cards import create_all_cards
from app.routers.router import router
from app.database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await create_all_cards()
    yield

app = FastAPI(title='pineApple', lifespan=lifespan)
auth.handle_errors(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=router)

def main() -> None:
    run(app=app, reload=True)

if __name__ == '__main__':
    main()
