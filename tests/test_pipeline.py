# -*- coding: utf-8 -*-
"""够用的自检：跑一遍完整流水线，确认清洗和分类真的生效。

运行方式：
    python tests/test_pipeline.py

刻意不用 pytest —— 几个 assert 就够，没必要为此多一个依赖。
它检查的是"逻辑坏掉时会不会响"，不是覆盖率。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让脚本能直接找到上层目录里的 ppt_review 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ppt_review.cleaner import clean_pages  # noqa: E402
from ppt_review.extractor import extract_points  # noqa: E402
from ppt_review.parsers import read_document  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_PPTX = PROJECT_ROOT / "demo" / "计算机网络_第3章_传输层.pptx"
DEMO_PDF = PROJECT_ROOT / "demo" / "操作系统_第2章_进程管理.pdf"

# 示例课件里故意埋的噪音，清洗后都不该出现
REPEATED_HEADER = "计算机网络 · 第 3 章 传输层"
COVER_LINE = "期末复习课件"
CLOSING_LINE = "谢谢观看"


def test_pptx_pipeline() -> None:
    """PPT：噪音被清掉，五类考点能分出来。"""
    pages = clean_pages(read_document(DEMO_PPTX))
    assert pages, "PPT 没读出任何内容"

    text = " ".join(block for page in pages for block in page.blocks)
    assert REPEATED_HEADER not in text, "重复页眉没被清掉"
    assert COVER_LINE not in text, "封面文字没被清掉"
    assert CLOSING_LINE not in text, "结尾致谢页没被清掉"

    points = extract_points(pages)
    categories = {point.category for point in points}
    missing = {"核心定义", "公式", "易错点", "简答考点"} - categories
    assert not missing, f"这几类考点一个都没分出来：{missing}"

    formulas = [point.text for point in points if point.category == "公式"]
    assert any("RTT" in line for line in formulas), "公式没被识别出来"

    starred = [point for point in points if point.importance == "★"]
    assert starred, "没有任何考点被标成 ★"

    print(f"PPT 自检通过：{len(pages)} 页有效内容，{len(points)} 条考点，"
          f"{len(starred)} 条 ★")


def test_pdf_pipeline() -> None:
    """PDF：能读出内容，页脚不会混进考点。"""
    pages = clean_pages(read_document(DEMO_PDF))
    assert pages, "PDF 没读出任何内容"

    text = " ".join(block for page in pages for block in page.blocks)
    assert "第 1 页" not in text, "PDF 页脚没被清掉"

    points = extract_points(pages)
    assert any(point.category == "核心定义" for point in points), "PDF 里的定义没分出来"
    print(f"PDF 自检通过：{len(pages)} 页有效内容，{len(points)} 条考点")


def main() -> None:
    test_pptx_pipeline()
    test_pdf_pipeline()
    print("全部自检通过")


if __name__ == "__main__":
    main()
