from typing import List
from Util.config import config
from Util.db import *
from fastapi import FastAPI
from fastapi.params import Body, Param
import time
import json
import requests
import string, random
from Util.util import dataclass
from fastapi import HTTPException
from pydantic import BaseModel

app = FastAPI()


def generate_key():
    return "".join(
        random.SystemRandom().choice(string.ascii_lowercase + string.digits)
        for _ in range(16)
    )


class AccessToken:
    def __init__(self) -> None:
        self.access_token = ""
        self.access_expire_time = 0

    def check_if_token_expires(self):
        if time.time() > self.access_expire_time:
            r = requests.get(
                f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={config['wework']['corpid']}&corpsecret={config['wework']['corpsecret']}"
            )
            ret = r.json()
            self.access_token = ret["access_token"]
            self.access_expire_time = int(time.time()) + ret["expires_in"] - 10

    def get(self):
        self.check_if_token_expires()
        return self.access_token


access_token = AccessToken()


def update_user_key():
    depart_r = requests.get(
        f"https://qyapi.weixin.qq.com/cgi-bin/department/list?access_token={access_token.get()}"
    )
    depart_list = depart_r.json()["department"]
    for department in depart_list:
        user_r = requests.get(
            f"https://qyapi.weixin.qq.com/cgi-bin/user/simplelist?access_token={access_token.get()}&department_id={department['id']}"
        )
        user_list = user_r.json()["userlist"]
        for user in user_list:
            uid = user["userid"]
            if key_db.find({"uid": uid}, {"_id": 0}).count() == 0:
                key_db.insert({"uid": uid, "key": generate_key()})


@dataclass
class UserKey(BaseModel):
    key: str
    uid: str


@app.get(
    "/key_list",
    response_model=List[UserKey],
    name="获取发送 KEY 列表",
)
async def key_list(secret: str = Param(...)):
    if secret != config["alala"]["secret"]:
        raise HTTPException(status_code=403)
    retval = []
    update_user_key()
    for key in key_db.find():
        retval.append(UserKey(key=key["key"], uid=key["uid"]))
    return retval


@app.post("/send_raw")
async def send_raw(key: str = Param(...), content: str = Body(...)):
    uid = key_db.find_one({"key": key})
    if uid is None:
        raise HTTPException(status_code=403, detail="Error Key.")
    request = {"touser": uid["uid"], "agentid": config["wework"]["agentid"], "safe": 0}
    content = json.loads(content, strict=False)
    request = {**content, **request}
    send_r = requests.post(
        f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token.get()}",
        json=request,
    )
    return send_r.content


@dataclass
class SendReq(BaseModel):
    content: str


@app.post("/send")
async def send(key: str = Param(...), req: SendReq = Body(...)):
    uid = key_db.find_one({"key": key})
    if uid is None:
        raise HTTPException(status_code=403, detail="Error Key.")
    request = {
        "touser": uid["uid"],
        "agentid": config["wework"]["agentid"],
        "safe": 0,
        "msgtype": "text",
        "text": {"content": req.content},
    }
    send_r = requests.post(
        f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token.get()}",
        json=request,
    )
    return send_r.content
