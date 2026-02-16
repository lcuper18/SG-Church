# Arquitectura de SG Church

Este documento describe las decisiones arquitectónicas clave del proyecto SG Church, su justificación y las alternativas consideradas.

## Tabla de Contenidos

- [Visión General](#visión-general)
- [Principios de Diseño](#principios-de-diseño)
- [Arquitectura Multi-Tenant](#arquitectura-multi-tenant)
- [Arquitectura de la Aplicación](#arquitectura-de-la-aplicación)
- [Patrón de Datos](#patrón-de-datos)
- [Autenticación y Autorización](#autenticación-y-autorización)
- [Procesamiento de Pagos](#procesamiento-de-pagos)
- [Sistema de Notificaciones](#sistema-de-notificaciones)
- [Background Jobs](#background-jobs)
- [Almacenamiento de Archivos](#almacenamiento-de-archivos)
- [Caching Strategy](#caching-strategy)
- [Escalabilidad](#escalabilidad)

---

## Visión General

SG Church es una plataforma SaaS multi-tenant diseñada para escalar desde pequeñas iglesias (10-50 miembros) hasta mega-iglesias (10,000+ miembros). La arquitectura prioriza:

1. **Aislamiento de datos** entre tenants (iglesias)
2. **Type safety** end-to-end
3. **Developer experience** para rápido desarrollo
4. **Cost efficiency** para mantener el servicio gratuito
5. **Escalabilidad** horizontal cuando sea necesario

### Diagrama de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                     USUARIO (Browser)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    NEXT.JS APP (Vercel)                     │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │  React UI      │  │  API Routes    │  │  tRPC Router │  │
│  │  (Server/      │◄─┤  (Webhooks,    │◄─┤  (Business   │  │
│  │   Client       │  │   Auth)        │  │   Logic)     │  │
│  │   Components)  │  │                │  │              │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└──────────────┬────────────────┬───────────────┬────────────┘
               │                │               │
       ┌───────▼──────┐   ┌────▼─────┐   ┌────▼────────┐
       │ PostgreSQL   │   │  Redis   │   │  S3/Storage │
       │ (Multi-      │   │  (Cache, │   │  (Images,   │
       │  Tenant DB)  │   │   Queue) │   │   Files)    │
       └──────────────┘   └──────────┘   └─────────────┘
               │
       ┌───────▼──────────┐
       │  BullMQ Worker   │
       │  (Background     │
       │   Jobs)          │
       └──────────────────┘
               │
       ┌───────▼──────────┐
       │  External APIs   │
       │  - Stripe        │
       │  - Resend/Email  │
       │  - Twilio/SMS    │
       └──────────────────┘
```

---

## Principios de Diseño

### 1. Modular Monolith First

**Decisión**: Comenzar con un monolito modular en lugar de microservicios.

**Justificación**:
- ✅ **Simplicidad**: Un solo deployment, menos overhead de infraestructura
- ✅ **Desarrollo rápido**: Menos boilerplate, refactoring más fácil
- ✅ **Type safety**: tRPC permite type safety end-to-end en un monolito
- ✅ **Debugging**: Stack traces completos, logging centralizado
- ✅ **Costo**: Un solo servidor para comenzar

**Módulos claramente definidos**:
- `members/` - Gestión de membresía
- `finance/` - Contabilidad y donaciones
- `education/` - Sistema LMS
- `baptisms/` - Registros sacramentales
- `auth/` - Autenticación y autorización

Cada módulo puede extraerse a un microservicio si escala independientemente.

**Alternativa considerada**: Microservicios desde el inicio
- ❌ Complejidad operacional alta para MVP
- ❌ Overhead de comunicación entre servicios
- ❌ Más difícil mantener type safety

### 2. Type Safety End-to-End

**Decisión**: TypeScript estricto + Prisma + tRPC

**Justificación**:
- ✅ **Catch errors en compile time** en lugar de runtime
- ✅ **IntelliSense** en frontend sabe exactamente qué devuelve el backend
- ✅ **Refactoring seguro**: Cambiar un tipo en DB propaga a toda la app
- ✅ **Menos tests necesarios**: TypeScript elimina clases enteras de bugs

**Stack**:
```typescript
Database Schema (Prisma)
    ↓ (prisma generate)
TypeScript Types
    ↓ (used by)
tRPC Routers (Backend)
    ↓ (exports types)
tRPC Client (Frontend)
    ↓ (fully typed)
React Components
```

**Ejemplo**:
```typescript
// Backend: apps/web/server/routers/members.ts
export const membersRouter = router({
  getById: publicProcedure
    .input(z.object({ id: z.string().uuid() }))
    .query(async ({ input, ctx }) => {
      return ctx.db.member.findUnique({ where: { id: input.id } })
    }),
})

// Frontend: apps/web/app/(dashboard)/members/[id]/page.tsx
const member = trpc.members.getById.useQuery({ id: params.id })
//    ^? const member: Member | null  ← Fully typed!
```

### 3. Progressive Enhancement

**Decisión**: Server Components por defecto, Client Components cuando sea necesario.

**Justificación**:
- ✅ **Performance**: HTML renderizado en servidor es más rápido
- ✅ **SEO**: Contenido disponible para crawlers
- ✅ **Bundle size**: Menos JS enviado al cliente
- ✅ **Security**: Queries a DB desde Server Components (no exponer en cliente)

**Regla**:
- **Server Component** (default): Mostrar datos, layouts estáticos
- **Client Component** (`'use client'`): Interactividad, forms, state

---

## Arquitectura Multi-Tenant

### Estrategias Evaluadas

| Estrategia | Pros | Contras | Decisión |
|------------|------|---------|----------|
| **Database per Tenant** | Máximo aislamiento, fácil backup individual | 🔴 Muy caro (100s de DBs), gestión compleja | ❌ Rechazado |
| **Shared DB, Row-Level Security** | Bajo costo, gestión simple | 🔴 Riesgo de data leaks, queries complejas | ❌ Rechazado |
| **Schema per Tenant** | Buen aislamiento, costo razonable | Límite ~1000 schemas por DB | ✅ **ELEGIDO** |

### Implementación: Schema-per-Tenant

Cada iglesia (tenant) tiene su propio schema PostgreSQL:

```sql
-- Iglesia 1
CREATE SCHEMA church_abc123;
CREATE TABLE church_abc123.members (...);
CREATE TABLE church_abc123.donations (...);

-- Iglesia 2
CREATE SCHEMA church_xyz789;
CREATE TABLE church_xyz789.members (...);
CREATE TABLE church_xyz789.donations (...);
```

**Schema público** para datos compartidos:
```sql
CREATE SCHEMA public;
CREATE TABLE public.tenants (
  id UUID PRIMARY KEY,
  schema_name TEXT UNIQUE,
  subdomain TEXT UNIQUE,
  name TEXT,
  created_at TIMESTAMPTZ
);
```

### Tenant Resolution

**Flujo**:
1. Usuario accede a `firstchurch.sgchurch.app`
2. Middleware extrae subdomain: `firstchurch`
3. Query a `public.tenants` para obtener `schema_name`
4. Todas las queries subsecuentes usan: `SET search_path TO church_abc123`

**Código**:
```typescript
// middleware.ts
export async function middleware(req: NextRequest) {
  const subdomain = getSubdomain(req.headers.get('host'))
  
  // Lookup tenant
  const tenant = await db.tenant.findUnique({
    where: { subdomain }
  })
  
  if (!tenant) return new Response('Church not found', { status: 404 })
  
  // Store tenant context
  req.headers.set('X-Tenant-Id', tenant.id)
  req.headers.set('X-Tenant-Schema', tenant.schema_name)
}

// db.ts - Prisma client wrapper
export function getDbForRequest(req: Request): PrismaClient {
  const schema = req.headers.get('X-Tenant-Schema')
  
  return new PrismaClient({
    datasources: {
      db: {
        url: `${DATABASE_URL}?schema=${schema}`
      }
    }
  })
}
```

### Tenant Provisioning

Cuando una iglesia se registra:

```typescript
export async function createTenant(input: CreateTenantInput) {
  const schemaName = `church_${nanoid()}`
  
  return await db.$transaction(async (tx) => {
    // 1. Crear registro en tabla tenants
    const tenant = await tx.tenant.create({
      data: {
        schemaName,
        subdomain: input.subdomain,
        name: input.churchName,
      }
    })
    
    // 2. Crear schema
    await tx.$executeRawUnsafe(`CREATE SCHEMA ${schemaName}`)
    
    // 3. Ejecutar migraciones en nuevo schema
    await runMigrationsForSchema(schemaName)
    
    // 4. Seedear datos default (roles, configuración)
    await seedTenant(schemaName)
    
    // 5. Crear cuenta Stripe Connect
    const stripeAccount = await stripe.accounts.create({
      type: 'standard',
      metadata: { tenantId: tenant.id }
    })
    
    await tx.tenant.update({
      where: { id: tenant.id },
      data: { stripeAccountId: stripeAccount.id }
    })
    
    return tenant
  })
}
```

**Ventajas del enfoque**:
- ✅ Aislamiento fuerte (schema-level isolation)
- ✅ Backups individuales: `pg_dump --schema=church_abc123`
- ✅ Migrar iglesias grandes a DB dedicada: exportar schema completo
- ✅ Costos razonables (single DB cluster)

**Limitaciones**:
- ⚠️ PostgreSQL limita ~1000 schemas por instancia (suficiente para comenzar)
- ⚠️ Migraciones deben aplicarse a todos los schemas (scripting necesario)

---

## Arquitectura de la Aplicación

### Estructura de Carpetas (Next.js App Router)

```
apps/web/
├── app/
│   ├── (auth)/                  # Route group: páginas de auth
│   │   ├── login/
│   │   ├── register/
│   │   └── onboard/             # Wizard de onboarding
│   │
│   ├── (dashboard)/             # Route group: app principal (requiere auth)
│   │   ├── layout.tsx           # Sidebar, nav
│   │   ├── members/
│   │   │   ├── page.tsx         # Lista de miembros
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx     # Detalle de miembro
│   │   │   └── new/
│   │   │       └── page.tsx     # Crear miembro
│   │   ├── finance/
│   │   ├── education/
│   │   └── settings/
│   │
│   ├── (public)/                # Route group: páginas públicas
│   │   ├── donate/
│   │   └── directory/
│   │
│   ├── api/
│   │   ├── trpc/[trpc]/         # tRPC endpoint
│   │   │   └── route.ts
│   │   ├── webhooks/
│   │   │   └── stripe/
│   │   │       └── route.ts
│   │   └── auth/
│   │       └── [...nextauth]/
│   │           └── route.ts
│   │
│   └── layout.tsx               # Root layout
│
├── components/
│   ├── ui/                      # Shadcn components
│   ├── members/                 # Feature-specific
│   └── providers/               # Context providers
│
├── lib/
│   ├── db.ts                    # Prisma client
│   ├── auth.ts                  # NextAuth config
│   ├── trpc.ts                  # tRPC setup
│   └── utils.ts
│
└── server/
    ├── routers/
    │   ├── members.ts
    │   ├── finance.ts
    │   └── _app.ts              # Root router
    └── context.ts               # tRPC context
```

### Flujo de Datos

**Loading Data (Server → Client)**:

```typescript
// 1. Server Component (default en App Router)
// apps/web/app/(dashboard)/members/page.tsx
import { getServerSession } from 'next-auth'
import { db } from '@/lib/db'

export default async function MembersPage() {
  const session = await getServerSession()
  const members = await db.member.findMany({
    where: { tenantId: session.tenant.id }
  })
  
  return <MembersList members={members} />
}

// 2. Client Component (para interactividad)
// apps/web/components/members/member-form.tsx
'use client'

import { trpc } from '@/lib/trpc'

export function MemberForm() {
  const utils = trpc.useContext()
  const createMember = trpc.members.create.useMutation({
    onSuccess: () => {
      utils.members.list.invalidate() // Refetch list
    }
  })
  
  return (
    <form onSubmit={(e) => {
      e.preventDefault()
      createMember.mutate(formData)
    }}>
      {/* ... */}
    </form>
  )
}
```

---

## Patrón de Datos

### Prisma Schema Highlights

```prisma
// packages/database/prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ============================================
// SCHEMA PÚBLICO (Shared across all tenants)
// ============================================

model Tenant {
  id              String   @id @default(uuid())
  schemaName      String   @unique
  subdomain       String   @unique
  name            String
  stripeAccountId String?  @unique
  settings        Json     @default("{}")
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  @@map("tenants")
  @@schema("public")
}

// ============================================
// SCHEMA PER-TENANT (Tables created in each church_xxx schema)
// ============================================

model User {
  id            String   @id @default(uuid())
  email         String   @unique
  passwordHash  String?
  name          String?
  role          Role     @default(MEMBER)
  memberId      String?  @unique
  member        Member?  @relation(fields: [memberId], references: [id])
  createdAt     DateTime @default(now())
  
  @@index([email])
}

enum Role {
  SUPER_ADMIN
  CHURCH_ADMIN
  PASTOR
  TREASURER
  TEACHER
  VOLUNTEER
  MEMBER
  GUEST
}

model Member {
  id            String    @id @default(uuid())
  firstName     String
  lastName      String
  email         String?
  phone         String?
  dateOfBirth   DateTime?
  photoUrl      String?
  status        MemberStatus @default(ACTIVE)
  familyId      String?
  family        Family?   @relation(fields: [familyId], references: [id])
  user          User?
  donations     Donation[]
  baptism       Baptism?
  courseEnrollments CourseEnrollment[]
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  
  @@index([email])
  @@index([lastName, firstName])
}

enum MemberStatus {
  ACTIVE
  INACTIVE
  DECEASED
}

model Family {
  id        String   @id @default(uuid())
  name      String
  members   Member[]
  address   String?
  city      String?
  state     String?
  zip       String?
}

model Donation {
  id               String         @id @default(uuid())
  amount           Decimal        @db.Decimal(10, 2)
  currency         String         @default("USD")
  memberId         String
  member           Member         @relation(fields: [memberId], references: [id])
  stripePaymentId  String?        @unique
  type             DonationType   @default(ONE_TIME)
  campaignId       String?
  campaign         Campaign?      @relation(fields: [campaignId], references: [id])
  transactionId    String         @unique
  transaction      Transaction    @relation(fields: [transactionId], references: [id])
  receiptEmailed   Boolean        @default(false)
  createdAt        DateTime       @default(now())
  
  @@index([memberId])
  @@index([createdAt])
}

enum DonationType {
  ONE_TIME
  RECURRING
}

model Transaction {
  id            String      @id @default(uuid())
  date          DateTime    @default(now())
  description   String
  amount        Decimal     @db.Decimal(10, 2)
  type          TransactionType
  accountId     String
  account       Account     @relation(fields: [accountId], references: [id])
  donation      Donation?
  createdAt     DateTime    @default(now())
  createdBy     String
  
  @@index([date])
  @@index([accountId])
}

enum TransactionType {
  DEBIT
  CREDIT
}

model Account {
  id            String        @id @default(uuid())
  name          String
  type          AccountType
  balance       Decimal       @db.Decimal(10, 2) @default(0)
  transactions  Transaction[]
}

enum AccountType {
  ASSET
  LIABILITY
  EQUITY
  REVENUE
  EXPENSE
}

model Course {
  id            String             @id @default(uuid())
  title         String
  description   String?
  instructorId  String
  lessons       Lesson[]
  enrollments   CourseEnrollment[]
  published     Boolean            @default(false)
  createdAt     DateTime           @default(now())
}

model Lesson {
  id          String   @id @default(uuid())
  courseId    String
  course      Course   @relation(fields: [courseId], references: [id])
  title       String
  content     String   @db.Text
  videoUrl    String?
  order       Int
  quizzes     Quiz[]
}

model CourseEnrollment {
  id          String   @id @default(uuid())
  courseId    String
  course      Course   @relation(fields: [courseId], references: [id])
  memberId    String
  member      Member   @relation(fields: [memberId], references: [id])
  progress    Int      @default(0) // Percentage 0-100
  completed   Boolean  @default(false)
  enrolledAt  DateTime @default(now())
  completedAt DateTime?
  
  @@unique([courseId, memberId])
}

model Baptism {
  id          String   @id @default(uuid())
  memberId    String   @unique
  member      Member   @relation(fields: [memberId], references: [id])
  date        DateTime
  location    String?
  officiant   String?
  witnesses   String?
  certificateUrl String?
  photos      String[] // Array of URLs
  createdAt   DateTime @default(now())
}
```

### Audit Logging

Todas las operaciones críticas (financieras, cambios en membresía) se auditan:

```prisma
model AuditLog {
  id        String   @id @default(uuid())
  userId    String
  action    String   // "CREATE", "UPDATE", "DELETE"
  entity    String   // "Member", "Donation", "Transaction"
  entityId  String
  changes   Json     // Snapshot de cambios
  ipAddress String?
  userAgent String?
  createdAt DateTime @default(now())
  
  @@index([userId])
  @@index([entity, entityId])
  @@index([createdAt])
}
```

---

## Autenticación y Autorización

### NextAuth.js v5 (Auth.js)

**Configuración**:
```typescript
// apps/web/lib/auth.ts
import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import Google from 'next-auth/providers/google'
import { PrismaAdapter } from '@auth/prisma-adapter'
import { db } from './db'

export const { handlers, signIn, signOut, auth } = NextAuth({
  adapter: PrismaAdapter(db),
  providers: [
    Credentials({
      credentials: {
        email: {},
        password: {},
      },
      authorize: async (credentials) => {
        // Validate credentials, check password hash
        const user = await db.user.findUnique({
          where: { email: credentials.email }
        })
        
        if (!user || !await verifyPassword(credentials.password, user.passwordHash)) {
          return null
        }
        
        return user
      }
    }),
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
  ],
  callbacks: {
    async session({ session, user }) {
      // Add tenant info to session
      const dbUser = await db.user.findUnique({
        where: { email: user.email },
        include: { member: { include: { family: true } } }
      })
      
      session.user.id = dbUser.id
      session.user.role = dbUser.role
      session.tenant = await getTenantFromContext() // From middleware
      
      return session
    }
  }
})
```

### Role-Based Access Control (RBAC)

**Usando CASL**:

```typescript
// apps/web/lib/rbac.ts
import { defineAbility } from '@casl/ability'

export function defineAbilitiesFor(user: User) {
  return defineAbility((can, cannot) => {
    if (user.role === 'SUPER_ADMIN') {
      can('manage', 'all')
    }
    
    if (user.role === 'CHURCH_ADMIN') {
      can('manage', 'Member')
      can('manage', 'Course')
      can('read', 'Transaction')
      can('manage', 'Settings')
    }
    
    if (user.role === 'TREASURER') {
      can('manage', 'Transaction')
      can('manage', 'Donation')
      can('read', 'Member')
    }
    
    if (user.role === 'PASTOR') {
      can('read', 'Member')
      can('update', 'Member', ['notes', 'status'])
      can('create', 'Baptism')
    }
    
    if (user.role === 'TEACHER') {
      can('manage', 'Course', { instructorId: user.id })
      can('read', 'CourseEnrollment')
    }
    
    if (user.role === 'MEMBER') {
      can('read', 'Member', { id: user.memberId })
      can('update', 'Member', { id: user.memberId }) // Own profile only
      can('read', 'Donation', { memberId: user.memberId })
    }
  })
}

// Usage en tRPC procedures
export const updateMemberProcedure = protectedProcedure
  .input(updateMemberSchema)
  .mutation(async ({ input, ctx }) => {
    const ability = defineAbilitiesFor(ctx.session.user)
    
    if (!ability.can('update', 'Member')) {
      throw new TRPCError({ code: 'FORBIDDEN' })
    }
    
    // Proceed with update
  })
```

---

## Procesamiento de Pagos

### Stripe Connect (Platform Model)

**Arquitectura**:
- **Platform Account**: SG Church (nosotros)
- **Connected Accounts**: Una por iglesia (tenant)
- **Payment Flow**: Donante → Connected Account de la iglesia

**Setup**:
```typescript
// Cuando se registra una iglesia
const account = await stripe.accounts.create({
  type: 'standard', // Express también es opción
  country: 'US',
  email: tenant.email,
  capabilities: {
    card_payments: { requested: true },
    transfers: { requested: true },
  },
  metadata: {
    tenantId: tenant.id,
  }
})

// Save to tenant
await db.tenant.update({
  where: { id: tenant.id },
  data: { stripeAccountId: account.id }
})
```

**Donación One-Time**:
```typescript
// Frontend
'use client'
import { loadStripe } from '@stripe/stripe-js'

export function DonateButton() {
  const donate = async (amount: number) => {
    // Create Checkout Session
    const session = await fetch('/api/donations/create-checkout', {
      method: 'POST',
      body: JSON.stringify({ amount })
    }).then(r => r.json())
    
    // Redirect to Stripe Checkout
    const stripe = await loadStripe(env.NEXT_PUBLIC_STRIPE_KEY)
    await stripe.redirectToCheckout({ sessionId: session.id })
  }
  
  return <button onClick={() => donate(50)}>Donate $50</button>
}

// Backend API Route
// apps/web/app/api/donations/create-checkout/route.ts
export async function POST(req: Request) {
  const { amount } = await req.json()
  const tenant = await getTenantFromRequest(req)
  
  const session = await stripe.checkout.sessions.create({
    mode: 'payment',
    line_items: [{
      price_data: {
        currency: 'usd',
        product_data: { name: 'Donation' },
        unit_amount: amount * 100, // cents
      },
      quantity: 1,
    }],
    success_url: `${req.headers.get('origin')}/donate/success`,
    cancel_url: `${req.headers.get('origin')}/donate`,
    metadata: {
      tenantId: tenant.id,
      type: 'donation',
    }
  }, {
    stripeAccount: tenant.stripeAccountId, // Route to church's account
  })
  
  return Response.json({ id: session.id })
}
```

**Webhooks**:
```typescript
// apps/web/app/api/webhooks/stripe/route.ts
import { headers } from 'next/headers'
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req: Request) {
  const body = await req.text()
  const sig = headers().get('stripe-signature')!
  
  let event: Stripe.Event
  
  try {
    event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET!
    )
  } catch (err) {
    return new Response(`Webhook Error`, { status: 400 })
  }
  
  // Handle the event
  switch (event.type) {
    case 'checkout.session.completed':
      const session = event.data.object as Stripe.Checkout.Session
      await handleDonationSuccess(session)
      break
      
    case 'customer.subscription.created':
      await handleRecurringDonationCreated(event.data.object)
      break
      
    // ... más eventos
  }
  
  return Response.json({ received: true })
}

async function handleDonationSuccess(session: Stripe.Checkout.Session) {
  const tenantId = session.metadata.tenantId
  
  // Create donation record
  await db.donation.create({
    data: {
      amount: session.amount_total / 100,
      currency: session.currency,
      stripePaymentId: session.payment_intent as string,
      type: 'ONE_TIME',
      // ... other fields
    }
  })
  
  // Create accounting transaction (double-entry)
  await createTransaction({
    debit: { account: 'Bank Account', amount: session.amount_total / 100 },
    credit: { account: 'Donation Revenue', amount: session.amount_total / 100 },
  })
  
  // Send receipt email
  await sendDonationReceipt(donation)
}
```

**Donaciones Recurrentes**:
- Usar Stripe Subscriptions
- Webhooks: `customer.subscription.created`, `invoice.paid`, `invoice.payment_failed`
- Portal de cliente para gestionar suscripciones

---

## Sistema de Notificaciones

### Arquitectura

```
┌─────────────┐
│  Trigger    │  (New member, donation, birthday, etc.)
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Notification       │
│  Service            │
│  (Determina canal)  │
└──────┬──────────────┘
       │
       ├───────┬───────┬───────┐
       │       │       │       │
       ▼       ▼       ▼       ▼
   ┌────┐  ┌────┐  ┌────┐  ┌─────┐
   │Email  │ SMS │  │Push│  │In-App
   │Queue│  │Queue│  │Queue  │Notif│
   └──┬─┘  └──┬─┘  └──┬─┘  └──┬──┘
      │       │       │       │
      ▼       ▼       ▼       ▼
   Workers process queues
```

### Implementación

**Email con React Email + Resend**:

```typescript
// packages/email-templates/donation-receipt.tsx
import { Html, Head, Body, Container, Section, Text } from '@react-email/components'

export function DonationReceipt({ donation, member, church }) {
  return (
    <Html>
      <Head />
      <Body style={{ fontFamily: 'sans-serif' }}>
        <Container>
          <Section>
            <Text>Dear {member.firstName},</Text>
            <Text>
              Thank you for your generous donation of ${donation.amount} to {church.name}.
            </Text>
            <Text>
              Date: {donation.createdAt.toLocaleDateString()}<br />
              Transaction ID: {donation.id}
            </Text>
            <Text>
              This email serves as your receipt for tax purposes.
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  )
}

// services/worker/jobs/send-email.ts
import { Resend } from 'resend'
import { DonationReceipt } from '@repo/email-templates'

const resend = new Resend(process.env.RESEND_API_KEY)

export async function sendDonationReceipt(donationId: string) {
  const donation = await db.donation.findUnique({
    where: { id: donationId },
    include: { member: true }
  })
  
  const church = await getTenantInfo()
  
  await resend.emails.send({
    from: `${church.name} <noreply@sgchurch.app>`,
    to: donation.member.email,
    subject: 'Donation Receipt',
    react: DonationReceipt({ donation, member: donation.member, church })
  })
  
  // Mark as sent
  await db.donation.update({
    where: { id: donationId },
    data: { receiptEmailed: true }
  })
}
```

**BullMQ Queues**:

```typescript
// services/worker/queues/email.ts
import { Queue, Worker } from 'bullmq'
import { Redis } from 'ioredis'

const connection = new Redis(process.env.REDIS_URL)

export const emailQueue = new Queue('emails', { connection })

// Add job
export async function queueEmail(data: EmailJob) {
  await emailQueue.add('send', data, {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 2000,
    }
  })
}

// Worker
const worker = new Worker('emails', async (job) => {
  switch (job.data.type) {
    case 'donation-receipt':
      await sendDonationReceipt(job.data.donationId)
      break
    case 'welcome':
      await sendWelcomeEmail(job.data.memberId)
      break
    // ... más tipos
  }
}, { connection })

worker.on('failed', (job, err) => {
  console.error(`Job ${job.id} failed:`, err)
  // Alert monitoring system
})
```

---

## Background Jobs

**BullMQ para tareas programadas**:

```typescript
// services/worker/jobs/birthday-reminders.ts
import { QueueScheduler } from 'bullmq'

// Ejecutar diario a las 8am
const scheduler = new QueueScheduler('birthday-reminders', { connection })

export async function sendBirthdayReminders() {
  const today = new Date()
  
  // Query across all tenants
  const tenants = await db.tenant.findMany()
  
  for (const tenant of tenants) {
    const dbTenant = getDbForSchema(tenant.schemaName)
    
    const membersWithBirthday = await dbTenant.member.findMany({
      where: {
        dateOfBirth: {
          gte: startOfDay(today),
          lte: endOfDay(today),
        },
        status: 'ACTIVE',
      }
    })
    
    for (const member of membersWithBirthday) {
      await queueEmail({
        type: 'birthday',
        memberId: member.id,
        tenantId: tenant.id,
      })
    }
  }
}

// Cron job (alternative: use cron in server)
import cron from 'node-cron'

cron.schedule('0 8 * * *', async () => {
  await sendBirthdayReminders()
})
```

**Otros background jobs**:
- Generación de reportes anuales (enero)
- Limpiar sesiones expiradas
- Sincronizar con servicios externos
- Procesar uploads masivos de datos

---

## Almacenamiento de Archivos

### Supabase Storage (Fase 1) → S3 (Escala)

**Estructura de buckets**:
```
sg-church-prod/
├── avatars/
│   └── {tenant-id}/
│       └── {member-id}.jpg
├── baptism-photos/
│   └── {tenant-id}/
│       └── {baptism-id}/
│           ├── photo1.jpg
│           └── photo2.jpg
├── course-materials/
│   └── {tenant-id}/
│       └── {course-id}/
│           └── lesson1.pdf
└── receipts/
    └── {tenant-id}/
        └── {year}/
            └── {receipt-id}.pdf
```

**Upload desde cliente**:
```typescript
'use client'

export function AvatarUpload() {
  const uploadAvatar = async (file: File) => {
    // 1. Get signed upload URL
    const { uploadUrl, key } = await fetch('/api/storage/upload-url', {
      method: 'POST',
      body: JSON.stringify({
        filename: file.name,
        contentType: file.type,
        folder: 'avatars'
      })
    }).then(r => r.json())
    
    // 2. Upload directly to S3/Supabase
    await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {  'Content-Type': file.type }
    })
    
    // 3. Save key to database
    await trpc.members.updateAvatar.mutate({ key })
  }
  
  return <input type="file" onChange={(e) => uploadAvatar(e.target.files[0])} />
}
```

**Image optimization**:
- Next.js Image component para CDN automático
- Supabase transforma imágenes on-the-fly: `?width=200&height=200`
- Cloudflare Images como alternativa

---

## Caching Strategy

### Cache Layers

```
┌───────────────────┐
│  CDN (Cloudflare) │  Static assets, images
└────────┬──────────┘
         │
┌────────▼──────────┐
│  Next.js Cache    │  Page cache, data cache
└────────┬──────────┘
         │
┌────────▼──────────┐
│  Redis            │  Query results, sessions
└────────┬──────────┘
         │
┌────────▼──────────┐
│  PostgreSQL       │  Source of truth
└───────────────────┘
```

### Redis Caching

```typescript
// lib/cache.ts
import { Redis } from 'ioredis'

const redis = new Redis(process.env.REDIS_URL)

export async function getCached<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = 300 // 5 min default
): Promise<T> {
  // Try cache first
  const cached = await redis.get(key)
  if (cached) return JSON.parse(cached)
  
  // Fetch and cache
  const data = await fetcher()
  await redis.setex(key, ttl, JSON.stringify(data))
  
  return data
}

// Usage
export async function getChurchSettings(tenantId: string) {
  return getCached(
    `tenant:${tenantId}:settings`,
    () => db.tenant.findUnique({ where: { id: tenantId } }),
    3600 // 1 hour TTL
  )
}
```

**Invalidación**:
```typescript
// On update
await db.tenant.update({ where: { id }, data: { ... } })
await redis.del(`tenant:${id}:settings`) // Invalidate cache
```

---

## Escalabilidad

### Horizontal Scaling Path

**Fase 1 (0-100 iglesias)**:
- Single Next.js instance (Vercel)
- Supabase hosted PostgreSQL
- Redis Cloud free tier

**Fase 2 (100-1,000 iglesias)**:
- Multiple Next.js instances (Vercel auto-scales)
- AWS RDS PostgreSQL (read replicas)
- Upstash Redis (serverless)
- Cloudflare CDN

**Fase 3 (1,000+ iglesias)**:
- Database sharding (shard by tenant ID)
- Dedicated DB for top 10% largest churches
- Separate worker cluster for background jobs
- Geographic distribution (multi-region)

### Performance Targets

| Métrica | Target | Estrategia |
|---------|--------|-----------|
| Page Load (P95) | < 2s | Server components, CDN |
| API Response (P95) | < 500ms | Database indexing, Redis cache |
| Donation Processing | < 3s | Async webhooks, optimized Stripe calls |
| Report Generation | < 5s | Background jobs for large reports |
| Member Search | < 200ms | Full-text search indexes, pagination |

### Database Optimization

**Indexes críticos**:
```sql
-- Members
CREATE INDEX idx_members_email ON members(email);
CREATE INDEX idx_members_name ON members(last_name, first_name);
CREATE INDEX idx_members_family ON members(family_id);

-- Donations
CREATE INDEX idx_donations_member_date ON donations(member_id, created_at DESC);
CREATE INDEX idx_donations_created ON donations(created_at DESC);

-- Transactions
CREATE INDEX idx_transactions_date ON transactions(date DESC);
CREATE INDEX idx_transactions_account ON transactions(account_id, date DESC);

-- Audit logs
CREATE INDEX idx_audit_entity ON audit_logs(entity, entity_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

**Connection Pooling**:
```typescript
// lib/db.ts
import { PrismaClient } from '@prisma/client'
import { Pool } from 'pg'

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20, // Max connections
})

export const db = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL + '?pgbouncer=true'
    }
  }
})
```

---

## Resumen de Decisiones

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Arquitectura** | Monolito modular | Simplicidad, type safety |
| **Multi-tenancy** | Schema-per-tenant | Balance aislamiento/costo |
| **Frontend** | Next.js 14 App Router | Server Components, SEO, DX |
| **Backend** | Next.js API + tRPC | Type safety end-to-end |
| **Database** | PostgreSQL + Prisma | Confiabilidad, ORM moderno |
| **Auth** | NextAuth.js v5 | Integrado, flexible |
| **Payments** | Stripe Connect | Best-in-class API |
| **Files** | Supabase Storage | Incluido, migration path a S3 |
| **Email** | Resend + React Email | Modern DX, templates en React |
| **Cache** | Redis | Estándar de la industria |
| **Jobs** | BullMQ | Confiable, monitoring built-in |
| **Hosting** | Vercel | Zero-config, auto-scaling |

---

**Próximos pasos**: Ver [ROADMAP.md](./ROADMAP.md) para implementación por fases.
