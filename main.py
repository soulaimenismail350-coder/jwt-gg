import json
import os
import random
import time
import uuid

import requests
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google_play_scraper import app as play_store_app
from google.protobuf.json_format import MessageToDict

import MajorLogin_pb2

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GARENA_TOKEN_URL = "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant"
VERSION_URL = "https://version.ggwhitehawk.com/live/ver.php"


class LoginServiceError(Exception):
    pass


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise LoginServiceError(f"Server configuration is missing: {name}")
    return value


def encrypt_api(plain_bytes: bytes) -> bytes:
    key = _required_env("AES_KEY").encode("utf-8")
    iv = _required_env("AES_IV").encode("utf-8")
    if len(key) != 16 or len(iv) != 16:
        raise LoginServiceError("AES_KEY and AES_IV must each be exactly 16 bytes.")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plain_bytes, AES.block_size))


def get_game_config() -> dict:
    try:
        version = play_store_app("com.dts.freefireth", lang="en", country="us")["version"]
        initial = requests.get(
            VERSION_URL,
            params={"lang": "en", "device": "android"},
            timeout=15,
        )
        initial.raise_for_status()
        latest_release = initial.json()["latest_release_version"]

        params = {
            "version": version,
            "lang": "en",
            "device": "android",
            "channel": "android",
            "appstore": "googleplay",
            "region": os.environ.get("GAME_REGION", "BD"),
            "release_version": latest_release,
            "whitelist_version": "1.8.0",
            "whitelist_sp_version": "1.0.0",
            "device_name": os.environ.get("DEVICE_NAME", "OPPO PHM110"),
            "device_CPU": os.environ.get("DEVICE_CPU", "x86-64 SSE3 SSE4.1 SSE4.2 AVX"),
            "device_GPU": os.environ.get("DEVICE_GPU", "Adreno (TM) 750"),
            "device_mem": os.environ.get("DEVICE_MEM", "3004"),
        }
        response = requests.get(VERSION_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        required = ("server_url", "latest_release_version", "remote_version", "vercfg_sign")
        missing = [key for key in required if key not in data]
        if missing:
            raise LoginServiceError(f"Game version service response is missing: {', '.join(missing)}")

        return {
            "server_url": data["server_url"],
            "obb": data["latest_release_version"],
            "remote_version": data["remote_version"],
            "vercfg_sign": data["vercfg_sign"],
        }
    except LoginServiceError:
        raise
    except Exception as exc:
        raise LoginServiceError(f"Could not retrieve game version configuration: {exc}") from exc


def guest_login(uid: str, password: str):
    url = GARENA_TOKEN_URL
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": (
            "GarenaMSDK/4.0.42(A5010 ;Android 9;en;US;"
            "app 2.126.1 2019118045;)"
        ),
    }
    payload = {
        "client_id": 100067,
        "client_secret": _required_env("GARENA_CLIENT_SECRET"),
        "client_type": 2,
        "device_id": "02-" + str(uuid.uuid4()),
        "password": str(password),
        "response_type": "token",
        "uid": int(uid),
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise LoginServiceError(f"Guest authentication request failed: {exc}") from exc

    if data.get("code") != 0:
        # Do not return the submitted password or full upstream response.
        raise LoginServiceError(f"Guest authentication was rejected (code: {data.get('code', 'unknown')}).")

    result = data.get("data") or {}
    access_token = result.get("access_token")
    open_id = result.get("open_id")
    platform = result.get("platform")
    if not all((access_token, open_id, platform)):
        raise LoginServiceError("Guest authentication response did not contain all required fields.")

    return access_token, open_id, platform


def major_login(access_token: str, open_id: str, platform: str, config: dict):
    payload = MajorLogin_pb2.MajorLoginRequest(
        Field3=time.strftime("%Y-%m-%d %H:%M:%S"),
        Field4="free fire",
        Field5=1,
        Field7=config["remote_version"],
        Field8="Android OS 14 / API-34",
        Field9="Handheld",
        Field10="Mobilis",
        Field11="WIFI",
        Field12=1600,
        Field13=900,
        Field14="240",
        Field15="x86-64 SSE3 SSE4.1 SSE4.2 AVX | 2865 | 6",
        Field16=5944,
        Field17="Adreno (TM) 750",
        Field18="OpenGL ES 3.1 v1",
        Field19=f"Google|{uuid.uuid4()}",
        Field20=(
            f"{random.randint(1,223)}.{random.randint(1,255)}."
            f"{random.randint(1,255)}.{random.randint(1,255)}"
        ),
        Field21="pt-br",
        Field22=str(open_id),
        Field23=str(platform),
        Field24="Handheld",
        Field25="samsung SM-N9860",
        Field29=str(access_token),
        Field30=1,
        Field41="Mobilis",
        Field42="WIFI",
        Field57="7428b253defc164018c604a1ebbfebdf",
        Field60=52691,
        Field61=48409,
        Field62=2519,
        Field63=70,
        Field64=23306,
        Field65=25131,
        Field66=50733,
        Field67=52691,
        Field73=3,
        Field74="/data/app/lib/arm64",
        Field76=1,
        Field77="b8e0cd5e295eee42f5860d3c86e483dd|/data/app/base.apk",
        Field78=3,
        Field79=2,
        Field81="64",
        Field83="2019121229",
        Field85=3,
        Field86="OpenGLES2",
        Field87=8191,
        Field88=4,
        Field89=(
            "KqsHT6dXfrd81vpmdClMMxZM3UCc59ys5/2cX5FVcMpI3tlWy8d0r8ZWGSBj+06/"
            "cGbBzY3JULeYT1rb5tBtz7+GCis6kpkGPjl2SSoYhrjsQOvA"
        ),
        Field92=7303,
        Field93="android",
        Field94=(
            "KqsHT6dXfrd81vpmdClMMxZM3UCc59ys5/2cX5FVcMpI3tlWy8d0r8ZWGSBj+06/"
            "cGbBzY3JULeYT1rb5tBtz7+GCis6kpkGPjl2SSoYhrjsQOvA"
        ),
        Field95=111207,
        Field96='{"cur_rate":null,"support_etc2":false}',
        Field97=1,
        Field98=1,
        Field99=str(platform),
        Field100=str(platform),
        Field102=b"",
        Field104=62270,
        Field105=1,
        Field106=(
            "https://dl.gmc.freefiremobile.com/live/ABHotUpdates/|"
            "https://core-gmc.freefiremobile.com/live/ABHotUpdates/|"
            "4a0070ac356973792f002e0b25b96c3b"
        ),
        Field107=config["vercfg_sign"],
    )

    headers = {
        "X-Unity-Version": "2018.4.11f1",
        "ReleaseVersion": config["obb"],
        "Content-Type": "application/x-www-form-urlencoded",
        "X-GA": "v1 1",
        "X-GA-SV": "1790794556",
        "User-Agent": (
            "Dalvik/2.1.0 (Linux; U; Android 7.1.2; "
            "ASUS_Z01QD Build/QKQ1.190825.002)"
        ),
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
    }

    try:
        response = requests.post(
            config["server_url"].rstrip("/") + "/MajorLogin",
            headers=headers,
            data=encrypt_api(payload.SerializeToString()),
            timeout=25,
        )
        response.raise_for_status()
        body = response.content[64:] if len(response.content) > 64 else response.content
        result = MajorLogin_pb2.MajorLoginResponse()
        result.ParseFromString(body)
        return result
    except Exception as exc:
        raise LoginServiceError(f"MajorLogin request failed: {exc}") from exc


def perform_login(uid: str, password: str) -> dict:
    config = get_game_config()
    access_token, open_id, platform = guest_login(uid, password)
    result = major_login(access_token, open_id, platform, config)
    return MessageToDict(result, preserving_proto_field_name=True)
