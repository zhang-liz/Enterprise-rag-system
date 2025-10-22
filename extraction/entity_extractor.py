"""Entity and relationship extraction using LLMs."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI
import json
from config import settings


class Entity(BaseModel):
    """Extracted entity."""
    name: str
    type: str  # PERSON, ORGANIZATION, LOCATION, CONCEPT, PRODUCT, etc.
    description: str = ""
    source_file_id: str
    source_modality: str
    confidence: float = Field(ge=0.0, le=1.0)


class Relationship(BaseModel):
    """Extracted relationship between entities."""
    source_entity: str
    target_entity: str
    relationship_type: str  # WORKS_FOR, LOCATED_IN, MENTIONED_IN, etc.
    description: str = ""
    source_file_id: str
    confidence: float = Field(ge=0.0, le=1.0)


class EntityExtractor:
    """Extract entities and relationships from processed content."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def extract(
        self,
        text: str,
        file_id: str,
        modality: str,
        context: Dict[str, Any] = None
    ) -> tuple[List[Entity], List[Relationship]]:
        """
        Extract entities and relationships from text using LLM.

        Args:
            text: Text to analyze
            file_id: Source file identifier
            modality: Source modality (text, image, audio, video)
            context: Additional context for extraction

        Returns:
            Tuple of (entities, relationships)
        """
        # Prepare prompt
        prompt = self._build_extraction_prompt(text, modality, context)

        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured information from text. Extract entities and relationships in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            # Parse response
            result = json.loads(response.choices[0].message.content)

            # Convert to models
            entities = self._parse_entities(result.get("entities", []), file_id, modality)
            relationships = self._parse_relationships(result.get("relationships", []), file_id)

            return entities, relationships

        except Exception as e:
            print(f"Entity extraction failed: {str(e)}")
            return [], []

    def _build_extraction_prompt(
        self,
        text: str,
        modality: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Build extraction prompt."""
        prompt = f"""Extract entities and relationships from the following {modality} content.

Content:
{text[:2000]}  # Limit to 2000 chars for API limits

Instructions:
1. Identify all named entities (people, organizations, locations, products, concepts)
2. Identify relationships between entities
3. Return ONLY valid JSON in this exact format:
{{
    "entities": [
        {{
            "name": "entity name",
            "type": "PERSON|ORGANIZATION|LOCATION|PRODUCT|CONCEPT",
            "description": "brief description",
            "confidence": 0.9
        }}
    ],
    "relationships": [
        {{
            "source_entity": "entity 1",
            "target_entity": "entity 2",
            "relationship_type": "WORKS_FOR|LOCATED_IN|MENTIONED_IN|RELATED_TO",
            "description": "relationship description",
            "confidence": 0.85
        }}
    ]
}}

Focus on:
- Named entities that appear multiple times
- Clear, explicit relationships
- Domain-specific terminology
- Cross-references to other entities
"""

        if context:
            prompt += f"\n\nAdditional Context: {json.dumps(context)}"

        return prompt

    def _parse_entities(
        self,
        raw_entities: List[Dict],
        file_id: str,
        modality: str
    ) -> List[Entity]:
        """Parse raw entity data into Entity models."""
        entities = []
        for e in raw_entities:
            try:
                entity = Entity(
                    name=e.get("name", ""),
                    type=e.get("type", "CONCEPT"),
                    description=e.get("description", ""),
                    source_file_id=file_id,
                    source_modality=modality,
                    confidence=e.get("confidence", 0.8)
                )
                entities.append(entity)
            except Exception as ex:
                print(f"Failed to parse entity: {ex}")

        return entities

    def _parse_relationships(
        self,
        raw_relationships: List[Dict],
        file_id: str
    ) -> List[Relationship]:
        """Parse raw relationship data into Relationship models."""
        relationships = []
        for r in raw_relationships:
            try:
                rel = Relationship(
                    source_entity=r.get("source_entity", ""),
                    target_entity=r.get("target_entity", ""),
                    relationship_type=r.get("relationship_type", "RELATED_TO"),
                    description=r.get("description", ""),
                    source_file_id=file_id,
                    confidence=r.get("confidence", 0.8)
                )
                relationships.append(rel)
            except Exception as ex:
                print(f"Failed to parse relationship: {ex}")

        return relationships

    async def link_cross_modal_entities(
        self,
        entities_by_file: Dict[str, List[Entity]]
    ) -> List[Dict[str, Any]]:
        """
        Link entities that appear across multiple modalities.

        This is crucial for enterprise RAG - linking "John Smith" in PDF
        to "John Smith" in video transcript.
        """
        entity_groups = {}

        # Group entities by name (case-insensitive)
        for file_id, entities in entities_by_file.items():
            for entity in entities:
                key = entity.name.lower()
                if key not in entity_groups:
                    entity_groups[key] = []
                entity_groups[key].append(entity)

        # Create cross-modal links
        cross_modal_links = []
        for entity_name, entities in entity_groups.items():
            if len(entities) > 1:
                # Entity appears in multiple files/modalities
                modalities = set(e.source_modality for e in entities)
                if len(modalities) > 1:
                    cross_modal_links.append({
                        "entity_name": entities[0].name,
                        "entity_type": entities[0].type,
                        "appears_in": [
                            {
                                "file_id": e.source_file_id,
                                "modality": e.source_modality,
                                "confidence": e.confidence
                            }
                            for e in entities
                        ],
                        "modalities": list(modalities)
                    })

        return cross_modal_links
