import asyncio
import random
from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    GroupMessageEvent,
    GROUP,
    Message,
    MessageSegment,
)

from utils.utils import is_number
from models.group_info import GroupInfo
from models.group_member_info import GroupInfoUser
from .data_source import text_audit, decode_message, base_path
from .model import DriftBottle

try:
    import ujson as json
except:
    import json


__zx_plugin_name__ = "漂流瓶"
__plugin_usage__ = """
usage：
    漂流瓶......
    （Bot所在所有群互通）
    指令：
        扔漂流瓶 [文本/图片]
        捡漂流瓶
        评论漂流瓶 [漂流瓶编号] [文本]
        举报漂流瓶 [漂流瓶编号]
        查看漂流瓶 [漂流瓶编号] (说明：仅被评论的漂流瓶才可以进行查看)
""".strip()
__plugin_des__ = "自动推送微博（可推送范围由维护者设定）"
__plugin_version__ = 0.1
__plugin_cmd__ = [
    "扔漂流瓶 [文本/图片]",
    "捡漂流瓶",
    "评论漂流瓶 [漂流瓶编号] [文本]",
    "举报漂流瓶 [漂流瓶编号]",
    "查看漂流瓶 [漂流瓶编号]",
    "清空漂流瓶 [_superuser]",
    "删除漂流瓶 [漂流瓶编号] [_superuser]",
]
__plugin_author__ = "Todysheep"
__plugin_settings__ = {"cmd": []}
__plugin_type__ = ("其他",)
__plugin_configs__ = {
    "api_key": {
        "value": None,
        "help": "百度智能云文字审核API：API_KEY",
        "default_value": None,
    },
    "secret_key": {
        "value": None,
        "help": "百度智能云文字审核API：SECRET_KEY",
        "default_value": None,
    },
}

throw = on_command("扔漂流瓶", aliases={"丢漂流瓶"}, permission=GROUP, priority=13, block=True)
get = on_command("捡漂流瓶", priority=100, block=True)
report = on_command("举报漂流瓶", priority=100, block=True)
comment = on_command("评论漂流瓶", priority=100, block=True)
check_bottle = on_command("查看漂流瓶", priority=100, block=True)

clear = on_command("清空漂流瓶", permission=SUPERUSER, priority=100, block=True)
remove = on_command("删除漂流瓶", permission=SUPERUSER, priority=100, block=True)


@throw.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    message_text = arg.extract_plain_text()
    if not arg:
        await throw.finish("想说些什么话呢？在后边写上吧！")
    if (t_l := len(message_text)) > 1000:
        await throw.finish(f"字数太多（>1000）写不下了，稍微删点吧，当前{t_l}")
    audit = await text_audit(text=message_text)
    if not audit == "pass":
        if audit == "Error":
            await throw.finish("文字审核未通过！原因：调用审核API失败")
        elif audit["conclusion"] == "不合规":
            await throw.finish("文字审核未通过！原因：" + audit["data"][0]["msg"])

    if group_name := await GroupInfo.get_group_info(event.group_id):
        group_name = group_name.group_name
    else:
        group_name = await bot.get_group_info(group_id=event.group_id)
        group_name = group_name["group_name"]

    if user_name := await GroupInfoUser.get_member_info(event.user_id, event.group_id):
        user_name = user_name.user_name
    else:
        user_name = await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.user_id
        )
        user_name = user_name.get("card") or user_name.get("nickname", "未知")

    await DriftBottle.Add(
        user_id=event.user_id,
        group_id=event.group_id,
        user_name=user_name,
        group_name=group_name,
        content=arg,
    )
    await throw.finish(f"你将一个漂流瓶以时速{random.randint(0, 2 ** 16)}km/h的速度扔出去，谁会捡到这个瓶子呢...")


@get.handle()
async def _():
    if not (bottle := await DriftBottle.Select()):
        await get.finish("好像一个瓶子也没有呢...要不要扔一个？")
    else:
        try:
            user_name = (
                await GroupInfoUser.get_member_info(bottle.user_id, bottle.group_id)
            ).user_name
        except AttributeError:
            user_name = bottle.user_name
        try:
            group_name = (await GroupInfo.get_group_info(bottle.group_id)).group_name
        except AttributeError:
            group_name = bottle.group_name

        comment_list = json.loads(bottle.comment)
        comment_list.reverse()
        comment = "\n".join(comment_list[:3])
        await get.finish(
            f"【漂流瓶No.{bottle.bottle_id}|被捡到{bottle.picked}次】来自【{group_name}】的 {user_name} ！\n"
            + decode_message(bottle.content, bottle.bottle_id)
            + (f"\n★评论共 {len(comment_list)} 条★\n{comment}")
        )


@report.handle()
async def _(arg: Message = CommandArg()):
    index = arg.extract_plain_text().strip()
    if not is_number(index):
        await check_bottle.finish(f"[{index}]不是一个有效的数字编号哦")
    index = int(index)
    result = await DriftBottle.Report(index)
    if result == 0:
        await report.finish("举报失败！该漂流瓶不存在或已沉没~")
    if result == 1:
        await report.finish(
            f"举报成功！关于此漂流瓶已经有 {await DriftBottle.Check_report(index)} 次举报"
        )
    if result == 2:
        await report.finish("举报成功！已自动将该漂流瓶流放于海底~")


@comment.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    mes = (arg.extract_plain_text()).split(maxsplit=1)
    if not is_number(mes[0]):
        await check_bottle.finish(f"[{mes[0]}]不是一个有效的数字编号哦")
    index = int(mes[0])
    if not (bottle := await DriftBottle.Check_bottle(index)):
        await check_bottle.finish("该漂流瓶不存在或已沉没~")
    if len(mes) < 2:
        await check_bottle.finish("想评论什么呀，在后边写上吧！")
    if (t_l := len(mes[1])) > 200:
        await check_bottle.finish(f"请将字数控制在200字以下哦，当前{t_l}字")
    audit = await text_audit(text=mes[1])
    if audit != "pass":
        if audit == "Error":
            await throw.finish("文字审核未通过！原因：调用审核API失败")
        elif audit["conclusion"] == "不合规":
            await throw.finish("文字审核未通过！原因：" + audit["data"][0]["msg"])
    try:
        user_name = (
            await GroupInfoUser.get_member_info(bottle.user_id, bottle.group_id)
        ).user_name
    except AttributeError:
        user_name = await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.user_id
        )
        user_name = user_name.get("card") or user_name.get("nickname", "未知")
    commen = f"{user_name}：{mes[1]}"
    if not await DriftBottle.Comment(index, commen):
        await comment.finish("评论失败~漂流瓶不存在")
    try:
        await bot.send_msg(
            group_id=bottle.group_id,
            message=Message(
                MessageSegment.at(bottle.user_id) + f"你的{index}号漂流瓶被评论啦！\n{commen}"
            ),
        )
    finally:
        await asyncio.sleep(1)
        await comment.finish("评论成功！")


@check_bottle.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    index = arg.extract_plain_text().strip()
    if not is_number(index):
        await check_bottle.finish(f"[{index}]不是一个有效的数字编号哦")
    index = int(index)

    if not (bottle := await DriftBottle.Check_bottle(index)):
        await check_bottle.finish("该漂流瓶不存在或已沉没~")
    try:
        user_name = (
            await GroupInfoUser.get_member_info(bottle.user_id, bottle.group_id)
        ).user_name
    except AttributeError:
        user_name = bottle.user_name
    try:
        group_name = (await GroupInfo.get_group_info(bottle.group_id)).group_name
    except AttributeError:
        group_name = bottle.group_name
    if (
        not (comment_list := await DriftBottle.Check_comment(index))
        and str(event.user_id) not in bot.config.superusers
    ):
        await check_bottle.finish("这个编号的漂流瓶还没有评论哦！")
    comment_list.reverse()
    comment = "\n".join(comment_list)
    await check_bottle.finish(
        f"来自【{group_name}】的 {user_name} 的第{index}号漂流瓶【这个瓶子被捡到了{bottle.picked}次！】：\n"
        + decode_message(bottle.content, bottle.bottle_id)
        + f"\n★评论共 {len(comment_list)} 条★\n{comment}"
    )


@clear.handle()
async def _():
    import shutil

    await DriftBottle.Clear()
    shutil.rmtree(base_path)
    base_path.mkdir()
    await clear.finish("所有漂流瓶清空成功！")


@remove.handle()
async def _(arg: Message = CommandArg()):
    index = arg.extract_plain_text().strip()
    if not is_number(index):
        await remove.finish(f"[{index}]不是一个有效的数字编号哦")
    if await DriftBottle.Remove(int(index)):
        await remove.finish(f"成功删除 {index} 号漂流瓶！")
    else:
        await remove.finish("删除失败！请检查编号")
