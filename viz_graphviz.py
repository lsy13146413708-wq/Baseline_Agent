# -*- coding: utf-8 -*-
"""
可视化引擎模块：使用 Graphviz 绘制分阶段三列布局的技术路线图。
支持纵向布局优化、宽度控制、纵横比设置与行内方法分组，避免横向过长。
"""

import os
import graphviz
from typing import Dict, List, Optional, Tuple
from schemas import Roadmap, NodeItem, EdgeItem, NodeType, ClusterItem


def _apply_font_env(fontpath: Optional[str]) -> None:
    # 设置字体搜索路径（Windows 上可用 GDFONTPATH）
    if fontpath and os.path.exists(fontpath):
        os.environ["GDFONTPATH"] = fontpath

def _parse_aspect(aspect: Optional[str]) -> Optional[Tuple[str, Optional[str]]]:
    # 将 "3:4"、"4:3"、"9:16" 等转换为 ratio（宽/高）与 size 提示
    if not aspect:
        return None
    s = aspect.strip().lower()
    if ":" in s:
        try:
            w, h = s.split(":", 1)
            wv = float(w)
            hv = float(h)
            if wv > 0 and hv > 0:
                ratio = str(wv / hv)
                # size 只作提示，不强制（SVG 更适合按视窗缩放）
                return (ratio, None)
        except Exception:
            return None
    return None


def draw_roadmap(
    roadmap_data: Roadmap,
    output_path: str = "roadmap",
    output_format: str = "svg",
    fontname: str = "Microsoft YaHei",
    fontpath: Optional[str] = None,
    aspect: Optional[str] = "3:4",
    max_methods_per_row: int = 3,
    ranksep: str = "0.7",
    nodesep: str = "0.4",
) -> str:
    # 全局属性：从上到下、正交线、中文字体，并尽量控制纵横比与间距
    _apply_font_env(fontpath)

    ratio_size = _parse_aspect(aspect)
    graph_attrs = {
        "rankdir": "TB",
        "splines": "ortho",
        "fontsize": "12",
        "fontname": fontname,
        "label": roadmap_data.title,
        "labelloc": "t",
        "newrank": "true",
        "ranksep": ranksep,
        "nodesep": nodesep,
    }
    if ratio_size:
        graph_attrs["ratio"] = ratio_size[0]

    dot = graphviz.Digraph(
        name="TechRoadmap",
        graph_attr=graph_attrs,
        node_attr={
            "fontname": fontname,
            "fontsize": "11",
        },
        edge_attr={
            "fontname": fontname,
            "fontsize": "10",
            "color": "#5c6f7b",
        },
    )

    phase_style = {"shape": "box", "style": "rounded,filled", "fillcolor": "#2b3a67", "fontcolor": "white", "color": "#2b3a67"}
    task_style = {"shape": "box", "style": "filled", "fillcolor": "#ffffff", "color": "#4a6fa5"}
    method_style = {"shape": "parallelogram", "style": "filled", "fillcolor": "#eef3ff", "color": "#7aa2f7"}

    nodes_by_id: Dict[str, NodeItem] = {n.id: n for n in roadmap_data.nodes}
    edges_by_source: Dict[str, List[EdgeItem]] = {}
    for e in roadmap_data.edges:
        edges_by_source.setdefault(e.source, []).append(e)

    # 保留原始节点顺序索引，供按输入顺序排序 cluster 内节点使用
    node_index: Dict[str, int] = {n.id: idx for idx, n in enumerate(roadmap_data.nodes)}

    # 收集 stage 顺序以便后续添加相邻箭头（display order）
    stage_order: List[str] = []

    # 按原始顺序遍历 cluster（正序渲染）
    # 为了让虚线大框不包含最左侧的 stage_label（第1列），我们把 stage_label 节点放到子图外面创建，
    # 仅把 task/sub_content/method 放入 cluster 子图。这样视觉上大框会缩小，不包含最左列。
    for cluster in roadmap_data.clusters:
        cluster_id = cluster.id if isinstance(cluster, ClusterItem) else str(cluster)
        cluster_label = cluster.label if isinstance(cluster, ClusterItem) else str(cluster)

        # stage（最左列）节点：先在主图上创建（不在子图内），保持样式不变
        stage_nodes = [n for n in roadmap_data.nodes if n.parent_cluster == cluster_id and n.type in (NodeType.phase, NodeType.stage_label)]
        # 按原始输入顺序排序
        stage_nodes = sorted(stage_nodes, key=lambda x: node_index.get(x.id, 0))
        for n in stage_nodes:
            style = phase_style
            dot.node(n.id, label=n.label, **style, group="phase")
            stage_order.append(n.id)

        # 其余节点放入 cluster 子图（虚线框内）
        with dot.subgraph(name=f"cluster_{cluster_id}") as c:
            c.attr(style="dashed", color="#9aa5b1", label=cluster_label, labelloc="t", labeljust="l")
            cluster_inner_nodes = [n for n in roadmap_data.nodes if n.parent_cluster == cluster_id and n.type not in (NodeType.phase, NodeType.stage_label)]
            # 保持 cluster 内节点按原始输入顺序
            cluster_inner_nodes = sorted(cluster_inner_nodes, key=lambda x: node_index.get(x.id, 0))
            for n in cluster_inner_nodes:
                style = task_style if n.type == NodeType.task else method_style
                group_val = "task" if n.type == NodeType.task else "method"
                c.node(n.id, label=n.label, **style, group=group_val)

            phase_nodes = stage_nodes
            for p in phase_nodes:
                row_tasks = [nodes_by_id[e.target] for e in edges_by_source.get(p.id, []) if nodes_by_id.get(e.target) and nodes_by_id[e.target].type == NodeType.task]
                if not row_tasks:
                    continue
                for t in row_tasks:
                    methods = [nodes_by_id[e.target] for e in edges_by_source.get(t.id, []) if nodes_by_id.get(e.target) and nodes_by_id[e.target].type == NodeType.method]

                    # 将方法按批次拆分，避免一行过长
                    def _chunks(lst: List[NodeItem], size: int) -> List[List[NodeItem]]:
                        return [lst[i : i + size] for i in range(0, len(lst), size)] or [[]]

                    for idx, mchunk in enumerate(_chunks(methods, max_methods_per_row)):
                        row_name = f"{cluster}_row_{p.id}_{t.id}_{idx}"
                        with c.subgraph(name=row_name) as row:
                            row.attr(rank="same")
                            # 使用不可见的 phase 代理节点保证列对齐，但不拉长原始 phase
                            proxy_id = f"proxy_{p.id}_{t.id}_{idx}"
                            row.node(proxy_id, label="", shape="box", style="invis", width="0", height="0", group="phase")
                            row.node(t.id)
                            for m in mchunk:
                                row.node(m.id)

            # 为当前 cluster 内的 task（第2列）按现有节点顺序添加相邻箭头（如果不存在）
            task_nodes_in_cluster = [n.id for n in cluster_inner_nodes if n.type == NodeType.task]
            existing_pairs = {(e.source, e.target) for e in roadmap_data.edges}
            for i in range(len(task_nodes_in_cluster) - 1):
                a = task_nodes_in_cluster[i]
                b = task_nodes_in_cluster[i + 1]
                if (a, b) not in existing_pairs:
                    dot.edge(a, b, style="solid", arrowhead="normal")

    for e in roadmap_data.edges:
        # 如果任一端是 method，则将边设为不可见以移除可视连线但保留布局约束
        src_node = nodes_by_id.get(e.source)
        tgt_node = nodes_by_id.get(e.target)
        # 规则：
        # - 只允许 Task -> Sub_content 显示为虚线（column2 -> column3），且无箭头
        # - 任何涉及 method 的边保持不可见（原行为）
        # - 其他涉及 sub_content 的边一律不可见
        if (src_node and src_node.type == NodeType.method) or (tgt_node and tgt_node.type == NodeType.method):
            dot.edge(e.source, e.target, label=(e.label or ""), style="invis", arrowhead="none")
        elif (src_node and src_node.type == NodeType.task) and (tgt_node and tgt_node.type == NodeType.sub_content):
            dot.edge(e.source, e.target, label=(e.label or ""), style="dashed", arrowhead="none")
        elif (src_node and src_node.type == NodeType.sub_content) or (tgt_node and tgt_node.type == NodeType.sub_content):
            # 任何其他与 sub_content 有关的连接都设为不可见
            dot.edge(e.source, e.target, label=(e.label or ""), style="invis", arrowhead="none")
        else:
            dot.edge(e.source, e.target, label=(e.label or ""), arrowhead="normal")

    # 在主图上为第1列（stage）添加相邻箭头，按渲染顺序（stage_order）连接
    existing_pairs = {(e.source, e.target) for e in roadmap_data.edges}
    for i in range(len(stage_order) - 1):
        a = stage_order[i]
        b = stage_order[i + 1]
        if (a, b) not in existing_pairs:
            dot.edge(a, b, style="solid", arrowhead="normal")

    outfile = dot.render(filename=output_path, format=output_format, cleanup=True)
    return outfile


def generate_beautiful_roadmap(
    roadmap_data: Roadmap,
    output_filename: str = "roadmap",
    fontname: str = "Microsoft YaHei",
    output_format: str = "svg",
) -> str:
    # 4-Column Layout: Phases -> Main Tasks -> Sub-contents -> Methods
    dot = graphviz.Digraph(name="G", comment="Research Roadmap")

    # 布局设置：LR (Left-to-Right)
    dot.attr(rankdir="LR")
    dot.attr(splines="ortho")
    dot.attr(nodesep="0.6")
    dot.attr(ranksep="0.8")
    dot.attr(fontname=fontname)
    dot.attr(compound="true")
    dot.attr(newrank="true")

    dot.attr("node", fontname=fontname, fontsize="12", shape="box", style="rounded,filled", fillcolor="white")
    dot.attr("edge", fontname=fontname, fontsize="11")

    data = roadmap_data.dict()
    clusters = data.get("clusters", [])
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # 已有边集合，避免重复添加
    existing_pairs = {(e.get("source"), e.get("target")) for e in edges}
    # stage 顺序记录（用于生成 column1 相邻箭头）
    stage_order: List[str] = []
    # 保留原始节点顺序索引，供按输入顺序排序 cluster 内节点使用
    node_index_dict: Dict[str, int] = {n["id"]: idx for idx, n in enumerate(nodes)}

    # 1. 绘制 Clusters (Phases)
    # 按原始顺序遍历 clusters（正序渲染）
    for cluster in clusters:
        cluster_id = cluster["id"] if isinstance(cluster, dict) else str(cluster)
        cluster_label = cluster.get("label", "") if isinstance(cluster, dict) else str(cluster)

        # 把 stage_label（第1列）节点放到主图（不在 cluster 子图内），以便虚线大框不包含最左列
        current_nodes = [n for n in nodes if n.get("parent_cluster") == cluster_id]
        # 按原始输入顺序排序 cluster 内节点
        current_nodes = sorted(current_nodes, key=lambda x: node_index_dict.get(x.get("id"), 0))
        stage_nodes = [n for n in current_nodes if n.get("type") in ("stage_label", "phase")]
        for node in stage_nodes:
            dot.node(
                node["id"],
                label=node["label"],
                shape="box",
                style="rounded,filled",
                fillcolor="#2b3a67",
                color="#2b3a67",
                fontcolor="white",
                width="2.5",
            )
            stage_order.append(node["id"])

        # 其余节点放入 cluster 子图（虚线框内）
        with dot.subgraph(name=f"cluster_{cluster_id}") as c:
            c.attr(label=cluster_label)
            c.attr(style="dashed")
            c.attr(color="#404040")
            c.attr(fontcolor="#404040")
            c.attr(bgcolor="#F9F9F9")

            task_nodes = [n for n in current_nodes if n.get("type") == "task"]
            sub_nodes = [n for n in current_nodes if n.get("type") == "sub_content"]
            method_nodes = [n for n in current_nodes if n.get("type") == "method"]

            # 绘制 Task Nodes (第2列)
            for node in task_nodes:
                c.node(node["id"], label=node["label"], shape="box", style="filled", fillcolor="white", color="black", width="2.5")

            # 绘制 Sub-content Nodes (第3列)
            for node in sub_nodes:
                # 使用花括号或虚线风格
                c.node(node["id"], label=node["label"], shape="note", style="dashed", fillcolor="#F5F5F5", color="#666666", width="2.0")

            # 绘制 Method Nodes (第4列)
            for node in method_nodes:
                c.node(node["id"], label=node["label"], shape="ellipse", style="filled", fillcolor="#E1F5FE", color="#01579B")

            # 为当前 cluster 内的 task（第2列）按现有节点顺序添加相邻箭头（如果不存在）
            task_ids = [n.get("id") for n in task_nodes]
            for i in range(len(task_ids) - 1):
                a = task_ids[i]
                b = task_ids[i + 1]
                if (a, b) not in existing_pairs:
                    dot.edge(a, b, style="solid", arrowhead="normal")

            # 强制布局逻辑：Task -> Sub-content -> Method (水平)
            # 但 Task 内部是垂直连接 (A->B->C)，由 edges 定义
            # 这里我们需要确保 Sub-content 在 Task 右侧
            
            # 辅助对齐：每个 Task 右侧对齐其 Sub-content
            # 通过 rank=same 约束 Task 和 Sub-content
            # 注意：如果一个 Task 对应多个 Sub-content，这可能比较复杂。
            # 简化假设：主要由 Edge 驱动布局，我们用 invisible edges 辅助。
            
            # 由于 rankdir=LR，rank=same 意味着垂直对齐 (same x coordinate)？
            # 不，rankdir=LR 时，rank=same 意味着在同一列 (same rank)。
            # 所以我们希望 Task 和 Sub-content 在不同的 rank。
            # Task 在 Rank 2, Sub-content 在 Rank 3, Method 在 Rank 4.
            
            # 更好的做法是让 Graphviz 自动处理，我们通过 Edge 约束。
            pass

    # 2. 绘制 Edges
    for edge in edges:
        src_id = edge.get("source")
        tgt_id = edge.get("target")
        label = edge.get("label", "")
        
        src_node = next((n for n in nodes if n["id"] == src_id), None)
        tgt_node = next((n for n in nodes if n["id"] == tgt_id), None)
        
        edge_attrs = {"color": "#333333"}
        
        if src_node and tgt_node:
            src_type = src_node.get("type")
            tgt_type = tgt_node.get("type")
            
            # 逻辑连接规则：
            # Task -> Task (垂直向下): 由于 rankdir=LR，这实际上是同级或跨级？
            # 等等，用户要求 "Task A -> Task B" 是向下箭头。
            # 在 rankdir=LR 模式下，默认箭头是向右的。
            # 要实现 "Task A 下方是 Task B"，我们需要它们在 "same rank" 吗？
            # 或者，如果整个图是 LR，那么 Phases 是从左到右排的吗？
            # 用户描述：
            # 第1列：Phases (左)
            # 第2列：Tasks (中左)
            # 第3列：Sub-contents (中右)
            # 第4列：Methods (右)
            
            # 如果 rankdir=LR，那么流向是 左->右。
            # Phase -> Task -> Sub -> Method
            # 这符合逻辑。
            
            # 但是 "Task A -> Task B" (垂直向下) 在 LR 布局中意味着 Task A 和 Task B 在同一列（Rank），但 A 在 B 上方。
            # Graphviz 在 LR 模式下，节点堆叠是自动的，但没有直接的 "A->B" 向下箭头支持（那是 rankdir=TB 的特性）。
            # 在 LR 模式下，"A->B" 会试图把 B 放在 A 的右边。
            
            # 修正策略：保持 rankdir=TB (Top-Bottom) 可能更适合 "垂直堆叠" 的描述？
            # 用户说： "请放弃之前的“水平长流程”，改用垂直堆叠的方式... 图表从左到右依次为四个层级"
            # 这听起来像是：
            # Column 1 | Column 2 | Column 3 | Column 4
            # Phase    | Tasks    | Subs     | Methods
            #          |  ↓       |          |
            #          | Task A   |-- Sub A  |
            #          |  ↓       |          |
            #          | Task B   |-- Sub B  |
            
            # 这是一个典型的 "Table-like" 或 "Matrix" 布局。
            # 用 rankdir=LR 实现：
            # Rank 1: Phase Label
            # Rank 2: Tasks
            # Rank 3: Subs
            # Rank 4: Methods
            
            # 问题：Task A -> Task B 需要是垂直箭头。
            # 在 rankdir=LR 中，同 Rank 的节点从上到下排列。
            # 我们可以用 subgraph cluster 来包裹它们，并让它们自然堆叠。
            # 显式的 A->B 箭头在 LR 模式下会变成 A 指向右边的 B（如果 B 在下一 Rank）或者 A 指向同 Rank 的 B（这会导致布局混乱）。
            
            # **关键 Trick**: 使用 `rankdir=TB`，但是强制 Cluster 从左到右排列？
            # 不，Graphviz 很难做到 Cluster 横排而内容竖排。
            
            # **回归 LR 方案**:
            # 让 Task A -> Task B 的箭头不可见 (`style=invis`) 或者用 `constraint=false` 加上 `dir=none` 仅仅为了定序？
            # 其实在 LR 模式下，如果 Task A 和 Task B 都在 Rank 2，它们会自动垂直排列。
            # 如果我们需要画箭头，可以用 `constraint=false`。
            
            # 隐藏所有与 method 相关的边（仅影响可视化，不影响布局）
            if src_type == "method" or tgt_type == "method":
                edge_attrs.update({"style": "invis", "arrowhead": "none", "constraint": "true"})
            # 仅允许 task -> sub_content 显示为虚线（column2 -> column3），其余任何涉及 sub_content 的边都设为不可见
            elif src_type == "task" and tgt_type == "sub_content":
                edge_attrs.update({"style": "dashed", "arrowhead": "none"})
            elif src_type == "sub_content" or tgt_type == "sub_content":
                edge_attrs.update({"style": "invis", "arrowhead": "none"})
            elif src_type == "task" and tgt_type == "task":
                # 垂直连接 (同 Rank)
                # 在 LR 模式下，这通常是不可见的排序约束，或者弯曲的箭头。
                # 为了强制垂直排列，我们可以在同一个 subgraph 中列出它们。
                edge_attrs.update({"style": "solid", "constraint": "false"}) 
                # 注意：在 LR 布局中画垂直箭头很难看，通常我们省略箭头，只靠位置。
                # 或者使用 HTML-like Label 表格？不，太复杂。
                # 让我们尝试 constraint=false，看看效果。
            
            elif src_type == "task" and tgt_type == "sub_content":
                # 向右展开 (跨 Rank: Task -> Sub)
                edge_attrs.update({"style": "dashed", "arrowhead": "none"})
            
            elif src_type == "sub_content" and tgt_type == "method":
                 # 向右 (跨 Rank: Sub -> Method) - 即使没有直接连线，布局上也应该在右边。
                 pass

        dot.edge(src_id, tgt_id, label=label, **edge_attrs)

    # 3. 强制列对齐 (The 4 Columns)
    # 我们收集每一列的节点，强制它们属于同一个 Rank。
    # 注意：Phase 节点可能不存在（作为 Cluster 标签），或者如果是节点的话：
    
    # 提取所有 Task
    all_tasks = [n["id"] for n in nodes if n["type"] == "task"]
    # 提取所有 Subs
    all_subs = [n["id"] for n in nodes if n["type"] == "sub_content"]
    # 提取所有 Methods
    all_methods = [n["id"] for n in nodes if n["type"] == "method"]
    
    # Phase Labels (如果存在)
    all_stages = [n["id"] for n in nodes if n["type"] == "stage_label"]

    # 强制 Rank
    if all_stages:
        with dot.subgraph(name="rank_stage") as r:
            r.attr(rank="same") # 并不是 same，因为 LR 布局下 rank 是列。
            # 等等，LR 布局下，rank="same" 意味着它们在同一列（垂直线）。
            # 这正是我们想要的！
            for nid in all_stages: r.node(nid)
    
    if all_tasks:
        with dot.subgraph(name="rank_task") as r:
            r.attr(rank="same")
            for nid in all_tasks: r.node(nid)
            
    if all_subs:
        with dot.subgraph(name="rank_sub") as r:
            r.attr(rank="same")
            for nid in all_subs: r.node(nid)
            
    if all_methods:
        with dot.subgraph(name="rank_method") as r:
            r.attr(rank="same")
            for nid in all_methods: r.node(nid)

    # 4. 强制列之间的顺序 (Phase -> Task -> Sub -> Method)
    # 选取每列的一个代表节点，建立 invisible edge
    # 假设每列至少有一个节点
    rep_stage = all_stages[0] if all_stages else None
    rep_task = all_tasks[0] if all_tasks else None
    rep_sub = all_subs[0] if all_subs else None
    rep_method = all_methods[0] if all_methods else None
    
    chain = [n for n in [rep_stage, rep_task, rep_sub, rep_method] if n]
    for i in range(len(chain) - 1):
        dot.edge(chain[i], chain[i+1], style="invis", weight="100")

    # 在主图上为第1列（stage）添加相邻箭头，按渲染顺序（stage_order）连接
    for i in range(len(stage_order) - 1):
        a = stage_order[i]
        b = stage_order[i + 1]
        if (a, b) not in existing_pairs:
            dot.edge(a, b, style="solid", arrowhead="normal")

    outfile = dot.render(filename=output_filename, format=output_format, cleanup=True)
    return outfile
