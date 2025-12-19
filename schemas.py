# -*- coding: utf-8 -*-
"""
数据模型模块（Pydantic）：定义技术路线图的结构化 Schema。
支持对象化的 clusters 以及左/中/右三类节点。
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, validator


class NodeType(str, Enum):
    # 节点类型：左侧阶段标题、核心任务、具体细分内容、方法（兼容旧的 phase）
    stage_label = "stage_label"
    task = "task"
    sub_content = "sub_content"
    method = "method"
    phase = "phase"


class ClusterItem(BaseModel):
    # 阶段（行）对象：用于在图中形成一个横向区域
    id: str
    label: str

    @validator("id", "label")
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("cluster 字段不能为空")
        return v.strip()


class NodeItem(BaseModel):
    # 节点：包含标识、标签、类型、所属阶段
    id: str
    label: str
    type: NodeType
    parent_cluster: str

    @validator("id")
    def id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Node id 不能为空")
        return v.strip()

    @validator("label")
    def label_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Node label 不能为空")
        return v.strip()

    @validator("parent_cluster")
    def cluster_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("parent_cluster 不能为空")
        return v.strip()


class EdgeItem(BaseModel):
    # 边：连接两个节点，可选标签
    source: str
    target: str
    label: Optional[str] = ""

    @validator("source", "target")
    def endpoint_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Edge 端点不能为空")
        return v.strip()


class Roadmap(BaseModel):
    # 技术路线图整体数据
    title: str
    clusters: List[ClusterItem]
    nodes: List[NodeItem]
    edges: List[EdgeItem]

    @validator("title")
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title 不能为空")
        return v.strip()

    @validator("clusters")
    def clusters_non_empty(cls, v: List[ClusterItem]) -> List[ClusterItem]:
        if not v:
            raise ValueError("clusters 不能为空")
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            raise ValueError("clusters id 不唯一")
        return v

    @validator("nodes")
    def nodes_non_empty(cls, v: List[NodeItem]) -> List[NodeItem]:
        if not v:
            raise ValueError("nodes 不能为空")
        return v

    @validator("edges")
    def edges_non_empty(cls, v: List[EdgeItem]) -> List[EdgeItem]:
        # 边可以为空（仅展示结构时）
        return v or []

    def ensure_consistency(self) -> None:
        # 一致性校验：id 唯一、边端点存在、cluster 声明
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("节点 id 不唯一")
        id_set = set(ids)
        for e in self.edges:
            if e.source not in id_set or e.target not in id_set:
                raise ValueError(f"边指向不存在的节点: {e.source} -> {e.target}")
        cluster_ids = {c.id for c in self.clusters}
        for n in self.nodes:
            if n.parent_cluster not in cluster_ids:
                raise ValueError(f"节点所属 cluster 未声明: {n.parent_cluster}")
