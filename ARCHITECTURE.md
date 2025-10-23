# Enterprise RAG System - Architecture Documentation

## Overview

This document describes the architecture of the Enterprise RAG system, designed with modularity, scalability, and evaluation-first principles.

## Design Principles

### 1. Evaluation-First
- Success criteria defined before implementation
- Comprehensive test suite for all query types
- Metrics tracked for every query
- Graceful failure scenarios documented

### 2. Modularity
- Clean separation of concerns
- Independent, testable components
- Easy to extend with new modalities or search strategies
- Dependency injection for flexibility

### 3. Enterprise-Grade
- Robust error handling
- Input validation at all entry points
- Source citation and confidence scoring
- Audit trail and logging

## System Components

### 1. Ingestion Pipeline

**Location**: `ingestion/`

**Purpose**: Process multimodal documents into searchable format

**Components**:
- `BaseProcessor`: Abstract base class for all processors
- `TextProcessor`: PDF and TXT files
- `ImageProcessor`: JPG, PNG with OCR (Tesseract) and captioning (GPT-4V)
- `AudioProcessor`: MP3, WAV transcription (Whisper)
- `VideoProcessor`: MP4, AVI frame extraction and audio transcription

**Flow**:
```
File Upload → Validation → Processing → Text Extraction → Chunking → Output
```

**Key Features**:
- Modality-specific processing logic
- Metadata enrichment
- Configurable chunking (size, overlap)
- Error handling with partial results

### 2. Entity Extraction

**Location**: `extraction/`

**Purpose**: Extract structured entities and relationships using LLMs

**Components**:
- `EntityExtractor`: Main extraction logic
- `Entity`: Entity model (name, type, source, confidence)
- `Relationship`: Relationship model (source, target, type, confidence)

**Flow**:
```
Text → LLM Prompt → JSON Response → Parse → Entity/Relationship Objects
```

**Entity Types**:
- PERSON
- ORGANIZATION
- LOCATION
- PRODUCT
- CONCEPT

**Relationship Types**:
- WORKS_FOR
- LOCATED_IN
- MENTIONED_IN
- RELATED_TO

**Cross-Modal Linking**:
- Links same entity across different files/modalities
- Example: "John Smith" in PDF + video transcript = same entity

### 3. Knowledge Graph

**Location**: `graph/`

**Purpose**: Store and query structured knowledge

**Technology**: Neo4j

**Schema**:
```
(Entity)-[:RELATES_TO]->(Entity)
(Entity)-[:EXTRACTED_FROM]->(File)
(File {id, name, modality})
```

**Capabilities**:
- Entity lookup by name or type
- Relationship traversal (configurable depth)
- Keyword search in entity names/descriptions
- Graph statistics

**Query Patterns**:
- Direct entity lookup: `MATCH (e:Entity {name: "John Smith"})`
- Relationship traversal: `MATCH path = (e)-[:RELATES_TO*1..3]-(related)`
- Keyword search: `MATCH (e:Entity) WHERE e.name =~ "(?i).*keyword.*"`

### 4. Vector Database

**Location**: `vector_store/`

**Purpose**: Semantic similarity search

**Technology**: Qdrant

**Configuration**:
- Vector size: 1536 (text-embedding-3-small)
- Distance metric: Cosine similarity
- Score threshold: 0.7 (configurable)

**Capabilities**:
- Chunk-level embeddings
- Metadata filtering (modality, file type, etc.)
- Semantic search with score thresholding
- Batch operations

**Storage Strategy**:
- Each chunk gets unique ID: `{file_id}_chunk_{index}`
- Metadata includes: file_name, modality, chunk_index, file_id
- Full text stored in payload for context retrieval

### 5. Hybrid Search Orchestrator

**Location**: `search/`

**Purpose**: Combine multiple search strategies

**Search Strategies**:

#### a) Graph Search
- **When**: Entities detected in query
- **How**: Look up entity in graph, traverse relationships
- **Best for**: Semantic linkage, relationship queries
- **Example**: "Who works for Acme Corp?"

#### b) Keyword Search
- **When**: Specific terms identified
- **How**: Pattern matching in graph nodes
- **Best for**: Exact matches, filtering
- **Example**: "Documents mentioning 'Q4 revenue'"

#### c) Vector Search
- **When**: Always (fallback)
- **How**: Semantic similarity via embeddings
- **Best for**: Natural language, fuzzy matching
- **Example**: "Tell me about the company's performance"

**Ranking Algorithm**:
```python
# Weight by source
vector_results: weight = 1.0
graph_results: weight = 0.9
keyword_results: weight = 0.8

# Sort by weighted score
# Deduplicate by content similarity
```

**Cross-Modal Search**:
- Filter by modality during vector search
- Example: Find "John Smith" in both text AND video

### 6. Query Processing Pipeline

**Location**: `pipeline/`

**Purpose**: End-to-end query processing

**Stages**:

#### 1. Input Validation
- Length checks (3-1000 chars)
- Sanitization
- Format validation

#### 2. Query Triage
- Classify query type (FACTUAL_LOOKUP, SUMMARIZATION, etc.)
- Identify entities and keywords
- Determine search strategies needed
- Uses GPT-4 for classification

**Example**:
```
Query: "What products did John mention in the video?"
→ Type: SEMANTIC_LINKAGE
→ Entities: ["John", "products"]
→ Modalities: ["video", "text"]
→ Needs: graph=True, vector=True, keyword=False
```

#### 3. Query Rewriting
- Optimize for better retrieval
- Expand abbreviations
- Add context

#### 4. Hybrid Search Execution
- Parallel execution of enabled strategies
- Result aggregation

#### 5. Answer Generation
- Context-based generation (GPT-4)
- Source citation enforcement
- Confidence calculation

#### 6. Post-Processing
- Add metadata
- Calculate confidence
- Detect warnings (low confidence, insufficient context)

#### 7. Evaluation
- Track metrics (if enabled)
- Log for analysis

### 7. Evaluation Framework

**Location**: `evaluation/`

**Purpose**: Define and track success criteria

**Components**:

#### Metrics
- **Retrieval Quality**: Precision, recall, relevance
- **Answer Quality**: Correctness, completeness, hallucination score
- **Performance**: Latency (retrieval, generation, total)
- **Cross-Modal**: Consistency across modalities

#### Query Types
- FACTUAL_LOOKUP
- SUMMARIZATION
- SEMANTIC_LINKAGE
- REASONING
- EXPLORATORY

#### Test Suite
- Minimal test cases covering all query types
- Expected entities, relationships, modalities
- Ground truth answers

#### Thresholds
- Min context relevance: 0.7
- Min answer correctness: 0.8
- Min hallucination score: 0.9
- Max latency: 5000ms

#### Failure Scenarios
- No relevant context → Return low confidence + explanation
- Ambiguous query → Request clarification
- Conflicting information → Present both sources
- Missing modality → Search available, note missing
- Timeout → Return partial results

### 8. Web Application

**Location**: `app.py`

**Technology**: FastAPI

**Endpoints**:
- `POST /upload`: Upload and process documents
- `POST /query`: Query and get answer
- `GET /stats`: System statistics
- `GET /health`: Health check
- `GET /`: Web UI

**UI Features**:
- Drag-and-drop file upload
- Real-time query processing
- Answer display with sources
- Confidence visualization
- System statistics dashboard

## Data Flow

### Document Ingestion Flow
```
1. User uploads file
2. File saved to disk
3. Processor selected based on file type
4. Content extracted and chunked
5. Entities/relationships extracted (LLM)
6. Added to knowledge graph (Neo4j)
7. Chunks embedded and stored (Qdrant)
8. Return success with statistics
```

### Query Processing Flow
```
1. User submits query
2. Input validation
3. Query triage (classify type, identify entities)
4. Query rewriting (optimization)
5. Hybrid search execution (parallel):
   - Graph search (if entities found)
   - Keyword search (if keywords found)
   - Vector search (always)
6. Result ranking and deduplication
7. Answer generation (LLM with context)
8. Post-processing (confidence, warnings)
9. Evaluation (if enabled)
10. Return answer with metadata
```

## Technology Stack

### Core
- **Python 3.13**: Main language
- **FastAPI**: Web framework
- **Pydantic**: Data validation

### AI/ML
- **OpenAI GPT-4**: LLM for extraction and generation
- **OpenAI text-embedding-3-small**: Embeddings
- **Whisper**: Audio transcription
- **Tesseract**: OCR

### Databases
- **Neo4j 5.13**: Knowledge graph
- **Qdrant**: Vector database

### Processing
- **PyPDF2**: PDF processing
- **Pillow**: Image processing
- **OpenCV**: Video frame extraction
- **MoviePy**: Video processing

### Testing
- **Pytest**: Testing framework
- **DeepEval**: Evaluation framework

## Scalability Considerations

### Horizontal Scaling
- **Application**: Stateless, can run multiple instances behind load balancer
- **Neo4j**: Cluster mode for high availability
- **Qdrant**: Cluster mode for distributed vectors

### Performance Optimization
- **Caching**: Cache embeddings, common queries
- **Batch Processing**: Process multiple documents in parallel
- **Async Operations**: All I/O operations are async
- **Connection Pooling**: Reuse database connections

### Resource Management
- **Memory**: Chunk processing to avoid loading large files
- **CPU**: Parallel processing where possible
- **GPU**: Can be added for faster embedding generation

## Security Considerations

### Input Validation
- File type validation
- File size limits
- Query length limits
- Sanitization of user inputs

### Access Control
- API key authentication (future)
- User-level isolation (future)
- Rate limiting (future)

### Data Privacy
- No sensitive data logged
- Temporary file cleanup
- Secure connections to databases

## Monitoring and Observability

### Logging
- Application logs in `logs/`
- Structured logging with timestamps
- Error tracking and stack traces

### Metrics (Future)
- Query latency histogram
- Success/failure rates
- Entity extraction accuracy
- Embedding generation time

### Alerts (Future)
- High error rates
- Slow queries (> threshold)
- Database connection issues

## Future Enhancements

### Planned Features
1. **Scene Detection**: Video scene boundary detection
2. **Sentiment Analysis**: Text/audio sentiment
3. **Topic Reranking**: Rerank by topic relevance
4. **Real-Time Feedback**: User feedback loop
5. **Access Control**: User roles and permissions

### Optimization Opportunities
1. **Embedding Cache**: Cache embeddings for common queries
2. **Query Cache**: Cache answers for exact queries
3. **Async Background Processing**: Queue-based ingestion
4. **Streaming Responses**: Stream answers as they generate

## Deployment

### Development
```bash
docker-compose up -d  # Start Neo4j and Qdrant
python app.py         # Run application
```

### Production
```bash
docker-compose up -d  # All services including app
```

### Environment Variables
See `.env.example` for required configuration.

## Conclusion

This architecture provides a solid foundation for an enterprise RAG system with:
- Modular, extensible design
- Multiple search strategies
- Comprehensive evaluation
- Production-ready error handling
- Clear separation of concerns

The system is designed to be maintainable, scalable, and performant while maintaining high answer quality and low hallucination rates.
