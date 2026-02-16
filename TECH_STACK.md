# Stack Tecnológico - SG Church

Documentación completa de todas las tecnologías, herramientas y servicios utilizados en el proyecto.

## Tabla de Contenidos

- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Frontend](#frontend)
- [Backend](#backend)
- [Base de Datos](#base-de-datos)
- [Autenticación y Autorización](#autenticación-y-autorización)
- [Pagos y Procesamiento](#pagos-y-procesamiento)
- [Almacenamiento y Archivos](#almacenamiento-y-archivos)
- [Email y Comunicaciones](#email-y-comunicaciones)
- [Background Jobs](#background-jobs)
- [Infraestructura y Hosting](#infraestructura-y-hosting)
- [Monitoreo y Analytics](#monitoreo-y-analytics)
- [Herramientas de Desarrollo](#herramientas-de-desarrollo)
- [Versiones y Compatibilidad](#versiones-y-compatibilidad)

---

## Resumen Ejecutivo

### Decisión Clave: Stack Full-TypeScript

**Ventajas**:
- ✅ Type safety end-to-end (desde DB hasta UI)
- ✅ Excelente developer experience (IntelliSense, refactoring)
- ✅ Menos bugs en producción
- ✅ Código más mantenible
- ✅ Comunidad grande y activa

### Stack Principal

```
┌──────────────────────────────────────┐
│         FRONTEND                     │
│  Next.js 14 + React 18 + TypeScript  │
│  Tailwind CSS + shadcn/ui            │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         BACKEND                      │
│  Next.js API Routes + tRPC           │
│  NextAuth.js v5 (Auth)               │
└──────────────┬───────────────────────┘
               │
        ┌──────┴──────┬───────────┐
        │             │           │
┌───────▼─────┐ ┌────▼────┐ ┌────▼────┐
│ PostgreSQL  │ │  Redis  │ │  S3/    │
│ + Prisma    │ │ + BullMQ│ │ Supabase│
└─────────────┘ └─────────┘ └─────────┘
```

---

## Frontend

### Framework Principal

#### **Next.js 14+** 
![Next.js](https://img.shields.io/badge/Next.js-14+-black)

**Versión**: 14.1+ (App Router)

**Por qué Next.js**:
- ✅ **React Server Components**: Renderizado en servidor para performance
- ✅ **App Router**: File-based routing moderno
- ✅ **API Routes**: Backend y frontend en mismo proyecto
- ✅ **Image Optimization**: Automático con `next/image`
- ✅ **SEO-friendly**: SSR/SSG out of the box
- ✅ **TypeScript**: First-class support
- ✅ **Vercel Deploy**: Zero-config deployment

**Configuración**:
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['your-bucket.supabase.co'],
  },
  experimental: {
    serverActions: true,
  },
}

module.exports = nextConfig
```

**Alternativas consideradas**:
- ❌ Remix: Menos maduro, comunidad más pequeña
- ❌ Vite + React Router: Requiere más configuración
- ❌ Astro: No ideal para apps altamente dinámicas

---

### UI Framework

#### **React 18+**
![React](https://img.shields.io/badge/React-18+-61DAFB)

**Versión**: 18.2+

**Características usadas**:
- ✅ Server Components (Next.js integration)
- ✅ Suspense para lazy loading
- ✅ Error Boundaries
- ✅ Concurrent rendering
- ✅ Automatic batching

---

### Styling

#### **Tailwind CSS 3+**
![Tailwind](https://img.shields.io/badge/Tailwind-3+-38B2AC)

**Versión**: 3.4+

**Por qué Tailwind**:
- ✅ Utility-first = desarrollo rápido
- ✅ Purge CSS automático = bundle pequeño
- ✅ Design system consistente
- ✅ Dark mode built-in
- ✅ Responsive design fácil

**Configuración**:
```javascript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          // ... color palette
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

#### **shadcn/ui**

**Por qué shadcn/ui**:
- ✅ Componentes copiables (no npm package = control total)
- ✅ Accesibilidad (Radix UI primitives)
- ✅ Customizable completamente
- ✅ TypeScript out of the box
- ✅ Diseño moderno y profesional

**Componentes clave**:
- `Dialog`, `Popover`, `DropdownMenu` (modals e interacciones)
- `Form` (con React Hook Form integration)
- `Table`, `DataTable` (grids)
- `Card`, `Tabs`, `Badge` (layouts)
- `Button`, `Input`, `Select` (forms)

**Instalación**:
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button dialog form table
```

---

### Form Management

#### **React Hook Form 7+**
![React Hook Form](https://img.shields.io/badge/React_Hook_Form-7+-EC5990)

**Versión**: 7.50+

**Por qué**:
- ✅ Performance (uncontrolled components)
- ✅ Menos re-renders
- ✅ Excelente DX
- ✅ Integración con Zod para validación

**Ejemplo**:
```typescript
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const memberSchema = z.object({
  firstName: z.string().min(1, 'Required'),
  lastName: z.string().min(1, 'Required'),
  email: z.string().email().optional(),
})

function MemberForm() {
  const form = useForm({
    resolver: zodResolver(memberSchema),
  })
  
  return <form onSubmit={form.handleSubmit(onSubmit)}>...</form>
}
```

#### **Zod 3+**
![Zod](https://img.shields.io/badge/Zod-3+-3E67B1)

**Versión**: 3.22+

**Por qué**:
- ✅ TypeScript-first schema validation
- ✅ Inferencia automática de tipos
- ✅ Compartible entre frontend y backend
- ✅ Excellent error messages

---

### State Management

#### **TanStack Query (React Query) 5+**

**Versión**: 5.20+

**Por qué**:
- ✅ Server state management (cache, refetch)
- ✅ Optimistic updates
- ✅ Automatic garbage collection
- ✅ Integración perfecta con tRPC

**Nota**: Con tRPC, no necesitamos otro state manager global (Zustand, Redux) en la mayoría de casos.

#### **Zustand 4+** (opcional)

**Versión**: 4.5+

**Uso**:
- Client-side state simple (UI state, theme)
- Alternativa ligera a Redux

```typescript
import { create } from 'zustand'

const useStore = create((set) => ({
  theme: 'light',
  toggleTheme: () => set((state) => ({ 
    theme: state.theme === 'light' ? 'dark' : 'light' 
  })),
}))
```

---

### Data Tables

#### **TanStack Table v8**

**Versión**: 8.11+

**Por qué**:
- ✅ Headless (control total del UI)
- ✅ TypeScript-first
- ✅ Sorting, filtering, pagination built-in
- ✅ Server-side data support
- ✅ Column visibility, resizing

**Ejemplo con shadcn/ui**:
```bash
npx shadcn-ui@latest add data-table
```

---

### Charts y Visualización

#### **Recharts 2+**

**Versión**: 2.10+

**Por qué**:
- ✅ Componentes React nativos
- ✅ Fácil de usar
- ✅ Responsive
- ✅ Suficiente para dashboards financieros

**Tipos de gráficos usados**:
- Line Chart (tendencias de donaciones)
- Bar Chart (asistencia por servicio)
- Pie Chart (distribución demográfica)
- Area Chart (ingresos vs gastos)

**Alternativas**:
- Apache ECharts: Más potente pero más complejo
- Chart.js: No es React-native

---

### Rich Text Editing

#### **Tiptap 2+**

**Versión**: 2.1+

**Por qué**:
- ✅ Extensible (prosemirror-based)
- ✅ TypeScript support
- ✅ Excelente UX
- ✅ Markdown support

**Uso**: Editor de contenido de lecciones en LMS

---

## Backend

### API Layer

#### **tRPC 10+**
![tRPC](https://img.shields.io/badge/tRPC-10+-2596BE)

**Versión**: 10.45+

**Por qué tRPC**:
- ✅ **Type safety end-to-end**: Frontend sabe exactamente qué devuelve backend
- ✅ **No code generation**: Los tipos se infieren automáticamente
- ✅ **Excelente DX**: Autocomplete en frontend
- ✅ **Más rápido que GraphQL** para proyectos TypeScript full-stack

**Estructura**:
```typescript
// server/routers/_app.ts
import { router } from '../trpc'
import { membersRouter } from './members'
import { financeRouter } from './finance'
import { coursesRouter } from './courses'

export const appRouter = router({
  members: membersRouter,
  finance: financeRouter,
  courses: coursesRouter,
})

export type AppRouter = typeof appRouter
```

**Cliente en frontend**:
```typescript
// lib/trpc.ts
import { createTRPCReact } from '@trpc/react-query'
import type { AppRouter } from '@/server/routers/_app'

export const trpc = createTRPCReact<AppRouter>()

// En componente:
const members = trpc.members.list.useQuery()
//    ^? const members: Member[]  ← Fully typed!
```

**Alternativas**:
- ❌ GraphQL: Más verboso, necesita codegen
- ❌ REST: No type-safe sin herramientas adicionales
- ❌ gRPC: Overkill para web app

---

### Runtime

#### **Node.js 20+**
![Node.js](https://img.shields.io/badge/Node.js-20+-339933)

**Versión**: 20.11+ LTS

**Por qué Node 20**:
- ✅ Performance improvements
- ✅ Native test runner
- ✅ Mejor soporte para ES modules
- ✅ LTS hasta 2026

---

### Type System

#### **TypeScript 5+**
![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6)

**Versión**: 5.3+

**Configuración estricta**:
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "allowUnusedLabels": false,
    "allowUnreachableCode": false,
    "exactOptionalPropertyTypes": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true,
    "noPropertyAccessFromIndexSignature": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
  }
}
```

---

## Base de Datos

### Database

#### **PostgreSQL 16+**
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791)

**Versión**: 16.1+

**Por qué PostgreSQL**:
- ✅ **Multi-schema support**: Perfecto para multi-tenancy
- ✅ **JSONB**: Flexible storage para configuraciones
- ✅ **Full-text search**: Built-in
- ✅ **Row-level security**: Seguridad adicional
- ✅ **Transacciones ACID**: Crítico para finanzas
- ✅ **Extensible**: PostGIS, pg_cron, etc.
- ✅ **Open source y gratis**

**Extensiones usadas**:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";        -- UUIDs
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query analysis
CREATE EXTENSION IF NOT EXISTS "pg_trgm";           -- Fuzzy search
```

**Alternativas**:
- ❌ MySQL: No tiene schemas (tendríamos que usar multiple DBs)
- ❌ MongoDB: No relacional, no ideal para contabilidad
- ❌ SQL Server: Paid, vendor lock-in

---

### ORM

#### **Prisma 5+**
![Prisma](https://img.shields.io/badge/Prisma-5+-2D3748)

**Versión**: 5.9+

**Por qué Prisma**:
- ✅ **Type-safe queries**: Genera tipos TypeScript desde schema
- ✅ **Excelente DX**: Prisma Studio para explorar DB
- ✅ **Migrations**: Versionadas y aplicables
- ✅ **Auto-completion**: IntelliSense en queries
- ✅ **Relation handling**: Fácil trabajar con JOINs

**Schema ejemplo**:
```prisma
model Member {
  id        String   @id @default(uuid())
  firstName String
  lastName  String
  email     String?  @unique
  
  donations Donation[]
  
  @@index([lastName, firstName])
}
```

**Alternativas**:
- Drizzle ORM: Más nuevo, menos maduro
- TypeORM: Más verboso, decorators
- Kysely: Query builder, no ORM completo

---

### Caching

#### **Redis 7+**
![Redis](https://img.shields.io/badge/Redis-7+-DC382D)

**Versión**: 7.2+

**Usos**:
- ✅ Query result caching
- ✅ Session storage
- ✅ Rate limiting
- ✅ BullMQ job queues
- ✅ Pub/Sub para real-time features

**Cliente**:
```typescript
import { Redis } from 'ioredis'

const redis = new Redis(process.env.REDIS_URL)
```

**Hosting**:
- Desarrollo: Local Redis
- Producción: **Upstash** (serverless) o **Redis Cloud**

---

## Autenticación y Autorización

### Auth Provider

#### **NextAuth.js v5 (Auth.js)**
![NextAuth](https://img.shields.io/badge/NextAuth.js-v5-blue)

**Versión**: 5.0.0-beta+

**Por qué**:
- ✅ Integración nativa con Next.js
- ✅ Multiple providers (Credentials, OAuth)
- ✅ Session management
- ✅ JWT o database sessions
- ✅ CSRF protection
- ✅ gratuito y open source

**Providers configurados**:
```typescript
import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import Google from 'next-auth/providers/google'

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: { email: {}, password: {} },
      authorize: async (credentials) => {
        // Verify credentials
      },
    }),
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
  ],
})
```

**Alternativas**:
- Clerk: Más fácil pero paid
- Auth0: Paid, vendor lock-in
- Supabase Auth: Buena opción si usamos Supabase DB

---

### Authorization

#### **CASL 6+**

**Versión**: 6.6+

**Por qué**:
- ✅ Isomorphic (funciona en frontend y backend)
- ✅ Attribute-based access control (ABAC)
- ✅ Type-safe con TypeScript
- ✅ UI conditional rendering fácil

**Ejemplo**:
```typescript
import { defineAbility } from '@casl/ability'

export const defineAbilitiesFor = (user: User) => {
  return defineAbility((can, cannot) => {
    if (user.role === 'CHURCH_ADMIN') {
      can('manage', 'all')
    }
    
    if (user.role === 'TREASURER') {
      can('manage', 'Transaction')
      can('read', 'Member')
    }
    
    // Field-level permissions
    can('read', 'Member', ['firstName', 'lastName'])
    cannot('read', 'Member', ['ssn']) // unless admin
  })
}
```

---

## Pagos y Procesamiento

### Payment Processor

#### **Stripe**
![Stripe](https://img.shields.io/badge/Stripe-Latest-008CDD)

**Por qué Stripe**:
- ✅ **Best-in-class API**: Excelente documentación
- ✅ **Stripe Connect**: Perfecto para plataformas multi-tenant
- ✅ **Subscriptions**: Para donaciones recurrentes
- ✅ **Compliance**: PCI DSS handled
- ✅ **Webhooks**: Eventos en tiempo real
- ✅ **Dashboard**: Excelente UX para iglesias
- ✅ **Customer Portal**: Manejo de suscripciones self-service

**Librerías**:
```json
{
  "stripe": "^14.0.0",
  "@stripe/stripe-js": "^2.4.0",
  "@stripe/react-stripe-js": "^2.4.0"
}
```

**Arquitectura**:
- **Platform Account**: SG Church
- **Connected Accounts**: Una por iglesia (tenant)
- **Payment flow**: Donante → Connected Account directo

**Alternativas**:
- PayPal: Menos developer-friendly, alta brand recognition
- Square: Más enfocado en punto de venta físico
- Plaid: Para ACH, considerar en Fase 3

---

## Almacenamiento y Archivos

### Object Storage

#### **Supabase Storage** (Fase 1) → **AWS S3** (Escala)

**Por qué Supabase inicialmente**:
- ✅ Incluido si usamos Supabase DB
- ✅ CDN integrado
- ✅ Image transformations on-the-fly
- ✅ Signed URLs para uploads directos
- ✅ Gratis hasta 100GB

**Migración a S3**:
- Cuando crezca (>500GB)
- S3 + CloudFront CDN
- Más económico a escala

**Cliente**:
```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
)

// Upload
const { data, error } = await supabase.storage
  .from('avatars')
  .upload(`${tenantId}/${memberId}.jpg`, file)
```

---

## Email y Comunicaciones

### Transactional Email

#### **Resend** (Desarrollo) → **AWS SES** (Escala)

**Por qué Resend**:
- ✅ **Developer-first**: API moderna
- ✅ **React Email**: Templates en React
- ✅ **Delivery tracking**: Opens, clicks
- ✅ **Generous free tier**: 3,000 emails/mes

**React Email**:
```typescript
// packages/email-templates/donation-receipt.tsx
import { Html, Text, Button } from '@react-email/components'

export function DonationReceipt({ donation }) {
  return (
    <Html>
      <Text>Thank you for your ${donation.amount} donation!</Text>
      <Button href={`${baseUrl}/donations/${donation.id}`}>
        View Receipt
      </Button>
    </Html>
  )
}

// Send
import { Resend } from 'resend'
import { DonationReceipt } from '@repo/email-templates'

const resend = new Resend(process.env.RESEND_API_KEY)

await resend.emails.send({
  from: 'noreply@sgchurch.app',
  to: member.email,
  subject: 'Donation Receipt',
  react: DonationReceipt({ donation }),
})
```

**Migración a SES**:
- Cuando > 10K emails/día
- 10x más barato ($0.10 per 1K)
- Requiere más setup (DKIM, SPF)

**Alternativas**:
- SendGrid: Más establecido, free tier 100/día
- Postmark: Excelente deliverability, más caro
- Mailgun: Menos moderno

---

### SMS

#### **Twilio**

**Versión**: API v2010-04-01

**Por qué**:
- ✅ Industry standard
- ✅ Reliable delivery
- ✅ Compliance tools (opt-out handling)
- ✅ International support

**Costo**: ~$0.0075 USD per SMS (US)

**Alternativas**:
- Telnyx: Más barato ($0.004)
- Vonage: Similar pricing

---

## Background Jobs

### Queue System

#### **BullMQ 5+**
![BullMQ](https://img.shields.io/badge/BullMQ-5+-E0234E)

**Versión**: 5.1+

**Por qué**:
- ✅ Built on Redis
- ✅ Job retries con exponential backoff
- ✅ Job prioritization
- ✅ Scheduled/delayed jobs (cron)
- ✅ Rate limiting
- ✅ Web UI (Bull Board)

**Ejemplo**:
```typescript
import { Queue, Worker } from 'bullmq'

const emailQueue = new Queue('emails', {
  connection: redis
})

// Add job
await emailQueue.add('send-receipt', {
  donationId: '123',
  email: 'user@example.com'
}, {
  attempts: 3,
  backoff: { type: 'exponential', delay: 2000 }
})

// Worker
new Worker('emails', async (job) => {
  if (job.name === 'send-receipt') {
    await sendDonationReceipt(job.data)
  }
}, { connection: redis })
```

**Alternativas**:
- Agenda: MongoDB-based
- pg-boss: PostgreSQL-based (considera si no queremos Redis)

---

## Infraestructura y Hosting

### Application Hosting

#### **Vercel**
![Vercel](https://img.shields.io/badge/Vercel-000000)

**Por qué**:
- ✅ **Zero-config**: Deploy desde Git push
- ✅ **Edge network**: CDN global automático
- ✅ **Serverless functions**: Escala automático
- ✅ **Preview deployments**: Por cada PR
- ✅ **Analytics**: Web Vitals built-in
- ✅ **Free tier**: Generoso para comenzar

**Pricing**:
- Free: $0 (hobby projects)
- Pro: $20/mes por miembro (para equipo)

**Alternativas**:
- Railway: Más económico a escala, menos features
- AWS Amplify: Más control, más complejo
- Netlify: Similar a Vercel

---

### Database Hosting

#### **Supabase** (Fase 1) → **AWS RDS** (Escala)

**Por qué Supabase**:
- ✅ **All-in-one**: PostgreSQL + Storage + Auth
- ✅ **Generous free tier**: 500MB, 2GB bandwidth
- ✅ **Daily backups**: Automáticos  
- ✅ **Dashboard**: Fácil de usar
- ✅ **Realtime**: Pub/sub built-in

**Pricing**:
- Free: $0
- Pro: $25/mes (8GB DB, sin pausar)
- Team: Desde $599/mes

**Migración a RDS**:
- Cuando > 100 tenants o necesitemos multi-region
- AWS RDS con read replicas
- Más control sobre performance tuning

**Alternativas**:
- Neon: Serverless PostgreSQL, branching
- PlanetScale: MySQL-as-a-Service
- Railway: PostgreSQLincluido

---

### Redis Hosting

#### **Upstash**

**Por qué**:
- ✅ **Serverless**: Pay per request
- ✅ **Generous free tier**: 10K requests/día
- ✅ **Global edge**: Multi-region
- ✅ **Zero maintenance**

**Pricing**:
- Free: 10K requests/día
- Pay-as-you-go: $0.20 per 100K requests

**Alternativas**:
- Redis Cloud: Free 30MB, luego $5/mes
- Railway: Redis incluido en plan

---

### CDN y Edge

#### **Cloudflare**

**Por qué**:
- ✅ **Free tier**: Unlimited bandwidth
- ✅ **DDoS protection**: Automático
- ✅ **WAF**: Web Application Firewall
- ✅ **DNS**: Rápido y gratis
- ✅ **SSL**: Gratis
- ✅ **R2 Storage**: S3-compatible, más barato

---

## Monitoreo y Analytics

### Error Tracking

#### **Sentry**
![Sentry](https://img.shields.io/badge/Sentry-362D59)

**Por qué**:
- ✅ Error tracking automático
- ✅ Source maps para stacktraces legibles
- ✅ Release tracking
- ✅ Performance monitoring
- ✅ Alerts (Slack, email)

**Free tier**: 5K events/mes

### Web Analytics

#### **Vercel Analytics** + **Plausible**

**Vercel Analytics**:
- Web Vitals (CLS, FID, LCP)
- Incluido gratis con Vercel

**Plausible**:
- Privacy-focused (GDPR compliant)
- No cookies
- Lightweight (<1KB script)

**Alternativas**:
- PostHog: Product analytics, open source
- Umami: Self-hosted, privacy-focused
- Google Analytics: Más completo pero privacy concerns

### Application Monitoring

#### **Vercel Speed Insights** + **Custom Dashboard**

**Métricas custom**:
- Stripe webhook latency
- Background job success rate
- Database query times
- Email delivery rate

---

## Herramientas de Desarrollo

### Package Manager

#### **pnpm 8+**
![pnpm](https://img.shields.io/badge/pnpm-8+-F69220)

**Por qué pnpm**:
- ✅ **Rápido**: Hasta 2x más rápido que npm
- ✅ **Eficiente**: Usa hard links (ahorra espacio)
- ✅ **Workspace support**: Perfecto para monorepos
- ✅ **Strict**: Menos dependency hell

---

### Monorepo

#### **Turborepo**
![Turborepo](https://img.shields.io/badge/Turborepo-EF4444)

**Por qué**:
- ✅ **Build caching**: Incremental builds rápidos
- ✅ **Parallel execution**: Corre tasks en paralelo
- ✅ **Remote caching**: Compartir cache con equipo
- ✅ **Simple config**: Menos verboso que Nx

**Estructura**:
```
turborepo.json:
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {}
  }
}
```

---

### Code Quality

#### **ESLint 8+**

**Configuración**:
```json
{
  "extends": [
    "next/core-web-vitals",
    "plugin:@typescript-eslint/recommended",
    "prettier"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}
```

#### **Prettier 3+**

**Config**:
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

#### **Husky + lint-staged**

Pre-commit hooks:
```json
{
  "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
  "*.{json,md}": ["prettier --write"]
}
```

---

### Testing

#### **Vitest** (Unit/Integration)

**Por qué**:
- ✅ Más rápido que Jest
- ✅ Compatible con Vite ecosystem
- ✅ TypeScript out of the box
- ✅ Watch mode excelente

#### **Playwright** (E2E)

**Por qué**:
- ✅ Multi-browser (Chromium, Firefox, WebKit)
- ✅ Codegen para generar tests
- ✅ Parallel execution
- ✅ Trace viewer para debugging

**Ejemplo**:
```typescript
import { test, expect } from '@playwright/test'

test('onboarding flow', async ({ page }) => {
  await page.goto('/register')
  await page.fill('[name="churchName"]', 'First Baptist')
  await page.fill('[name="email"]', 'admin@church.com')
  await page.click('button[type="submit"]')
  
  await expect(page).toHaveURL('/dashboard')
})
```

---

### CI/CD

#### **GitHub Actions**

**Workflow**:
```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'
      
      - run: pnpm install
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build
  
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
```

---

## Versiones y Compatibilidad

### Versiones Mínimas Requeridas

| Herramienta | Versión Mínima | Versión Recomendada |
|-------------|----------------|---------------------|
| Node.js | 20.0.0 | 20.11+ LTS |
| pnpm | 8.0.0 | 8.15+ |
| PostgreSQL | 15.0 | 16.1+ |
| Redis | 6.2 | 7.2+ |
| TypeScript | 5.0 | 5.3+ |
| Next.js | 14.0 | 14.1+ |
| React | 18.0 | 18.2+ |

### Navegadores Soportados

```json
// package.json
{
  "browserslist": [
    "last 2 Chrome versions",
    "last 2 Firefox versions",
    "last 2 Safari versions",
    "last 2 Edge versions"
  ]
}
```

**Mobile**:
- iOS Safari 15+
- Chrome Android (últimas 2 versiones)

---

## Decisiones Tecnológicas - Resumen

| Aspecto | Tecnología | Alternativa Principal | Por Qué Elegimos |
|---------|-----------|----------------------|------------------|
| **Framework** | Next.js 14 | Remix | SSR, App Router, ecosystem |
| **Backend API** | tRPC | GraphQL | Type safety sin codegen |
| **Database** | PostgreSQL | MySQL | Multi-schema support |
| **ORM** | Prisma | Drizzle | Madurez, DX, tooling |
| **Auth** | NextAuth.js | Clerk | Open source, flexible |
| **Payments** | Stripe | PayPal | Best API, Connect model |
| **Storage** | Supabase → S3 | Cloudflare R2 | All-in-one → cost at scale |
| **Email** | Resend → SES | SendGrid | Modern DX → cost |
| **Hosting** | Vercel | Railway | Zero-config, edge |
| **Cache/Jobs** | Redis + BullMQ | pg-boss | Performance, features |

---

## Costos Estimados (Mensual)

### Fase 1 (10 iglesias, <1,000 miembros totales)
- Vercel: **$0** (Free tier)
- Supabase: **$0** (Free tier)
- Upstash Redis: **$0** (Free tier)
- Resend: **$0** (Free tier)
- **Total: $0/mes** ✅

### Fase 2 (50 iglesias, 5,000 miembros)
- Vercel Pro: **$20/mes**
- Supabase Pro: **$25/mes**
- Upstash: **~$10/mes**
- Resend: **~$20/mes**
- Twilio SMS: **~$50/mes**
- **Total: ~$125/mes**

### Fase 3 (200 iglesias, 20,000 miembros)
- Vercel Team: **$100/mes**
- AWS RDS (db.t3.medium): **~$50/mes**
- Redis Cloud: **~$30/mes**
- AWS SES: **~$10/mes**
- S3 + CloudFront: **~$20/mes**
- Twilio: **~$200/mes**
- **Total: ~$410/mes**

### Fase 4 (500+ iglesias, 50,000+ miembros)
- Vercel Enterprise: **$500-1,000/mes**
- AWS RDS (larger instance + replicas): **~$500/mes**
- Redis: **~$100/mes**
- Email/SMS: **~$500/mes**
- Monitoring: **~$100/mes**
- **Total: ~$2,000-2,500/mes**

**Sostenibilidad**: Con 500 iglesias, 4-5 donaciones de $500/año cubren costos operacionales.

---

**Última actualización**: Febrero 15, 2026
**Mantenido por**: Equipo Técnico SG Church
