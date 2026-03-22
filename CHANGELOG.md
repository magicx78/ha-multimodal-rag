# Changelog

## v1.1.0 (2026-03-22)

### ✨ New Features

- **Web-UI** — Complete Vue 3 web application for multimodal-rag
  - Login page with authentication
  - Dashboard with 5 interactive modules
  - Upload module (drag-drop support)
  - Search module (semantic search)
  - Reasoning module (Q&A chat)
  - Collections management
  - Admin panel with settings
- **API Integration** — RESTful API layer with axios
- **State Management** — Pinia stores for auth & documents
- **Routing** — Vue Router with protected routes
- **Styling** — Tailwind CSS + responsive design

### 🔧 Technical

- Vue 3 + Composition API
- Vite build tool
- TypeScript strict mode
- ESLint configuration
- PostCSS + Autoprefixer

### 📦 Updated

- Dependencies: vue@3.4, vite@5, tailwind@3, pinia@2

## v1.0.3 (2026-03-22)

### 📋 Added

- Comprehensive memory system
- Coordinator framework (Phase 2-8)
- Architecture documentation
- Decision records

### 🐛 Fixed

- Token security handling
- GitHub workflows setup
- HACS validation

## v1.0.2 (2026-03-22)

### 🔧 Fixed

- Reduced manifest.json dependencies
- Removed heavy ML libraries from defaults

## v1.0.1 (2026-03-21)

### ✨ New

- Bug fixes
- UX improvements

## v1.0.0 (2026-03-20)

### 🎉 Initial Release

- Core RAG integration for Home Assistant
- 5 services (upload, search, reason, list, delete)
- Multi-provider support
- Config flow
