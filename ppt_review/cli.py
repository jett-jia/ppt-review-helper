# -*- coding: utf-8 -*-
"""命令行入口：把各模块串起来。

用法示例：
    python -m ppt_review 课件.pptx -o 输出目录
    python -m ppt_review 课件.pdf --only 名词解释
    python -m ppt_review 课件.pptx --format review
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cleaner import clean_pages
from .extractor import extract_points
from .parsers import read_document
from .renderer import filter_points, render_mindmap, render_review

# 输出文件名后缀
REVIEW_SUFFIX = "_复习笔记.md"
MINDMAP_SUFFIX = "_思维导图.md"


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="ppt-review",
        description="PPT / PDF 课件知识点提取复习助手：把课件提炼成考点清单。",
    )
    parser.add_argument("input", help="课件文件路径（支持 .pptx / .pdf）")
    parser.add_argument(
        "-o", "--outdir", default="output",
        help="输出目录，默认是当前目录下的 output/",
    )
    parser.add_argument(
        "--only", default="全部",
        help="只输出某一类考点，例如：名词解释 / 简答 / 公式 / 易错点 / 全部（默认）",
    )
    parser.add_argument(
        "--format", choices=["all", "review", "mindmap"], default="all",
        help="输出哪种格式：all（默认，两种都出）/ review（只要复习笔记）/ mindmap（只要思维导图）",
    )
    parser.add_argument(
        "--title", default=None,
        help="Markdown 一级标题，默认用课件文件名",
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="只把复习笔记打印到终端，不写文件",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """程序主流程。返回值 0 表示成功。"""
    args = build_parser().parse_args(argv)
    source = Path(args.input)

    try:
        # 1. 解析：读成页面文本
        pages = read_document(source)
        # 2. 清洗：去掉装饰文字和重复页眉
        pages = clean_pages(pages)
        # 3. 提炼：归类成考点
        points = filter_points(extract_points(pages), args.only)
    except (FileNotFoundError, ValueError) as error:
        print(f"[错误] {error}", file=sys.stderr)
        return 1
    except Exception as error:  # 解析库自身的异常，尽量给一句人话
        print(f"[错误] 读取课件失败：{error}", file=sys.stderr)
        return 1

    if not pages:
        print("[提示] 没有读到任何文字。如果是扫描版 PDF 或图片版 PPT，"
              "需要先做 OCR 才能提取。", file=sys.stderr)

    title = args.title or source.stem
    review_md = render_review(title, source.name, len(pages), points)

    # 只打印到终端的情况
    if args.stdout:
        print(review_md)
        return 0

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if args.format in ("all", "review"):
        target = outdir / f"{source.stem}{REVIEW_SUFFIX}"
        target.write_text(review_md, encoding="utf-8")
        written.append(target)

    if args.format in ("all", "mindmap"):
        target = outdir / f"{source.stem}{MINDMAP_SUFFIX}"
        target.write_text(render_mindmap(title, points), encoding="utf-8")
        written.append(target)

    print(f"[完成] 共 {len(pages)} 页有效内容，提取考点 {len(points)} 条。")
    for path in written:
        print(f"       已生成：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
