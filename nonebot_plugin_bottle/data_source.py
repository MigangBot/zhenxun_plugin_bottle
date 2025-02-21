import re
from httpx import AsyncClient
from pathlib import Path
from configs.config import Config
from utils.http_utils import AsyncHttpx
from configs.path_config import IMAGE_PATH
from nonebot.adapters.onebot.v11 import Message, MessageSegment

base_path = IMAGE_PATH / "drift_bottle"

base_path.mkdir(exist_ok=True, parents=True)


def decode_message(text: str, bottle_id: int) -> Message:
    path = base_path / str(bottle_id)
    while g := re.search(r"\[__bottle_image:(\d+)__]", text):
        text = text.replace(
            f"[__bottle_image:{g.group(1)}__]",
            str(MessageSegment.image(path / g.group(1))),
            1,
        )
    return Message(text)


async def encode_message(msg: Message, bottle_id) -> str:
    import os

    if isinstance(msg, str):
        return msg
    text = ""
    path = base_path / str(bottle_id)
    path.mkdir(exist_ok=True)
    count = 0
    for seg in msg:
        if seg.type == "image":
            text += f"[__bottle_image:{count}__]"
            await AsyncHttpx.download_file(seg.data["url"], path / str(count))
            count += 1
        elif seg.type == "at":
            continue
        else:
            text += str(seg)
    if count == 0:
        os.rmdir(path)
    return text


async def text_audit(text: str):
    """
    文本审核(百度智能云)
    `text`: 待审核文本
    """
    if (not Config.get_config(Path(__file__).parent.name, "API_KEY")) or (
        not Config.get_config(Path(__file__).parent.name, "SECRET_KEY")
    ):
        # 未配置key 直接通过审核
        return "pass"
    async with AsyncClient() as client:
        response = await client.post(
            "https://aip.baidubce.com/oauth/2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": Config.get_config(Path(__file__).parent.name, "API_KEY"),
                "client_secret": Config.get_config(
                    Path(__file__).parent.name, "SECRET_KEY"
                ),
            },
        )
        if response:
            access_token = response.json()["access_token"]
        else:
            return "Error"
        response = await client.post(
            "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined",
            data={"text": text, "access_token": access_token},
        )
        if response:
            return response.json()
        else:
            return "Error"
