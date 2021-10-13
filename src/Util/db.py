import pymongo
import urllib.parse
import yaml
from Util.config import config


db_config = config["database"]

username = urllib.parse.quote_plus(db_config["username"])
password = urllib.parse.quote_plus(db_config["password"])
client = pymongo.MongoClient(
    "mongodb://%s:%s@%s:%s/"
    % (username, password, db_config["path"], db_config["port"])
)

db = client["alala_chan"]
key_db = db["key"]
