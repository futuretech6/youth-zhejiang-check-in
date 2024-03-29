import json
import os
import re
from typing import Dict, Optional

import requests
import toml

verbose = True
# profile = toml.load("profile.toml")
profile = toml.load(
    os.path.dirname(os.path.realpath(__file__)) + "/profile.toml"
)
urls = profile["profile"]["url"]
wxAppId = profile["profile"]["other"]["wxAppId"]
headers = {
    "User-Agent": profile["profile"]["other"]["UA"],
}


def getToken(openId: str) -> Optional[str]:
    response = requests.get(
        url=urls["accessToken"],
        params={"appid": wxAppId, "openid": openId},
        headers={},
    )
    accessTokenMatch = re.compile(
        r"(['\"])(?P<accessToken>([A-Z0-9]|-)+)(\1)"
    ).search(response.text)
    if accessTokenMatch is not None:
        accessToken = accessTokenMatch.groupdict()["accessToken"]
        return accessToken


def getInfo(
    accessToken: str, nid: Optional[str], cardNo: Optional[str]
) -> Optional[Dict[str, str]]:
    infoResponse = requests.get(
        urls["lastInfo"], params={"accessToken": accessToken}, headers=headers
    )
    userInfo = infoResponse.json()["result"]
    if userInfo is None:
        return

    # if can't get nid or cardNo, then get it using config
    _nid = userInfo["nid"]
    if _nid is None:
        _nid = nid
    _cardNo = userInfo["cardNo"]
    if _cardNo is None:
        _cardNo = cardNo

    # still None, config is not set
    if _nid is None or _cardNo is None:
        return None

    courseResponse = requests.get(
        urls["currentCourse"],
        params={"accessToken": accessToken},
        headers=headers,
    )
    classInfo = courseResponse.json()["result"]
    if classInfo is None:
        return
    classId = classInfo["id"]
    faculty = [item["title"] for item in userInfo["nodes"]]

    if verbose:
        print(
            "[*] Course title: " + classInfo["title"],
            "[*] Group info: " + str(faculty) + ", nid: " + _nid,
            "[*] cardNo: " + _cardNo,
            sep="\n",
        )
    return {"course": classId, "nid": _nid, "cardNo": _cardNo}


def getUserScore(accessToken: str) -> str:
    return requests.get(
        url=urls["userInfo"],
        params={"accessToken": accessToken},
        headers=headers,
    ).json()["result"]["score"]


def join(accessToken: str, joinData: Dict[str, str]) -> bool:
    response = requests.post(
        urls["join"],
        params={"accessToken": accessToken},
        data=json.dumps(joinData),
        headers=headers,
    )
    content = response.json()

    if content["status"] == 200:
        print("[*] Check in success")
        return True
    else:
        print("[!] Error:", content["message"])
        return False


def runCheckIn(
    openid: str, nid: Optional[str] = None, cardNo: Optional[str] = None
) -> None:
    accessToken = getToken(openid)
    if accessToken is None:
        print("[!] Error getting accessToken, maybe your openid is invalid")
        exit(-1)

    joinData = getInfo(accessToken, nid=nid, cardNo=cardNo)
    if joinData is None:
        print(
            "[!] Error getting join data, maybe your openid is invalid or given nid/cardNo is invalid"
        )
        exit(-1)

    print("[*] Score before checkin:", getUserScore(accessToken))

    if not join(accessToken, joinData):
        exit(-1)

    print("[*] Score after checkin:", getUserScore(accessToken))


if "OPENID" in os.environ:
    print("[*] Reading openid from environ", end="\n\n")
    verbose = False
    for openid in os.environ["OPENID"].split(","):
        runCheckIn(openid)
else:
    print("[*] Reading openid from config.toml", end="\n\n")

    config = toml.load(
        os.path.dirname(os.path.realpath(__file__)) + "/config.toml"
    )
    for name, user in config["user"].items():
        print("[*] Checking in for openid", name)
        runCheckIn(user["openid"], user["nid"], user["cardNo"])
