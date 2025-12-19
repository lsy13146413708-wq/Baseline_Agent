# -*- coding: utf-8 -*-
"""
LLM 分析模块：调用 DeepSeek API 动态解析论文结构并返回 Roadmap。
"""

import re
import json
from typing import Optional

from secure_api import load_api_key
from schemas import Roadmap
from pydantic import ValidationError
from fallback import build_fallback_roadmap


LLM_SYSTEM_PROMPT = (
    "你是一名科研架构师。请阅读论文，设计一个结构化的技术路线图。请将研究过程划分为 3-5 个主要阶段（如：研究背景与问题、理论框架构建、核心模型设计、实验验证与应用等）。"
    "为了满足‘四列层级布局’要求，你需要生成以下四类节点：\n"
    "1. 'stage_label': 阶段名称（第1列）。\n"
    "2. 'task': 核心任务（第2列），动词+核心对象（如‘构建双螺旋耦合模型’）。\n"
    "3. 'sub_content': 细分内容（第3列），列出具体指标、变量或执行点（如‘输入：R&D经费’）。\n"
    "4. 'method': 方法与工具（第4列），该阶段涉及的方法。\n"
    "输出必须严格符合 JSON Schema：\n"
    "{\n"
    "  \"title\": string,\n"
    "  \"clusters\": [ { \"id\": string, \"label\": string } ],\n"
    "  \"nodes\": [ { \"id\": string, \"label\": string, \"type\": \"stage_label\"|\"task\"|\"sub_content\"|\"method\", \"parent_cluster\": string } ],\n"
    "  \"edges\": [ { \"source\": string, \"target\": string, \"label\"?: string } ]\n"
    "}\n"
    "要求：\n"
    "1. 每个 cluster 代表图中的一行（横向区域）。\n"
    "2. 每个 cluster 内必须有一个 'stage_label' 类型的节点（放在左侧）。\n"
    "3. 核心逻辑流向主要体现在 'task' 之间（垂直向下），'task' 指向其对应的 'sub_content'（水平向右）。\n"
    "4. 'sub_content' 内容要具体（拒绝空泛），提取具体指标或变量名。\n"
    "5. 节点文字要精简（不超过 15 个字，允许换行），避免长句。\n"
    "6. 不要输出任何非 JSON 的附加说明。"
)


def _extract_json_block(text: str) -> Optional[str]:
    # 从回答中提取 JSON 代码块或最外层 JSON
    code_block = re.search(r"```\s*json\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if code_block:
        return code_block.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def analyze_structure(text: str, model: str = "deepseek-chat", api_key_env: str = "DEEPSEEK_API_KEY", key_file: Optional[str] = None, pass_env: str = "DEEPSEEK_KEY_PASSPHRASE", env_file: Optional[str] = None, key_name: str = "DEEPSEEK_API_KEY") -> Roadmap:
    # 加载 API Key（优先 .env，其次加密文件，最后环境变量）
    api_key = load_api_key(api_key_env=api_key_env, encrypted_file=key_file, pass_env=pass_env, env_file=env_file, key_name=key_name)

    content = None
    # 优先使用 OpenAI SDK 兼容模式（设置 base_url 指向 DeepSeek）
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content
    except Exception:
        # 回退到 requests 直连 DeepSeek REST API
        try:
            import requests

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.2,
            }
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data_resp = r.json()
            content = data_resp["choices"][0]["message"]["content"]
        except Exception as e:
            # 无法获取内容，降级
            return build_fallback_roadmap(text, error=str(e))

    raw_json = _extract_json_block(content) or content
    try:
        data = json.loads(raw_json)
    except Exception:
        cleaned = raw_json.replace("'", '"')
        cleaned = re.sub(r",\s*}\s*$", "}", cleaned)
        data = json.loads(cleaned)

    try:
        roadmap = Roadmap(**data)
        roadmap.ensure_consistency()
        return roadmap
    except (ValidationError, ValueError) as e:
        return build_fallback_roadmap(text, error=str(e))
