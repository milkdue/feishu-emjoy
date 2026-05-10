from typing import List
from pathlib import Path
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    custom_font_path: Path = Path(__file__).parent / "resources" / "fonts"
    default_fallback_fonts: List[str] = [
        "NotoSansSC-Regular",
        "NotoSerifSC-Regular",
        "FZSJ-QINGCRJ",
        "FZSEJW",
        "FZXS14",
        "Arial",
        "Tahoma",
        "Helvetica Neue",
        "Segoe UI",
        "PingFang SC",
        "Hiragino Sans GB",
        "Microsoft YaHei",
        "Source Han Sans SC",
        "Noto Sans SC",
        "Noto Sans CJK JP",
        "WenQuanYi Micro Hei",
        "Apple Color Emoji",
        "Noto Color Emoji",
        "Segoe UI Emoji",
        "Segoe UI Symbol",
    ]
