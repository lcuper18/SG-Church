# SG Church - Project Structure

This document explains the organization and structure of the SG Church project.

## Current Structure

```
SG_Church/
├── .github/                          # GitHub configuration
│   ├── ISSUE_TEMPLATE/              # Issue templates
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── documentation.md
│   └── pull_request_template.md     # PR template
│
├── docs/                            # Project documentation
│   ├── README.md                    # Documentation index
│   ├── DEPLOYMENT.md                # Deployment guide
│   ├── FAQ.md                       # Frequently asked questions
│   └── GLOSSARY.md                  # Glossary of terms
│
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── .prettierrc                      # Prettier configuration
│
├── ARCHITECTURE.md                  # Architecture documentation
├── CHANGELOG.md                     # Version history
├── CONTRIBUTING.md                  # Contribution guidelines
├── DATABASE.md                      # Database schema
├── LICENSE                          # MIT License
├── README.md                        # Main project readme
├── ROADMAP.md                       # Development roadmap
├── SECURITY.md                      # Security policy
├── TECH_STACK.md                    # Technology stack
│
├── package.json                     # Root package.json
├── tsconfig.base.json              # Base TypeScript config
├── tsconfig.json                   # TypeScript config
└── turbo.json                      # Turborepo configuration
```

## Planned Structure (To Be Created)

Once development begins, the project will expand to include:

```
SG_Church/
├── apps/                           # Applications
│   ├── web/                        # Main Next.js web application
│   │   ├── app/                    # Next.js App Router
│   │   ├── components/             # React components
│   │   ├── lib/                    # Utilities and helpers
│   │   ├── public/                 # Static assets
│   │   ├── styles/                 # Global styles
│   │   ├── middleware.ts           # Next.js middleware
│   │   ├── next.config.js          # Next.js config
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── mobile/ (Phase 4)           # React Native mobile app
│       ├── android/
│       ├── ios/
│       └── src/
│
├── packages/                       # Shared packages
│   ├── ui/                         # Shared UI components (shadcn/ui)
│   ├── database/                   # Prisma schema and client
│   ├── api/                        # tRPC routers
│   ├── auth/                       # Authentication logic
│   ├── email/                      # Email templates
│   ├── config/                     # Shared configs (ESLint, TS, etc.)
│   └── utils/                      # Shared utilities
│
├── services/                       # Backend services
│   ├── worker/                     # Background job worker (BullMQ)
│   └── api/ (Phase 4)             # Standalone API service
│
├── scripts/                        # Utility scripts
│   ├── seed.ts                     # Database seeding
│   ├── migrate.ts                  # Migration utilities
│   └── setup.ts                    # Setup script
│
└── tests/                          # E2E and integration tests
    ├── e2e/                        # Playwright tests
    └── integration/                # Integration tests
```

## Key Directories

### `/apps/web`
Main Next.js application serving the church management platform.

**Key subdirectories:**
- `app/` - App Router pages and layouts
- `app/api/` - API routes (including tRPC endpoint)
- `app/(auth)/` - Authentication pages
- `app/(dashboard)/` - Main dashboard and features
- `components/` - React components
- `lib/` - Utilities, helpers, and configurations

### `/packages`
Reusable packages shared across applications.

**Key packages:**
- `@sg-church/ui` - Shared UI components
- `@sg-church/database` - Prisma client and types
- `@sg-church/api` - tRPC API definitions
- `@sg-church/auth` - Authentication utilities
- `@sg-church/email` - Email templates and sending

### `/services`
Background services and workers.

**Services:**
- `worker` - BullMQ worker for background jobs
- `api` - Standalone API service (Phase 4)

## Configuration Files

### Root Level
- **package.json**: Root package with workspaces
- **turbo.json**: Turborepo pipeline configuration
- **tsconfig.base.json**: Base TypeScript config extended by all packages
- **tsconfig.json**: Root TypeScript config
- **.prettierrc**: Code formatting rules
- **.gitignore**: Git ignore patterns
- **.env.example**: Environment variables template

### Per Package/App
Each package and app will have:
- Own `package.json` with dependencies
- Own `tsconfig.json` extending the base
- Own build/dev scripts

## Naming Conventions

### Files
- **Components**: PascalCase (e.g., `MemberCard.tsx`)
- **Utilities**: camelCase (e.g., `formatDate.ts`)
- **Types**: PascalCase with `.types.ts` suffix (e.g., `Member.types.ts`)
- **API Routes**: kebab-case (e.g., `create-member.ts`)
- **Tests**: Same as source with `.test.ts` or `.spec.ts` suffix

### Directories
- **Features/Modules**: kebab-case (e.g., `member-management/`)
- **Components**: PascalCase if representing a single component
- **Utilities**: lowercase (e.g., `lib/`, `utils/`)

## Import Aliases

The following import aliases will be configured:

```typescript
// In apps/web
import { Button } from '@/components/ui/button'
import { prisma } from '@/lib/prisma'
import { getCurrentUser } from '@/lib/auth'

// Across the monorepo
import { Button } from '@sg-church/ui'
import { prisma } from '@sg-church/database'
import { memberRouter } from '@sg-church/api'
```

## Development Workflow

### Starting Development
```bash
# Install dependencies
pnpm install

# Generate Prisma client
pnpm db:generate

# Run migrations
pnpm db:migrate

# Seed database (optional)
pnpm db:seed

# Start development servers
pnpm dev
```

### Running Tests
```bash
# Run all tests
pnpm test

# Run E2E tests
pnpm test:e2e

# Type checking
pnpm type-check
```

### Building
```bash
# Build all apps and packages
pnpm build

# Build specific app
pnpm --filter web build
```

## Database Organization

### Schema Strategy
- **Public schema**: Contains `tenants` table and shared lookups
- **Per-tenant schemas**: Each church gets its own PostgreSQL schema
- **Naming**: Schemas named as `tenant_<uuid>` (e.g., `tenant_123e4567`)

### Migrations
- Migrations stored in `packages/database/prisma/migrations/`
- Public schema migrations separate from tenant migrations
- Migration tools handle creating schemas for new tenants

## Documentation Organization

### `/docs`
Contains in-depth guides and references:
- Architecture decisions
- Deployment procedures
- API documentation
- User guides
- FAQ and troubleshooting

### Root Level
High-level project information:
- README: Project overview
- CONTRIBUTING: How to contribute
- ROADMAP: Development plan
- CHANGELOG: Release history

## Next Steps

After approval of this planning phase, the next actions will be:

1. **Initialize Monorepo**
   - Create `apps/web/` with Next.js
   - Create `packages/` structure
   - Set up Turborepo pipelines

2. **Setup Database**
   - Initialize Prisma in `packages/database`
   - Create initial schemas
   - Set up migrations

3. **Configure Development Environment**
   - Setup ESLint and Prettier
   - Configure testing frameworks
   - Setup CI/CD pipelines

4. **Begin Phase 1 Development**
   - Start Sprint 1 tasks
   - Implement authentication
   - Build initial UI layouts

---

For questions about project structure, see [CONTRIBUTING.md](./CONTRIBUTING.md) or open a discussion on GitHub.
