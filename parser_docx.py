# -*- coding: utf-8 -*-
"""
文档解析模块：使用 python-docx 读取 .docx 文本并清洗。
"""

import re
from typing import List
from docx import Document


def read_docx(file_path: str, max_chars: int = 15000) -> str:
    # 读取并清洗文本，限制最大长度防止 Token 溢出
    doc = Document(file_path)
    lines: List[str] = []
    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if len(text) >= 2:
            text = re.sub(r"\s+", " ", text)
            lines.append(text)
    full_text = "\n".join(lines)
    return full_text[:max_chars]

