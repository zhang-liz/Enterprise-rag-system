"""Knowledge Graph implementation using Neo4j."""

import json
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from config import settings
from extraction import Entity, Relationship

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Knowledge graph for storing and querying entities and relationships."""

    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self._initialize_schema()

    def close(self):
        """Close database connection."""
        self.driver.close()

    def _initialize_schema(self):
        """Initialize graph schema with constraints and indexes."""
        with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
                "CREATE CONSTRAINT file_id IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception:
                    pass  # Constraint might already exist

            # Create indexes
            indexes = [
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX entity_modality IF NOT EXISTS FOR (e:Entity) ON (e.modality)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                except Exception:
                    pass

    def add_entity(self, entity: Entity) -> bool:
        """Add entity to knowledge graph."""
        with self.driver.session() as session:
            try:
                query = """
                MERGE (e:Entity {name: $name})
                SET e.type = $type,
                    e.description = $description,
                    e.confidence = $confidence
                MERGE (f:File {id: $file_id})
                MERGE (e)-[:EXTRACTED_FROM {modality: $modality}]->(f)
                """
                session.run(
                    query,
                    name=entity.name,
                    type=entity.type,
                    description=entity.description,
                    confidence=entity.confidence,
                    file_id=entity.source_file_id,
                    modality=entity.source_modality
                )
                return True
            except Exception as e:
                logger.exception("Failed to add entity: %s", entity.name)
                return False

    def add_relationship(self, relationship: Relationship) -> bool:
        """Add relationship between entities."""
        with self.driver.session() as session:
            try:
                query = """
                MERGE (e1:Entity {name: $source_entity})
                MERGE (e2:Entity {name: $target_entity})
                MERGE (e1)-[r:RELATES_TO {
                    type: $rel_type,
                    description: $description,
                    confidence: $confidence,
                    source_file: $file_id
                }]->(e2)
                """
                session.run(
                    query,
                    source_entity=relationship.source_entity,
                    target_entity=relationship.target_entity,
                    rel_type=relationship.relationship_type,
                    description=relationship.description,
                    confidence=relationship.confidence,
                    file_id=relationship.source_file_id
                )
                return True
            except Exception as e:
                logger.exception("Failed to add relationship: %s -> %s", relationship.source_entity, relationship.target_entity)
                return False

    def add_document(
        self,
        file_id: str,
        file_name: str,
        modality: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Add document node to graph."""
        with self.driver.session() as session:
            try:
                query = """
                MERGE (f:File {id: $file_id})
                SET f.name = $file_name,
                    f.modality = $modality,
                    f.metadata = $metadata
                """
                session.run(
                    query,
                    file_id=file_id,
                    file_name=file_name,
                    modality=modality,
                    metadata=json.dumps(metadata, default=str)
                )
                return True
            except Exception as e:
                logger.exception("Failed to add document: %s", file_id)
                return False

    def find_entity(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """Find entity by name."""
        with self.driver.session() as session:
            query = """
            MATCH (e:Entity {name: $name})
            OPTIONAL MATCH (e)-[:EXTRACTED_FROM]->(f:File)
            RETURN e, collect(f) as files
            """
            result = session.run(query, name=entity_name)
            record = result.single()

            if record:
                entity = dict(record["e"])
                files = [dict(f) for f in record["files"]]
                return {"entity": entity, "files": files}

            return None

    def find_related_entities(
        self,
        entity_name: str,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Find entities related to given entity up to max_depth."""
        with self.driver.session() as session:
            query = """
            MATCH path = (e:Entity {name: $name})-[:RELATES_TO*1..$max_depth]-(related:Entity)
            RETURN related, relationships(path) as rels
            """
            result = session.run(query, name=entity_name, max_depth=max_depth)

            related = []
            for record in result:
                entity = dict(record["related"])
                relationships = [dict(r) for r in record["rels"]]
                related.append({
                    "entity": entity,
                    "relationships": relationships
                })

            return related

    def search_entities_by_type(
        self,
        entity_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search entities by type."""
        with self.driver.session() as session:
            query = """
            MATCH (e:Entity {type: $entity_type})
            RETURN e
            LIMIT $limit
            """
            result = session.run(query, entity_type=entity_type, limit=limit)

            return [dict(record["e"]) for record in result]

    def keyword_search(
        self,
        keywords: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search entities by keywords in name or description."""
        with self.driver.session() as session:
            # Build keyword filter
            keyword_pattern = "|".join(keywords)

            query = """
            MATCH (e:Entity)
            WHERE e.name =~ $pattern OR e.description =~ $pattern
            OPTIONAL MATCH (e)-[r:RELATES_TO]-(related:Entity)
            RETURN e, collect(distinct related) as related_entities
            LIMIT $limit
            """
            result = session.run(
                query,
                pattern=f"(?i).*({keyword_pattern}).*",
                limit=limit
            )

            results = []
            for record in result:
                entity = dict(record["e"])
                related = [dict(r) for r in record["related_entities"] if r]
                results.append({
                    "entity": entity,
                    "related_entities": related
                })

            return results

    def traverse_graph(
        self,
        start_entity: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Traverse graph from a starting entity.

        Returns nodes and edges in the subgraph.
        """
        with self.driver.session() as session:
            if relationship_types:
                # Note: max_depth must be literal in variable-length path; relationship_types uses parameter
                query = f"""
                MATCH path = (start:Entity {{name: $start_entity}})-[r:RELATES_TO*1..{max_depth}]-(node:Entity)
                WHERE all(rel in relationships(path) WHERE rel.type IN $relationship_types)
                RETURN nodes(path) as nodes, relationships(path) as edges
                """
                result = session.run(
                    query,
                    start_entity=start_entity,
                    relationship_types=relationship_types
                )
            else:
                query = f"""
                MATCH path = (start:Entity {{name: $start_entity}})-[r:RELATES_TO*1..{max_depth}]-(node:Entity)
                RETURN nodes(path) as nodes, relationships(path) as edges
                """
                result = session.run(query, start_entity=start_entity)

            nodes = set()
            edges = []

            for record in result:
                for node in record["nodes"]:
                    nodes.add((node["name"], node["type"]))

                for edge in record["edges"]:
                    edge_props = dict(edge) if hasattr(edge, "keys") else {}
                    edges.append({
                        "source": edge.start_node["name"],
                        "target": edge.end_node["name"],
                        "type": edge_props.get("type", "RELATES_TO"),
                        "description": edge_props.get("description", "")
                    })

            return {
                "nodes": [{"name": n, "type": t} for n, t in nodes],
                "edges": edges
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        with self.driver.session() as session:
            stats = {}

            # Count entities
            result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            stats["num_entities"] = result.single()["count"]

            # Count relationships
            result = session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count")
            stats["num_relationships"] = result.single()["count"]

            # Count files
            result = session.run("MATCH (f:File) RETURN count(f) as count")
            stats["num_files"] = result.single()["count"]

            # Entity types distribution
            result = session.run("""
                MATCH (e:Entity)
                RETURN e.type as type, count(e) as count
                ORDER BY count DESC
            """)
            stats["entity_types"] = {record["type"]: record["count"] for record in result}

            return stats
