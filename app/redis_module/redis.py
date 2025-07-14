import redis.asyncio as redis

redis_client = redis.Redis(
  host='localhost',
  port=8080,
  decode_responses=True,
  )

#@router.get("/set/{key}/{value}")
async def set_value(key: str, value: str):
    await redis_client.set(key, value)
    return {"status": "ok"}

#@router.get("/get/{key}")
async def get_value(key: str):
    value = await redis_client.get(key)
    return {"value": value}
