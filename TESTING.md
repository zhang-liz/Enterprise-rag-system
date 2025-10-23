# Testing Guide

Comprehensive testing guide for the Enterprise RAG system.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_eval_framework.py   # Evaluation framework tests
├── test_ingestion.py        # Ingestion pipeline tests
└── ...                      # Additional test modules
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_eval_framework.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

### Run Specific Test
```bash
pytest tests/test_eval_framework.py::test_evaluation_metrics_validation -v
```

## Test Categories

### 1. Unit Tests

Test individual components in isolation.

**Evaluation Framework**:
```bash
pytest tests/test_eval_framework.py -v
```

Tests:
- Metric validation
- Threshold checking
- Test suite definition
- Failure scenarios

**Ingestion Pipeline**:
```bash
pytest tests/test_ingestion.py -v
```

Tests:
- File validation
- Text processing
- Chunking logic
- Metadata extraction

### 2. Integration Tests

Test components working together.

**Example**: Upload document → Extract entities → Store in graph

```python
@pytest.mark.asyncio
async def test_full_ingestion_pipeline():
    """Test complete ingestion workflow."""
    # Process document
    processor = TextProcessor()
    content = await processor.process(sample_file)

    # Extract entities
    extractor = EntityExtractor()
    entities, rels = await extractor.extract(content.text, ...)

    # Store in graph
    kg = KnowledgeGraph()
    for entity in entities:
        assert kg.add_entity(entity) is True
```

### 3. End-to-End Tests

Test complete user workflows.

```python
@pytest.mark.e2e
async def test_upload_and_query():
    """Test uploading document and querying."""
    # Upload
    response = client.post("/upload", files={"file": test_file})
    assert response.status_code == 200

    # Query
    response = client.post("/query", json={"query": "test query"})
    assert response.status_code == 200
    assert "answer" in response.json()
```

## Evaluation Tests

### Test Evaluation Framework

The evaluation framework defines success criteria:

```python
def test_evaluation_metrics():
    """Ensure metrics meet thresholds."""
    metrics = EvaluationMetrics(
        retrieval_precision=0.85,
        retrieval_recall=0.80,
        context_relevance=0.90,
        answer_correctness=0.88,
        answer_completeness=0.85,
        hallucination_score=0.95,
        latency_ms=2500,
        retrieval_latency_ms=1500,
        generation_latency_ms=1000,
        query_type=QueryType.FACTUAL_LOOKUP
    )

    thresholds = EvaluationThresholds()
    assert metrics.is_passing(thresholds) is True
```

### Test Query Types

Ensure all query types are handled:

```python
@pytest.mark.parametrize("query_type", [
    QueryType.FACTUAL_LOOKUP,
    QueryType.SUMMARIZATION,
    QueryType.SEMANTIC_LINKAGE,
    QueryType.REASONING,
    QueryType.EXPLORATORY
])
async def test_query_type_handling(query_type):
    """Test each query type."""
    request = QueryRequest(query="test query")
    analysis = await processor._triage_query(request.query)
    # Verify analysis is valid
```

### Test Failure Scenarios

Ensure graceful failures:

```python
async def test_no_results_scenario():
    """Test behavior when no results found."""
    answer = processor._handle_no_results("unknown query", analysis)
    assert answer.confidence == 0.0
    assert answer.warning is not None
    assert "couldn't find" in answer.answer.lower()
```

## Manual Testing Checklist

### Ingestion Tests

- [ ] Upload PDF file
- [ ] Upload TXT file
- [ ] Upload JPG/PNG image (with text)
- [ ] Upload MP3 audio file
- [ ] Upload MP4 video file
- [ ] Verify entity extraction
- [ ] Verify chunks are created
- [ ] Check knowledge graph has entities
- [ ] Check vector DB has embeddings

### Query Tests

- [ ] Factual lookup query
- [ ] Summarization query
- [ ] Cross-modal query (entity in multiple files)
- [ ] Query with no results
- [ ] Ambiguous query
- [ ] Complex reasoning query

### Evaluation Tests

- [ ] Check metrics are computed
- [ ] Verify confidence scoring
- [ ] Test with ground truth answers
- [ ] Verify hallucination detection
- [ ] Test latency tracking

### UI Tests

- [ ] Load homepage
- [ ] Upload file via drag-and-drop
- [ ] Submit query via text box
- [ ] View results with sources
- [ ] Check confidence visualization
- [ ] Load system statistics
- [ ] Verify error handling (bad file, empty query)

## Performance Testing

### Load Testing

Test system under load:

```python
import asyncio

async def load_test():
    """Simulate multiple concurrent queries."""
    queries = ["query 1", "query 2", "query 3"] * 10
    tasks = [processor.process(QueryRequest(query=q)) for q in queries]
    results = await asyncio.gather(*tasks)

    # Check latencies
    latencies = [r.evaluation_metrics.latency_ms for r in results]
    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 5000  # Under 5 seconds
```

### Benchmark Tests

```bash
# Benchmark ingestion
time python -c "
from ingestion import TextProcessor
import asyncio
processor = TextProcessor()
asyncio.run(processor.process('sample.pdf'))
"

# Benchmark query processing
time curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

## Test Data

### Creating Test Data

```python
# Create sample documents
def create_test_document(tmp_path, content):
    """Create test document."""
    doc = tmp_path / "test.txt"
    doc.write_text(content)
    return doc

# Create test with known entities
sample_content = """
John Smith is the CEO of Acme Corp.
The Q4 revenue was $10 million.
Widget Pro is the main product.
"""
```

### Test Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def knowledge_graph():
    """Create test knowledge graph."""
    kg = KnowledgeGraph()
    yield kg
    # Cleanup after test
    kg.close()

@pytest.fixture
def sample_entities():
    """Sample entities for testing."""
    return [
        Entity(
            name="John Smith",
            type="PERSON",
            source_file_id="test123",
            source_modality="text",
            confidence=0.9
        )
    ]
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      neo4j:
        image: neo4j:5.13.0
        env:
          NEO4J_AUTH: neo4j/password
        ports:
          - 7687:7687

      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.13

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: pytest tests/ -v --cov
```

## Debugging Tests

### Verbose Output
```bash
pytest tests/ -vv -s
```

### Print Debug Info
```python
@pytest.mark.debug
async def test_with_debug():
    """Test with debug output."""
    result = await some_function()
    print(f"Result: {result}")  # Will show with -s flag
    assert result is not None
```

### Run Specific Test with Debugging
```bash
pytest tests/test_ingestion.py::test_text_processor -vv -s
```

## Test Coverage

### Generate Coverage Report
```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html  # View coverage
```

### Coverage Goals
- Overall: > 80%
- Critical paths: > 95%
- Evaluation framework: 100%

## Common Issues

### Issue: Tests fail due to missing API keys

**Solution**: Set test environment variables
```bash
export OPENAI_API_KEY=test_key
pytest tests/
```

### Issue: Database connection errors

**Solution**: Ensure Docker containers are running
```bash
docker-compose up -d
pytest tests/
```

### Issue: Async tests not running

**Solution**: Install pytest-asyncio
```bash
pip install pytest-asyncio
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Use fixtures for setup/teardown
3. **Mocking**: Mock external services (API calls, etc.)
4. **Fast**: Keep unit tests fast (< 1s each)
5. **Clear**: Use descriptive test names
6. **Coverage**: Aim for high coverage on critical paths

## Adding New Tests

When adding a new feature:

1. Write tests first (TDD)
2. Add unit tests for the component
3. Add integration tests if needed
4. Update this document with new test cases
5. Ensure all tests pass before merging

## Test Maintenance

- Review and update tests when features change
- Remove obsolete tests
- Keep test data up to date
- Monitor test execution time
- Fix flaky tests immediately

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [DeepEval Documentation](https://docs.confident-ai.com/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
