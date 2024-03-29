import logging
import os
import sys
from enum import Enum

from envparse import env
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.isfile(os.path.join(ROOT_DIR, ".env")):
    env.read_envfile(os.path.join(ROOT_DIR, ".env"))
else:
    logging.warning("No .env file found. Using default values.")

DEBUG = env.bool("DEBUG", default=False)
SITE_HOST = env.str("HOST", default="127.0.0.1")
SITE_PORT = env.int("PORT", default=1337)
MONGO_HOST = env.str("MONGO_HOST", default="mongodb://localhost:27017/")
MONGO_DB_NAME = env.str("MONGO_DB_NAME", default="packet-view")
MONGO_COLLECTION_INTEREST = env.str("MONGO_COLLECTION_INTEREST", default="pv-interest")
MONGO_COLLECTION_DATA = env.str("MONGO_COLLECTION_DATA", default="pv-data")
MONGO_COLLECTION_NACK = env.str("MONGO_COLLECTION_NACK", default="pv-nack")
MONGO_COLLECTION_FRAGMENT = env.str("MONGO_COLLECTION_FRAGMENT", default="pv-fragment")

# DB
DB_CLIENT = AsyncIOMotorClient(MONGO_HOST)
DB = DB_CLIENT[MONGO_DB_NAME]

# LOG
LOGGER = logging.getLogger("ANALYSER")
LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
LOGGER.addHandler(_console_handler)


# NDN
class NDNPACKETTYPES(Enum):
    INTEREST = "I"
    DATA = "D"
    NACK = "N"
