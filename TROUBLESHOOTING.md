# Troubleshooting Guide

## Docker Build Issues

### Issue: `openai-whisper` package fails to install

**Error**:
```
KeyError: '__version__'
Getting requirements to build wheel did not run successfully
```

**Cause**: The `openai-whisper` package has compatibility issues with Python 3.13 and some build environments.

**Solution**: We've removed this package from requirements.txt because the code already uses OpenAI's Whisper API (via the `openai` package) instead. The audio processor at `ingestion/audio_processor.py` uses `client.audio.transcriptions.create()` which doesn't require the local whisper package.

**Fixed in**: Latest commit

### Issue: `opencv-python` fails in Docker

**Error**:
```
Could not find a version that satisfies the requirement opencv-python
```

**Cause**: `opencv-python` requires GUI libraries that aren't available in Docker.

**Solution**: Use `opencv-python-headless` instead, which is designed for server environments.

**Fixed in**: Latest commit

### Issue: Build dependencies missing

**Error**:
```
error: command 'gcc' failed
```

**Cause**: Some Python packages require compilation.

**Solution**: Install build-essential in Dockerfile:
```dockerfile
RUN apt-get install -y build-essential git
```

**Fixed in**: Latest commit

## Runtime Issues

### Issue: Neo4j connection refused

**Error**:
```
Failed to connect to Neo4j at bolt://localhost:7687
```

**Solution**:
```bash
# Check if Neo4j is running
docker-compose ps

# Start Neo4j if not running
docker-compose up -d neo4j

# Wait for Neo4j to be ready (takes ~30 seconds)
sleep 30
```

### Issue: Qdrant connection refused

**Error**:
```
Failed to connect to Qdrant at localhost:6333
```

**Solution**:
```bash
# Check if Qdrant is running
docker-compose ps

# Start Qdrant if not running
docker-compose up -d qdrant

# Check Qdrant health
curl http://localhost:6333/health
```

### Issue: OpenAI API errors

**Error**:
```
AuthenticationError: Invalid API key
```

**Solution**:
1. Check your `.env` file has a valid OpenAI API key:
   ```bash
   cat .env | grep OPENAI_API_KEY
   ```

2. Get an API key from: https://platform.openai.com/api-keys

3. Update `.env`:
   ```env
   OPENAI_API_KEY=sk-proj-...your-key-here
   ```

4. Restart the application

### Issue: OCR not working

**Error**:
```
TesseractNotFoundError: tesseract is not installed
```

**Solution (Local Development)**:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

**Solution (Docker)**: Already included in Dockerfile

### Issue: Video processing fails

**Error**:
```
FileNotFoundError: ffmpeg not found
```

**Solution (Local Development)**:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from: https://ffmpeg.org/download.html
```

**Solution (Docker)**: Already included in Dockerfile

## Performance Issues

### Issue: Slow query responses

**Symptoms**: Queries take >10 seconds

**Solutions**:
1. **Check database connectivity**:
   ```bash
   # Test Neo4j
   curl http://localhost:7474

   # Test Qdrant
   curl http://localhost:6333/health
   ```

2. **Reduce search scope**:
   - Lower `top_k` in search settings
   - Reduce `max_depth` in graph traversal
   - Increase `score_threshold` for vector search

3. **Check LLM API latency**:
   - OpenAI API might be slow
   - Consider using faster models (gpt-3.5-turbo)

### Issue: High memory usage

**Symptoms**: Container crashes with OOM errors

**Solutions**:
1. **Increase Docker memory limit**:
   ```yaml
   # In docker-compose.yml
   services:
     app:
       mem_limit: 4g
   ```

2. **Reduce batch sizes**:
   - Process files one at a time
   - Reduce chunk size in `config.py`

3. **Optimize processing**:
   - For videos, reduce number of frames extracted
   - For PDFs, process in batches

## Installation Issues

### Issue: pip install fails with dependency conflicts

**Error**:
```
ERROR: Cannot install package due to dependency conflicts
```

**Solution**:
```bash
# Clean install
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# If still failing, try installing in order
pip install fastapi uvicorn
pip install openai anthropic
pip install qdrant-client neo4j
# ... etc
```

### Issue: Module not found errors

**Error**:
```
ModuleNotFoundError: No module named 'config'
```

**Solution**:
1. Make sure you're in the project directory:
   ```bash
   cd /path/to/test-rag
   ```

2. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run from project root:
   ```bash
   python app.py
   ```

## Common Workflow Issues

### Issue: Files upload but don't appear in search

**Symptoms**: Upload succeeds but queries return no results

**Solutions**:
1. **Check processing succeeded**:
   - Look at upload response for errors
   - Check logs for processing failures

2. **Verify data in databases**:
   ```bash
   # Check Neo4j (open http://localhost:7474)
   MATCH (f:File) RETURN count(f)
   MATCH (e:Entity) RETURN count(e)

   # Check Qdrant (open http://localhost:6333/dashboard)
   ```

3. **Check embeddings were created**:
   ```bash
   curl http://localhost:8000/stats
   # Should show num_vectors > 0
   ```

### Issue: Answers have low confidence

**Symptoms**: All answers show confidence < 0.5

**Solutions**:
1. **Improve data quality**:
   - Upload more relevant documents
   - Ensure documents contain clear information

2. **Adjust thresholds**:
   ```python
   # In config.py or .env
   MIN_RELEVANCE_SCORE=0.6  # Lower threshold
   ```

3. **Check query formulation**:
   - Make queries more specific
   - Include entity names
   - Use keywords from documents

## Docker Compose Issues

### Issue: Services fail to start

**Error**:
```
Error: service 'neo4j' failed to build
```

**Solution**:
```bash
# Clean up and rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Port conflicts

**Error**:
```
Error: port 7474 is already allocated
```

**Solution**:
```bash
# Find process using the port
lsof -i :7474  # macOS/Linux
netstat -ano | findstr :7474  # Windows

# Kill the process or change port in docker-compose.yml
```

### Issue: Container keeps restarting

**Symptoms**: `docker-compose ps` shows "Restarting"

**Solution**:
```bash
# Check logs
docker-compose logs app
docker-compose logs neo4j
docker-compose logs qdrant

# Common causes:
# 1. Missing environment variables
# 2. Database connection failures
# 3. Port conflicts
```

## Development Issues

### Issue: Tests fail

**Error**:
```
pytest: command not found
```

**Solution**:
```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

### Issue: Hot reload not working

**Symptoms**: Code changes don't reflect immediately

**Solution**:
1. **Use uvicorn with reload**:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Or mount volume in Docker**:
   ```yaml
   services:
     app:
       volumes:
         - .:/app
   ```

## Getting More Help

1. **Check logs**:
   ```bash
   # Application logs
   tail -f logs/app.log

   # Docker logs
   docker-compose logs -f app
   ```

2. **Enable debug mode**:
   ```python
   # In app.py
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Check system status**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/stats
   ```

4. **Verify configuration**:
   ```bash
   # Check environment variables
   cat .env

   # Check Docker services
   docker-compose ps

   # Check ports
   netstat -an | grep LISTEN
   ```

## Quick Fixes Summary

| Problem | Quick Fix |
|---------|-----------|
| Build fails | Remove `openai-whisper` from requirements.txt |
| Neo4j connection fails | `docker-compose up -d neo4j && sleep 30` |
| OpenAI errors | Check API key in `.env` |
| Import errors | `pip install -r requirements.txt` |
| Port conflicts | Change ports in `docker-compose.yml` |
| Low disk space | `docker system prune -a` |
| Slow performance | Reduce `top_k` and `max_depth` |
| Container crashes | Increase memory limit |

## Still Having Issues?

1. Check this file first: `TROUBLESHOOTING.md`
2. Review documentation: `README.md`, `ARCHITECTURE.md`
3. Check GitHub issues
4. Enable verbose logging and check error messages
