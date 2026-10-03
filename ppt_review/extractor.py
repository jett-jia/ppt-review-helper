# -*- coding: utf-8 -*-
"""知识点提炼模块：把清洗后的页面文本归类成考试会用到的考点。

归类用的是「关键词规则」，不是机器学习模型。为什么这样做：
1. 完全本地运行，课件不出你的电脑；
2. 规则可读、可改，学生自己能看懂，也能按自己老师的出题习惯调整；
3. 不需要下载几百 MB 的模型文件。

代价是它不理解语义，只能靠措辞判断。所以本模块的输出定位是
"把课件里像考点的句子挑出来并分好类"，最终的取舍仍然由你自己决定。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections import Counter

from .parsers import Page

# 五类考点的固定顺序（输出时按这个顺序排版）
CATEGORIES = ["核心定义", "公式", "结论", "易错点", "简答考点"]

# 公式里常见的数学符号
FORMULA_SYMBOLS = set("=≈≠≤≥∑Σ∫√∞πθαβγλμσΔ∂→⇒∈∉⊆⊂∪∩±×÷·^~≈")

# 各类考点的判定关键词（按顺序匹配，先匹配到的优先）
DEFINITION_MARKERS = ("是指", "称为", "叫做", "定义为", "指的是", "又称", "简称", "是一种", "属于")
PITFALL_MARKERS = (
    "易错", "误区", "常见错误", "切忌", "容易混淆", "不要混",
    "注意区分", "易混淆", "注意", "区别在于", "不同点",
)
CONCLUSION_MARKERS = ("因此", "所以", "可见", "由此", "综上", "结论", "可知", "可以得出", "定理", "推论", "性质")
QUESTION_MARKERS = ("为什么", "如何", "怎样", "简述", "试述", "列举", "比较", "说明", "优缺点", "作用", "意义", "步骤", "流程")

# 重要性标记关键词
MUST_MARKERS = ("重点", "必考", "考点", "掌握", "核心", "关键", "必须")
OPTIONAL_MARKERS = ("了解", "选学", "补充", "扩展", "背景", "自学")


@dataclass
class Point:
    """一条提炼出来的考点。"""

    category: str  # 五类之一
    text: str  # 考点原文（已压缩空白）
    page: int  # 出现在第几页
    importance: str = ""  # "★" 必考 / "☆" 了解 / "" 普通
    heat: int = 0  # 这条考点的主术语在全篇出现了多少次

    @property
    def display(self) -> str:
        """输出时用的文本，带重要性和页码。"""
        prefix = f"{self.importance} " if self.importance else ""
        return f"{prefix}{self.text}（P{self.page}）"


def _has_formula(text: str) -> bool:
    """判断一句话里有没有公式。"""
    symbol_count = sum(1 for ch in text if ch in FORMULA_SYMBOLS)
    if symbol_count >= 2:
        return True
    # 形如 "T = L / R" 这种等式，即使只有一个等号也算公式
    return bool(re.search(r"[A-Za-z\u4e00-\u9fa5]\s*=\s*\S", text))


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    """文本里是否出现任意一个关键词。"""
    return any(marker in text for marker in markers)


def _classify(text: str) -> str:
    """给一句话归类。

    顺序很重要：先判断特征最强的（公式、易错点），再判断定义，
    最后才是结论和简答题——因为"因此…说明…"这类句子很容易被误判。
    """
    if _has_formula(text):
        return "公式"
    if _has_any(text, PITFALL_MARKERS):
        return "易错点"
    if _has_any(text, DEFINITION_MARKERS):
        return "核心定义"
    # 以问号结尾的句子基本就是简答考点
    if text.rstrip().endswith(("？", "?")):
        return "简答考点"
    if _has_any(text, QUESTION_MARKERS):
        return "简答考点"
    if _has_any(text, CONCLUSION_MARKERS):
        return "结论"
    return "结论"


def _extract_term(text: str) -> str:
    """尝试从一句话里抽出它讲的那个"术语"。

    例如 "时延是指数据从网络一端传送到另一端所需的时间" -> "时延"
    抽不出来就返回空字符串，不影响后续处理。
    """
    match = re.match(
        r"^[\s\d一二三四五六七八九十、.．()（）]*"
        r"([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9]{1,14}?)"
        r"(是指|称为|叫做|定义为|指的是|是一种|即|:)",
        text,
    )
    return match.group(1) if match else ""


def _mark_importance(points: list[Point], full_text: str) -> None:
    """给每条考点打上 ★ / ☆ 标记（就地修改）。

    两条判断依据，优先级从高到低：
    1. 课件里自己写了"重点/必考"这类词 -> ★；写了"了解/选学" -> ☆；
    2. 没有明确标注时，如果这个术语在全篇出现 3 次以上，说明反复讲 -> ★。

    顺带把术语在全篇的出现次数记到 point.heat 上，供"高频考点速览"使用。
    """
    for point in points:
        term = _extract_term(point.text)
        if term:
            point.heat = full_text.count(term)

        if _has_any(point.text, MUST_MARKERS):
            point.importance = "★"
        elif _has_any(point.text, OPTIONAL_MARKERS):
            point.importance = "☆"
        elif point.heat >= 3:
            point.importance = "★"


def extract_points(pages: list[Page]) -> list[Point]:
    """从清洗后的页面里提炼考点。

    同一句话在多页重复出现时只保留第一次，避免复习笔记里全是重复条目。
    """
    full_text = " ".join(block for page in pages for block in page.blocks)
    points: list[Point] = []
    seen: set[str] = set()

    for page in pages:
        for block in page.blocks:
            # 归一化后再比对，防止因为首尾空格差异导致去重失效
            key = re.sub(r"\s+", "", block)
            if key in seen:
                continue
            seen.add(key)
            points.append(Point(category=_classify(block), text=block, page=page.index))

    _mark_importance(points, full_text)
    return points


def points_by_category(points: list[Point]) -> dict[str, list[Point]]:
    """按五类分组，并保持 CATEGORIES 里的固定顺序。"""
    grouped: dict[str, list[Point]] = {name: [] for name in CATEGORIES}
    for point in points:
        grouped[point.category].append(point)
    return grouped


def keyword_summary(
    points: list[Point], min_count: int = 2, top_n: int = 12
) -> list[tuple[str, int]]:
    """统计反复出现的术语，用来在笔记开头做一份"高频考点速览"。

    只统计能从"X 是指…"这类句式里抽出来的术语，而且只保留出现
    2 次以上的——只出现一次的词算不上"高频"，列出来反而干扰阅读。
    """
    best: Counter[str] = Counter()
    for point in points:
        term = _extract_term(point.text)
        if term and point.heat > best[term]:
            best[term] = point.heat

    hot = [(term, count) for term, count in best.items() if count >= min_count]
    hot.sort(key=lambda item: (-item[1], item[0]))
    return hot[:top_n]
