# SocietyOS AI — Architecture Document

> Last updated: Phase 0 (November 2026)

---

## 1. System Overview

SocietyOS AI is a three-tier web application with an AI orchestration layer:

```
┌─────────────────────────────────────────────────────────┐
│                      FRONTEND                           │
│           Next.js 14 · TypeScript · Tailwind            │
│                                                         │
│  Landing ─── Auth ─── Dashboard ─── Event Management    │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS (REST + SSE + WebSocket)
┌───────────────────────┴─────────────────────────────────┐
│                      BACKEND                            │
│              FastAPI · Python · Async                    │
│                                                         │
│  Auth ─── API Layer ─── Services ─── AI Engine          │
│                                                         │
│  ┌────────────────────────────────────────────────┐     │
│  │            AI ORCHESTRATOR                      │     │
│  │                                                 │     │
│  │  Proposal · Budget · Sponsorship · Approvals    │     │
│  │  Tasks · Policy Analysis · Post-Event           │     │
│  └────────────────────┬───────────────────────────┘     │
│                       │                                  │
└───────────┬───────────┼──────────┬──────────────────────┘
            │           │          │
    ┌───────┴───┐  ┌────┴────┐  ┌─┴──────────┐
    │PostgreSQL │  │ Gemini  │  │   Redis     │
    │ +pgvector │  │   API   │  │ Cache/PubSub│
    └───────────┘  └─────────┘  └────────────┘
```

## 2. Frontend Architecture

### 2.1 App Router Structure

```
src/app/
├── layout.tsx              # Root layout: fonts, providers, global styles
├── page.tsx                # Public landing page
├── (auth)/
│   ├── layout.tsx          # Centered card layout for auth
│   ├── login/page.tsx
│   └── register/page.tsx
└── (dashboard)/
    ├── layout.tsx          # Sidebar + topbar + main content area
    ├── dashboard/page.tsx  # Overview / home
    ├── events/
    │   ├── page.tsx        # Event list
    │   ├── new/page.tsx    # Create event (NL input)
    │   └── [id]/
    │       ├── page.tsx    # Event detail
    │       ├── proposal/   # Proposal editor
    │       ├── budget/     # Budget editor
    │       ├── tasks/      # Kanban board
    │       └── dashboard/  # Event dashboard
    ├── societies/
    │   ├── page.tsx        # Society list / management
    │   └── setup/page.tsx  # Onboarding wizard
    └── settings/page.tsx   # User settings
```

### 2.2 Component Organization

```
components/
├── ui/                     # Design system atoms
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Card.tsx
│   ├── Badge.tsx
│   ├── Dialog.tsx
│   ├── Select.tsx
│   ├── Tabs.tsx
│   ├── Toast.tsx
│   ├── Skeleton.tsx
│   └── DataTable.tsx
├── layout/
│   ├── Sidebar.tsx
│   ├── TopBar.tsx
│   ├── AppShell.tsx
│   └── MobileNav.tsx
├── forms/
│   ├── SocietyForm.tsx
│   ├── EventForm.tsx
│   └── PolicyUpload.tsx
├── events/
│   ├── EventCard.tsx
│   ├── EventList.tsx
│   ├── NLEventInput.tsx
│   ├── EventReview.tsx
│   └── GenerationProgress.tsx
└── dashboard/
    ├── ApprovalTracker.tsx
    ├── KanbanBoard.tsx
    ├── GanttTimeline.tsx
    ├── BudgetBurn.tsx
    └── SponsorPipeline.tsx
```

### 2.3 Data Flow

```
User Action
  → Component calls hook (e.g., useCreateEvent)
    → Hook calls API client (lib/api.ts)
      → API client sends HTTP request with JWT
        → Backend processes request
          → Response returned
        → Hook updates local state
      → Component re-renders
```

### 2.4 Real-Time Architecture

**SSE (Generation Progress)**:
```
POST /api/v1/events/{id}/generate-all
  → Backend starts orchestrator
  → SSE stream sends: { agent: "proposal", status: "running" }
  → SSE stream sends: { agent: "proposal", status: "complete", data: {...} }
  → SSE stream sends: { agent: "budget", status: "running" }
  → ...
  → SSE stream closes on completion or error
```

**WebSocket (Dashboard)**:
```
WS /api/v1/events/{id}/dashboard
  → Client authenticates via token in first message
  → Server subscribes to Redis pub/sub for this event
  → Any change (task update, approval change) publishes to channel
  → WebSocket pushes update to all connected clients
```

## 3. Backend Architecture

### 3.1 Layer Diagram

```
HTTP Request
  │
  ├── Middleware (error handler, rate limiter, CORS)
  │
  ├── Route Handler (api/v1/endpoints/)
  │     │ Parse request, validate input, check auth
  │     │
  │     ├── Dependencies (core/dependencies.py)
  │     │     │ get_db_session, get_current_user, check_permissions
  │     │
  │     ├── Service Layer (services/)
  │     │     │ Business logic, orchestration
  │     │     │
  │     │     ├── AI Services (services/ai/)
  │     │     │     │ Provider interface, Gemini implementation
  │     │     │
  │     │     ├── Agent Services (services/agents/)
  │     │     │     │ Orchestrator, specialist agents
  │     │     │
  │     │     └── Document Services (services/documents/)
  │     │           │ PDF, DOCX, XLSX generation
  │     │
  │     └── Schema Validation (schemas/)
  │           │ Pydantic models for request/response
  │
  └── Data Layer
        ├── ORM Models (models/)
        ├── Database Session (db/session.py)
        └── Alembic Migrations (alembic/)
```

### 3.2 Key Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| Repository | Data access in services | Isolate DB queries from business logic |
| Strategy | AI provider interface | Swap Gemini for Claude/other without changing agents |
| Observer | Redis pub/sub → WebSocket | Decouple data changes from real-time delivery |
| Factory | Agent creation in orchestrator | Each agent shares interface but has distinct logic |
| Builder | Document generation templates | Build complex PDFs/DOCX section by section |

### 3.3 Configuration

All configuration via environment variables with Pydantic `BaseSettings`:

```python
class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SocietyOS AI"
    APP_ENV: str = "development"      # development | staging | production
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str                  # postgresql+asyncpg://...
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AI
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.3
    GEMINI_MAX_TOKENS: int = 8192
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
```

## 4. Database Architecture

### 4.1 Entity-Relationship Diagram

```
┌──────────┐     ┌──────────────┐     ┌───────────────┐
│  users   │────<│  society_    │>────│  societies    │
│          │     │  memberships │     │               │
│ id (PK)  │     │              │     │ id (PK)       │
│ email    │     │ user_id (FK) │     │ name          │
│ password │     │ society_id   │     │ university_id │
│ name     │     │ role (enum)  │     │ department    │
└──────────┘     └──────────────┘     │ advisor_name  │
                                      │ advisor_email │
                                      │ type (enum)   │
                                      │ approval_chain│
                                      └───────┬───────┘
                                              │
                                              │ 1:N
                                              ▼
┌────────────────┐     ┌──────────────┐     ┌───────────────┐
│ universities   │────<│  societies   │────<│ event_records │
│                │     │              │     │               │
│ id (PK)        │     │              │     │ id (PK)       │
│ name           │     │              │     │ society_id    │
│ city           │     │              │     │ title         │
│ country        │     │              │     │ event_type    │
└────────────────┘     └──────────────┘     │ description   │
                                            │ audience_size │
                                            │ date          │
                                            │ budget_target │
                                            │ status (enum) │
                                            └───────┬───────┘
                                                    │
                        ┌───────────┬───────────┬───┴───┬───────────┐
                        ▼           ▼           ▼       ▼           ▼
                 ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐ ┌────────┐
                 │policy_   │ │proposal │ │budget_  │ │tasks │ │sponsor │
                 │data      │ │_docs    │ │plans    │ │      │ │_pkgs   │
                 └──────────┘ └─────────┘ └─────────┘ └──────┘ └────────┘
                                                    
                                            ┌───────────────┐
                                            │event_outcomes │
                                            │               │
                                            │ id (PK)       │
                                            │ event_id (FK) │
                                            │ approval_result│
                                            │ budget_variance│
                                            │ lessons_learned│
                                            │ embedding (vec)│
                                            └───────────────┘
```

### 4.2 Key Tables

| Table | Phase | Purpose |
|-------|-------|---------|
| `users` | 1 | User accounts |
| `universities` | 1 | University registry |
| `societies` | 1 | Society profiles with approval chain (JSONB) |
| `society_memberships` | 1 | User ↔ Society with role enum |
| `event_records` | 2 | Core event data |
| `policy_data` | 3 | Extracted university policies |
| `proposal_docs` | 4 | Generated proposals (JSONB sections) |
| `budget_plans` | 4 | Budget line items |
| `sponsorship_packages` | 4 | Sponsor tiers + email drafts |
| `approval_steps` | 4 | Approval workflow steps |
| `tasks` | 4 | Task board items |
| `event_outcomes` | 7 | Post-event actuals + pgvector embedding |

### 4.3 pgvector Setup (Phase 7)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE event_outcomes
  ADD COLUMN embedding vector(768);

CREATE INDEX ON event_outcomes
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

## 5. AI Orchestration Architecture

### 5.1 Agent Execution Flow

```
User clicks "Generate All"
  │
  ▼
Orchestrator.run(event_id)
  │
  ├── 1. Load EventRecord, SocietyProfile, PolicyData
  ├── 2. Validate all required inputs present
  ├── 3. Build shared EventContext
  │
  ├── 4. Execute PARALLEL group:
  │     ├── ProposalAgent.generate(context)  → ProposalDoc
  │     ├── BudgetAgent.generate(context)    → BudgetPlan
  │     └── SponsorshipAgent.generate(context) → SponsorshipPackage
  │
  ├── 5. Execute SEQUENTIAL (needs policy + profile):
  │     └── ApprovalAgent.generate(context)  → ApprovalTimeline
  │
  ├── 6. Execute AFTER approvals (needs timeline):
  │     └── TaskAgent.generate(context)      → TaskBoard
  │
  ├── 7. Validate all outputs
  ├── 8. Save to database
  └── 9. Publish completion event
```

### 5.2 Agent Interface

Every specialist agent implements:

```python
class BaseAgent(ABC):
    agent_name: str
    
    @abstractmethod
    async def generate(self, context: EventContext) -> AgentOutput:
        """Run the agent and return validated output."""
        pass
    
    @abstractmethod
    def get_prompt(self, context: EventContext) -> str:
        """Build the prompt for this agent."""
        pass
    
    @abstractmethod
    def validate_output(self, raw: dict) -> AgentOutput:
        """Validate and structure the raw AI response."""
        pass
```

### 5.3 Provider Abstraction

```python
class AIProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        pass
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        pass

class GeminiProvider(AIProvider):
    # Implements using google.generativeai SDK
    pass
```

## 6. Security Architecture

### 6.1 Authentication Flow

```
Register: POST /auth/register
  → Validate email uniqueness
  → Hash password (bcrypt, 12 rounds)
  → Create user record
  → Return access + refresh tokens

Login: POST /auth/login
  → Verify email exists
  → Verify password hash
  → Generate access token (15 min) + refresh token (7 days)
  → Return both tokens

Refresh: POST /auth/refresh
  → Validate refresh token
  → Generate new access token
  → Return new access token

Protected Request:
  → Extract Bearer token from Authorization header
  → Decode and validate JWT
  → Load user from token's sub claim
  → Check role permissions for the endpoint
  → Proceed or return 403
```

### 6.2 Authorization Matrix

| Action | President | Admin | Organizer | Sponsor Lead | Advisor | Uni Admin |
|--------|-----------|-------|-----------|-------------|---------|-----------|
| Create society | ✓ | — | — | — | — | ✓ |
| Edit society profile | ✓ | ✓ | — | — | — | ✓ |
| Create event | ✓ | ✓ | ✓ | — | — | — |
| Generate package | ✓ | ✓ | ✓ | — | — | — |
| Edit proposal | ✓ | ✓ | ✓ | — | — | — |
| Edit budget | ✓ | ✓ | — | — | — | — |
| Manage sponsors | ✓ | ✓ | — | ✓ | — | — |
| Update approvals | ✓ | ✓ | — | — | ✓ | ✓ |
| Assign tasks | ✓ | ✓ | ✓ | — | — | — |
| View dashboard | ✓ | ✓ | ✓ | ✓ | ✓ (read-only) | ✓ |
| Export documents | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Enter outcomes | ✓ | ✓ | — | — | — | — |

## 7. Deployment Architecture

### 7.1 Production Topology

```
                    ┌─────────────┐
                    │   Vercel    │
                    │  (Frontend) │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │   Railway   │
                    │  (Backend)  │
                    │   Docker    │
                    └──┬───┬───┬──┘
                       │   │   │
              ┌────────┘   │   └────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌─────────┐ ┌──────────┐
        │ Supabase │ │  Redis  │ │ Supabase │
        │ Postgres │ │(Upstash)│ │ Storage  │
        │+pgvector │ │         │ │ (Files)  │
        └──────────┘ └─────────┘ └──────────┘
```

### 7.2 Environment Variables

See `.env.example` in the repository root. Required variables:

```
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/societyos

# Redis
REDIS_URL=redis://localhost:6379

# Auth
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>

# AI
GEMINI_API_KEY=<from-google-ai-studio>

# CORS
CORS_ORIGINS=http://localhost:3000

# App
APP_ENV=development
```

## 8. Document Processing Pipeline

```
File Upload
  │
  ├── Validate (type, size, magic bytes)
  ├── Store (local dev / S3 prod)
  │
  ├── Extract Text
  │     ├── PDF → PyMuPDF or pdfplumber
  │     ├── DOCX → python-docx
  │     └── URL → httpx + BeautifulSoup
  │
  ├── Identify Relevant Sections (for prospectus)
  │     └── Gemini with section-identification prompt
  │
  ├── Extract Policy Data
  │     └── Gemini with structured extraction prompt
  │
  ├── Validate & Score Confidence
  │     └── Fields below 0.7 flagged for human review
  │
  └── Save PolicyData Record
```

## 9. Export Pipeline

```
Request Export (event_id, format)
  │
  ├── Load latest saved document data
  │
  ├── PDF (WeasyPrint)
  │     ├── Render HTML template with data
  │     ├── Apply CSS for print layout
  │     └── Generate PDF binary
  │
  ├── DOCX (python-docx)
  │     ├── Load template (.dotx if available)
  │     ├── Build sections programmatically
  │     └── Generate .docx binary
  │
  └── XLSX (XlsxWriter)
        ├── Create workbook
        ├── Write headers, data, formulas
        ├── Apply formatting
        └── Generate .xlsx binary
```

---

*This document is updated at the end of every development phase.*
