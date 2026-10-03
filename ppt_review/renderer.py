# -*- coding: utf-8 -*-
"""输出模块：把考点渲染成 Markdown。

输出两种格式：
1. 精简复习版——按考点类别分组，条目化，适合考前直接背；
2. 思维导图大纲版——纯层级列表，可以直接粘进 XMind / 幕布。
"""

from __future__ import annotations

from datetime import date

from .extractor import CATEGORIES, Point, keyword_summary, points_by_category

# 用户可以用 --only 指定的筛选值 -> 实际保留的类别
ONLY_ALIASES = {
    "全部": None,
    "all": None,
    "名词解释": ["核心定义"],
    "定义": ["核心定义"],
    "简答": ["简答考点"],
    "简答题": ["简答考点"],
    "公式": ["公式"],
    "易错点": ["易错点"],
    "结论": ["结论"],
}


def filter_points(points: list[Point], only: str) -> list[Point]:
    """按 --only 筛出指定类别的考点。

    only 取值见 ONLY_ALIASES；不认识的值会原样报错，避免"以为筛了其实没筛"。
    """
    key = only.strip()
    if key not in ONLY_ALIASES:
        allowed = "、".join(ONLY_ALIASES.keys())
        raise ValueError(f"不认识的筛选类别：{only}，可选：{allowed}")

    wanted = ONLY_ALIASES[key]
    if wanted is None:
        return list(points)
    return [point for point in points if point.category in wanted]


def render_review(title: str, source_name: str, page_count: int, points: list[Point]) -> str:
    """渲染「精简复习版」Markdown。"""
    grouped = points_by_category(points)
    lines: list[str] = []

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> 来源课件：{source_name} ｜ 有效内容 {page_count} 页 ｜ "
                 f"提取考点 {len(points)} 条 ｜ 生成日期：{date.today():%Y-%m-%d}")
    lines.append("> 条目末尾的 P 编号是幻灯片／PDF 的原始页码。")
    lines.append("> 内容全部来自课件原文，只做了筛选和归类。"
                 "最终以老师画的重点为准。")
    lines.append("")

    # 开头放一份高频考点速览，考前最后一遍就看这里
    hot = keyword_summary(points)
    if hot:
        lines.append("## 高频考点速览")
        lines.append("")
        for term, count in hot:
            lines.append(f"- **{term}**（出现 {count} 次）")
        lines.append("")

    for category in CATEGORIES:
        items = grouped[category]
        if not items:
            continue
        lines.append(f"## {category}（{len(items)} 条）")
        lines.append("")
        for point in items:
            lines.append(f"- {point.display}")
        lines.append("")

    if not points:
        lines.append("_没有提取到任何考点。可能这份课件是扫描件或纯图片版，"
                     "文字没法直接读取。_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("由「PPT 知识点提取复习助手」生成")
    lines.append("")
    return "\n".join(lines)


def render_mindmap(title: str, points: list[Point]) -> str:
    """渲染「思维导图大纲版」Markdown。

    只使用 # 标题和 - 列表，这是 XMind、幕布、Markmap 都认的通用形式。
    """
    grouped = points_by_category(points)
    lines: list[str] = [f"# {title}", ""]

    for category in CATEGORIES:
        items = grouped[category]
        if not items:
            continue
        lines.append(f"- {category}")
        for point in items:
            marker = f"{point.importance} " if point.importance else ""
            lines.append(f"  - {marker}{point.text}")
            lines.append(f"    - 出处：第 {point.page} 页")

    if not points:
        lines.append("- （未提取到考点）")

    lines.append("")
    return "\n".join(lines)
