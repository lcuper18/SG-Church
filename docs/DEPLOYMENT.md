# Deployment Guide - SG Church

Guía completa para deployar SG Church a producción.

## Tabla de Contenidos

- [Opciones de Deployment](#opciones-de-deployment)
- [Deployment Recomendado (Vercel + Supabase)](#deployment-recomendado-vercel--supabase)
- [Deployment Alternativo (AWS)](#deployment-alternativo-aws)
- [Variables de Entorno](#variables-de-entorno)
- [Database Setup](#database-setup)
- [Migraciones](#migraciones)
- [Monitoring](#monitoring)
- [Backups](#backups)
- [Troubleshooting](#troubleshooting)

---

## Opciones de Deployment

### Opción 1: Vercel + Supabase (Recomendado para MVP)

**Pros**:
- ✅ Zero-config deployment
- ✅ Free tier generoso
- ✅ Auto-scaling
- ✅ Great DX

**Cons**:
- ⚠️ Vendor lock-in
- ⚠️ Costos crecen con escala

**Ideal para**: Fase 1 y 2 (hasta 100 iglesias)

---

### Opción 2: AWS ECS + RDS

**Pros**:
- ✅ Más control
- ✅ Más económico a escala
- ✅ Multi-region support

**Cons**:
- ⚠️ Requiere más conocimiento DevOps
- ⚠️ Setup más complejo

**Ideal para**: Fase 3 y 4 (100+ iglesias)

---

### Opción 3: Self-Hosted (Docker)

**Pros**:
- ✅ Control total
- ✅ Privacidad máxima
- ✅ Sin dependencia de providers

**Cons**:
- ⚠️ Mantenimiento manual
- ⚠️ Necesita expertise

**Ideal para**: Iglesias grandes que quieren hosting propio

---

## Deployment Recomendado (Vercel + Supabase)

### 1. Setup de Supabase

#### Crear Proyecto

1. Ir a [supabase.com](https://supabase.com)
2. Click "New Project"
3. Configurar:
   - **Name**: `sg-church-prod`
   - **Database Password**: Generar seguro
   - **Region**: Más cercana a tus usuarios
   - **Plan**: Free (para comenzar)

#### Configurar Database

```sql
-- Habilitar extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- El resto se aplicará via Prisma migrations
```

#### Configurar Storage

1. Storage > Create bucket
2. Name: `avatars`
3. Public: Yes (files will have signed URLs)
4. Configurar políticas:

```sql
-- Policy: Enable read access for authenticated users
CREATE POLICY "Authenticated users can read avatars"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'avatars');

-- Policy: Enable upload for authenticated users (their tenant only)
CREATE POLICY "Users can upload to their tenant folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'avatars' AND (storage.foldername(name))[1] = auth.jwt() ->> 'tenant_id');
```

### 2. Setup de Stripe

#### Crear Cuenta Stripe

1. Ir a [stripe.com](https://stripe.com)
2. Registrarse
3. Activar cuenta (puede tomar 1-2 días)

#### Configurar Stripe Connect

1. Dashboard > Connect > Get Started
2. Type: Platform or marketplace
3. Configurar onboarding form
4. Obtener keys:
   - Publishable key: `pk_live_...`
   - Secret key: `sk_live_...`

#### Configurar Webhooks

1. Dashboard > Developers > Webhooks
2. Add endpoint: `https://tu-dominio.com/api/webhooks/stripe`
3. Events a escuchar:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
4. Copiar **Webhook signing secret**: `whsec_...`

### 3. Setup de Vercel

#### Instalar Vercel CLI

```bash
npm install -g vercel
```

#### Login y Link Project

```bash
# Login
vercel login

# Link project (desde root del repo)
vercel link
```

#### Configurar Variables de Entorno

```bash
# Producción
vercel env add DATABASE_URL production
vercel env add NEXTAUTH_SECRET production
vercel env add STRIPE_SECRET_KEY production
# ... todas las variables

# Preview (para PRs)
vercel env add DATABASE_URL preview
# ... etc
```

O manualmente en dashboard:
1. Project Settings > Environment Variables
2. Agregar todas las variables (ver sección [Variables de Entorno](#variables-de-entorno))

#### Deploy

```bash
# Deploy production
vercel --prod

# O push a main branch (auto-deploy si configurado)
git push origin main
```

### 4. Configurar Dominio

#### En Vercel

1. Project Settings > Domains
2. Add domain: `sgchurch.app`
3. Configurar DNS según instrucciones

#### En tu DNS provider

Agregar records:

```
Type: A
Name: @
Value: 76.76.21.21

Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

Vercel automáticamente provisiona SSL certificate.

### 5. Ejecutar Migraciones

```bash
# Desde local, apuntando a producción
DATABASE_URL="tu-supabase-url" pnpm db:migrate

# O create migration y deploy automáticamente ejecuta
pnpm db:migrate:deploy
```

### 6. Seed Tenant de Demo (Opcional)

```bash
DATABASE_URL="prod-url" pnpm db:seed
```

---

## Deployment Alternativo (AWS)

### Arquitectura AWS

```
┌──────────────────────┐
│  CloudFront (CDN)    │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  ALB                 │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  ECS Fargate         │
│  (Next.js containers)│
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐  ┌────▼────┐
│RDS PG  │  │ElastiCache
│(Multi- │  │(Redis)  │
│ AZ)    │  │         │
└────────┘  └─────────┘
```

### Terraform Setup (Infraestructura como Código)

```hcl
# infrastructure/terraform/main.tf

provider "aws" {
  region = "us-east-1"
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "sgchurch-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  enable_dns_hostnames = true
}

# RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier           = "sgchurch-db"
  engine               = "postgres"
  engine_version       = "16.1"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  storage_encrypted    = true
  
  db_name  = "sgchurch"
  username = "sgchurch_admin"
  password = var.db_password
  
  multi_az               = true
  backup_retention_period = 30
  
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  skip_final_snapshot = false
  final_snapshot_identifier = "sgchurch-final-snapshot"
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "sgchurch-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379
  
  subnet_group_name = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "sgchurch-cluster"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "sgchurch-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  
  container_definitions = jsonencode([{
    name  = "sgchurch-web"
    image = "${aws_ecr_repository.app.repository_url}:latest"
    
    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]
    
    environment = [
      { name = "NODE_ENV", value = "production" },
      { name = "DATABASE_URL", value = "postgresql://..." }
      # ... más env vars
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/sgchurch"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# S3 para storage
resource "aws_s3_bucket" "storage" {
  bucket = "sgchurch-storage"
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  versioning_configuration {
    status = "Enabled"
  }
}
```

### Deploy con Terraform

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

---

## Variables de Entorno

### Producción (.env.production)

```env
# Application
NODE_ENV=production
NEXT_PUBLIC_APP_URL=https://sgchurch.app

# Database
DATABASE_URL=postgresql://user:pass@host:5432/sgchurch?schema=public&sslmode=require
DATABASE_URL_UNPOOLED=  # Para migraciones (sin pooler)

# NextAuth
NEXTAUTH_URL=https://sgchurch.app
NEXTAUTH_SECRET=  # Generar con: openssl rand -base64 32

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...

# Email (Resend o SES)
RESEND_API_KEY=re_...
# O para AWS SES:
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
SES_FROM_EMAIL=noreply@sgchurch.app

# SMS (Twilio)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=+1234567890

# Redis
REDIS_URL=redis://host:6379

# Storage (Supabase o S3)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# O para S3:
AWS_S3_BUCKET=sgchurch-storage
AWS_S3_REGION=us-east-1

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/...

# Analytics
NEXT_PUBLIC_PLAUSIBLE_DOMAIN=sgchurch.app
```

---

## Migraciones

### Estrategia de Migraciones Multi-Tenant

#### 1. Crear Nueva Migración

```bash
pnpm db:migrate:create --name add_learning_paths
```

#### 2. Aplicar a Todos los Tenants

Crear script `scripts/migrate-all-tenants.ts`:

```typescript
import { PrismaClient } from '@prisma/client'
import { execSync } from 'child_process'

const db = new PrismaClient()

async function migrateAllTenants() {
  // Get all tenants
  const tenants = await db.tenant.findMany()
  
  console.log(`Found ${tenants.length} tenants to migrate`)
  
  for (const tenant of tenants) {
    console.log(`Migrating ${tenant.name} (${tenant.schemaName})...`)
    
    try {
      // Set DATABASE_URL with schema
      const dbUrl = `${process.env.DATABASE_URL}?schema=${tenant.schemaName}`
      
      // Run migration
      execSync('pnpm prisma migrate deploy', {
        env: { ...process.env, DATABASE_URL: dbUrl },
        stdio: 'inherit'
      })
      
      console.log(`✅ ${tenant.name} migrated successfully`)
    } catch (error) {
      console.error(`❌ Failed to migrate ${tenant.name}:`, error)
      process.exit(1)
    }
  }
  
  console.log('All tenants migrated successfully!')
}

migrateAllTenants()
```

Ejecutar:
```bash
DATABASE_URL="prod-url" tsx scripts/migrate-all-tenants.ts
```

#### 3. Rollback Strategy

Para rollback, crear migration que revierte:

```bash
pnpm db:migrate:create --name revert_learning_paths
```

---

## Monitoring

### Sentry Setup

```typescript
// apps/web/instrumentation.ts
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,  // 10% of requests
  
  beforeSend(event, hint) {
    // Don't send certain errors
    if (event.exception?.values?.[0]?.type === 'NotFoundError') {
      return null
    }
    return event
  },
})
```

### Health Check Endpoint

```typescript
// apps/web/app/api/health/route.ts
import { db } from '@/lib/db'
import { redis } from '@/lib/redis'

export async function GET() {
  try {
    // Check database  
    await db.$queryRaw`SELECT 1`
    
    // Check Redis
    await redis.ping()
    
    return Response.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      services: {
        database: 'up',
        redis: 'up',
      }
    })
  } catch (error) {
    return Response.json({
      status: 'unhealthy',
      error: error.message,
    }, { status: 503 })
  }
}
```

### Uptime Monitoring

Configurar en UptimeRobot o similar:
- URL: `https://sgchurch.app/api/health`
- Interval: 5 minutes
- Alertas vía email/SMS si down

---

## Backups

### Automatic Backups (Supabase)

- Daily automatic backups (included)
- Point-in-time recovery (Pro plan)
- Retention: 7 days (Free), 30 days (Pro)

### Manual Backup Script

```bash
#!/bin/bash
# scripts/backup-production.sh

DATE=$(date +%Y-%m-%d-%H%M)
BACKUP_DIR="/backups/sgchurch"

mkdir -p "$BACKUP_DIR"

# Backup public schema (tenants table)
pg_dump "$DATABASE_URL" \
  --schema=public \
  --format=custom \
  --file="$BACKUP_DIR/public_$DATE.dump"

# Backup each tenant schema
psql "$DATABASE_URL" -t -c "SELECT schema_name FROM public.tenants" | \
while read schema; do
  echo "Backing up $schema..."
  pg_dump "$DATABASE_URL" \
    --schema="$schema" \
    --format=custom \
    --file="$BACKUP_DIR/${schema}_$DATE.dump"
done

# Compress all backups
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" "$BACKUP_DIR"/*.dump

# Upload to S3
aws s3 cp "$BACKUP_DIR/backup_$DATE.tar.gz" \
  s3://sgchurch-backups/production/

# Clean local files
rm "$BACKUP_DIR"/*.dump
```

Configurar cron job:
```cron
# Daily backup at 3 AM
0 3 * * * /path/to/scripts/backup-production.sh
```

---

## Troubleshooting

### Issue: Deploy Fails

**Error**: `Build exceeded maximum duration`

**Solución**:
```json
// vercel.json
{
  "builds": [
    {
      "src": "apps/web/package.json",
      "use": "@vercel/next",
      "config": {
        "maxDuration": 60
      }
    }
  ]
}
```

### Issue: Database Connection Timeout

**Error**: `P1001: Can't reach database server`

**Solución**:
1. Verificar security groups (AWS) o allowlist (Supabase)
2. Agregar Vercel IPs a whitelist
3. Usar connection pooling (PgBouncer)

### Issue: Out of Memory

**Error**: `JavaScript heap out of memory`

**Solución**:
```json
// package.json
{
  "scripts": {
    "build": "NODE_OPTIONS='--max-old-space-size=4096' next build"
  }
}
```

### Issue: Stripe Webhook Failures

**Error**: Webhook signature verification failed

**Solución**:
1. Verificar `STRIPE_WEBHOOK_SECRET` correcto
2. Check que endpoint es HTTPS
3. Ver logs en Stripe Dashboard > Webhooks

---

**¿Problemas?** Contacta support@sgchurch.app
