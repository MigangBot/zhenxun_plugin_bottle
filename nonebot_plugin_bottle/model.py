from services.db_context import db
from nonebot.adapters.onebot.v11 import Message
from .data_source import encode_message

try:
    import ujson as json
except:
    import json


class DriftBottle(db.Model):
    __tablename__ = "drift_bottle"

    bottle_id = db.Column(db.BigInteger(), primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    user_name = db.Column(db.Text(), nullable=False)
    group_name = db.Column(db.Text(), nullable=False)
    content = db.Column(db.Text(), nullable=False)
    comment = db.Column(db.Text(), nullable=False)
    report = db.Column(db.Integer(), nullable=False)
    picked = db.Column(db.Integer(), nullable=False)
    is_del = db.Column(db.Boolean(), nullable=False)

    @classmethod
    async def Add(
        cls,
        user_id: int,
        group_id: int,
        user_name: str,
        group_name: str,
        content: Message,
    ):
        """
        说明:
            添加一个新的漂流瓶
        参数:
            :param user_id: 用户id
            :param group_id: 群id
            :param user_name: 用户名
            :param group_name: 群名
            :param text: 漂流瓶内容
        """
        async with db.transaction():
            bottle = await cls.create(
                user_id=user_id,
                group_id=group_id,
                user_name=user_name,
                group_name=group_name,
                content="",
                comment="[]",
                report=0,
                picked=0,
                is_del=False,
            )
            content = await encode_message(content, bottle.bottle_id)
            await bottle.update(content=content).apply()

    @classmethod
    async def Select(cls) -> "drift_bottle":
        """
        说明:
            随机获取一条漂流瓶的数据
        """
        async with db.transaction():
            bottle = (
                await cls.query.where(cls.is_del == False)
                .order_by(db.func.random())
                .with_for_update()
                .gino.first()
            )

            if not bottle:
                return None
            await bottle.update(picked=bottle.picked + 1).apply()
            return bottle

    @classmethod
    async def Clear(cls):
        """
        说明:
            清空表格
        """
        await db.first(db.text("TRUNCATE TABLE drift_bottle RESTART IDENTITY;"))

    @classmethod
    async def Report(cls, index: int, times_max: int = 5):
        """
        说明:
            清空表格
        参数:
            :param index: 漂流瓶编号
            :param times_max: 到达此数值自动处理
        返回
            0 举报失败
            1 举报成功
            2 举报成功并且已经自动处理
            3 已经删除
        """
        async with db.transaction():
            bottle = (
                await cls.query.where((cls.bottle_id == index) & (cls.is_del == False))
                .with_for_update()
                .gino.first()
            )
            if not bottle:
                return 0
            await bottle.update(report=bottle.report + 1).apply()
            if bottle.report + 1 >= times_max:
                if await cls.Remove(index):
                    return 2
                return 0
            return 1

    @classmethod
    async def Check_report(cls, index: int):
        """
        说明:
            返回漂流瓶被举报次数
        参数:
            :param index: 漂流瓶编号
        """
        bottle = (
            await cls.select("report")
            .where((cls.bottle_id == index) & (cls.is_del == False))
            .gino.first()
        )
        if not bottle:
            return -1
        return bottle.report

    @classmethod
    async def Comment(cls, index: int, comment: str):
        """
        说明:
            评论漂流瓶
        参数:
            :param index: 漂流瓶编号
            :param comment: 评论内容
        """
        async with db.transaction():
            bottle = (
                await cls.query.where((cls.bottle_id == index) & (cls.is_del == False))
                .with_for_update()
                .gino.first()
            )
            if not bottle:
                return False
            com_list = json.loads(bottle.comment)
            com_list.append(comment)
            await bottle.update(comment=json.dumps(com_list)).apply()
        return True

    @classmethod
    async def Check_comment(cls, index: int):
        """
        说明:
            查看评论
        参数:
            :param index: 漂流瓶编号
        """
        bottle = (
            await cls.select("comment")
            .where((cls.bottle_id == index) & (cls.is_del == False))
            .gino.first()
        )
        if not bottle:
            return ["漂流瓶不存在"]
        return json.loads(bottle.comment)

    @classmethod
    async def Check_bottle(cls, index: int):
        """
        说明:
            获取漂流瓶信息
        参数:
            :param index: 漂流瓶编号
        """
        return await cls.query.where(
            (cls.bottle_id == index) & (cls.is_del == False)
        ).gino.first()

    @classmethod
    async def Remove(cls, index: int):
        """
        说明:
            直接移除漂流瓶
        参数:
            :param index: 漂流瓶编号
        """
        bottle = await cls.query.where(
            (cls.bottle_id == index) & (cls.is_del == False)
        ).gino.first()
        if not bottle:
            return False
        await bottle.update(is_del=True).apply()
        return True
