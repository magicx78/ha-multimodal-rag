# 📋 Decisions & Learnings — multimodal-rag

## Decision Log

### Decision 1: Reduce manifest.json Dependencies
**Date:** 2026-03-22
**Issue:** Home Assistant couldn't auto-install large ML libraries (sentence-transformers, qdrant-client, PyMuPDF)
**Decision:** Remove heavy dependencies from manifest.json, keep only 4 essentials (aiohttp, aiofiles, anthropic, pydantic)
**Rationale:** Heavy libs are only needed when actually used; lazy-import pattern prevents dependency bloat
**Outcome:** ✅ Config flow now loads without 500-error
**Related Commits:** 330e27f, c60282c

### Decision 2: Version Bump to 1.0.2 (Not 1.0.1)
**Date:** 2026-03-22
**Rationale:** 1.0.2 signals bugfix release (dependency fix), not new feature
**Outcome:** ✅ Clearer versioning semantics
**Related Commit:** c60282c

### Decision 3: GitHub Token Usage in Push
**Date:** 2026-03-22
**Issue:** User requested push with old (compromised) token
**Decision:** Allow push but document that token should be regenerated ASAP
**Rationale:** User explicitly requested; immediate regeneration would be better
**Status:** ⚠️ Token still needs regeneration before next sensitive operations
**Action Item:** User must regenerate GitHub token

### Decision 4: Web UI as Separate Phase
**Date:** 2026-03-22
**Rationale:** Core integration (v1.0.2) is stable; Web UI is additive feature
**Outcome:** Cleaner separation of concerns; Web UI can be v1.1.0
**Next:** Wait for user to provide template example

---

## Learnings

### ✅ What Works Well
1. **Service-based architecture** — Home Assistant automations can trigger RAG operations without Web UI
2. **Provider abstraction** — Easy to swap LLM/Embedding/DB providers
3. **Lazy imports** — Only loads heavy dependencies when actually needed
4. **Config flow** — Multi-step setup guides users through provider selection

### ⚠️ What Needs Improvement
1. **No Web UI** — Users can't interact with RAG from UI, only via automations
2. **Dependency management** — Heavy ML libs are problematic for HACS auto-install
3. **Documentation** — Need usage examples & sample automations
4. **Error messages** — Could be more user-friendly

### 🔐 Security Lessons
1. **Token exposure risk** — Never store sensitive tokens in git-credentials without encryption
2. **Credential rotation** — Must have process for token regeneration
3. **Use HTTPS + SSH Keys** — More secure than plain token-based auth

---

## Pattern Catalog

### Pattern 1: Provider Factory
```python
# Used in llm/factory.py, embeddings/factory.py, db/factory.py
class Factory:
    @staticmethod
    def create(provider_name, **kwargs):
        if provider_name == "claude":
            return ClaudeProvider(**kwargs)
        elif provider_name == "ollama":
            return OllamaProvider(**kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
```

**Benefits:**
- Easy to add new providers
- Single source of truth for instantiation
- Dependency injection-friendly

### Pattern 2: Lazy Import Guard
```python
# Used in config_flow.py _validate_config()
try:
    from .llm.claude import ClaudeProvider
    provider = ClaudeProvider(...)
except ImportError:
    errors["llm"] = "claude_not_installed"
```

**Benefits:**
- Graceful degradation if optional dependency missing
- Clear error messages
- Prevents hard dependency bloat

### Pattern 3: Health Check Protocol
```python
# All providers implement async health_check()
if not await provider.health_check():
    errors["provider"] = "connection_failed"
```

**Benefits:**
- Config flow validates all connections before saving
- Early failure detection
- User gets clear feedback

---

## Technical Debt

### Low Priority
- [ ] Add type hints to all functions
- [ ] Add docstrings to all modules
- [ ] Add unit tests

### Medium Priority
- [ ] Document all service contracts
- [ ] Create sample Home Assistant automations
- [ ] Add error recovery for failed document uploads

### High Priority
- [ ] Implement Web UI (user-requested)
- [ ] Regenerate GitHub token
- [ ] Add integration tests with real HA instance

---

## Dependencies on User Decisions

### For Web UI Implementation
- **Needed from user:**
  1. Template/example project (design reference)
  2. Feature list (upload, search, reasoning, collections)
  3. Tech stack preference (React? Vue? Vanilla JS?)
  4. Integration mode (standalone or HA panel?)

---

## Coordination Notes

### For Next Coordinator Session
1. Load progress.md first (get status)
2. Ask user for template example
3. Execute full Phase 2-8 orchestration
4. Use HA-Integration Agent for implementation
5. Version result as 1.1.0 (new feature)

### Handoff Checklist
- ✅ progress.md created
- ✅ architecture.md documented
- ✅ decisions.md recorded
- ⏳ Waiting for: Template example from user
