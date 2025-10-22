# Quick Start Guide

Get the Enterprise RAG system running in 5 minutes.

## Prerequisites

1. **Python 3.9+**
   ```bash
   python --version
   ```

2. **Docker Desktop** (for Neo4j and Qdrant)
   ```bash
   docker --version
   ```

3. **OpenAI API Key**
   - Get one from: https://platform.openai.com/api-keys

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env  # or use your favorite editor
```

Required settings:
```env
OPENAI_API_KEY=sk-your-key-here
```

### 3. Start Infrastructure

```bash
# Start Neo4j and Qdrant
docker-compose up -d

# Wait for services to be ready (about 30 seconds)
# Check status:
docker-compose ps
```

You should see:
- Neo4j running on port 7474 (UI) and 7687 (Bolt)
- Qdrant running on port 6333

### 4. Start the Application

```bash
python app.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Open the Web UI

Open your browser and go to:
```
http://localhost:8000
```

## First Steps

### Upload a Document

1. Click the upload area
2. Select a file (PDF, TXT, image, audio, or video)
3. Wait for processing (you'll see a success message)

### Ask a Question

1. Type your question in the query box
2. Click "Search & Answer"
3. View the answer with sources and confidence score

### Example Queries

Try these with your uploaded documents:
- "What is mentioned about [topic]?"
- "Who is [person name]?"
- "Summarize the key points"
- "What are the main entities?"

## Troubleshooting

### Issue: "Connection refused" errors

**Solution**: Make sure Docker containers are running
```bash
docker-compose up -d
docker-compose ps
```

### Issue: "Module not found" errors

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: OCR not working on images

**Solution**: Install Tesseract
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Issue: Video processing fails

**Solution**: Install ffmpeg
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from: https://ffmpeg.org/download.html
```

### Issue: Application crashes on startup

**Solution**: Check .env file has valid OpenAI API key
```bash
cat .env | grep OPENAI_API_KEY
```

## Verify Installation

### Check Neo4j
1. Open http://localhost:7474
2. Login with username: `neo4j`, password: `password`
3. You should see the Neo4j Browser

### Check Qdrant
1. Open http://localhost:6333/dashboard
2. You should see the Qdrant dashboard

### Check Application
```bash
curl http://localhost:8000/health
```

Should return:
```json
{"status": "healthy", "version": "1.0.0"}
```

## Next Steps

1. **Read the README**: `README.md` for full documentation
2. **Explore the architecture**: `ARCHITECTURE.md` for system design
3. **Run tests**: `pytest tests/ -v`
4. **Try the example**: `python example_usage.py`

## Quick Reference

### Start Everything
```bash
docker-compose up -d && python app.py
```

### Stop Everything
```bash
# Stop application (Ctrl+C)
# Stop infrastructure
docker-compose down
```

### Reset Everything
```bash
# Warning: This deletes all data!
docker-compose down -v
rm -rf data/uploads/* data/processed/*
```

### View Logs
```bash
# Application logs
tail -f logs/app.log

# Docker logs
docker-compose logs -f
```

## Common Workflows

### Workflow 1: Process Multiple Documents
```python
# See example_usage.py for programmatic access
python example_usage.py
```

### Workflow 2: Batch Upload via API
```bash
# Upload multiple files
for file in documents/*.pdf; do
    curl -X POST -F "file=@$file" http://localhost:8000/upload
done
```

### Workflow 3: Query via API
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the revenue?"}'
```

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **README.md**: Full documentation
- **ARCHITECTURE.md**: Technical details
- **Code comments**: Inline documentation

## Success Criteria

You'll know it's working when:
1. ✅ Docker containers are running
2. ✅ Web UI loads at http://localhost:8000
3. ✅ You can upload a document successfully
4. ✅ You can query and get answers with sources
5. ✅ Statistics show your uploaded documents

Happy building! 🚀
