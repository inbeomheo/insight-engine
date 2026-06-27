"""
지식 그래프 저장소 — networkx 인메모리 그래프 + JSON 파일 영속화
사용자별 그래프를 관리하고 BFS 기반 관련 노드 탐색 제공
"""
import json
import logging
import os
from collections import deque
from typing import Any

import networkx as nx

from utils.runtime_paths import app_data_path

logger = logging.getLogger(__name__)

# 기본 그래프 저장 경로
_DEFAULT_STORE_PATH = app_data_path("graph_store")


class GraphStore:
    """사용자별 지식 그래프를 관리하는 저장소.

    - 인메모리: networkx DiGraph (방향 있는 그래프)
    - 영속화: JSON 파일 (사용자별 1개 파일)
    """

    def __init__(self, store_path: str = _DEFAULT_STORE_PATH):
        self._store_path = store_path
        os.makedirs(store_path, exist_ok=True)
        # 사용자별 그래프 캐시: {user_id: nx.DiGraph}
        self._graphs: dict[str, nx.DiGraph] = {}

    def _graph_file(self, user_id: str) -> str:
        """사용자 그래프 파일 경로를 반환합니다."""
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return os.path.join(self._store_path, f"{safe_id}.json")

    def _load_graph(self, user_id: str) -> nx.DiGraph:
        """파일에서 그래프를 로드합니다 (캐시 우선)."""
        if user_id in self._graphs:
            return self._graphs[user_id]

        g = nx.DiGraph()
        fpath = self._graph_file(user_id)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 노드 복원
                for node_data in data.get("nodes", []):
                    name = node_data.pop("name")
                    g.add_node(name, **node_data)
                # 엣지 복원
                for edge_data in data.get("edges", []):
                    source = edge_data.pop("source")
                    target = edge_data.pop("target")
                    g.add_edge(source, target, **edge_data)
                logger.info(f"그래프 로드: user={user_id}, 노드={g.number_of_nodes()}, 엣지={g.number_of_edges()}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"그래프 파일 손상, 초기화: {e}")
                g = nx.DiGraph()

        self._graphs[user_id] = g
        return g

    def _save_graph(self, user_id: str) -> None:
        """현재 그래프를 파일에 저장합니다."""
        g = self._graphs.get(user_id)
        if g is None:
            return

        nodes = [{"name": n, **attrs} for n, attrs in g.nodes(data=True)]
        edges = [{"source": u, "target": v, **attrs} for u, v, attrs in g.edges(data=True)]

        fpath = self._graph_file(user_id)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump({"nodes": nodes, "edges": edges}, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"그래프 저장 실패: {e}")

    def add_entities(self, user_id: str, entities: list[dict]) -> None:
        """엔티티 목록을 그래프에 추가합니다. 중복 노드는 속성을 갱신합니다.

        Args:
            user_id: 사용자 ID
            entities: [{"name": str, "type": str, "description": str}, ...]
        """
        g = self._load_graph(user_id)
        for ent in entities:
            name = ent.get("name", "").strip()
            if not name:
                continue
            if g.has_node(name):
                # 기존 노드 속성 갱신 (description이 비어있지 않을 때만)
                if ent.get("description"):
                    g.nodes[name]["description"] = ent["description"]
            else:
                g.add_node(name, type=ent.get("type", "concept"), description=ent.get("description", ""))
        self._save_graph(user_id)

    def add_relations(self, user_id: str, relations: list[dict]) -> None:
        """관계 목록을 그래프에 추가합니다. 노드가 없으면 자동 생성합니다.

        Args:
            user_id: 사용자 ID
            relations: [{"source": str, "target": str, "relation": str, "weight": float}, ...]
        """
        g = self._load_graph(user_id)
        for rel in relations:
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            if not source or not target:
                continue
            # 노드가 없으면 concept 타입으로 자동 생성
            if not g.has_node(source):
                g.add_node(source, type="concept", description="")
            if not g.has_node(target):
                g.add_node(target, type="concept", description="")
            g.add_edge(source, target, relation=rel.get("relation", "관련"), weight=rel.get("weight", 0.5))
        self._save_graph(user_id)

    def search_related(
        self,
        user_id: str,
        query_entities: list[str],
        max_depth: int = 2,
        max_results: int = 20,
    ) -> list[dict]:
        """BFS로 관련 노드를 탐색하여 반환합니다.

        Args:
            user_id: 사용자 ID
            query_entities: 탐색 시작 엔티티명 목록
            max_depth: 최대 탐색 깊이 (기본 2)
            max_results: 최대 반환 노드 수

        Returns:
            [{"name": str, "type": str, "description": str, "depth": int, "relations": [...]}]
        """
        g = self._load_graph(user_id)
        if g.number_of_nodes() == 0:
            return []

        visited: dict[str, int] = {}  # name -> depth
        queue: deque[tuple[str, int]] = deque()

        # 시작 노드 설정 (그래프에 존재하는 것만)
        for ent_name in query_entities:
            # 정확 매칭 먼저, 없으면 부분 매칭
            if g.has_node(ent_name):
                if ent_name not in visited:
                    visited[ent_name] = 0
                    queue.append((ent_name, 0))
            else:
                # 대소문자 무시 부분 매칭
                lower_name = ent_name.lower()
                for node in g.nodes():
                    if lower_name in node.lower() and node not in visited:
                        visited[node] = 0
                        queue.append((node, 0))
                        break

        results = []
        while queue and len(results) < max_results:
            node_name, depth = queue.popleft()
            attrs = g.nodes[node_name]

            # 이 노드와 연결된 관계 정보 수집
            relations_info = []
            for neighbor in g.successors(node_name):
                edge_data = g.edges[node_name, neighbor]
                relations_info.append({
                    "target": neighbor,
                    "relation": edge_data.get("relation", "관련"),
                    "direction": "outgoing",
                })
            for predecessor in g.predecessors(node_name):
                edge_data = g.edges[predecessor, node_name]
                relations_info.append({
                    "source": predecessor,
                    "relation": edge_data.get("relation", "관련"),
                    "direction": "incoming",
                })

            results.append({
                "name": node_name,
                "type": attrs.get("type", "concept"),
                "description": attrs.get("description", ""),
                "depth": depth,
                "relations": relations_info,
            })

            # 인접 노드를 큐에 추가
            if depth < max_depth:
                for neighbor in list(g.successors(node_name)) + list(g.predecessors(node_name)):
                    if neighbor not in visited:
                        visited[neighbor] = depth + 1
                        queue.append((neighbor, depth + 1))

        return results

    def get_subgraph(self, user_id: str, entity: str) -> dict[str, Any]:
        """특정 엔티티의 1-hop 이웃 서브그래프를 반환합니다.

        Args:
            user_id: 사용자 ID
            entity: 중심 엔티티명

        Returns:
            {"center": str, "nodes": [...], "edges": [...]}
        """
        g = self._load_graph(user_id)
        if not g.has_node(entity):
            return {"center": entity, "nodes": [], "edges": []}

        # 1-hop 이웃 (in + out)
        neighbors = set(g.successors(entity)) | set(g.predecessors(entity))
        neighbors.add(entity)

        nodes = []
        for n in neighbors:
            attrs = g.nodes[n]
            nodes.append({
                "name": n,
                "type": attrs.get("type", "concept"),
                "description": attrs.get("description", ""),
                "is_center": n == entity,
            })

        edges = []
        for u, v, attrs in g.edges(data=True):
            if u in neighbors and v in neighbors:
                edges.append({
                    "source": u,
                    "target": v,
                    "relation": attrs.get("relation", "관련"),
                    "weight": attrs.get("weight", 0.5),
                })

        return {"center": entity, "nodes": nodes, "edges": edges}

    def get_stats(self, user_id: str) -> dict[str, int]:
        """그래프 통계를 반환합니다."""
        g = self._load_graph(user_id)
        return {
            "node_count": g.number_of_nodes(),
            "edge_count": g.number_of_edges(),
        }

    def clear(self, user_id: str) -> None:
        """사용자 그래프를 초기화합니다."""
        self._graphs[user_id] = nx.DiGraph()
        fpath = self._graph_file(user_id)
        if os.path.exists(fpath):
            os.remove(fpath)
        logger.info(f"그래프 초기화: user={user_id}")


# 싱글턴 인스턴스
_store_path = os.environ.get("GRAPH_STORE_PATH") or _DEFAULT_STORE_PATH
graph_store = GraphStore(store_path=_store_path)
