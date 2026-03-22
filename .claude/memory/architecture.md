# 🏗️ Architecture — multimodal-rag

## System Overview

```
User (Home Assistant UI or Web)
    ↓
multimodal-rag Integration
    ├── Config Flow (5 steps)
    ├── Services (5 endpoints)
    └── RAG Engine
        ├── LLM Provider (Claude/Ollama)
        ├── Embedding Provider (Claude/SentenceTransformers)
        ├── Vector DB (Qdrant/SQLite)
        └── Document Processors (PDF/Image/Text/Audio/Video)
```

## Integration Layers

### Layer 1: Home Assistant Core
- Standard config entries
- Config flow for multi-step setup
- Service registration (YAML automations)
- Event dispatching
- Data storage management

### Layer 2: RAG Engine
- Document processing pipeline
- Semantic embedding & chunking
- Vector similarity search
- LLM-powered reasoning

### Layer 3: Provider Plugins
- LLM: Claude API / Ollama
- Embedding: Claude Voyage / Sentence-Transformers
- Vector DB: Qdrant / SQLite
- Processors: Text/PDF/Image/Audio/Video

## Service Contracts

```yaml
multimodal_rag.upload_document:
  input: { file_path: str, collection: str }
  output: { status: str, document_id: str, error?: str }

multimodal_rag.search:
  input: { query: str, collection?: str, top_k?: int }
  output: { results: [{ text, score, source }] }

multimodal_rag.reason:
  input: { query: str, collection?: str, temperature?: float }
  output: { answer: str, sources: [str] }

multimodal_rag.list_collections:
  input: {}
  output: { collections: [{ name, doc_count }] }

multimodal_rag.delete_document:
  input: { document_id: str, collection: str }
  output: { status: str }
```

## Data Flow

### Upload
```
User → upload_document service
  → File validation
  → Document processor (detect type)
  → Chunking (configurable size/overlap)
  → Embedding (via embedding provider)
  → Vector DB storage
  → HA event: multimodal_rag_document_indexed
```

### Search
```
User → search service
  → Query embedding
  → Vector similarity search (top-k)
  → Re-ranking (optional)
  → Source attribution
  → Return results with metadata
```

### Reasoning
```
User → reason service
  → Retrieve relevant documents (search)
  → Build context from chunks
  → LLM prompt + context
  → Generate response
  → Track sources
  → HA event: multimodal_rag_search_completed
```

## Storage Structure

```
config/multimodal_rag/
├── vectors.db              (SQLite embeddings — if SQLite provider)
├── documents/              (Local document cache)
│   ├── {doc_id}_chunks.json
│   └── metadata.json
└── collections/            (Collection definitions)
    └── {collection}_meta.json
```

## Configuration

### Required (Config Flow Step 1)
- Claude Access Type: API Key / Subscription / None

### Optional (Config Flow Steps 2-5)
- LLM Provider & Model
- Embedding Provider & Model
- Vector DB (Qdrant host/port or SQLite)
- Storage path
- Collection name

## Error Handling Strategy

1. **Health Checks:** Each provider has `health_check()` method
2. **Graceful Degradation:** Fallbacks built into factories
3. **Retry Logic:** Document processing has built-in retries
4. **Validation:** Config flow validates all connections

## Dependency Tree

```
multimodal_rag
├── anthropic>=0.21.0       (Claude API)
├── aiohttp>=3.9.0          (HTTP requests)
├── aiofiles>=23.0.0        (async file I/O)
├── pydantic>=2.0.0         (data validation)
│
├── [LAZY] sentence-transformers  (if user selects)
├── [LAZY] qdrant-client          (if user selects)
├── [LAZY] PyMuPDF                (if user uploads PDFs)
├── [LAZY] Pillow                 (if user uploads images)
└── [LAZY] ollama                 (if user selects Ollama)
```

## Next Phase: Web UI Architecture (TBD)

Will be designed after template example provided by user.

Expected additions:
- Web server (FastAPI / aiohttp?)
- Frontend framework (React/Vue/Vanilla?)
- Authentication layer
- WebSocket for real-time updates
- File upload handler (Multer/FormData)
