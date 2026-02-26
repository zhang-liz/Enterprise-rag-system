# Enterprise RAG System

A production-grade, multimodal Retrieval-Augmented Generation (RAG) system with knowledge graph integration, built with an **evaluation-first** approach.

## Features

### Core Capabilities
- **Multimodal Ingestion**: Support for text (PDF, TXT), images (JPG, PNG), audio (MP3, WAV), and video (MP4, AVI, MOV)
- **Knowledge Graph**: Neo4j-based graph for structured entity and relationship storage
- **Vector Database**: Qdrant for semantic similarity search
- **Hybrid Search**: Combines graph traversal, keyword filtering, and vector retrieval
- **Evaluation Framework**: Built-in metrics and test suites (DeepEval compatible)
- **Query Processing**: Intelligent query triage, rewriting, and answer generation
- **Web UI**: Simple, intuitive interface for document upload and querying

### Enterprise Features
- **Evaluation-First Design**: Success criteria defined before implementation
- **Modular Architecture**: Clean separation of concerns, easy to extend
- **Graceful Failure Handling**: Comprehensive error handling and fallback strategies
- **Cross-Modal Entity Linking**: Link entities across different modalities
- **Source Citation**: All answers cite their sources
- **Confidence Scoring**: Answers include confidence levels
- **Input Validation**: Robust validation at all entry points

## Architecture

```
┌─────────────────┐
│   Web UI        │
│   (FastAPI)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      Query Processor                │
│  (Triage → Rewrite → Generate)      │
└────────┬───────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Hybrid Search Orchestrator        │
│  ┌──────────┬──────────┬─────────┐  │
│  │  Graph   │ Keyword  │ Vector  │  │
│  │  Search  │ Search   │ Search  │  │
│  └──────────┴──────────┴─────────┘  │
└────────┬───────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌──────┐  ┌──────┐
│Neo4j │  │Qdrant│
└──────┘  └──────┘
```

## Installation

### Prerequisites
- Python 3.13
- Docker and Docker Compose (for Neo4j and Qdrant)
- OpenAI API key

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Enterprise-rag-system
   ```

2. **Install dependencies** (local development only)
   > Skip this step if you plan to run the FastAPI app inside Docker. The container image installs Python dependencies during the build.
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Start infrastructure**
   ```bash
   docker compose up -d
   ```

5. **Run the application**
   ```bash
   python app.py
   ```
   > Prefer running the API inside Docker? Uncomment the `app` service in `docker-compose.yml` and run `docker compose up --build app`. In that workflow you can skip the local `pip install` step.

6. **Access the UI**
   Open http://localhost:8000 in your browser

## Usage

### Upload Documents
1. Click the upload area in the web UI
2. Select files (PDF, TXT, images, audio, or video)
3. Wait for processing to complete

### Ask Questions
1. Enter your question in the query box
2. Click "Search & Answer"
3. View answer with sources and confidence score

### Example Queries
- **Factual Lookup**: "What is the revenue mentioned in the Q4 report?"
- **Summarization**: "Summarize the key points from the meeting recording"
- **Semantic Linkage**: "Show all mentions of John Smith across documents"
- **Cross-Modal**: "What products are shown in the presentation slides?"
- **Reasoning**: "Based on the budget and timeline, is the project feasible?"

## Evaluation Framework

### Query Types
- `FACTUAL_LOOKUP`: Direct fact retrieval
- `SUMMARIZATION`: Summarize multiple sources
- `SEMANTIC_LINKAGE`: Cross-modal entity linking
- `REASONING`: Multi-hop reasoning
- `EXPLORATORY`: Open-ended exploration

### Metrics Tracked
- **Retrieval Quality**: Precision, recall, context relevance
- **Answer Quality**: Correctness, completeness, hallucination score
- **Performance**: Latency (retrieval, generation, end-to-end)
- **Cross-Modal**: Consistency across modalities

### Evaluation Goals
1. **Retrieval Quality**: High precision and recall
2. **Hallucination Control**: Near-zero hallucination rate
3. **Latency**: Sub-5-second response time (95th percentile)
4. **Reliability**: Graceful failure handling

### Running Tests
```bash
pytest tests/ -v
```

## API Documentation

### Endpoints

#### `POST /upload`
Upload and process a document.

**Request**: Multipart form with file

**Response**:
```json
{
  "status": "success",
  "file_id": "abc123",
  "file_name": "document.pdf",
  "content_type": "text",
  "num_entities": 15,
  "num_relationships": 8,
  "num_chunks": 42
}
```

#### `POST /query`
Process a query and return answer.

**Request**:
```json
{
  "query": "What is the revenue in Q4?",
  "user_id": "optional",
  "context": {}
}
```

**Response**:
```json
{
  "query": "What is the revenue in Q4?",
  "answer": "The Q4 revenue was $10 million [Source 1]",
  "sources": [...],
  "confidence": 0.92,
  "query_type": "FACTUAL_LOOKUP",
  "warning": null
}
```

#### `GET /stats`
Get system statistics.

**Response**:
```json
{
  "graph": {
    "num_entities": 150,
    "num_relationships": 89,
    "num_files": 12
  },
  "vector": {
    "num_vectors": 523,
    "vector_size": 1536
  }
}
```

## Configuration

Key settings in `.env`:

```env
# LLM Configuration
OPENAI_API_KEY=your_key
LLM_MODEL=gpt-4-turbo-preview
EMBEDDING_MODEL=text-embedding-3-small

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Application
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MIN_RELEVANCE_SCORE=0.7
```

## Module Documentation

### Ingestion Pipeline (`ingestion/`)
- `TextProcessor`: Handles PDF and TXT files
- `ImageProcessor`: OCR and image captioning (GPT-4 Vision)
- `AudioProcessor`: Audio transcription (Whisper)
- `VideoProcessor`: Frame extraction and audio transcription

### Entity Extraction (`extraction/`)
- `EntityExtractor`: LLM-based entity and relationship extraction
- Cross-modal entity linking

### Knowledge Graph (`graph/`)
- `KnowledgeGraph`: Neo4j integration for structured data
- Entity and relationship management
- Graph traversal and keyword search

### Vector Store (`vector_store/`)
- `VectorDatabase`: Qdrant integration for semantic search
- Embedding generation and similarity search
- Modality-filtered search

### Search (`search/`)
- `HybridSearchOrchestrator`: Combines graph, keyword, and vector search
- Result ranking and deduplication
- Cross-modal search

### Pipeline (`pipeline/`)
- `QueryProcessor`: End-to-end query processing
- Query triage and rewriting
- Answer generation with source citation
- Confidence scoring and evaluation

### Evaluation (`evaluation/`)
- `EvaluationFramework`: Metrics and test suites
- Query type classification
- Success criteria and thresholds

## Development

### Adding New Modalities
1. Create a new processor in `ingestion/`
2. Inherit from `BaseProcessor`
3. Implement `process()` and `validate()` methods
4. Register in `app.py`

### Extending Search
1. Add methods to `HybridSearchOrchestrator`
2. Update ranking logic if needed
3. Add tests

### Custom Evaluation Metrics
1. Extend `EvaluationMetrics` in `evaluation/eval_framework.py`
2. Update `evaluate_response()` function
3. Add corresponding tests

## Performance Optimization

### Recommended Settings
- **Production**: Increase `top_k` in search for better recall
- **Low Latency**: Reduce `max_depth` in graph traversal
- **High Accuracy**: Increase `score_threshold` in vector search

### Caching
- Enable query caching for common queries
- Cache embeddings for frequently accessed documents

### Scaling
- Use Neo4j cluster for graph database
- Use Qdrant cluster for vector database
- Deploy behind load balancer (e.g., nginx)

## Troubleshooting

### Issue: OCR not working
**Solution**: Install Tesseract OCR
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract
```

### Issue: Video processing fails
**Solution**: Install ffmpeg
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Issue: Connection refused to Neo4j/Qdrant
**Solution**: Ensure Docker containers are running
```bash
docker compose ps
docker compose up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with FastAPI, Neo4j, Qdrant, and OpenAI
- Inspired by enterprise RAG best practices
- Evaluation framework follows DeepEval principles
