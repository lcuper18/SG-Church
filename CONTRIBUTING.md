# Guía de Contribución - SG Church

¡Gracias por tu interés en contribuir a SG Church! Este proyecto existe para servir a iglesias de todos los tamaños de forma gratuita, y tu ayuda es muy valiosa.

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Puedo Contribuir](#cómo-puedo-contribuir)
- [Setup de Desarrollo](#setup-de-desarrollo)
- [Proceso de Desarrollo](#proceso-de-desarrollo)
- [Guías de Estilo](#guías-de-estilo)
- [Proceso de Pull Request](#proceso-de-pull-request)
- [Reportar Bugs](#reportar-bugs)
- [Sugerir Features](#sugerir-features)

---

## Código de Conducta

Este proyecto adhiere al [Contributor Covenant Code of Conduct](./CODE_OF_CONDUCT.md). Al participar, se espera que mantengas este código. Por favor reporta comportamientos inaceptables a conduct@sgchurch.app.

### Nuestro Compromiso

- Crear un ambiente acogedor e inclusivo
- Respetar diferentes puntos de vista y experiencias
- Aceptar críticas constructivas con gracia
- Enfocarnos en lo que es mejor para la comunidad
- Mostrar empatía hacia otros miembros de la comunidad

---

## Cómo Puedo Contribuir

Hay muchas formas de contribuir a SG Church:

### 1. 🐛 Reportar Bugs

Si encuentras un bug:
- Busca en [issues existentes](https://github.com/your-org/sg-church/issues) para ver si ya fue reportado
- Si no existe, [crea un nuevo issue](https://github.com/your-org/sg-church/issues/new?template=bug_report.md)
- Incluye toda la información posible (ver [Reportar Bugs](#reportar-bugs))

### 2. 💡 Sugerir Features

Tienes una idea para mejorar SG Church:
- Revisa el [ROADMAP.md](./ROADMAP.md) para ver si ya está planificado
- Busca en issues existentes con label `enhancement`
- [Crea un Feature Request](https://github.com/your-org/sg-church/issues/new?template=feature_request.md)

### 3. 📝 Mejorar Documentación

La documentación siempre puede mejorar:
- Corregir typos o errores
- Agregar ejemplos o clarificaciones
- Traducir documentación a otros idiomas
- Crear tutoriales o guías

### 4. 💻 Contribuir Código

Hay varios tipos de contribuciones de código:

**Good First Issues**:
- Busca issues con label [`good first issue`](https://github.com/your-org/sg-church/labels/good%20first%20issue)
- Son tareas bien definidas, ideales para primeros contribuidores

**Bug Fixes**:
- Busca issues con label [`bug`](https://github.com/your-org/sg-church/labels/bug)
- Comenta en el issue que trabajarás en él

**Features**:
- Busca issues con label [`enhancement`](https://github.com/your-org/sg-church/labels/enhancement)
- Discute el approach antes de empezar código

**Tests**:
- Agregar tests para código sin coverage
- Mejorar tests existentes

### 5. 🎨 Diseño y UX

- Sugerir mejoras de UI/UX
- Crear mockups o prototipos
- Hacer accessibility audits

### 6. 🌍 Traducciones

- Traducir la aplicación a tu idioma
- Revisar traducciones existentes
- Ver [`docs/i18n.md`](./docs/i18n.md) para guía

---

## Setup de Desarrollo

### Prerequisitos

Asegúrate de tener instalado:

- **Node.js** 20+ ([descarga](https://nodejs.org/))
- **pnpm** 8+ (instalar: `npm install -g pnpm`)
- **Git** ([descarga](https://git-scm.com/))
- **PostgreSQL** 16+ ([descarga](https://www.postgresql.org/download/))
  - Alternativa: Cuenta en [Supabase](https://supabase.com) (gratis)
- **Redis** 7+ ([descarga](https://redis.io/download))
  - Alternativa: Cuenta en [Upstash](https://upstash.com) (gratis)

### Clonar el Repositorio

```bash
# Fork el repositorio en GitHub primero, luego:
git clone https://github.com/TU-USUARIO/sg-church.git
cd sg-church

# Agregar upstream remote
git remote add upstream https://github.com/your-org/sg-church.git
```

### Instalar Dependencias

```bash
pnpm install
```

Esto instalará todas las dependencias de todos los paquetes en el monorepo.

### Configurar Variables de Entorno

```bash
# Copiar ejemplo
cp apps/web/.env.example apps/web/.env.local

# Editar con tus valores
nano apps/web/.env.local  # o usa tu editor favorito
```

**Variables mínimas para desarrollo**:

```env
# Database (usa Supabase o PostgreSQL local)
DATABASE_URL="postgresql://postgres:password@localhost:5432/sgchurch_dev"

# NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="genera-secreto-con-openssl-rand-base64-32"

# Stripe (usa test keys)
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_test_..."

# Email (Resend free tier)
RESEND_API_KEY="re_..."

# Redis (local o Upstash)
REDIS_URL="redis://localhost:6379"

# Storage (Supabase)
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_ANON_KEY="eyJ..."
```

### Setup de Base de Datos

1. **Crear base de datos**:
```bash
createdb sgchurch_dev
```

2. **Ejecutar migraciones**:
```bash
pnpm db:migrate
```

3. **Seedear datos de prueba** (opcional):
```bash
pnpm db:seed
```

Esto creará un tenant de prueba con datos de ejemplo.

### Iniciar Servidor de Desarrollo

```bash
# Inicia todos los servicios
pnpm dev

# O inicia servicios individuales
pnpm dev:web      # Solo Next.js app
pnpm dev:worker   # Solo background workers
```

La app estará disponible en `http://localhost:3000`

### Verificar Setup

```bash
# Ejecutar tests
pnpm test

# Ejecutar linter
pnpm lint

# Build para verificar que compila
pnpm build
```

Si todo pasa ✅, estás listo para contribuir!

---

## Proceso de Desarrollo

### 1. Sincronizar tu Fork

Antes de empezar cualquier trabajo nuevo:

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

### 2. Crear Branch de Feature

```bash
# Nomenclatura: type/short-description
git checkout -b feat/member-bulk-delete
git checkout -b fix/donation-receipt-email
git checkout -b docs/update-api-guide
```

**Tipos de branches**:
- `feat/` - Nueva funcionalidad
- `fix/` - Bug fix
- `docs/` - Solo documentación
- `refactor/` - Refactorización sin cambiar funcionalidad
- `test/` - Agregar tests
- `chore/` - Mantenimiento, deps, configs

### 3. Hacer Cambios

- Escribe código siguiendo las [Guías de Estilo](#guías-de-estilo)
- Haz commits pequeños y descriptivos
- Escribe tests para tu código
- Actualiza documentación si es necesario

### 4. Commit Guidelines

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Formato
<type>(<scope>): <subject>

# Ejemplos
feat(members): add bulk delete functionality
fix(donations): correct receipt email template
docs(api): update tRPC router documentation
refactor(auth): extract permission logic to utility
test(members): add unit tests for family relationships
```

**Types**:
- `feat`: Nueva feature
- `fix`: Bug fix
- `docs`: Cambios en documentación
- `style`: Formatting, sin cambios de código
- `refactor`: Refactoring
- `test`: Agregar tests
- `chore`: Mantenimiento

**Scope** (opcional): Módulo afectado (members, donations, courses, etc.)

### 5. Push y Crear Pull Request

```bash
git push origin feat/member-bulk-delete
```

Luego en GitHub, crea un Pull Request desde tu branch hacia `main` del repositorio upstream.

---

## Guías de Estilo

### TypeScript

- **Strict mode**: Siempre habilitar TypeScript strict
- **No `any`**: Evita `any`, usa `unknown` si es necesario
- **Explicit return types**: Para funciones públicas
- **Interfaces over types**: Para objetos, prefiere `interface`

```typescript
// ✅ Good
interface Member {
  id: string
  firstName: string
  lastName: string
}

async function getMember(id: string): Promise<Member | null> {
  // ...
}

// ❌ Bad
function getMember(id: any) {  // any, no return type
  // ...
}
```

### React Components

- **Functional components**: Usa function declarations
- **TypeScript props**: Siempre tipea props
- **Server Components**: Por defecto (Next.js App Router)
- **Client Components**: Solo cuando necesario (`'use client'`)

```typescript
// ✅ Good - Server Component
interface MemberCardProps {
  member: Member
  showEmail?: boolean
}

export function MemberCard({ member, showEmail = false }: MemberCardProps) {
  return (
    <div>
      <h3>{member.firstName} {member.lastName}</h3>
      {showEmail && <p>{member.email}</p>}
    </div>
  )
}

// ✅ Good - Client Component (cuando necesario)
'use client'

export function MemberForm() {
  const [firstName, setFirstName] = useState('')
  // ...
}
```

### Naming Conventions

- **Components**: PascalCase (`MemberCard.tsx`)
- **Functions**: camelCase (`getMemberById`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_UPLOAD_SIZE`)
- **Files**: kebab-case para utils (`format-currency.ts`)
- **CSS classes**: Tailwind utilities (no custom CSS en lo posible)

### File Organization

```
feature/
├── components/
│   ├── member-card.tsx        # Component
│   ├── member-form.tsx
│   └── member-list.tsx
├── hooks/
│   └── use-members.ts         # Custom hooks
├── lib/
│   ├── validations.ts         # Zod schemas
│   └── utils.ts               # Utility functions
└── page.tsx                   # Next.js page
```

### Imports Order

```typescript
// 1. React y frameworks
import { useState } from 'react'
import { useRouter } from 'next/navigation'

// 2. External libraries
import { z } from 'zod'
import { useForm } from 'react-hook-form'

// 3. Internal packages
import { db } from '@/lib/db'
import { trpc } from '@/lib/trpc'

// 4. Components
import { Button } from '@/components/ui/button'
import { MemberCard } from './components/member-card'

// 5. Types
import type { Member } from '@/types'

// 6. Styles (si aplica)
import styles from './page.module.css'
```

### Comments

- **JSDoc**: Para funciones públicas
- **Inline comments**: Solo cuando código no es obvio
- **TODOs**: Incluye issue number

```typescript
/**
 * Retrieves a member by ID with related data
 * @param id - Member UUID
 * @param include - Related data to include
 * @returns Member with relations or null
 */
export async function getMemberWithRelations(
  id: string,
  include: { donations?: boolean; family?: boolean } = {}
): Promise<MemberWithRelations | null> {
  // TODO(#123): Add caching layer
  return await db.member.findUnique({
    where: { id },
    include,
  })
}
```

### Testing

- **Test files**: Co-located con código (`member-card.test.tsx`)
- **Describe blocks**: Por función/componente
- **Test names**: Descriptivos y específicos

```typescript
// member-card.test.tsx
import { render, screen } from '@testing-library/react'
import { MemberCard } from './member-card'

describe('MemberCard', () => {
  it('renders member name', () => {
    const member = { firstName: 'John', lastName: 'Doe' }
    render(<MemberCard member={member} />)
    expect(screen.getByText('John Doe')).toBeInTheDocument()
  })
  
  it('shows email when showEmail prop is true', () => {
    const member = { firstName: 'John', lastName: 'Doe', email: 'john@example.com' }
    render(<MemberCard member={member} showEmail />)
    expect(screen.getByText('john@example.com')).toBeInTheDocument()
  })
})
```

### Git Commit Messages

- Primera línea: máximo 72 caracteres
- Presente imperativo: "Add feature" no "Added feature"
- Cuerpo opcional con detalles
- Referenciar issues: `Closes #123`

```
feat(members): add bulk delete with confirmation dialog

- Implement multi-select in MemberList component
- Add confirmation modal with member count
- Create tRPC mutation for bulk delete
- Add optimistic updates to cache

Closes #123
```

---

## Proceso de Pull Request

### Antes de Crear el PR

- [ ] ✅ Sync con upstream/main (no merge conflicts)
- [ ] ✅ Tests pasan (`pnpm test`)
- [ ] ✅ Linter pasa (`pnpm lint`)
- [ ] ✅ Build exitoso (`pnpm build`)
- [ ] ✅ Commits siguen convención
- [ ] ✅ Documentación actualizada si aplica
- [ ] ✅ Código auto-documentado o comentado

### Crear el PR

1. **Título descriptivo**:
   ```
   feat(members): add bulk delete functionality
   ```

2. **Descripción completa** usando template:

```markdown
## Description
Implements bulk delete feature for members with confirmation dialog.

## Type of Change
- [x] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update

## Related Issue
Closes #123

## Screenshots (si UI changes)
![Before](url)
![After](url)

## Checklist
- [x] Tests added
- [x] Documentation updated
- [x] No breaking changes
- [x] Follows style guide
```

3. **Request reviewers**: El equipo asignará reviewers automáticamente

### Durante Code Review

- **Responde a comentarios**: Discute constructivamente
- **Haz cambios solicitados**: Push nuevos commits al branch
- **No hacer force push**: Mantén historia de review
- **Mark conversations resolved**: Cuando hagas el cambio

### Después de Approval

- **Squash and merge**: Usamos squash merge strategy
- **Delete branch**: GitHub lo hace automáticamente
- **Cerrar issue**: Si era referenced con `Closes #123`

---

## Reportar Bugs

### Antes de Reportar

1. **Verifica que sea realmente un bug** (no feature faltante)
2. **Busca en issues existentes**
3. **Reproduce en última versión** de main

### Crear Bug Report

Usa el [template de bug report](https://github.com/your-org/sg-church/issues/new?template=bug_report.md):

**Información requerida**:

```markdown
**Describe the bug**
Clara descripción del bug.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
Qué esperabas que pasara.

**Screenshots**
Si aplica, agrega screenshots.

**Environment:**
 - OS: [e.g. macOS 14.2]
 - Browser: [e.g. Chrome 121]
 - Version: [e.g. v0.1.0]

**Additional context**
Cualquier otro contexto sobre el problema.

**Console errors** (si aplica)
```javascript
// Paste console errors here
```
```

### Severidad

Marca con label apropiado:
- `critical`: Sistema down o data loss
- `high`: Feature importante broken
- `medium`: Bug molesto pero workaround existe
- `low`: Bug cosmético

---

## Sugerir Features

### Feature Request Process

1. **Verifica ROADMAP.md**: Puede estar ya planificado
2. **Busca feature requests existentes**
3. **[Crea Feature Request](https://github.com/your-org/sg-church/issues/new?template=feature_request.md)**

### Template

```markdown
**Is your feature request related to a problem?**
Descripción del problema. "I'm frustrated when..."

**Describe the solution you'd like**
Clara descripción de lo que quieres que pase.

**Describe alternatives you've considered**
Otras soluciones que consideraste.

**Use case**
Cómo usarías esta feature en práctica.

**Additional context**
Screenshots, mockups, etc.
```

### Proceso de Evaluación

1. **Community feedback**: Reacciones 👍 en issue
2. **Team review**: Evalúa fit con roadmap
3. **Priority assignment**: Based on impact y effort
4. **Phase assignment**: Asignado a Fase 2, 3, o 4

---

## Recursos Adicionales

### Documentación

- [Architecture Guide](./ARCHITECTURE.md)
- [Database Schema](./DATABASE.md)
- [Tech Stack](./TECH_STACK.md)
- [API Documentation](./docs/API.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)

### Comunicación

- **GitHub Issues**: Bugs, features, questions
- **GitHub Discussions**: General discussion, Q&A
- **Discord** (coming soon): Real-time chat con contribuidores
- **Email**: contribute@sgchurch.app

### Recursos de Aprendizaje

**Next.js**:
- [Next.js Docs](https://nextjs.org/docs)
- [Next.js Learn](https://nextjs.org/learn)

**tRPC**:
- [tRPC Docs](https://trpc.io/docs)
- [tRPC Quickstart](https://trpc.io/docs/quickstart)

**Prisma**:
- [Prisma Docs](https://www.prisma.io/docs)
- [Prisma Schema Reference](https://www.prisma.io/docs/reference/api-reference/prisma-schema-reference)

**TypeScript**:
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

---

## Reconocimiento

Todos los contribuidores son listados en:
- [Contributors Page](https://github.com/your-org/sg-church/graphs/contributors)
- [CONTRIBUTORS.md](./CONTRIBUTORS.md) (actualizado mensualmente)

Las contribuciones significativas pueden resultar en:
- Mencionado en release notes
- Invitación a equipo de core contributors
- Swag (stickers, t-shirts) si el proyecto crece

---

## Licencia

Al contribuir a SG Church, aceptas que tus contribuciones serán licenciadas bajo la [MIT License](./LICENSE).

---

**¡Gracias por hacer de SG Church un mejor proyecto para servir a iglesias alrededor del mundo! 🙏**

**¿Dudas?** Pregunta en [GitHub Discussions](https://github.com/your-org/sg-church/discussions) o contacta contribute@sgchurch.app
