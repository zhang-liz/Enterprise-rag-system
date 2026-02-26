"""
Enterprise RAG System - Main Application

FastAPI application with endpoints for:
- File upload and ingestion
- Query processing
- Knowledge graph exploration
- System statistics
"""

import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from extraction import EntityExtractor
from graph import KnowledgeGraph
from ingestion import TextProcessor, ImageProcessor, AudioProcessor, VideoProcessor
from pipeline import QueryProcessor, QueryRequest, Answer
from search import HybridSearchOrchestrator
from vector_store import VectorDatabase

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate required config at startup so the app fails fast with a clear error."""
    settings.validate_required()
    yield


# Initialize FastAPI
app = FastAPI(
    title="Enterprise RAG System",
    description="Multimodal Retrieval-Augmented Generation with Knowledge Graph",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize components
kg = KnowledgeGraph()
vdb = VectorDatabase()
search_orchestrator = HybridSearchOrchestrator(kg, vdb)
query_processor = QueryProcessor(search_orchestrator)
entity_extractor = EntityExtractor()

# Processors
text_processor = TextProcessor()
image_processor = ImageProcessor()
audio_processor = AudioProcessor()
video_processor = VideoProcessor()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main UI."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Enterprise RAG System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .content { padding: 30px; }
        .section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            background: white;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover {
            background: #f0f4ff;
            border-color: #764ba2;
        }
        .query-box {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            margin-bottom: 15px;
            transition: border-color 0.3s;
        }
        .query-box:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn:active { transform: translateY(0); }
        .result {
            background: white;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }
        .result h3 { color: #667eea; margin-bottom: 10px; }
        .source {
            background: #f0f4ff;
            padding: 10px;
            border-radius: 6px;
            margin: 10px 0;
            font-size: 0.9em;
        }
        .confidence {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .confidence.high { background: #d4edda; color: #155724; }
        .confidence.medium { background: #fff3cd; color: #856404; }
        .confidence.low { background: #f8d7da; color: #721c24; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stat-card h3 { font-size: 2em; color: #667eea; }
        .stat-card p { color: #666; margin-top: 5px; }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #667eea;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Enterprise RAG System</h1>
            <p>Multimodal Knowledge Graph with Hybrid Search</p>
        </div>

        <div class="content">
            <!-- Upload Section -->
            <div class="section">
                <h2>Upload Documents</h2>
                <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <p style="font-size: 1.2em; color: #667eea; margin-bottom: 10px;">📁 Click to upload files</p>
                    <p style="color: #666;">Supports: PDF, TXT, JPG, PNG, MP3, MP4</p>
                    <input type="file" id="fileInput" multiple style="display: none;" onchange="uploadFiles()">
                </div>
                <div id="uploadStatus" style="margin-top: 15px;"></div>
            </div>

            <!-- Query Section -->
            <div class="section">
                <h2>Ask Questions</h2>
                <textarea class="query-box" id="queryInput" rows="3" placeholder="Enter your question here... (e.g., 'What is mentioned about John Smith in the documents?')"></textarea>
                <button class="btn" onclick="submitQuery()">Search & Answer</button>
                <div class="loading" id="loading">⏳ Processing your query...</div>
                <div id="queryResult"></div>
            </div>

            <!-- Statistics Section -->
            <div class="section">
                <h2>System Statistics</h2>
                <button class="btn" onclick="loadStats()">Refresh Statistics</button>
                <div id="statsDisplay" class="stats-grid"></div>
            </div>
        </div>
    </div>

    <script>
        async function uploadFiles() {
            const fileInput = document.getElementById('fileInput');
            const files = fileInput.files;
            const statusDiv = document.getElementById('uploadStatus');

            if (files.length === 0) return;

            statusDiv.innerHTML = '<p style="color: #667eea;">Uploading files...</p>';

            for (let file of files) {
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (response.ok) {
                        statusDiv.innerHTML += `<p style="color: #28a745;">✓ ${file.name} uploaded successfully</p>`;
                    } else {
                        statusDiv.innerHTML += `<p style="color: #dc3545;">✗ ${file.name} failed: ${result.detail}</p>`;
                    }
                } catch (error) {
                    statusDiv.innerHTML += `<p style="color: #dc3545;">✗ ${file.name} error: ${error.message}</p>`;
                }
            }
        }

        async function submitQuery() {
            const query = document.getElementById('queryInput').value.trim();
            const resultDiv = document.getElementById('queryResult');
            const loading = document.getElementById('loading');

            if (!query) {
                alert('Please enter a question');
                return;
            }

            loading.style.display = 'block';
            resultDiv.innerHTML = '';

            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });

                const result = await response.json();

                if (response.ok) {
                    displayResult(result);
                } else {
                    resultDiv.innerHTML = `<div class="result"><p style="color: #dc3545;">Error: ${result.detail}</p></div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="result"><p style="color: #dc3545;">Error: ${error.message}</p></div>`;
            } finally {
                loading.style.display = 'none';
            }
        }

        function displayResult(result) {
            const resultDiv = document.getElementById('queryResult');

            let confidenceClass = 'low';
            if (result.confidence >= 0.7) confidenceClass = 'high';
            else if (result.confidence >= 0.4) confidenceClass = 'medium';

            let html = `
                <div class="result">
                    <h3>Answer</h3>
                    <p style="margin-bottom: 15px; line-height: 1.6;">${result.answer}</p>
                    <p><span class="confidence ${confidenceClass}">Confidence: ${(result.confidence * 100).toFixed(0)}%</span></p>

                    ${result.warning ? `<p style="color: #856404; margin-top: 10px;">⚠️ ${result.warning}</p>` : ''}

                    ${result.sources && result.sources.length > 0 ? `
                        <h4 style="margin-top: 20px; color: #667eea;">Sources:</h4>
                        ${result.sources.map(s => `
                            <div class="source">
                                <strong>Source ${s.id}</strong> (${s.source_type}) - Score: ${(s.score * 100).toFixed(0)}%
                            </div>
                        `).join('')}
                    ` : ''}
                </div>
            `;

            resultDiv.innerHTML = html;
        }

        async function loadStats() {
            const statsDiv = document.getElementById('statsDisplay');
            statsDiv.innerHTML = '<p style="color: #667eea; text-align: center;">Loading statistics...</p>';

            try {
                const response = await fetch('/stats');
                const stats = await response.json();

                let html = `
                    <div class="stat-card">
                        <h3>${stats.graph.num_entities || 0}</h3>
                        <p>Entities</p>
                    </div>
                    <div class="stat-card">
                        <h3>${stats.graph.num_relationships || 0}</h3>
                        <p>Relationships</p>
                    </div>
                    <div class="stat-card">
                        <h3>${stats.graph.num_files || 0}</h3>
                        <p>Documents</p>
                    </div>
                    <div class="stat-card">
                        <h3>${stats.vector.num_vectors || 0}</h3>
                        <p>Vectors</p>
                    </div>
                `;

                statsDiv.innerHTML = html;
            } catch (error) {
                statsDiv.innerHTML = `<p style="color: #dc3545;">Error loading statistics</p>`;
            }
        }

        // Load stats on page load
        window.onload = function() {
            loadStats();
        };
    </script>
</body>
</html>
"""


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a file."""
    try:
        # Sanitize filename to prevent path traversal (e.g. ../../etc/passwd)
        raw_name = file.filename or "unnamed"
        safe_name = Path(raw_name).name
        if not safe_name or safe_name == ".":
            raise HTTPException(status_code=400, detail="Invalid filename")
        # Use unique filename to avoid overwriting existing uploads
        unique_name = f"{uuid.uuid4().hex[:12]}_{safe_name}"
        file_path = (settings.upload_dir / unique_name).resolve()
        upload_dir_resolved = settings.upload_dir.resolve()
        if not str(file_path).startswith(str(upload_dir_resolved)):
            raise HTTPException(status_code=400, detail="Invalid file path")
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Determine processor
        suffix = file_path.suffix.lower()
        processor = None

        if suffix in ['.pdf', '.txt']:
            processor = text_processor
        elif suffix in ['.jpg', '.jpeg', '.png']:
            processor = image_processor
        elif suffix in ['.mp3', '.wav', '.m4a']:
            processor = audio_processor
        elif suffix in ['.mp4', '.avi', '.mov']:
            processor = video_processor
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

        # Process file
        processed_content = await processor.process(file_path)

        # Extract entities and relationships
        entities, relationships = await entity_extractor.extract(
            text=processed_content.text,
            file_id=processed_content.file_id,
            modality=processed_content.metadata.get("file_type", "unknown"),
            context=processed_content.metadata
        )

        # Add to knowledge graph
        kg.add_document(
            file_id=processed_content.file_id,
            file_name=safe_name,
            modality=processed_content.content_type,
            metadata=processed_content.metadata
        )

        for entity in entities:
            kg.add_entity(entity)

        for rel in relationships:
            kg.add_relationship(rel)

        # Add to vector database
        vdb.add_chunks(
            file_id=processed_content.file_id,
            chunks=processed_content.chunks,
            metadata={
                "file_name": safe_name,
                "modality": processed_content.content_type,
                **processed_content.metadata
            }
        )

        return JSONResponse({
            "status": "success",
            "file_id": processed_content.file_id,
            "file_name": safe_name,
            "content_type": processed_content.content_type,
            "num_entities": len(entities),
            "num_relationships": len(relationships),
            "num_chunks": len(processed_content.chunks)
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Upload processing failed")


@app.post("/query", response_model=Answer)
async def query(request: QueryRequest):
    """Process a query and return answer."""
    try:
        answer = await query_processor.process(request)
        return answer
    except HTTPException:
        raise
    except Exception:
        logger.exception("Query processing failed")
        raise HTTPException(status_code=500, detail="Query processing failed")


@app.get("/stats")
async def get_statistics():
    """Get system statistics."""
    try:
        graph_stats = kg.get_statistics()
        vector_stats = vdb.get_statistics()

        return {
            "graph": graph_stats,
            "vector": vector_stats
        }
    except Exception:
        logger.exception("Failed to retrieve statistics")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
