# Multimodal RAG Web-UI

Intelligente Dokumentenverarbeitung mit Vue 3 + Tailwind CSS.

## 🚀 Quick Start

```bash
cd web-ui
npm install
npm run dev
```

Öffne http://localhost:5173 in deinem Browser.

## 📋 Features

- **🔐 Authentication** — Benutzername + Passwort Login
- **📤 Upload** — Drag-drop Dokumentenupload (PDF, Images, Text)
- **🔍 Search** — Semantische Suche über deine Dokumente
- **💭 Reasoning** — KI Q&A über deine Dokumente
- **📚 Collections** — Verwalte Dokumentkollektion
- **⚙️ Admin Panel** — Einstellungen & System-Info

## 🏗️ Architecture

```
Frontend:  Vue 3 + Composition API
Build:     Vite (fast, modern)
State:     Pinia stores
Routing:   Vue Router (protected)
Styling:   Tailwind CSS
HTTP:      axios + interceptors
API:       RESTful (multimodal-rag backend)
```

## 📦 Dependencies

```json
{
  "vue": "^3.4.0",
  "vue-router": "^4.3.0",
  "pinia": "^2.1.0",
  "axios": "^1.6.0"
}
```

## 🔌 API Integration

Konfiguriere die API in `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
```

**Endpoints:**
- POST /auth/login
- POST /documents/upload
- POST /documents/search
- POST /documents/reason
- GET /collections
- DELETE /documents/{id}

## 🔐 Authentication

Login mit credentials und erhalte einen Bearer Token. Der Token wird automatisch bei jedem Request mitgesendet.

```typescript
// Login
POST /auth/login
Body: { username, password }
Response: { token, user_id, expires_in }

// Subsequent requests
Authorization: Bearer <token>
```

## 📚 Build & Deploy

```bash
# Development
npm run dev

# Build for production
npm run build
npm run preview

# Lint
npm run lint

# Type check
npm run type-check
```

## 📝 License

Multimodal RAG v1.1.0
