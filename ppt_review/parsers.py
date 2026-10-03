# -*- coding: utf-8 -*-
"""文件解析模块：把课件读成统一的「页面文本」结构。

这一层只负责"把文字读出来"，不做任何重要性判断。
这样设计的好处是：以后要支持 Word、OneNote 等新格式，
只需要在这里加一个 parse_xxx 函数，其它模块完全不用改。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pptx import Presentation
from pypdf import PdfReader

# 目前支持的课件格式
SUPPORTED_SUFFIXES = {".pptx", ".pdf"}


@dataclass
class Page:
    """课件里的一页：PPT 的一页幻灯片，或 PDF 的一页纸。"""

    index: int  # 页码，从 1 开始
    title: str = ""  # 推测出来的标题
    blocks: list[str] = field(default_factory=list)  # 这一页的正文文本块

    @property
    def is_empty(self) -> bool:
        """这一页是不是没有任何文字。"""
        return not self.blocks


def _squeeze(text: str) -> str:
    """把文本里连续的空白（空格、换行、制表符）压成一个空格。"""
    return " ".join(text.split())


def parse_pptx(path: Path) -> list[Page]:
    """解析 .pptx 文件：逐页取出文本框里的文字。

    注意：只在有文本框的形状里取字，图片、SmartArt 里的字取不到。
    课件里的公式如果是图片形式，这里也会读不到——
    这是刻意的取舍，因为引入 OCR 会显著增加依赖体积。
    """
    prs = Presentation(str(path))
    pages: list[Page] = []

    for page_no, slide in enumerate(prs.slides, start=1):
        blocks: list[str] = []

        # 遍历这一页的所有形状，收集文本框里的每一段
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                line = _squeeze(paragraph.text)
                if line:
                    blocks.append(line)

        # 标题猜测：优先用版式自带的标题占位符
        title = ""
        title_shape = slide.shapes.title
        if title_shape is not None and title_shape.has_text_frame:
            title = _squeeze(title_shape.text_frame.text)

        # 取不到标题占位符时，退而用第一个文本块当标题
        if not title and blocks:
            title = blocks[0]

        # 标题如果就是从正文里拿的，就别在正文里重复一遍
        if blocks and blocks[0] == title:
            blocks = blocks[1:]

        pages.append(Page(index=page_no, title=title, blocks=blocks))

    return pages


def parse_pdf(path: Path) -> list[Page]:
    """解析 .pdf 文件：用 pypdf 按页抽取文字。

    扫描版 PDF（本质是一堆图片）抽不出文字，这里会得到空页。
    遇到这种情况工具会如实提示，而不是假装读到了内容。
    """
    reader = PdfReader(str(path))
    pages: list[Page] = []

    for page_no, pdf_page in enumerate(reader.pages, start=1):
        raw_text = pdf_page.extract_text() or ""
        lines = [_squeeze(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line]

        title = lines[0] if lines else ""
        body = lines[1:] if lines else []
        pages.append(Page(index=page_no, title=title, blocks=body))

    return pages


def read_document(path: str | Path) -> list[Page]:
    """统一入口：根据后缀名选择解析器，返回页面列表。"""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"找不到文件：{file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".pptx":
        return parse_pptx(file_path)
    if suffix == ".pdf":
        return parse_pdf(file_path)

    supported = "、".join(sorted(SUPPORTED_SUFFIXES))
    raise ValueError(f"暂不支持 {suffix} 格式，目前支持：{supported}")
