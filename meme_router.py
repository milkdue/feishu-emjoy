import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from typing import Callable, Dict, List, Optional

import main


@dataclass(frozen=True)
class MemeRoute:
    names: tuple[str, ...]
    arg_count: int
    extension: str
    call: Callable[[List[str]], object]


@dataclass(frozen=True)
class GeneratedMeme:
    command: str
    extension: str
    mime_type: str
    buffer: BytesIO


class MemeCommandError(Exception):
    pass


MIME_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
}


ROUTES = [
    MemeRoute(("psyduck", "可达鸭", "可达鸭举牌"), 2, "gif", lambda a: main.psyduck(a)),
    MemeRoute(("fanatic", "狂爱粉"), 1, "jpg", lambda a: main.fanatic(a[0])),
    MemeRoute(("luxunsay", "鲁迅说"), 1, "png", lambda a: main.luxunsay(a[0])),
    MemeRoute(("ascension", "升天"), 1, "jpg", lambda a: main.ascension(a[0])),
    MemeRoute(("badnews", "悲报"), 1, "png", lambda a: main.badnews(a[0])),
    MemeRoute(("bronya_holdsign", "大鸭鸭举牌"), 1, "jpg", lambda a: main.bronya_holdsign(a[0])),
    MemeRoute(("findchips", "整点薯条"), 4, "jpg", lambda a: main.findchips(a)),
    MemeRoute(("goodnews", "喜报"), 1, "png", lambda a: main.goodnews(a[0])),
    MemeRoute(("high_EQ", "高情商", "高情商低情商"), 2, "jpg", lambda a: main.high_EQ(a[0], a[1])),
    MemeRoute(("holdgrudge", "记仇"), 1, "jpg", lambda a: main.holdgrudge(a[0])),
    MemeRoute(("imprison", "坐牢"), 1, "jpg", lambda a: main.imprison(a[0])),
    MemeRoute(("meteor", "流星"), 1, "jpg", lambda a: main.meteor(a[0])),
    MemeRoute(("murmur", "低语"), 1, "png", lambda a: main.murmur(a[0])),
    MemeRoute(("nokia", "有内鬼"), 1, "jpg", lambda a: main.nokia(a[0])),
    MemeRoute(("not_call_me", "不喊我"), 1, "png", lambda a: main.not_call_me(a[0])),
    MemeRoute(("raisesign", "举牌"), 1, "jpg", lambda a: main.raisesign(a[0])),
    MemeRoute(("run", "黑人快跑", "快跑"), 1, "jpg", lambda a: main.run(a[0])),
    MemeRoute(("scratchoff", "刮刮乐"), 1, "jpg", lambda a: main.scratchoff(a[0])),
    MemeRoute(("scroll", "滚屏"), 1, "gif", lambda a: main.scroll(a[0])),
    MemeRoute(("shutup", "别说了"), 1, "jpg", lambda a: main.shutup(a[0])),
    MemeRoute(("slap", "一巴掌"), 1, "jpg", lambda a: main.slap(a[0])),
    MemeRoute(("slogan", "口号"), 6, "jpg", lambda a: main.slogan(a)),
    MemeRoute(("wakeup", "牛起来了"), 1, "jpg", lambda a: main.wakeup(a[0])),
    MemeRoute(("wish_fail", "许愿失败"), 1, "jpg", lambda a: main.wish_fail(a[0])),
    MemeRoute(("wujing", "吴京"), 2, "jpg", lambda a: main.wujing(a[0], a[1])),
    MemeRoute(("laotou", "老头"), 1, "jpg", lambda a: main.laotou(a[0])),
    MemeRoute(("dezui", "得罪"), 1, "png", lambda a: main.dezui(a[0])),
    MemeRoute(("wangjingze", "王境泽"), 4, "gif", lambda a: main.make_gif_by_type("wangjingze", a)),
    MemeRoute(("weisuoyuwei", "为所欲为"), 9, "gif", lambda a: main.make_gif_by_type("weisuoyuwei", a)),
    MemeRoute(("chanshenzi", "馋身子"), 3, "gif", lambda a: main.make_gif_by_type("chanshenzi", a)),
    MemeRoute(("qiegewala", "窃格瓦拉", "窃贼周先生"), 6, "gif", lambda a: main.make_gif_by_type("qiegewala", a)),
    MemeRoute(("shuifandui", "谁反对"), 4, "gif", lambda a: main.make_gif_by_type("shuifandui", a)),
    MemeRoute(("zengxiaoxian", "曾小贤"), 4, "gif", lambda a: main.make_gif_by_type("zengxiaoxian", a)),
    MemeRoute(("yalidaye", "压力大爷"), 3, "gif", lambda a: main.make_gif_by_type("yalidaye", a)),
    MemeRoute(("nihaosaoa", "你好骚啊"), 3, "gif", lambda a: main.make_gif_by_type("nihaosaoa", a)),
    MemeRoute(("shishilani", "食屎啦你"), 4, "gif", lambda a: main.make_gif_by_type("shishilani", a)),
    MemeRoute(("wunian", "五年"), 4, "gif", lambda a: main.make_gif_by_type("wunian", a)),
]

COMMANDS: Dict[str, MemeRoute] = {
    name.lower(): route for route in ROUTES for name in route.names
}


@contextmanager
def disable_file_output():
    old_value = os.environ.get("MEME_WRITE_FILES")
    os.environ["MEME_WRITE_FILES"] = "0"
    try:
        yield
    finally:
        if old_value is None:
            os.environ.pop("MEME_WRITE_FILES", None)
        else:
            os.environ["MEME_WRITE_FILES"] = old_value


def command_help() -> str:
    names = [route.names[-1] for route in ROUTES]
    return "可用指令：" + "、".join(names)


def strip_bot_mentions(text: str) -> str:
    text = re.sub(r"<at[^>]*>.*?</at>", " ", text)
    text = re.sub(r"@\S+", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return text.strip()


def parse_command(text: str) -> tuple[str, str]:
    text = strip_bot_mentions(text)
    if not text:
        raise MemeCommandError(command_help())
    parts = text.split(maxsplit=1)
    command = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""
    return command, rest


def split_args(text: str, count: int) -> List[str]:
    if count == 0:
        return []
    if count == 1:
        if not text:
            raise MemeCommandError("这个指令需要 1 段文字")
        return [text]

    if "|" in text:
        args = [part.strip() for part in text.split("|") if part.strip()]
    elif "\n" in text:
        args = [part.strip() for part in text.splitlines() if part.strip()]
    else:
        args = [part.strip() for part in re.split(r"\s+", text, maxsplit=count - 1) if part.strip()]

    if len(args) != count:
        raise MemeCommandError(f"这个指令需要 {count} 段文字，建议用 | 分隔")
    return args


def generate_from_text(text: str) -> GeneratedMeme:
    command, rest = parse_command(text)
    route = COMMANDS.get(command)
    if route is None:
        raise MemeCommandError(f"未知指令：{command}\n{command_help()}")

    args = split_args(rest, route.arg_count)
    with disable_file_output():
        result = route.call(args)

    if isinstance(result, str):
        raise MemeCommandError(result)
    if result is None:
        raise MemeCommandError("生成失败，请缩短文字后重试")
    if not isinstance(result, BytesIO):
        raise MemeCommandError("生成失败：函数没有返回图片数据")

    result.seek(0)
    return GeneratedMeme(
        command=route.names[-1],
        extension=route.extension,
        mime_type=MIME_TYPES[route.extension],
        buffer=result,
    )
