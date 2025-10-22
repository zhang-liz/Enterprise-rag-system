"""
Example usage of the Enterprise RAG system programmatically.

This demonstrates how to use the system without the web UI.
"""

import asyncio
from pathlib import Path

from graph import KnowledgeGraph
from vector_store import VectorDatabase
from search import HybridSearchOrchestrator
from pipeline import QueryProcessor, QueryRequest
from ingestion import TextProcessor
from extraction import EntityExtractor


async def main():
    """Example workflow."""

    print("🚀 Initializing Enterprise RAG System...")

    # Initialize components
    kg = KnowledgeGraph()
    vdb = VectorDatabase()
    search = HybridSearchOrchestrator(kg, vdb)
    processor = QueryProcessor(search)
    entity_extractor = EntityExtractor()

    # Example 1: Process a document
    print("\n📄 Example 1: Processing a document")
    print("-" * 50)

    # Create sample document
    sample_doc = Path("data/uploads/sample.txt")
    sample_doc.parent.mkdir(parents=True, exist_ok=True)
    sample_doc.write_text("""
    John Smith is the CEO of Acme Corporation. The company reported
    strong revenue growth in Q4 2024, reaching $10 million.
    The main product, Widget Pro, was mentioned as a key driver of growth.
    The company is headquartered in San Francisco.
    """)

    # Process document
    text_processor = TextProcessor()
    processed = await text_processor.process(sample_doc)

    print(f"✅ Processed: {processed.content_type}")
    print(f"   Chunks: {len(processed.chunks)}")

    # Extract entities
    entities, relationships = await entity_extractor.extract(
        text=processed.text,
        file_id=processed.file_id,
        modality="text"
    )

    print(f"   Entities: {len(entities)}")
    print(f"   Relationships: {len(relationships)}")

    # Add to knowledge graph
    for entity in entities:
        kg.add_entity(entity)
    for rel in relationships:
        kg.add_relationship(rel)

    print("   ✅ Added to knowledge graph")

    # Add to vector database
    vdb.add_chunks(
        file_id=processed.file_id,
        chunks=processed.chunks,
        metadata={"file_name": "sample.txt", "modality": "text"}
    )

    print("   ✅ Added to vector database")

    # Example 2: Query the system
    print("\n❓ Example 2: Querying the system")
    print("-" * 50)

    queries = [
        "What is the revenue mentioned?",
        "Who is the CEO of Acme Corporation?",
        "What products are mentioned?",
        "Where is the company located?"
    ]

    for query_text in queries:
        print(f"\n🔍 Query: {query_text}")

        request = QueryRequest(query=query_text)
        answer = await processor.process(request)

        print(f"   Answer: {answer.answer}")
        print(f"   Confidence: {answer.confidence:.2f}")
        print(f"   Sources: {len(answer.sources)}")

        if answer.warning:
            print(f"   ⚠️  Warning: {answer.warning}")

    # Example 3: Explore knowledge graph
    print("\n🕸️  Example 3: Knowledge graph exploration")
    print("-" * 50)

    # Find entity
    entity_info = kg.find_entity("Acme Corporation")
    if entity_info:
        print("✅ Found entity: Acme Corporation")
        print(f"   Type: {entity_info['entity'].get('type')}")

        # Find related entities
        related = kg.find_related_entities("Acme Corporation", max_depth=2)
        print(f"   Related entities: {len(related)}")
        for rel in related[:3]:  # Show first 3
            print(f"      - {rel['entity'].get('name')}")

    # Example 4: Statistics
    print("\n📊 Example 4: System statistics")
    print("-" * 50)

    graph_stats = kg.get_statistics()
    vector_stats = vdb.get_statistics()

    print("Knowledge Graph:")
    print(f"   Entities: {graph_stats.get('num_entities', 0)}")
    print(f"   Relationships: {graph_stats.get('num_relationships', 0)}")
    print(f"   Files: {graph_stats.get('num_files', 0)}")

    print("\nVector Database:")
    print(f"   Vectors: {vector_stats.get('num_vectors', 0)}")
    print(f"   Dimension: {vector_stats.get('vector_size', 0)}")

    print("\n✅ Example completed successfully!")

    # Cleanup
    kg.close()


if __name__ == "__main__":
    asyncio.run(main())
