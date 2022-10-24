import asyncio
import random
from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GROUP,
    Message,
    MessageSegment,
)

from utils.utils import is_number
from .data_source import text_audit, decode_message, base_path
from .model import DriftBottle

try:
    import ujson as json
except:
    import json


__zx_plugin_name__ = "漂流瓶"
__plugin_usage__ = """
usage：
    密封着未知的漂流瓶随着海浪愈行愈远...
    （Bot所在所有群互通）
    指令：
        扔漂流瓶 [文本/图片]
        捡漂流瓶
        评论漂流瓶 [漂流瓶编号] [文本]
        举报漂流瓶 [漂流瓶编号]
        查看漂流瓶 [漂流瓶编号]
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
__plugin_type__ = ("好玩的",)
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

throw = on_command("扔漂流瓶", aliases={"丢瓶子"}, permission=GROUP, priority=13, block=True)
get = on_command("捡漂流瓶", aliases={"捡瓶子"}, priority=100, block=True)
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
    audit = await text_audit(text=message_text)
    if not audit == "pass":
        if audit == "Error":
            await throw.finish("文字审核未通过！原因：调用审核API失败")
        elif audit["conclusion"] == "不合规":
            await throw.finish("文字审核未通过！原因：" + audit["data"][0]["msg"])

    group_name = await bot.get_group_info(group_id=event.group_id)
    group_name = group_name["group_name"]
    user_name = await bot.get_group_member_info(
        group_id=event.group_id, user_id=event.user_id
    )
    user_name = user_name["nickname"]

    await DriftBottle.Add(
        user_id=event.user_id,
        group_id=event.group_id,
        user_name=user_name,
        group_name=group_name,
        content=arg,
    )
    await throw.finish(f"你将一个漂流瓶以时速{random.randint(0, 2 ** 16)}km/h的速度扔出去，谁会捡到这个瓶子呢...")


@get.handle()
async def _(bot: Bot):
    if not (bottle := await DriftBottle.Select()):
        await get.finish("好像一个瓶子也没有呢..要不要扔一个？")
    else:
        try:
            user = await bot.get_group_member_info(
                group_id=bottle.group_id, user_id=bottle.user_id
            )
            user = user.get("card") or user.get("nickname", "未知")
        except:
            user = bottle.user_name
        try:
            group = await bot.get_group_info(group_id=bottle.group_id)
            group = group["group_name"]
        except:
            group = bottle.group_name

        comment_list = json.loads(bottle.comment)
        comment: str = ""
        for i in comment_list[-3:]:
            comment += i + "\n"
        await get.finish(
            f"【漂流瓶No.{bottle.bottle_id}|被捡到{bottle.picked}次】来自【{group}】的 {user} ！\n"
            + decode_message(bottle.content, bottle.bottle_id)
            + (f"\n★评论共 {len(comment_list)} 条★\n{comment.strip()}" if comment else "")
        )


@report.handle()
async def _(arg: Message = CommandArg()):
    index = arg.extract_plain_text().strip()
    if not is_number(index):
        await check_bottle.finish(f"[{index}]不是一个有效的数字编号哦")
    index = int(index)
    result = await DriftBottle.Report(index)
    if result == 0:
        await report.finish("举报失败！请检查编号")
    if result == 1:
        await report.finish(
            f"举报成功！关于此漂流瓶已经有 {await DriftBottle.Check_report(index)} 次举报"
        )
    if result == 2:
        await report.finish("举报成功！已经进行删除该漂流瓶处理！")
    if result == 3:
        await report.finish("该漂流瓶已经被删除！")


@comment.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    mes = str(arg.extract_plain_text()).split(maxsplit=1)
    if not is_number(mes[0]):
        await check_bottle.finish(f"[{mes[0]}]不是一个有效的数字编号哦")
    index = int(mes[0])
    data = await DriftBottle.Check_bottle(index)
    if not data:
        await check_bottle.finish("该漂流瓶不存在或已被删除！")
    user = await bot.get_group_member_info(
        group_id=event.group_id, user_id=event.user_id
    )
    audit = await text_audit(text=mes[1])
    if not audit == "pass":
        if audit == "Error":
            await throw.finish("文字审核未通过！原因：调用审核API失败")
        elif audit["conclusion"] == "不合规":
            await throw.finish("文字审核未通过！原因：" + audit["data"][0]["msg"])
    try:
        commen = f"{user['nickname']}：{mes[1]}"
    except:
        await comment.finish("想评论什么呀，在后边写上吧！")
    if not await DriftBottle.Comment(index, commen):
        await comment.finish("评论失败~漂流瓶不存在")
    try:
        bottle = await DriftBottle.Check_bottle(index)
        await bot.send_msg(
            group_id=bottle.group_id,
            message=Message(
                MessageSegment.at(bottle.user_id) + f"你的{index}号漂流瓶被评论啦！\n{commen}"
            ),
        )
        await asyncio.sleep(2)
    finally:
        await comment.finish("回复成功！")


@check_bottle.handle()
async def _(bot: Bot, arg: Message = CommandArg()):
    index = arg.extract_plain_text().strip()
    if not is_number(index):
        await check_bottle.finish(f"[{index}]不是一个有效的数字编号哦")
    index = int(index)

    if not (bottle := await DriftBottle.Check_bottle(index)):
        await check_bottle.finish("该漂流瓶不存在或已被删除！")
    try:
        user = await bot.get_group_member_info(
            group_id=bottle.group_id, user_id=bottle.user_id
        )
        user = user.get("card") or user.get("nickname", "未知")
    except:
        user = await bottle.user_name
    try:
        group = await bot.get_group_info(group_id=bottle.group_id)
        group = group["group_name"]
    except:
        group = await bottle.group_name
    comment_list = await DriftBottle.Check_comment(index)
    if not comment_list:
        await check_bottle.finish("这个编号的漂流瓶还没有评论哦！")
    comment = ""
    for i in comment_list:
        comment += i + "\n"
    await check_bottle.finish(
        f"来自【{group}】的 {user} 的第{index}号漂流瓶：\n"
        + decode_message(bottle.content, bottle.bottle_id)
        + f"\n★评论共 {len(comment_list)} 条★\n{comment}【这个瓶子被捡到了{bottle.picked}次！】"
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
