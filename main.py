# -*- coding: utf-8 -*-
"""
主入口模块：串联文档解析、LLM 分析/Mock、Pydantic 验证与 Graphviz 绘制。
"""

import os
import argparse

from parser_docx import read_docx
from llm_analyzer import analyze_structure
from fallback import build_fallback_roadmap
from viz_graphviz import draw_roadmap


def main():
    parser = argparse.ArgumentParser(description="论文技术路线图自动生成 Agent")
    parser.add_argument("--input", "-i", type=str, help="输入 .docx 文件路径")
    parser.add_argument("--output", "-o", type=str, default="roadmap", help="输出文件前缀（不含扩展名）")
    parser.add_argument("--format", "-f", type=str, default="svg", choices=["svg", "png", "pdf"], help="输出格式")
    parser.add_argument("--mock", action="store_true", help="使用内置 Mock 数据（跳过 LLM）")
    parser.add_argument("--font", type=str, default="Microsoft YaHei", help="中文字体名称（例如 SimSun, Microsoft YaHei）")
    parser.add_argument("--fontpath", type=str, default="", help="字体文件目录（可选）")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="DeepSeek 模型名称")
    parser.add_argument("--api_key_env", type=str, default="DEEPSEEK_API_KEY", help="API Key 环境变量名")
    parser.add_argument("--key_file", type=str, default="", help="加密存储的 API Key 文件路径（可选）")
    parser.add_argument("--pass_env", type=str, default="DEEPSEEK_KEY_PASSPHRASE", help="用于解密的口令环境变量名")
    parser.add_argument("--env_file", type=str, default=".env", help=".env 文件路径（优先从此读取密钥）")
    parser.add_argument("--key_name", type=str, default="DEEPSEEK_API_KEY", help=".env 中密钥的键名")
    parser.add_argument("--aspect", type=str, default="3:4", help="输出纵横比（如 3:4、4:3、9:16）")
    parser.add_argument("--max_methods_per_row", type=int, default=3, help="每行最多方法节点数，用于控制宽度")
    parser.add_argument("--ranksep", type=str, default="0.7", help="Graphviz ranksep 间距")
    parser.add_argument("--nodesep", type=str, default="0.4", help="Graphviz nodesep 间距")
    parser.add_argument("--style", type=str, default="beautiful", choices=["beautiful", "classic"], help="绘图风格")

    args = parser.parse_args()

    fontname = args.font
    fontpath = args.fontpath or None

    if args.mock:
        roadmap_data = build_fallback_roadmap(raw_text="Mock Data")
    else:
        if not args.input:
            raise RuntimeError("未提供 --input .docx 文件路径，或使用 --mock 进行测试")
        if not os.path.exists(args.input):
            raise FileNotFoundError(f"文件不存在：{args.input}")
        text = read_docx(args.input)
        roadmap_data = analyze_structure(
            text,
            model=args.model,
            api_key_env=args.api_key_env,
            key_file=(args.key_file or None),
            pass_env=args.pass_env,
            env_file=(args.env_file or None),
            key_name=args.key_name,
        )

    roadmap_data.ensure_consistency()
    if args.style == "beautiful":
        from viz_graphviz import generate_beautiful_roadmap
        outpath = generate_beautiful_roadmap(
            roadmap_data=roadmap_data,
            output_filename=args.output,
            fontname=fontname,
            output_format=args.format,
        )
    else:
        outpath = draw_roadmap(
            roadmap_data=roadmap_data,
            output_path=args.output,
            output_format=args.format,
            fontname=fontname,
            fontpath=fontpath,
            aspect=args.aspect,
            max_methods_per_row=args.max_methods_per_row,
            ranksep=args.ranksep,
            nodesep=args.nodesep,
        )
    print(f"已生成：{outpath}")


if __name__ == "__main__":
    main()
