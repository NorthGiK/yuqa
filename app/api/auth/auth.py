from fastapi import Depends, HTTPException, APIRouter, Response
from authx import AuthX, AuthXConfig

from app.database.schemas.UserLogin import UserLoginSchema # type: ignore
from app.core.dotenv_absolute_path import DOTENVPATH # type: ignore
from app.database.database import AsyncSessionLocal, create_user, get_user, delete_user# type: ignore
from app.database.models.User import User # type: ignore

config = AuthXConfig()

with open(DOTENVPATH, 'r') as f:
  JWT_SECRET_KEY: str = f.read()
config.JWT_SECRET_KEY = JWT_SECRET_KEY
config.JWT_ACCESS_COOKIE_NAME = 'user_is_verify'
config.JWT_TOKEN_LOCATION = ['cookies']

auth: AuthX = AuthX(config=config)

router = APIRouter()

@router.delete('/test__/delete/{user_id}')
async def delete_user_handler(user_id: int):
  await delete_user(user_id=user_id)

@router.post('/signin')
async def signin(creds: UserLoginSchema, response: Response):
#  -> dict[str, str]
  username: str = creds.username
  email: str = creds.email
  password: str = creds.password

  user_is_exist: bool = await get_user(username=username) is not None
  if user_is_exist:
    raise HTTPException(400, 'change username')

  user: User = await create_user(username=username, email=email, password=password)

  token = auth.create_access_token(uid=str(username))

  response.set_cookie(config.JWT_ACCESS_COOKIE_NAME, token)
  response.set_cookie('username', username)
  response.set_cookie('user_id', str(user.id))

  return {'token': token, 'create_user': 'seccessful!' if user else 'problems'}

@router.post('/login')
async def login(creds: UserLoginSchema, response: Response):
  user = await get_user(username=creds.username)
  if user is None:
      raise HTTPException(401, detail={'message': 'invalid credentials'})

  token = auth.create_access_token(uid=str(creds.username))
  auth.set_access_cookies(config.JWT_ACCESS_COOKIE_NAME, token) #type:ignore
  response.set_cookie('id', str(user.id))
  response.set_cookie('username', user.username)

  return {'access_token': token}

@router.get('/protectred', dependencies=[Depends(auth.access_token_required)])
def get_secure():
    return {'super_secret_data': ';D'}
