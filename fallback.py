# -*- coding: utf-8 -*-
"""
降级与示例模块：当 LLM 返回异常时，提供可视化用的简易路线图。
"""

from schemas import Roadmap, NodeItem, EdgeItem, NodeType, ClusterItem


def build_fallback_roadmap(raw_text: str, error: str = "") -> Roadmap:
    # 当 LLM 解析失败时，生成一个默认的 4-Column 结构的 roadmap
    title = f"技术路线图（解析失败回退）"
    if error:
        title += f" [Error: {error[:20]}...]"

    # 构造示例数据
    clusters = [
        {"id": "phase1", "label": "阶段一：研究准备"},
        {"id": "phase2", "label": "阶段二：核心研究"},
        {"id": "phase3", "label": "阶段三：应用验证"}
    ]
    nodes = [
        # Phase 1
        {"id": "s1", "label": "研究准备", "type": "stage_label", "parent_cluster": "phase1"},
        {"id": "t1", "label": "文献调研", "type": "task", "parent_cluster": "phase1"},
        {"id": "sub1", "label": "输入：知网/WOS", "type": "sub_content", "parent_cluster": "phase1"},
        {"id": "m1", "label": "文献分析法", "type": "method", "parent_cluster": "phase1"},
        
        # Phase 2
        {"id": "s2", "label": "核心研究", "type": "stage_label", "parent_cluster": "phase2"},
        {"id": "t2", "label": "构建模型", "type": "task", "parent_cluster": "phase2"},
        {"id": "sub2", "label": "变量：GDP/R&D", "type": "sub_content", "parent_cluster": "phase2"},
        {"id": "m2", "label": "回归分析", "type": "method", "parent_cluster": "phase2"},
        
        # Phase 3
        {"id": "s3", "label": "应用验证", "type": "stage_label", "parent_cluster": "phase3"},
        {"id": "t3", "label": "实证分析", "type": "task", "parent_cluster": "phase3"},
        {"id": "sub3", "label": "指标：准确率", "type": "sub_content", "parent_cluster": "phase3"},
        {"id": "m3", "label": "案例研究", "type": "method", "parent_cluster": "phase3"},
    ]
    edges = [
        {"source": "t1", "target": "t2"},
        {"source": "t2", "target": "t3"},
        {"source": "t1", "target": "sub1"},
        {"source": "t2", "target": "sub2"},
        {"source": "t3", "target": "sub3"},
        {"source": "sub1", "target": "m1"},
        {"source": "sub2", "target": "m2"},
        {"source": "sub3", "target": "m3"}
    ]

    return Roadmap(title=title, clusters=clusters, nodes=nodes, edges=edges)
