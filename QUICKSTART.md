# Quick Start Guide - SG Church

Esta guía te ayudará a comenzar con el desarrollo de SG Church en cuestión de minutos.

## 📋 Prerequisitos

Antes de comenzar, asegúrate de tener instalado:

- **Node.js**: v20.0.0 o superior
- **pnpm**: v8.0.0 o superior
- **PostgreSQL**: v16.0 o superior
- **Redis**: v7.0 o superior (opcional en desarrollo)
- **Git**: Para control de versiones

### Instalación de Prerequisitos

#### Linux (Ubuntu/Debian)
```bash
# Node.js (via nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# pnpm
npm install -g pnpm

# PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Redis
sudo apt install redis-server
```

#### macOS
```bash
# Homebrew (si no está instalado)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Node.js
brew install node@20

# pnpm
npm install -g pnpm

# PostgreSQL
brew install postgresql@16

# Redis
brew install redis
```

## 🚀 Inicio Rápido (Proyecto Completo - Próximamente)

> **Nota**: El código aún no está implementado. Esta guía estará disponible una vez que se apruebe la planificación y se implemente la Fase 1.

### 1. Clonar el Repositorio
```bash
git clone https://github.com/your-org/sg-church.git
cd sg-church
```

### 2. Instalar Dependencias
```bash
pnpm install
```

### 3. Configurar Variables de Entorno
```bash
# Copiar el archivo de ejemplo
cp .env.example .env.local

# Editar con tus valores
nano .env.local
```

**Variables mínimas requeridas para desarrollo:**
```bash
# Database
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/sg_church?schema=public"

# NextAuth
NEXTAUTH_SECRET="your-super-secret-key-here"
NEXTAUTH_URL="http://localhost:3000"
```

### 4. Configurar Base de Datos
```bash
# Generar cliente Prisma
pnpm db:generate

# Ejecutar migraciones
pnpm db:migrate

# (Opcional) Poblar con datos de prueba
pnpm db:seed
```

### 5. Iniciar Servidor de Desarrollo
```bash
pnpm dev
```

La aplicación estará disponible en: http://localhost:3000

## 🛠️ Comandos Disponibles

### Desarrollo
```bash
pnpm dev              # Iniciar todos los servicios en modo desarrollo
pnpm dev:web          # Solo la aplicación web
pnpm dev:worker       # Solo el worker de trabajos en segundo plano
```

### Base de Datos
```bash
pnpm db:generate      # Generar cliente Prisma
pnpm db:migrate       # Ejecutar migraciones pendientes
pnpm db:migrate:create # Crear nueva migración
pnpm db:seed          # Poblar base de datos con datos de prueba
pnpm db:studio        # Abrir Prisma Studio (GUI para DB)
```

### Testing
```bash
pnpm test             # Ejecutar tests unitarios
pnpm test:watch       # Tests en modo watch
pnpm test:e2e         # Ejecutar tests E2E con Playwright
pnpm test:coverage    # Generar reporte de cobertura
```

### Build y Deploy
```bash
pnpm build            # Compilar todo el proyecto
pnpm start            # Iniciar en modo producción
pnpm lint             # Ejecutar linter
pnpm format           # Formatear código con Prettier
pnpm type-check       # Verificar tipos TypeScript
```

### Utilidades
```bash
pnpm clean            # Limpiar builds y node_modules
pnpm --filter web build  # Compilar solo la app web
```

## 📁 Estructura del Proyecto

### Estructura Actual (Documentación)
```
SG_Church/
├── docs/                    # Documentación detallada
│   ├── DEPLOYMENT.md       # Guía de deployment
│   ├── FAQ.md              # Preguntas frecuentes
│   └── GLOSSARY.md         # Glosario de términos
│
├── .github/                # Configuración de GitHub
│   ├── ISSUE_TEMPLATE/     # Plantillas de issues
│   └── pull_request_template.md
│
├── ARCHITECTURE.md         # Arquitectura del sistema
├── CHANGELOG.md            # Historial de cambios
├── CONTRIBUTING.md         # Guía de contribución
├── DATABASE.md             # Esquema de base de datos
├── LICENSE                 # Licencia MIT
├── README.md               # Documentación principal
├── ROADMAP.md              # Plan de desarrollo
├── SECURITY.md             # Política de seguridad
├── TECH_STACK.md           # Stack tecnológico
│
├── .env.example            # Plantilla de variables de entorno
├── .gitignore              # Archivos ignorados por Git
├── .prettierrc             # Configuración de Prettier
├── package.json            # Dependencias y scripts
├── tsconfig.json           # Configuración TypeScript
└── turbo.json              # Configuración Turborepo
```

### Estructura Planeada (Código)

Una vez que comience el desarrollo, el proyecto se expandirá a:

```
SG_Church/
├── apps/                           # Aplicaciones
│   ├── web/                        # App Next.js principal
│   │   ├── app/                   # App Router
│   │   ├── components/            # Componentes React
│   │   ├── lib/                   # Utilidades
│   │   ├── public/                # Assets estáticos
│   │   └── middleware.ts          # Next.js middleware
│   │
│   └── mobile/ (Fase 4)           # React Native app
│
├── packages/                       # Paquetes compartidos
│   ├── ui/                        # Componentes UI (shadcn/ui)
│   ├── database/                  # Prisma schema y cliente
│   ├── api/                       # Routers tRPC
│   ├── auth/                      # Lógica de autenticación
│   ├── email/                     # Templates de email
│   └── config/                    # Configs compartidas
│
├── services/                       # Servicios backend
│   ├── worker/                    # BullMQ worker
│   └── api/ (Fase 4)             # API standalone
│
└── tests/                          # Tests E2E e integración
```

### Convenciones de Nombres

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Componentes | PascalCase | `MemberCard.tsx` |
| Utilidades | camelCase | `formatDate.ts` |
| Tipos | PascalCase + `.types.ts` | `Member.types.ts` |
| Rutas API | kebab-case | `create-member.ts` |
| Tests | Mismo + `.test.ts` | `member.test.ts` |

### Alias de Import

```typescript
// En apps/web
import { Button } from '@/components/ui/button'
import { prisma } from '@/lib/prisma'
import { getCurrentUser } from '@/lib/auth'

// En todo el monorepo
import { Button } from '@sg-church/ui'
import { prisma } from '@sg-church/database'
import { memberRouter } from '@sg-church/api'
```

## 🎯 Próximos Pasos en el Desarrollo

Una vez aprobada la planificación, se implementará:

1. **Estructura del Monorepo**
   - `apps/web/` - Aplicación Next.js principal
   - `packages/` - Paquetes compartidos (UI, API, Database, etc.)
   - `services/` - Servicios backend (Worker, etc.)

2. **Configuración Inicial**
   - Setup de Next.js 14 con App Router
   - Configuración de Prisma
   - Setup de tRPC
   - Configuración de NextAuth.js

3. **Primera Funcionalidad (Sprint 1)**
   - Sistema de autenticación
   - Registro de iglesias (tenants)
   - Dashboard básico
   - Gestión de usuarios

## 📖 Recursos Útiles

### Documentación Esencial
- [README Principal](./README.md) - Visión general del proyecto
- [Arquitectura](./ARCHITECTURE.md) - Decisiones técnicas
- [Roadmap](./ROADMAP.md) - Plan de desarrollo por fases
- [Contributing](./CONTRIBUTING.md) - Cómo contribuir

### Enlaces Externos
- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [tRPC Documentation](https://trpc.io/docs)
- [NextAuth.js Documentation](https://next-auth.js.org)

## ❓ Problemas Comunes

### Error de conexión a PostgreSQL
```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Iniciar PostgreSQL
sudo systemctl start postgresql
```

### Puerto 3000 ya en uso
```bash
# Matar el proceso en el puerto 3000
lsof -ti:3000 | xargs kill -9

# O usar un puerto diferente
PORT=3001 pnpm dev
```

### Error de permisos en PostgreSQL
```bash
# Crear usuario y base de datos
sudo -u postgres psql
CREATE DATABASE sg_church;
CREATE USER sg_church_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE sg_church TO sg_church_user;
\q
```

### Prisma genera error de schema
```bash
# Limpiar y regenerar
pnpm db:generate --force
```

## 🤝 Obtener Ayuda

Si tienes problemas:

1. **Revisa la [FAQ](./docs/FAQ.md)** - Respuestas a preguntas comunes
2. **Busca en [Issues](https://github.com/your-org/sg-church/issues)** - Problemas conocidos
3. **Pregunta en [Discussions](https://github.com/your-org/sg-church/discussions)** - Foro de la comunidad
4. **Email**: support@sgchurch.app

## 🎓 Aprender Más

### Tutoriales Recomendados
- [Next.js App Router Tutorial](https://nextjs.org/learn)
- [Prisma Getting Started](https://www.prisma.io/docs/getting-started)
- [tRPC with Next.js](https://trpc.io/docs/quickstart)
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)

### Conceptos Clave
- **Multi-Tenancy**: [Comprender schema-per-tenant](./ARCHITECTURE.md#multi-tenancy-strategy)
- **tRPC**: [APIs Type-Safe](./ARCHITECTURE.md#api-layer-trpc)
- **Prisma**: [ORM y Migraciones](./DATABASE.md)

## 📝 Estado Actual

> ⚠️ **IMPORTANTE**: Este proyecto está actualmente en **fase de planificación**.
> 
> Toda la documentación está completa y lista para revisión. El código se implementará una vez que se apruebe la planificación.
> 
> **Documentos completados:**
> - ✅ Planificación completa (ROADMAP con 4 fases)
> - ✅ Arquitectura técnica definida
> - ✅ Esquema de base de datos diseñado
> - ✅ Stack tecnológico seleccionado
> - ✅ Guías de contribución y seguridad
> - ✅ Templates de GitHub
> - ✅ Configuración de proyecto (TypeScript, Turborepo, etc.)
> 
> **Próximo paso**: Revisión y aprobación de la planificación

---

**¿Listo para contribuir?** Lee [CONTRIBUTING.md](./CONTRIBUTING.md) para empezar.

**¿Tienes preguntas?** Consulta la [FAQ](./docs/FAQ.md) o abre una [Discussion](https://github.com/your-org/sg-church/discussions).
