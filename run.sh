#!/bin/bash
# Startup script for Enterprise RAG System

set -e

echo "🚀 Starting Enterprise RAG System..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your API keys before continuing."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start infrastructure
echo "🐳 Starting Neo4j and Qdrant..."
docker-compose up -d neo4j qdrant

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check Neo4j
echo "🔍 Checking Neo4j..."
until curl -s http://localhost:7474 > /dev/null; do
    echo "   Waiting for Neo4j..."
    sleep 2
done
echo "✅ Neo4j is ready"

# Check Qdrant
echo "🔍 Checking Qdrant..."
until curl -s http://localhost:6333/health > /dev/null; do
    echo "   Waiting for Qdrant..."
    sleep 2
done
echo "✅ Qdrant is ready"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/uploads data/processed logs

# Start application
echo "🎯 Starting RAG application..."
python app.py
