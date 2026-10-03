# -*- coding: utf-8 -*-
"""文本清洗模块：把解析出来的原始文本块洗成干净的教学内容。

做四件事：
1. 去掉页码、"第 X 页"、"版权所有"这类装饰文字；
2. 去掉"谢谢观看""本章结束"这类不含知识点的收尾页；
3. 去掉跨页重复出现的页眉页脚（同一段文字在很多页顶端重复）。
"""

from __future__ import annotations

import re
from collections import Counter

from .parsers import Page

# 完全匹配就丢弃的句子（整页废话）
NOISE_PHRASES = {
    "谢谢观看",
    "谢谢聆听",
    "感谢观看",
    "感谢聆听",
    "本章结束",
    "本节结束",
    "本节完",
    "再见",
    "the end",
    "thank you",
}

# 正则匹配就丢弃的句子
NOISE_PATTERNS = [
    re.compile(r"^第?\s*\d+\s*页$"),  # 第 3 页 / 3 页
    re.compile(r"^[-—\s]*\d{1,3}[-—\s]*$"),  # 单独的页码数字
    re.compile(r"^[©（(]?\s*(版权|版权所有|copyright)", re.IGNORECASE),
    re.compile(r"^[\W_]+$"),  # 全是符号，一个中英文字都没有
    # 封面页常见的几行字：课程名、教师名、教材名，这些不含知识点
    re.compile(r"^.{0,10}(复习课件|主讲人|主讲教师|授课教师|任课教师)$"),
    re.compile(r"^(教材|课程名称|参考教材)[:：]"),
]

# 短于这个长度、且没有任何中英文数字的块直接丢掉
MIN_BLOCK_LENGTH = 2

def _is_noise_line(line: str) -> bool:
    """判断单个文本块是不是装饰文字。"""
    stripped = line.strip()
    if len(stripped) < MIN_BLOCK_LENGTH:
        return True
    if not re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", stripped):
        return True
    if stripped.lower() in NOISE_PHRASES:
        return True
    return any(pattern.search(stripped) for pattern in NOISE_PATTERNS)


def _find_repeated_headers(pages: list[Page]) -> set[str]:
    """找出跨页重复出现的页眉页脚。

    判断标准：同一段文字出现在至少 3 页、且覆盖全部页面的 30% 以上，
    同时长度不超过 40 字（太长的多半是正文，不是页眉）。

    这里扫描每一页的全部文本块，而不是只看首尾：实际课件里，
    页眉常常排在标题占位符后面、页码前面，只看首尾容易漏掉。
    """
    counter: Counter[str] = Counter()
    for page in pages:
        for block in set(page.blocks):
            counter[block] += 1

    threshold = max(3, int(len(pages) * 0.3))
    return {
        text
        for text, count in counter.items()
        if count >= threshold and len(text) <= 40
    }


def clean_pages(pages: list[Page]) -> list[Page]:
    """清洗页列表，返回新的 Page 列表（不修改传入的对象）。"""
    repeated = _find_repeated_headers(pages)
    cleaned: list[Page] = []

    for page in pages:
        kept = [
            block
            for block in page.blocks
            if not _is_noise_line(block) and block not in repeated
        ]
        if not kept:
            # 整页都是装饰文字（封面、致谢、章节过渡页常常如此），直接跳过
            continue

        cleaned.append(Page(index=page.index, blocks=kept))

    return cleaned
