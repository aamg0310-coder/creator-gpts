# AGENTS.md — GPT Creator Platform

## Project Overview
Django REST platform for creating, managing, and chatting with AI chatbots. Uses OpenRouter for LLM inference and InsForge for RAG vector storage.

## Tech Stack
- **Backend:** Django 6.1 + DRF 3.18
- **Database:** SQLite (dev) / PostgreSQL + pgvector via InsForge (prod)
- **Frontend:** Server-side Django templates + vanilla JS
- **Auth:** Session-based with custom User model (admin/creator/user roles)
- **AI:** OpenRouter API (multi-model: GPT, Claude, Llama, Gemini, etc.)
- **RAG:** InsForge Edge Functions + pgvector embeddings

## Project Structure
```
creator-gpts/
├── apps/
│   ├── chatbots/          # Core app: Chatbot, ChatSession, ChatMessage models
│   │   ├── models.py      # Chatbot, ChatSession, ChatMessage, GeneralChatbot, ChatbotDocument
│   │   ├── views.py       # ChatbotViewSet, ChatSessionViewSet, ChatMessageViewSet
│   │   ├── serializers.py # All DRF serializers
│   │   ├── services.py    # RagService (RAG pipeline)
│   │   ├── memory_service.py  # ChatbotMemoryService (InsForge sync)
│   │   ├── insforge_client.py # InsForge REST client
│   │   ├── document_extract.py# Text extraction (PDF, DOCX, TXT)
│   │   ├── permissions.py # IsCreatorOrReadOnlyIfShared
│   │   ├── signals.py     # Auto-create GeneralChatbot, sync RAG on doc changes
│   │   ├── share_urls.py  # Public chatbot share view
│   │   ├── admin.py       # Django admin config
│   │   └── tests.py       # API tests
│   ├── users/             # Custom User model + auth views
│   │   ├── models.py      # User (AbstractUser) with roles
│   │   ├── views.py       # UserViewSet, register/login/logout views
│   │   ├── serializers.py # UserSerializer, RegisterSerializer, LoginSerializer
│   │   └── admin.py       # Custom UserAdmin
│   └── core/              # Shared utilities
│       ├── constants.py   # FREE_MODELS list
│       ├── validators.py  # validate_file_size
│       ├── views.py       # health_check, stats_view, page views
│       └── page_urls.py   # Template page routes
├── core/                  # Project config
│   ├── settings/
│   │   ├── base.py        # Shared settings
│   │   ├── development.py # Dev settings (SQLite, DEBUG=True)
│   │   └── production.py  # Prod settings (PostgreSQL, SSL)
│   └── urls.py            # Root URL config
├── templates/             # Django templates
│   ├── base.html          # Base layout with sidebar
│   └── pages/             # Page templates
├── static/                # Static files
│   ├── css/base.css       # Main styles + responsive
│   ├── css/editor.css     # Chatbot editor styles
│   └── js/editor.js       # Editor functionality
├── functions/rag/         # InsForge Edge Function (Deno/TypeScript)
├── migrations/insforge/   # InsForge SQL migrations
├── scripts/init_db.py     # Database initialization script
└── start_servers.sh       # Dev server startup script
```

## Key Models
- **Chatbot** — AI chatbot config (model, soul, instructions, funciones, documents)
- **ChatSession** — One active session per (chatbot, user) pair
- **ChatMessage** — Messages within a session (user or assistant)
- **GeneralChatbot** — Auto-created per user (asistente general)
- **ChatbotDocument** — Uploaded files for RAG indexing
- **User** — Custom model with role (admin/creator/user)

## RAG Pipeline (AGENTS.md System)
Each chatbot's instructions, soul, and capabilities are stored in InsForge vector DB as a structured document (like an AGENTS.md file). On every query:

1. **Retrieve bot memory** — `InsForgeClient.retrieve_bot_memory()` fetches the `memory_*.txt` file from vector DB
2. **Retrieve user documents** — `RagService.retrieve_documents()` searches uploaded docs
3. **Build system prompt** — Bot memory is injected FIRST: `[INSTRUCCIONES DEL CHATBOT — Lee y sigue estas instrucciones siempre]`
4. **Generate response** — LLM receives instructions before processing the user question

**Sync triggers:**
- Chatbot save (create/update) → `signals.py: sync_memory_on_chatbot_save`
- Document upload/delete → `signals.py: sync_memory_on_document_*`
- Memory format: `# AGENTS.MD — Instrucciones del Chatbot: {name}` with sections for Soul, Instructions, Capabilities, Actions

## API Endpoints
- `GET /api/chatbots/` — List chatbots (public if anon; own+shared+public if auth)
- `POST /api/chatbots/` — Create chatbot (requires can_create_chatbot)
- `GET/PATCH/DELETE /api/chatbots/<slug>/` — CRUD on chatbot
- `POST /api/chatbots/<slug>/share/` — Share with users / toggle public
- `POST /api/chatbots/<slug>/ask/` — Ask question → {answer, session_id}
- `DELETE /api/chatbots/<slug>/delete_documents/` — Delete RAG documents
- `GET/POST /api/sessions/` — List/create sessions (auth required)
- `GET/POST /api/sessions/<id>/messages/` — List/create messages (auth required)

## Page Routes
- `/` — Home
- `/mis-chatbots/` — My chatbots (creator dashboard)
- `/crear-chatbot/` — Create chatbot
- `/editar-chatbot/<slug>/` — Edit chatbot (split layout with preview)
- `/chat/<slug>/` — Chat with chatbot
- `/buscar/` — Search chatbots
- `/lista-chatbots/` — Public chatbot list
- `/<slug>/` — Shareable chatbot view
- `/register/`, `/login/`, `/logout/` — Auth pages
- `/account/` — User account

## Privacy & Security
- **Sessions are private:** Each user has their own session per chatbot. No session sharing between accounts.
- **Anonymous sessions:** Always isolated (new session per request, never shared).
- **User field read-only:** Cannot manipulate session ownership via API.
- **Access control:** `IsCreatorOrReadOnlyIfShared` — creators manage, shared users read, public readable.
- **XSS protection:** User content sanitized with `.replace(/</g, '&lt;')` in templates.
- **CSRF:** All fetch calls include CSRF token.
- **Delete protection:** Only creator or admin can delete chatbots.

## Responsive Design
- **Desktop:** Sidebar expanded (260px), split layout for editor
- **Tablet (≤768px):** Sidebar hidden, full-width content, stacked card actions
- **Mobile (≤600px):** Header stacks vertically, modal buttons full-width, editor panels stack
- No hover-to-expand sidebar on mobile (fixed hidden state)

## Delete Flow
1. User clicks "Eliminar" button (creator only)
2. Confirmation modal appears with chatbot name
3. User confirms → `DELETE /api/chatbots/{slug}/`
4. Backend checks `IsCreatorOrReadOnlyIfShared` permission
5. On success → redirect to "Mis Chatbots"
6. On error → alert with error message

## Environment Variables
Required in `.env.local`:
- `SECRET_KEY` — Django secret key
- `OPENROUTER_API_KEY` — OpenRouter API key
- `INSFORGE_BASE_URL` — InsForge project URL
- `INSFORGE_ANON_KEY` — InsForge anonymous key
- `APP_URL` — Application URL for CORS

## Development
```bash
# Start servers
bash start_servers.sh

# Or manually
python manage.py runserver 0.0.0.0:8000

# Initialize database with sample data
python scripts/init_db.py
```

## Recent Changes (2026-09-22)
- **Fixed chat rendering bug:** streamed replies used a duplicate DOM id (`stream-bubble`) + `getElementById`, so tokens were written into the *previous* answer (user text appeared after the bot reply and answers vanished until refresh). Now uses a direct `querySelector` reference per message.
- **Stream robustness:** rewritten promise chain — input always re-enabled, partial answers kept on screen with an "interrupted" notice, no blind re-send of the question (backend dedupes retries), last SSE line flushed on close, anti-double-submit flag.
- **Backend persistence:** `ask_stream` generator wrapped in `try/finally` — partial answers are always saved (survive refresh/disconnect); `X-Session-ID` header lets the client recover the session id even if the body fails; unanswered-retry dedupe in `ask/` and `ask_stream`.
- **Multiple conversations:** `_get_or_create_session` now *creates* a new session when no `session_id` is sent, so "Nueva conversación" produces separate history entries (previously `get_or_create` always reused one session).
- **Chat history UI:** sidebar ✕ replaced by a chevron "Ocultar historial" toggle; hidden state shows a floating "Mostrar historial" button; preference persisted in `localStorage`. Messages now render timestamps (backend passes `timestamp` in `existing_messages`).
- **Share page:** sends `session_id` so authenticated visitors keep a single conversation.
- **Tests:** new `ConversationPersistenceTests` (6 tests): separate sessions, session reuse, retry dedupe, answered-repeat allowed, partial answer saved on stream break, clean retry after zero-token failure.

## Recent Changes (2026-09-21)
- Fixed `NameError: ChatSession` (stale .pyc cache)
- Fixed session privacy: anonymous sessions now isolated
- Added delete chatbot button with confirmation modal
- Added responsive styles for all screen sizes
- Removed hover-to-expand sidebar on mobile
- Removed hamburger menu button on mobile
- Made `user` field read-only in session serializers
- Cleaned up unused imports across codebase
- Removed obsolete files: `apps/users/permissions.py`, empty directories, outdated docs
- **AGENTS.md system:** Chatbot instructions/soul now stored in InsForge vector DB and retrieved on every query as system context (like an AGENTS.md file)
- **SSL fix:** Added certifi + SSL context for Windows compatibility (avoids `CERTIFICATE_VERIFY_FAILED`)
- **Memory sync signal:** Chatbot save now auto-syncs memory to vector DB via Django signal
- **Null safety:** Answer endpoints now handle None responses gracefully
- **Removed `acciones` field:** Eliminated from Chatbot model, templates, JS, serializers, and RAG pipeline
- **Custom templates:** Users can create, save, and reuse their own chatbot templates via `ChatbotTemplate` model + API

<!-- INSFORGE:START -->
## InsForge backend

This project uses [InsForge](https://insforge.dev): an all-in-one, open-source Postgres-based backend (BaaS) that gives this app a database, authentication, file storage, edge functions, realtime, an AI model gateway, and payments through one platform.

- **Project:** **creator_chat** (API base `https://885xdbkm.us-east.insforge.app`)
- **Skills:** these InsForge skills are installed for supported coding agents. Reach for them before implementing any InsForge feature instead of guessing the API:
  - `insforge`: app code with the `@insforge/sdk` client (database CRUD, auth, storage, edge functions, realtime, AI, email, and Stripe payments).
  - `insforge-cli`: backend and infrastructure via the `insforge` CLI (projects, SQL, migrations, RLS policies, storage buckets, functions, secrets, payment setup, schedules, deploys).
  - `insforge-debug`: diagnosing failures (SDK/HTTP errors, RLS denials, auth and OAuth issues) and running security or performance audits.
  - `insforge-integrations`: wiring external auth providers (Clerk, Auth0, WorkOS, Better Auth, etc.) for JWT-based RLS, or the OKX x402 payment facilitator.
  - `find-skills`: discovering additional skills on demand.
- **Credentials:** app code reads keys from `.env.local`; the CLI reads `.insforge/project.json`. Never hardcode or commit keys.

Key patterns:

- Database inserts take an array: `insert([{ ... }])`.
- Reference users with `auth.users(id)`; use `auth.uid()` in RLS policies.
- For storage uploads, persist both the returned `url` and `key`.
<!-- INSFORGE:END -->
