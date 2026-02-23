"""Vector database implementation using Qdrant."""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from openai import OpenAI
from config import settings
import uuid


def _point_id(doc_or_chunk_id: str) -> str:
    """Generate a stable, Qdrant-compatible UUID from a string ID."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_or_chunk_id))


class VectorDatabase:
    """Vector database for semantic search using Qdrant."""

    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.collection_name = settings.qdrant_collection
        self._initialize_collection()

    def _initialize_collection(self):
        """Initialize Qdrant collection."""
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            # Create collection with text-embedding-3-small dimensions (1536)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1536,  # text-embedding-3-small dimension
                    distance=Distance.COSINE
                )
            )

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                model=settings.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Add document to vector database."""
        try:
            # Generate embedding
            embedding = self.generate_embedding(text)

            # Create point (UUID required by Qdrant for string IDs)
            point = PointStruct(
                id=_point_id(doc_id),
                vector=embedding,
                payload={
                    "doc_id": doc_id,
                    "text": text[:1000],  # Store truncated text
                    "full_text": text,
                    **metadata
                }
            )

            # Upsert point
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            return True

        except Exception as e:
            print(f"Failed to add document: {str(e)}")
            return False

    def add_chunks(
        self,
        file_id: str,
        chunks: List[str],
        metadata: Dict[str, Any]
    ) -> bool:
        """Add multiple chunks from a document."""
        try:
            points = []

            for idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                # Generate embedding
                embedding = self.generate_embedding(chunk)

                # Create unique ID for chunk (stable UUID for same file+index)
                chunk_id = f"{file_id}_chunk_{idx}"
                point_id = _point_id(chunk_id)

                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "chunk_id": chunk_id,
                        "file_id": file_id,
                        "chunk_index": idx,
                        "text": chunk,
                        **metadata
                    }
                )

                points.append(point)

            # Batch upsert
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )

            return True

        except Exception as e:
            print(f"Failed to add chunks: {str(e)}")
            return False

    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search.

        Args:
            query: Search query
            limit: Maximum number of results
            filters: Optional filters (e.g., {"modality": "text"})
            score_threshold: Minimum similarity score

        Returns:
            List of search results with text and metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)

            # Build filter if provided
            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=conditions)

            # Search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=query_filter,
                score_threshold=score_threshold
            )

            # Format results
            results = []
            for hit in search_results:
                results.append({
                    "id": hit.payload.get("chunk_id", hit.payload.get("doc_id")),
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "metadata": {
                        k: v for k, v in hit.payload.items()
                        if k not in ["text", "full_text", "chunk_id", "doc_id"]
                    }
                })

            return results

        except Exception as e:
            print(f"Semantic search failed: {str(e)}")
            return []

    def search_by_modality(
        self,
        query: str,
        modality: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search within a specific modality."""
        return self.semantic_search(
            query=query,
            limit=limit,
            filters={"modality": modality}
        )

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID."""
        try:
            point_id = _point_id(doc_id)
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )

            if result:
                return result[0].payload

            return None

        except Exception as e:
            print(f"Failed to retrieve document: {str(e)}")
            return None

    def delete_document(self, doc_id: str) -> bool:
        """Delete document from vector database."""
        try:
            point_id = _point_id(doc_id)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
            return True

        except Exception as e:
            print(f"Failed to delete document: {str(e)}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get vector database statistics."""
        try:
            collection_info = self.client.get_collection(self.collection_name)

            return {
                "num_vectors": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance.value
            }

        except Exception as e:
            print(f"Failed to get statistics: {str(e)}")
            return {}
