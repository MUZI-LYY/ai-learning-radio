"""长文分块：优先按标题和段落边界切分，每块目标 6000-8000 字，保留少量上下文重叠。"""

from __future__ import annotations

TARGET_CHARS = 7000
OVERLAP_CHARS = 200


def chunk_text(text: str, target: int = TARGET_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """把规范化正文切分为接近 target 长度的块。"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= target:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        if current and current_len + len(paragraph) > target:
            chunks.append("\n".join(current))
            # 保留少量重叠：把最后一段也作为下一块的起点
            tail = current[-1] if overlap > 0 else ""
            current = [tail] if tail else []
            current_len = len(tail)
        current.append(paragraph)
        current_len += len(paragraph)

    if current:
        chunks.append("\n".join(current))

    # 若单段超长，按字符硬切
    result: list[str] = []
    for chunk in chunks:
        if len(chunk) <= target + overlap:
            result.append(chunk)
        else:
            result.extend(_hard_split(chunk, target))
    return result


def _hard_split(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]
