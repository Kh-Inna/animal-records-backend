import redis
from api.settings import REDIS_HOST,REDIS_PORT
session_storage = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)