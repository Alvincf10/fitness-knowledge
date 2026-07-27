Implement Phase 4 of the Fitness Knowledge Base project.

Build a production-ready Retrieval-Augmented Generation (RAG) pipeline using the existing FAISS HNSW index and metadata.

Requirements:

1. Create retriever.py to perform embedding, FAISS search, duplicate removal, metadata lookup, and configurable Top-K retrieval.
2. Create reranker.py using BAAI/bge-reranker-base (or bge-reranker-v2-m3 if supported) to rerank retrieved chunks and return the best contexts.
3. Create prompt_builder.py that assembles a hallucination-resistant prompt using only retrieved context and instructs the LLM to answer only from the knowledge base, returning citations.
4. Create pipeline.py that orchestrates embedding → retrieval → reranking → prompt construction → LLM inference → formatted response.
5. Create citations.py to generate structured source references from metadata.
6. Expose the pipeline through POST /chat, returning answer, sources, confidence score, retrieval time, rerank time, and total latency.
7. Implement confidence thresholding so that low-confidence retrieval returns an "insufficient knowledge" response instead of hallucinating.
8. Add automated retrieval and hallucination benchmark tests with at least 100 evaluation questions.
9. Move all runtime parameters into a centralized config file or environment variables.
10. Ensure modular, well-documented, production-ready code with type hints, logging, and unit tests.

The implementation must prioritize factual accuracy, citation integrity, and low latency.