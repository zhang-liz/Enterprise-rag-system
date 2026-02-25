"""
Hybrid search orchestrator combining:
1. Graph traversal (structured knowledge)
2. Keyword filtering (exact matches)
3. Semantic vector retrieval (similarity search)

Sync Neo4j and Qdrant calls are run in a thread pool via asyncio.to_thread
so the event loop is not blocked.
"""

import asyncio
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from evaluation import QueryType
from graph import KnowledgeGraph
from vector_store import VectorDatabase


@dataclass
class SearchResult:
    """Unified search result."""
    content: str
    source: str  # "graph", "keyword", "vector"
    score: float
    metadata: Dict[str, Any]


class HybridSearchOrchestrator:
    """
    Orchestrates hybrid search across graph, keyword, and vector stores.

    This is the core retrieval engine that:
    1. Determines which search strategies to use based on query
    2. Executes searches in parallel where possible
    3. Merges and ranks results
    4. Returns top-k most relevant results
    """

    def __init__(
        self,
        knowledge_graph: KnowledgeGraph,
        vector_db: VectorDatabase
    ):
        self.kg = knowledge_graph
        self.vdb = vector_db

    async def search(
        self,
        query: str,
        query_type: QueryType = QueryType.FACTUAL_LOOKUP,
        top_k: int = 10,
        enable_graph: bool = True,
        enable_keyword: bool = True,
        enable_vector: bool = True
    ) -> List[SearchResult]:
        """
        Execute hybrid search.

        Args:
            query: User query
            query_type: Type of query (affects strategy)
            top_k: Number of results to return
            enable_graph: Enable graph search
            enable_keyword: Enable keyword search
            enable_vector: Enable vector search

        Returns:
            Ranked list of search results
        """
        results = []

        # Extract entities and keywords from query
        entities = self._extract_entities(query)
        keywords = self._extract_keywords(query)

        # 1. Graph Search (if entities found) - run sync KG calls in thread pool
        if enable_graph and entities:
            graph_results = await asyncio.to_thread(
                self._graph_search_sync, entities, query_type
            )
            results.extend(graph_results)

        # 2. Keyword Search - run sync KG calls in thread pool
        if enable_keyword and keywords:
            keyword_results = await asyncio.to_thread(
                self._keyword_search_sync, keywords
            )
            results.extend(keyword_results)

        # 3. Vector Semantic Search (always) - run sync Qdrant calls in thread pool
        if enable_vector:
            vector_results = await asyncio.to_thread(
                self._vector_search_sync, query, top_k
            )
            results.extend(vector_results)

        # Merge and rank results
        ranked_results = self._rank_results(results, query)

        return ranked_results[:top_k]

    def _graph_search_sync(
        self,
        entities: List[str],
        query_type: QueryType
    ) -> List[SearchResult]:
        """
        Sync implementation: search knowledge graph for entities and relationships.
        Called via asyncio.to_thread from _graph_search.
        """
        results = []

        for entity in entities:
            entity_info = self.kg.find_entity(entity)

            if entity_info:
                entity_data = entity_info["entity"]
                results.append(SearchResult(
                    content=f"Entity: {entity_data.get('name')} ({entity_data.get('type')})\n"
                            f"Description: {entity_data.get('description', 'N/A')}",
                    source="graph",
                    score=entity_data.get("confidence", 0.8),
                    metadata={
                        "entity_name": entity_data.get("name"),
                        "entity_type": entity_data.get("type"),
                        "source": "knowledge_graph"
                    }
                ))

                if query_type == QueryType.SEMANTIC_LINKAGE:
                    related = self.kg.find_related_entities(entity, max_depth=2)
                    for rel in related:
                        rel_entity = rel["entity"]
                        results.append(SearchResult(
                            content=f"Related Entity: {rel_entity.get('name')} ({rel_entity.get('type')})",
                            source="graph",
                            score=rel_entity.get("confidence", 0.7) * 0.9,
                            metadata={
                                "entity_name": rel_entity.get("name"),
                                "entity_type": rel_entity.get("type"),
                                "source": "knowledge_graph",
                                "relationship": "related_to",
                                "parent_entity": entity
                            }
                        ))

        return results

    def _keyword_search_sync(self, keywords: List[str]) -> List[SearchResult]:
        """
        Sync implementation: keyword-based search in knowledge graph.
        Called via asyncio.to_thread from _keyword_search.
        """
        results = []
        entities = self.kg.keyword_search(keywords, limit=10)

        for item in entities:
            entity = item["entity"]
            results.append(SearchResult(
                content=f"{entity.get('name')}: {entity.get('description', '')}",
                source="keyword",
                score=0.85,
                metadata={
                    "entity_name": entity.get("name"),
                    "entity_type": entity.get("type"),
                    "source": "keyword_search",
                    "matched_keywords": keywords
                }
            ))

        return results

    def _vector_search_sync(self, query: str, top_k: int) -> List[SearchResult]:
        """
        Sync implementation: semantic vector search.
        Called via asyncio.to_thread from _vector_search.
        """
        results = []
        vector_results = self.vdb.semantic_search(
            query=query,
            limit=top_k,
            score_threshold=0.7
        )

        for vr in vector_results:
            results.append(SearchResult(
                content=vr["text"],
                source="vector",
                score=vr["score"],
                metadata={
                    **vr["metadata"],
                    "source": "vector_search",
                    "id": vr["id"]
                }
            ))

        return results

    def _extract_entities(self, query: str) -> List[str]:
        """
        Extract potential entity names from query.

        Simple heuristic: capitalized words or quoted phrases.
        In production, use NER.
        """
        entities = []

        # Find quoted strings
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)

        # Find capitalized words (potential entity names)
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 1 and word not in ["What", "Who", "Where", "When", "Why", "How"]:
                entities.append(word)

        return list(set(entities))

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query.

        Remove stop words and keep meaningful terms.
        """
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "what", "who", "where", "when", "why", "how", "show", "find", "get"
        }

        # Simple tokenization
        words = re.findall(r'\b\w+\b', query.lower())

        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _rank_results(
        self,
        results: List[SearchResult],
        query: str
    ) -> List[SearchResult]:
        """
        Rank and deduplicate results.

        Ranking strategy:
        1. Vector results get highest weight (semantic similarity)
        2. Graph results get medium weight (structured knowledge)
        3. Keyword results get lower weight (exact matches)

        Then merge by score and deduplicate.
        """
        # Weight results by source
        source_weights = {
            "vector": 1.0,
            "graph": 0.9,
            "keyword": 0.8
        }

        # Apply weights
        for result in results:
            result.score *= source_weights.get(result.source, 0.7)

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)

        # Deduplicate by content similarity
        deduplicated = []
        seen_contents = set()

        for result in results:
            # Simple deduplication by content prefix
            content_key = result.content[:100].lower()
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                deduplicated.append(result)

        return deduplicated

    async def search_cross_modal(
        self,
        query: str,
        modalities: List[str],
        top_k: int = 10
    ) -> Dict[str, List[SearchResult]]:
        """
        Search across specific modalities.

        Example: Find "John Smith" in both text and video.
        """
        results_by_modality = {}

        for modality in modalities:
            vector_results = await asyncio.to_thread(
                self.vdb.search_by_modality,
                query=query,
                modality=modality,
                limit=top_k
            )

            modality_results = [
                SearchResult(
                    content=vr["text"],
                    source=f"vector_{modality}",
                    score=vr["score"],
                    metadata={
                        **vr["metadata"],
                        "modality": modality
                    }
                )
                for vr in vector_results
            ]

            results_by_modality[modality] = modality_results

        return results_by_modality
