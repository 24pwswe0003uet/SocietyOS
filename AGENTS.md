# SocietyOS AI — Project Guide (AGENTS.md)

> **This file is the permanent source of truth for all development on SocietyOS AI.**
> Every coding session must read this file before making changes.

---

## 1. Product Vision

SocietyOS AI is the operating system for university society events. It transforms a
natural-language event idea into a complete, submission-ready event package — proposal,
budget, compliance checklist, approval timeline, sponsorship materials, task board, and
progress dashboard — in under two minutes.

Long-term, the platform accumulates institutional memory: every completed event teaches
the system what works at each university, making each subsequent event cheaper, faster,
and more likely to be approved.

## 2. Project Objectives

1. Eliminate the 40–60 hours societies spend manually organizing each event.
2. Reduce proposal rejection rates from 30–40% to below 15%.
3. Provide AI-generated, human-editable event documents that match university standards.
4. Build a multi-agent orchestration system powered by Gemini.
5. Create institutional memory that improves with every completed event.
6. Deliver a production-grade B2B SaaS product targeting Pakistan's 200+ universities.

## 3. PRD Summary (v2.2)

| Requirement | ID     | Description |
|-------------|--------|-------------|
| Society Profile Setup | FR-000 | One-time onboarding: society name, university, department, advisor, type. Auto-generates approval chain. |
| Natural Language Event Creation | FR-001 | Free-text event description → structured EventRecord with AI extraction. |
| University Policy Analysis | FR-002 | Three modes: direct upload, prospectus parsing, questionnaire fallback. Outputs PolicyData. |
| Proposal Generator | FR-003 | Full event proposal with 8 sections. PDF/DOCX export. |
| Budget Planning | FR-004 | Itemized budget across 7 categories. 10% contingency default. XLSX export. |
| Sponsorship Agent | FR-005 | Gold/Silver/Bronze tiers, benefit grid, 3 personalized outreach emails. |
| Approval Workflow | FR-006 | Sequenced timeline with backward-calculated deadlines from event date. |
| Task Assignment | FR-007 | Tasks across 6 teams with owner, due date, priority, dependencies. |
| Progress Dashboard | FR-008 | Approval tracker, Kanban, Gantt, budget burn, sponsor pipeline. Real-time via WebSocket. |

**Business Model**: B2B SaaS — Society Plan (PKR 2,500/mo), Pay-per-event (PKR 800), University License (PKR 150,000/yr).

**Target Market**: Pakistan — 200+ HEC-registered universities, ~6,000 societies, Year 1 target 300 societies (5% penetration).

## 4. Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS | SSR/SSG, type safety, rapid styling |
| UI Components | Radix UI primitives + custom design system | Accessible, unstyled primitives we control |
| Backend | FastAPI (Python 3.11+) | Native async, SSE/WebSocket built-in, auto OpenAPI docs |
| Database | PostgreSQL 16 | Relational integrity, JSON support, pgvector extension |
| Vector Storage | pgvector | Semantic memory without a separate vector DB |
| Cache / Pub-Sub | Redis | Session cache, real-time pub/sub for dashboard, background job queue |
| AI Engine | Gemini 2.0 Flash (via backend) | 1M-token context, speed, free tier for development |
| Real-Time | Server-Sent Events (SSE) for generation, WebSocket for dashboard | SSE is simpler for one-way streaming; WS for bidirectional dashboard |
| PDF Generation | WeasyPrint | CSS-based layout, no headless browser |
| DOCX Generation | python-docx | Native .docx creation |
| XLSX Generation | XlsxWriter | Native .xlsx with formulas and formatting |
| Authentication | JWT (access + refresh tokens) | Stateless, works across frontend/backend split |
| File Storage | Local filesystem (dev), S3-compatible (prod) | Simple migration path |
| Migrations | Alembic | SQLAlchemy-compatible, versioned migrations |
| ORM | SQLAlchemy 2.0 (async) | Type-safe, async-first, Alembic integration |
| Testing | pytest (backend), Jest + React Testing Library (frontend) | Industry standard |
| Deployment | Vercel (frontend), Railway/Render (backend), Supabase (DB) | PRD-recommended stack |

## 5. Architecture Decisions

### 5.1 Frontend Architecture
- **Next.js 14 App Router** with route groups: `(auth)` for public auth pages, `(dashboard)` for protected app pages.
- **Server Components** by default; Client Components only where interactivity is required (forms, real-time, dropdowns).
- **API calls** go through a typed client library in `frontend/src/lib/api.ts`, never direct fetch in components.
- **State management**: React Context for auth/user state; no global state library needed initially.
- **Form handling**: React Hook Form + Zod validation, mirroring backend schemas.

### 5.2 Backend Architecture
- **Layered structure**: Routes → Services → Repositories → Models.
- **Routes** (`api/v1/endpoints/`) handle HTTP concerns only: parse request, call service, return response.
- **Services** (`services/`) contain business logic, orchestration, AI calls.
- **Models** (`models/`) are SQLAlchemy ORM classes. One file per entity.
- **Schemas** (`schemas/`) are Pydantic models for request/response validation.
- **Dependency injection** via FastAPI's `Depends()` for DB sessions, current user, permissions.

### 5.3 Database Architecture
- **PostgreSQL 16** with `pgvector` extension for semantic memory.
- **Alembic** for all schema migrations. Never modify the DB manually.
- **UUIDs** as primary keys for all entities.
- **Timestamps**: `created_at` and `updated_at` on every table.
- **Soft deletes**: `deleted_at` column where data retention matters.
- **Tenant isolation**: Every query scoped by `society_id` or `university_id`.

### 5.4 Authentication & Authorization
- **JWT-based**: Short-lived access tokens (15 min), long-lived refresh tokens (7 days).
- **Password hashing**: bcrypt via `passlib`.
- **Role-based access**: Roles stored in `society_memberships` table with enum role column.
- **Backend enforcement**: Every protected endpoint checks permissions via dependency.
- **Frontend**: Auth context wraps the app; protected routes redirect unauthenticated users.

### 5.5 AI Orchestration Architecture
- **Provider abstraction**: `services/ai/provider.py` defines the interface; `services/ai/gemini.py` implements it.
- **Orchestrator**: `services/agents/orchestrator.py` loads context, determines agent order, runs agents, validates outputs.
- **Specialist agents**: Each agent is a separate class in `services/agents/` with defined input/output schemas.
- **Structured output**: Every agent returns validated Pydantic models, never raw text.
- **Model config**: Model name, temperature, and tokens are environment variables, not hardcoded.
- **Never expose API keys to the frontend.** All AI calls go through the backend.

### 5.6 File Upload & Storage
- **Backend validates** all uploads: file type, size, content sniffing.
- **Allowed types**: PDF, DOCX, images (PNG/JPG for logos).
- **Max size**: 50MB per file (for large prospectuses).
- **Storage**: Local `uploads/` directory in dev; S3-compatible in production.
- **Access control**: Files served through authenticated API endpoints, never directly.

### 5.7 API Conventions
- **Base path**: `/api/v1/`
- **RESTful resources**: `/api/v1/events`, `/api/v1/societies`, `/api/v1/events/{id}/proposal`
- **Consistent response envelope**:
  ```json
  {
    "success": true,
    "data": { ... },
    "message": "Event created successfully"
  }
  ```
- **Error envelope**:
  ```json
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Budget target is required",
      "details": [...]
    }
  }
  ```
- **Pagination**: `?page=1&per_page=20` returning `{ data, total, page, per_page, pages }`
- **HTTP status codes**: 200 success, 201 created, 400 validation, 401 unauthorized, 403 forbidden, 404 not found, 422 unprocessable, 500 server error.

### 5.8 Error-Handling Strategy
- **Backend**: Global exception handler in middleware catches all errors, logs them, returns structured error response.
- **AI failures**: Retry up to 2 times with exponential backoff. Surface partial failures to the user.
- **Frontend**: API client catches errors, shows toast notifications, never shows raw stack traces.
- **Validation errors**: Backend returns field-level errors; frontend displays them inline.

### 5.9 Security Strategy
- Environment variables for all secrets (`.env` files, never committed).
- CORS restricted to known frontend origins.
- Rate limiting on auth endpoints (10 req/min) and AI endpoints (5 req/min).
- SQL injection prevention via ORM parameterized queries.
- XSS prevention via React's default escaping + CSP headers.
- File upload validation (type, size, content-type verification).
- Uploaded documents treated as untrusted content — never executed or used as system instructions.
- Tenant isolation enforced at the query level, not just the UI level.

### 5.10 Testing Strategy
- **Backend unit tests**: pytest, covering services, schemas, utils.
- **Backend integration tests**: pytest with test database, covering API endpoints.
- **Frontend unit tests**: Jest + React Testing Library for components.
- **E2E tests**: Playwright (Phase 8).
- **AI tests**: Mock Gemini responses for deterministic testing; live integration tests in CI.
- **Minimum coverage target**: 70% for services, 80% for schemas/validation.

### 5.11 Deployment Strategy
- **Frontend**: Vercel (auto-deploy from main branch).
- **Backend**: Railway or Render (Docker container).
- **Database**: Supabase PostgreSQL (pgvector enabled).
- **Redis**: Railway or Upstash.
- **File Storage**: Supabase Storage or S3-compatible.
- **CI/CD**: GitHub Actions — lint, test, build on PR; deploy on merge to main.
- **Environments**: development (local), staging, production.

## 6. Folder Structure

```
societyos-ai/
├── AGENTS.md                          # THIS FILE — permanent project guide
├── docs/
│   ├── ARCHITECTURE.md                # Detailed architecture document
│   └── PROJECT_PROGRESS.md            # Phase tracker
│
├── frontend/
│   ├── src/
│   │   ├── app/                       # Next.js App Router
│   │   │   ├── (auth)/                # Auth route group (public)
│   │   │   │   ├── login/
│   │   │   │   └── register/
│   │   │   ├── (dashboard)/           # Protected route group
│   │   │   │   ├── dashboard/
│   │   │   │   ├── events/
│   │   │   │   ├── societies/
│   │   │   │   └── settings/
│   │   │   ├── api/                   # Next.js API routes (if needed for BFF)
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx               # Landing page
│   │   ├── components/
│   │   │   ├── ui/                    # Design system primitives
│   │   │   ├── layout/                # Shell, sidebar, nav
│   │   │   ├── forms/                 # Reusable form components
│   │   │   ├── events/                # Event-specific components
│   │   │   └── dashboard/             # Dashboard widgets
│   │   ├── lib/                       # Utilities, API client, helpers
│   │   ├── hooks/                     # Custom React hooks
│   │   ├── types/                     # TypeScript type definitions
│   │   ├── styles/                    # Global styles, Tailwind config
│   │   └── constants/                 # App-wide constants
│   ├── public/
│   │   └── images/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app factory
│   │   ├── config.py                  # Environment-based settings
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py          # Mounts all endpoint routers
│   │   │       └── endpoints/
│   │   │           ├── auth.py
│   │   │           ├── users.py
│   │   │           ├── societies.py
│   │   │           ├── events.py
│   │   │           ├── policy.py
│   │   │           ├── generation.py
│   │   │           ├── documents.py
│   │   │           ├── tasks.py
│   │   │           └── dashboard.py
│   │   ├── core/
│   │   │   ├── security.py            # JWT, password hashing
│   │   │   ├── dependencies.py        # FastAPI dependencies
│   │   │   └── exceptions.py          # Custom exception classes
│   │   ├── db/
│   │   │   ├── session.py             # Async engine + session factory
│   │   │   └── base.py                # Declarative base, metadata
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── university.py
│   │   │   ├── society.py
│   │   │   ├── event.py
│   │   │   ├── policy.py
│   │   │   ├── proposal.py
│   │   │   ├── budget.py
│   │   │   ├── sponsorship.py
│   │   │   ├── task.py
│   │   │   └── event_outcome.py
│   │   ├── schemas/                   # Pydantic request/response models
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── society.py
│   │   │   ├── event.py
│   │   │   ├── policy.py
│   │   │   ├── generation.py
│   │   │   └── common.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── society_service.py
│   │   │   ├── event_service.py
│   │   │   ├── policy_service.py
│   │   │   ├── ai/
│   │   │   │   ├── provider.py        # Abstract AI provider interface
│   │   │   │   └── gemini.py          # Gemini implementation
│   │   │   ├── agents/
│   │   │   │   ├── orchestrator.py    # Agent coordinator
│   │   │   │   ├── proposal_agent.py
│   │   │   │   ├── budget_agent.py
│   │   │   │   ├── sponsorship_agent.py
│   │   │   │   ├── approval_agent.py
│   │   │   │   └── task_agent.py
│   │   │   └── documents/
│   │   │       ├── pdf_service.py
│   │   │       ├── docx_service.py
│   │   │       └── xlsx_service.py
│   │   ├── middleware/
│   │   │   ├── error_handler.py
│   │   │   └── rate_limiter.py
│   │   └── utils/
│   │       ├── file_utils.py
│   │       └── text_utils.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── templates/
│   │   ├── pdf/
│   │   └── docx/
│   ├── uploads/                       # Dev file storage (gitignored)
│   ├── requirements.txt
│   └── .env.example
│
├── .gitignore
├── .env.example
└── README.md
```

## 7. Coding Standards

### Python (Backend)
- **Style**: PEP 8, enforced by `ruff`.
- **Type hints**: Required on all function signatures.
- **Docstrings**: Required on all public functions and classes.
- **Imports**: stdlib → third-party → local, separated by blank lines.
- **Async**: Use `async def` for all route handlers and DB operations.
- **Max line length**: 100 characters.
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants.

### TypeScript (Frontend)
- **Strict mode**: `"strict": true` in tsconfig.
- **Components**: Functional components only, arrow function syntax.
- **Props**: Defined as interfaces, not inline types.
- **Naming**: `PascalCase` for components/types, `camelCase` for functions/variables, `kebab-case` for files.
- **Exports**: Named exports preferred over default exports (except page components).
- **No `any`**: Use `unknown` or proper types.

### SQL / Database
- **Table names**: `snake_case`, plural (e.g., `societies`, `event_records`).
- **Column names**: `snake_case`.
- **Foreign keys**: `{referenced_table_singular}_id` (e.g., `society_id`).
- **Indexes**: On all foreign keys and frequently queried columns.
- **Enums**: Defined as PostgreSQL enums or SQLAlchemy Enum types.

## 8. Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Python files | snake_case | `event_service.py` |
| Python classes | PascalCase | `EventService` |
| Python functions | snake_case | `create_event()` |
| Python constants | UPPER_SNAKE | `MAX_UPLOAD_SIZE` |
| TS/React components | PascalCase file + export | `EventCard.tsx` → `EventCard` |
| TS hooks | camelCase with `use` prefix | `useAuth.ts` → `useAuth()` |
| TS utilities | camelCase | `formatCurrency.ts` |
| API endpoints | kebab-case in URL | `/api/v1/generate-all` |
| DB tables | snake_case, plural | `society_memberships` |
| DB columns | snake_case | `faculty_advisor_name` |
| Env variables | UPPER_SNAKE | `GEMINI_API_KEY` |
| CSS classes | Tailwind utilities | `className="flex items-center"` |

## 9. UI/UX Design Principles

1. **Professional B2B SaaS** — not a student project. Clean, institutional, trustworthy.
2. **Information density over decoration** — every pixel earns its place.
3. **Consistent design system** — colors, spacing, typography, component states defined once.
4. **Mobile-responsive** — dashboard usable on phones.
5. **Progressive disclosure** — show summary first, details on demand.
6. **Loading states everywhere** — skeleton loaders, never empty flashes.
7. **Empty states with guidance** — tell users what to do, not just "no data."
8. **Error states that help** — explain what went wrong and what to do next.
9. **No AI branding on exports** — generated documents look like the user wrote them.
10. **Accessibility** — semantic HTML, keyboard navigation, sufficient contrast.

### Design Tokens
- **Primary**: Indigo-600 (`#4F46E5`) — intelligence, trust
- **Secondary**: Slate-600 (`#475569`) — professionalism
- **Success**: Emerald-600 (`#059669`)
- **Warning**: Amber-500 (`#F59E0B`)
- **Error**: Red-600 (`#DC2626`)
- **Background**: White / Slate-50
- **Text**: Slate-900 (primary), Slate-500 (secondary)
- **Border radius**: `0.5rem` (cards), `0.375rem` (inputs/buttons)
- **Font**: Inter (system fallback: `-apple-system, sans-serif`)

## 10. API Conventions

See Section 5.7 for full details. Summary:

- All endpoints under `/api/v1/`.
- JSON request and response bodies.
- Consistent success/error envelope.
- Bearer token authentication via `Authorization` header.
- Pagination on list endpoints.
- Standard HTTP status codes.

### Key Endpoints (from PRD)
| Endpoint | Method | Agent |
|----------|--------|-------|
| `/api/v1/auth/register` | POST | — |
| `/api/v1/auth/login` | POST | — |
| `/api/v1/auth/refresh` | POST | — |
| `/api/v1/users/me` | GET | — |
| `/api/v1/societies` | POST | FR-000 |
| `/api/v1/societies/{id}/profile` | GET/PUT | FR-000 |
| `/api/v1/events` | POST | FR-001 |
| `/api/v1/events/{id}` | GET/PUT | — |
| `/api/v1/events/{id}/policy` | POST | FR-002 |
| `/api/v1/events/{id}/proposal` | POST/GET | FR-003 |
| `/api/v1/events/{id}/budget` | POST/GET | FR-004 |
| `/api/v1/events/{id}/sponsorship` | POST/GET | FR-005 |
| `/api/v1/events/{id}/approvals` | POST/GET | FR-006 |
| `/api/v1/events/{id}/tasks` | POST/GET | FR-007 |
| `/api/v1/events/{id}/dashboard` | GET (WS) | FR-008 |
| `/api/v1/events/{id}/generate-all` | POST | Orchestrator |
| `/api/v1/events/{id}/outcome` | POST | Post-event |
| `/api/v1/exports/{id}/{format}` | GET | Export |

## 11. Database Rules

1. **All migrations via Alembic** — no manual DDL.
2. **UUIDs for primary keys** — `uuid4` generated in Python.
3. **Timestamps on every table** — `created_at`, `updated_at`.
4. **Foreign keys enforced** — cascade deletes only where explicitly justified.
5. **Indexes** on all foreign keys, `email`, `status`, `university_id`.
6. **No raw SQL in route handlers** — always go through ORM or repository layer.
7. **Connection pooling** — SQLAlchemy async pool, sized for concurrent agent execution.
8. **Enum types** for status fields — defined in models, mirrored in Pydantic schemas.
9. **Tenant isolation** — every query that returns society data must filter by the user's authorized societies.

## 12. Authentication & Security Rules

1. **JWT tokens** — access (15 min) + refresh (7 days).
2. **bcrypt password hashing** — minimum 12 rounds.
3. **Never store tokens in localStorage** — use httpOnly cookies or secure memory.
4. **Backend validates every request** — never trust frontend role checks alone.
5. **Rate limiting** — 10/min on auth, 5/min on AI generation, 100/min general.
6. **CORS** — whitelist only the frontend origin(s).
7. **Secrets in `.env`** — `.env` is gitignored; `.env.example` documents required variables.
8. **File uploads validated** — type, size, magic bytes checked on backend.
9. **Uploaded documents are untrusted** — never use as system prompts or executable instructions.
10. **Multi-tenancy** — a user can only access their own societies' data.

## 13. AI Integration Rules

1. **All AI calls go through the backend** — never expose API keys to the browser.
2. **Provider abstraction** — an interface that Gemini implements; swappable for other models.
3. **Structured output** — agents return Pydantic-validated data, not raw strings.
4. **Model configuration via env vars** — model name, temperature, max tokens.
5. **Retry with backoff** — 2 retries, exponential backoff on rate limit or transient errors.
6. **Timeout** — 120 seconds per agent call; fail gracefully after.
7. **Streaming** — SSE for generation progress; each agent reports start/progress/complete.
8. **Cost awareness** — log token usage per call for monitoring.
9. **No hallucination in policy** — confidence scores on extracted data; flag uncertain fields.
10. **Idempotency** — re-generating an event package creates a new version, never corrupts the previous one.

## 14. Testing Requirements

1. Every service function must have at least one unit test.
2. Every API endpoint must have an integration test for the happy path and primary error case.
3. AI agent tests use mocked Gemini responses for deterministic results.
4. Database tests run against a test PostgreSQL instance (not SQLite).
5. Frontend component tests verify rendering and user interaction.
6. E2E tests (Phase 8) cover the complete user journey.
7. Tests must pass before merging to main.

## 15. Development Phases

| Phase | Name | Scope |
|-------|------|-------|
| **0** | Repository Audit & Architecture | Inspect repo, define architecture, create this file, ARCHITECTURE.md, PROJECT_PROGRESS.md |
| **1** | Platform Foundation & Authentication | FastAPI setup, DB models (User, University, Society), auth, frontend shell, design system |
| **2** | Society Setup & Event Creation | FR-000, FR-001: onboarding wizard, NL event creation, Gemini extraction |
| **3** | University Policy Intelligence | FR-002: 3 input modes, document parsing, PolicyData output, human review |
| **4** | AI Agent Engine & Event Generation | Orchestrator + 5 specialist agents (FR-003–FR-007), SSE streaming |
| **5** | Generated Documents & Export System | Proposal/budget/sponsorship editors, PDF/DOCX/XLSX export engine |
| **6** | Event Management Dashboard | FR-006–FR-008: approval tracker, Kanban, Gantt, budget burn, sponsor pipeline, WebSocket |
| **7** | Institutional Memory & Learning | 3-layer memory, EventOutcome, pgvector semantic retrieval, learning loop |
| **8** | QA, Security & Deployment | Full audit, E2E tests, security hardening, production deployment |

## 16. Phase Completion Checklist

Before proceeding to the next phase, verify:

- [ ] Application runs without critical errors.
- [ ] Implemented features work against the real backend.
- [ ] Database changes and migrations are verified.
- [ ] Authorization and data isolation are tested.
- [ ] Existing functionality has not been broken.
- [ ] Relevant automated tests pass.
- [ ] AGENTS.md and PROJECT_PROGRESS.md are updated.
- [ ] Coding agent provides a clear completion report.

## 17. Known Issues & Technical Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Gemini-first, single model for hackathon | 1M token context, speed, free tier (PRD §06) | Decided |
| Provider abstraction from day one | Production may add Claude Sonnet for quality-sensitive agents | Decided |
| JWT over session cookies | Simpler for separate frontend/backend deployment | Decided |
| SSE for generation, WebSocket for dashboard | SSE is simpler for one-way agent progress; WS for bidirectional dashboard sync | Decided |
| Local file storage in dev, S3 in prod | Avoid S3 dependency during development | Decided |
| Radix UI for component primitives | Accessible, unstyled — we control the look | Decided |
| No Django — FastAPI only | Async-native, SSE/WS built-in, matches PRD direction | Decided |

### Open Questions
1. **Embedding model for pgvector**: Use Gemini's embedding API or a local model? → Decide in Phase 7.
2. **Email delivery for sponsorship outreach**: Which provider (SendGrid, Resend, etc.)? → Decide in Phase 5.
3. **Calendar export format**: .ics generation library? → Decide in Phase 6.
4. **OCR for scanned PDFs**: Tesseract or cloud OCR service? → Decide in Phase 3.
