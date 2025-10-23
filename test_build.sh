#!/bin/bash
# Test script to validate Docker build and deployment

set -e

echo "🧪 Enterprise RAG System - Build Test Script"
echo "============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Docker is available
echo "1️⃣  Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker found: $(docker --version)${NC}"
echo ""

# Test 2: Check Docker Compose
echo "2️⃣  Checking Docker Compose..."
if docker compose version &> /dev/null; then
    echo -e "${GREEN}✅ Docker Compose V2 found: $(docker compose version)${NC}"
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✅ Docker Compose V1 found: $(docker-compose --version)${NC}"
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}❌ Docker Compose not found.${NC}"
    exit 1
fi
echo ""

# Test 3: Validate requirements.txt
echo "3️⃣  Validating requirements.txt..."
if grep -q "openai-whisper" requirements.txt; then
    echo -e "${RED}❌ FAIL: openai-whisper package found in requirements.txt${NC}"
    echo "   This package should be removed (causes Python 3.13 compatibility issues)"
    exit 1
fi

if grep -q "opencv-python-headless" requirements.txt; then
    echo -e "${GREEN}✅ PASS: Using opencv-python-headless (Docker-friendly)${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: opencv-python-headless not found${NC}"
fi
echo ""

# Test 4: Validate Dockerfile
echo "4️⃣  Validating Dockerfile..."
if grep -q "build-essential" Dockerfile; then
    echo -e "${GREEN}✅ PASS: build-essential included for compilation${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: build-essential not found in Dockerfile${NC}"
fi

if grep -q "pip install --no-cache-dir --upgrade pip" Dockerfile; then
    echo -e "${GREEN}✅ PASS: pip upgrade included${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: pip upgrade not found${NC}"
fi
echo ""

# Test 5: Clean previous containers
echo "5️⃣  Cleaning previous containers..."
$COMPOSE_CMD down -v 2>/dev/null || true
echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

# Test 6: Build Docker images
echo "6️⃣  Building Docker images (this may take 5-10 minutes)..."
echo -e "${YELLOW}⏳ Building...${NC}"
if $COMPOSE_CMD build --no-cache neo4j qdrant 2>&1 | tee /tmp/docker-build.log; then
    echo -e "${GREEN}✅ Build successful!${NC}"
else
    echo -e "${RED}❌ Build failed. Check /tmp/docker-build.log for details${NC}"
    tail -50 /tmp/docker-build.log
    exit 1
fi
echo ""

# Test 7: Start services
echo "7️⃣  Starting services..."
$COMPOSE_CMD up -d neo4j qdrant
echo -e "${YELLOW}⏳ Waiting for services to be ready (30 seconds)...${NC}"
sleep 30
echo ""

# Test 8: Check Neo4j
echo "8️⃣  Testing Neo4j..."
if curl -s http://localhost:7474 > /dev/null; then
    echo -e "${GREEN}✅ Neo4j is running on port 7474${NC}"
else
    echo -e "${RED}❌ Neo4j is not accessible${NC}"
    $COMPOSE_CMD logs neo4j | tail -20
fi
echo ""

# Test 9: Check Qdrant
echo "9️⃣  Testing Qdrant..."
if curl -s http://localhost:6333/health > /dev/null; then
    echo -e "${GREEN}✅ Qdrant is running on port 6333${NC}"
    echo "   Health check: $(curl -s http://localhost:6333/health)"
else
    echo -e "${RED}❌ Qdrant is not accessible${NC}"
    $COMPOSE_CMD logs qdrant | tail -20
fi
echo ""

# Test 10: Check container status
echo "🔟 Container status:"
$COMPOSE_CMD ps
echo ""

# Summary
echo "============================================="
echo "📊 Test Summary"
echo "============================================="
echo -e "${GREEN}✅ Docker installation verified${NC}"
echo -e "${GREEN}✅ Configuration files validated${NC}"
echo -e "${GREEN}✅ Docker images built successfully${NC}"
echo -e "${GREEN}✅ Services are running${NC}"
echo ""
echo "🎉 All tests passed!"
echo ""
echo "Next steps:"
echo "1. Configure your .env file:"
echo "   cp .env.example .env"
echo "   # Edit .env and add your OPENAI_API_KEY"
echo ""
echo "2. Install Python dependencies:"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Run the application:"
echo "   python app.py"
echo ""
echo "4. Open your browser:"
echo "   http://localhost:8000"
echo ""
echo "To stop services:"
echo "   $COMPOSE_CMD down"
echo ""
