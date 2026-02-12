"""
Query processing pipeline with:
1. Input validation
2. Query triage (determine query type)
3. Query rewriting (optimization)
4. Answer generation
5. Post-processing
"""

from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI
from evaluation import QueryType, EvaluationMetrics, evaluate_response
from search import HybridSearchOrchestrator, SearchResult
from config import settings
import re
from datetime import datetime


class QueryRequest(BaseModel):
    """Validated query request."""
    query: str = Field(min_length=3, max_length=1000)
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is safe and meaningful."""
        # Remove excessive whitespace
        v = re.sub(r'\s+', ' ', v.strip())

        # Check for minimum meaningful content
        if len(v.split()) < 2:
            raise ValueError("Query too short - please provide more context")

        return v


class QueryAnalysis(BaseModel):
    """Results of query triage."""
    original_query: str
    rewritten_query: str
    query_type: QueryType
    requires_graph: bool
    requires_vector: bool
    requires_keyword: bool
    entities_mentioned: List[str] = Field(default_factory=list)
    modalities_expected: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class Answer(BaseModel):
    """Final answer with metadata."""
    query: str
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    query_type: QueryType
    retrieved_contexts: List[str] = Field(default_factory=list)
    evaluation_metrics: Optional[EvaluationMetrics] = None
    warning: Optional[str] = None


class QueryProcessor:
    """
    Main query processing pipeline.

    This orchestrates the entire RAG workflow:
    1. Validate and triage query
    2. Rewrite for better retrieval
    3. Execute hybrid search
    4. Generate answer
    5. Evaluate and return
    """

    def __init__(self, search_orchestrator: HybridSearchOrchestrator):
        self.search = search_orchestrator
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def process(self, request: QueryRequest) -> Answer:
        """
        Process query end-to-end.

        This is the main entry point for the RAG system.
        """
        start_time = datetime.now()

        # 1. Input Validation (handled by Pydantic)
        # Already validated by QueryRequest model

        # 2. Query Triage
        analysis = await self._triage_query(request.query)

        # 3. Query Rewriting (if beneficial)
        optimized_query = analysis.rewritten_query

        # 4. Hybrid Search
        search_results = await self.search.search(
            query=optimized_query,
            query_type=analysis.query_type,
            top_k=10,
            enable_graph=analysis.requires_graph,
            enable_keyword=analysis.requires_keyword,
            enable_vector=analysis.requires_vector
        )

        # 5. Check if we have sufficient context
        if not search_results:
            return self._handle_no_results(request.query, analysis)

        # 6. Generate Answer
        answer_text = await self._generate_answer(
            query=request.query,
            context_results=search_results,
            query_type=analysis.query_type
        )

        # 7. Post-processing
        answer = self._post_process_answer(
            query=request.query,
            answer_text=answer_text,
            search_results=search_results,
            analysis=analysis
        )

        # 8. Evaluate
        if settings.eval_mode == "development":
            answer.evaluation_metrics = evaluate_response(
                query=request.query,
                response=answer_text,
                retrieved_context=[r.content for r in search_results],
                query_type=analysis.query_type,
                start_time=start_time
            )

        return answer

    async def _triage_query(self, query: str) -> QueryAnalysis:
        """
        Analyze query to determine type and strategy.

        This determines which search methods to use.
        """
        try:
            prompt = f"""Analyze this query and determine its characteristics.

Query: {query}

Classify the query type:
- FACTUAL_LOOKUP: Direct fact retrieval
- SUMMARIZATION: Summarize multiple sources
- SEMANTIC_LINKAGE: Cross-modal entity linking
- REASONING: Multi-hop reasoning
- EXPLORATORY: Open-ended exploration

Also determine:
- Does it mention specific entities? (names, organizations, products)
- Does it require graph traversal? (relationships, connections)
- Does it require keyword matching? (exact terms)
- Does it require semantic search? (meaning, concepts)
- What modalities are expected? (text, image, audio, video)

Return JSON:
{{
    "query_type": "FACTUAL_LOOKUP",
    "rewritten_query": "optimized version of query",
    "requires_graph": true/false,
    "requires_vector": true/false,
    "requires_keyword": true/false,
    "entities_mentioned": ["entity1", "entity2"],
    "modalities_expected": ["text", "image"],
    "confidence": 0.9
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a query analysis expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return QueryAnalysis(
                original_query=query,
                rewritten_query=result.get("rewritten_query", query),
                query_type=QueryType[result.get("query_type", "FACTUAL_LOOKUP")],
                requires_graph=result.get("requires_graph", False),
                requires_vector=result.get("requires_vector", True),
                requires_keyword=result.get("requires_keyword", False),
                entities_mentioned=result.get("entities_mentioned", []),
                modalities_expected=result.get("modalities_expected", ["text"]),
                confidence=result.get("confidence", 0.8)
            )

        except Exception as e:
            print(f"Query triage failed: {str(e)}")
            # Fallback to defaults
            return QueryAnalysis(
                original_query=query,
                rewritten_query=query,
                query_type=QueryType.FACTUAL_LOOKUP,
                requires_graph=False,
                requires_vector=True,
                requires_keyword=False,
                confidence=0.5
            )

    async def _generate_answer(
        self,
        query: str,
        context_results: List[SearchResult],
        query_type: QueryType
    ) -> str:
        """
        Generate answer from retrieved context.

        Key principles:
        - Ground all answers in context (no hallucination)
        - Cite sources
        - Indicate confidence
        - Graceful handling of insufficient context
        """
        # Build context string
        context_parts = []
        for idx, result in enumerate(context_results[:5], 1):  # Top 5 results
            source_info = f"[Source {idx} - {result.source}, confidence: {result.score:.2f}]"
            context_parts.append(f"{source_info}\n{result.content}\n")

        context = "\n".join(context_parts)

        # Generate answer
        system_prompt = """You are an enterprise AI assistant providing accurate, grounded answers.

CRITICAL RULES:
1. ONLY use information from the provided context
2. If context is insufficient, say "I don't have enough information to answer this"
3. Cite sources using [Source N] notation
4. If sources conflict, mention both perspectives
5. Never make up information
6. Be concise but complete"""

        user_prompt = f"""Context:
{context}

Question: {query}

Provide a clear, accurate answer based ONLY on the context above. Cite your sources."""

        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def _post_process_answer(
        self,
        query: str,
        answer_text: str,
        search_results: List[SearchResult],
        analysis: QueryAnalysis
    ) -> Answer:
        """Post-process answer and add metadata."""

        # Extract sources
        sources = []
        for idx, result in enumerate(search_results[:5], 1):
            sources.append({
                "id": idx,
                "source_type": result.source,
                "score": result.score,
                "metadata": result.metadata
            })

        # Calculate confidence
        confidence = self._calculate_confidence(answer_text, search_results, analysis)

        # Check for warnings
        warning = None
        if confidence < 0.5:
            warning = "Low confidence answer - information may be incomplete"
        elif "I don't have enough information" in answer_text:
            warning = "Insufficient context to fully answer query"

        return Answer(
            query=query,
            answer=answer_text,
            sources=sources,
            confidence=confidence,
            query_type=analysis.query_type,
            retrieved_contexts=[r.content for r in search_results],
            warning=warning
        )

    def _calculate_confidence(
        self,
        answer: str,
        results: List[SearchResult],
        analysis: QueryAnalysis
    ) -> float:
        """Calculate confidence score for answer."""
        # Factors:
        # 1. Number of high-quality results
        # 2. Query analysis confidence
        # 3. Answer quality indicators

        if not results:
            return 0.0

        # Average result scores
        avg_score = sum(r.score for r in results[:5]) / min(len(results), 5)

        # Check for insufficient information indicators
        insufficient_indicators = [
            "don't have enough",
            "insufficient",
            "cannot answer",
            "unclear"
        ]

        has_insufficient = any(ind in answer.lower() for ind in insufficient_indicators)

        if has_insufficient:
            return min(0.3, avg_score)

        # Combine factors
        confidence = (avg_score + analysis.confidence) / 2

        return min(confidence, 1.0)

    def _handle_no_results(self, query: str, analysis: QueryAnalysis) -> Answer:
        """Handle graceful failure when no results found."""
        return Answer(
            query=query,
            answer="I couldn't find relevant information to answer your question. "
                   "This could mean: (1) the information isn't in the knowledge base, "
                   "(2) the query needs to be rephrased, or (3) the topic is outside "
                   "the current domain.",
            sources=[],
            confidence=0.0,
            query_type=analysis.query_type,
            warning="No relevant context found"
        )
