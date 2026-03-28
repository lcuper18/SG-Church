# Política de Seguridad

## Versiones Soportadas

Actualmente damos soporte y parches de seguridad para las siguientes versiones:

| Versión | Soportada          |
| ------- | ------------------ |
| 0.x     | :white_check_mark: |

Una vez lancemos v1.0:

| Versión | Soportada          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| 0.x     | :x:                |

---

## Reportar una Vulnerabilidad

**La seguridad de los datos de las iglesias es nuestra máxima prioridad.**

### ⚠️ NO Crear Issue Público

Por favor **NO** reportes vulnerabilidades de seguridad a través de issues públicos de GitHub, ya que esto podría poner en riesgo a iglesias que usan la plataforma.

### ✅ Proceso de Reporte Responsable

1. **Email**: Envía un email a **security@sgchurch.app**

2. **Incluye en tu reporte**:
   - Descripción detallada de la vulnerabilidad
   - Pasos para reproducir el problema
   - Impacto potencial (qué datos están en riesgo)
   - Severidad estimada (crítica, alta, media, baja)
   - Cualquier prueba de concepto (PoC) o exploit
   - Tu nombre/organización si deseas ser acreditado

3. **Qué esperar**:
   - **24 horas**: Confirmación de recepción
   - **72 horas**: Evaluación inicial de severidad
   - **7 días**: Plan de remediación comunicado
   - **30 días**: Fix deployed (para vulnerabilidades críticas)
   - **90 días**: Divulgación pública coordinada (opcional)

### Severidad y Tiempos de Respuesta

| Severidad | Descripción | Tiempo de Fix | Ejemplo |
|-----------|-------------|---------------|---------|
| **Crítica** | Acceso no autorizado a datos de multiple tenants | 24-48 horas | SQL injection que permite leer datos de otras iglesias |
| **Alta** | Acceso no autorizado a datos dentro de un tenant | 3-7 días | Fallo de autorización que permite miembro ver datos de otro |
| **Media** | Exposición de información sensible | 14 días | Información de miembro en HTML source |
| **Baja** | Issues de configuración o información | 30 días | Versión de software expuesta en headers |

### Programa de Recompensas (Bug Bounty)

Actualmente **NO** tenemos un programa formal de bug bounty, pero:

- ✅ **Reconocimiento público** (con tu permiso)
- ✅ **Mencionado en security advisories**
- ✅ **Swag del proyecto** (cuando esté disponible)

Consideraremos implementar un programa monetario en Fase 3 cuando tengamos funding.

---

## Mejores Prácticas de Seguridad

### Para Usuarios (Iglesias)

#### Contraseñas Fuertes
- Mínimo 12 caracteres
- Combina letras, números y símbolos
- No reutilices contraseñas de otros servicios
- Usa un password manager

#### Autenticación de Dos Factores (2FA)
- Habilita 2FA para cuentas admin (disponible en Fase 2)
- Usa apps como Google Authenticator o Authy

#### Permisos de Usuario
- Asigna roles siguiendo principio de **least privilege**
- Revisa permisos regularmente
- Desactiva cuentas de usuarios que ya no son parte del staff

#### Datos Sensibles
- No compartas credenciales de login
- No incluyas información sensible (SSN, números de cuenta) en notas de miembros
- Revisa configuración de privacidad del directorio de miembros

### Para Desarrolladores

#### Code Security

- ✅ **Input validation**: Validar todo input con Django Forms y serializers
- ✅ **SQL Injection**: Usamos Django ORM (queries parametrizadas automáticamente)
- ✅ **XSS Prevention**: Django templates escapan output automáticamente
- ✅ **CSRF Protection**: Django maneja CSRF tokens automáticamente
- ✅ **Sanitize HTML**: Si permitimos HTML, usar DOMPurify

#### Authentication & Authorization

- ✅ **Password hashing**: bcrypt con salt rounds 12+
- ✅ **Session management**: HTTP-only cookies
- ✅ **JWT tokens**: Short-lived (15 min), refresh tokens rotated
- ✅ **Permission checks**: En cada API endpoint (no solo UI)

```typescript
// ❌ Bad: Solo check en UI
{user.role === 'ADMIN' && <DeleteButton />}

// ✅ Good: Check en backend también
export const deleteMember = protectedProcedure
  .input(z.object({ id: z.string() }))
  .mutation(async ({ input, ctx }) => {
    // Authorization check
    const ability = defineAbilitiesFor(ctx.session.user)
    if (!ability.can('delete', 'Member')) {
      throw new TRPCError({ code: 'FORBIDDEN' })
    }
    
    // Proceed
    await ctx.db.member.delete({ where: { id: input.id } })
  })
```

#### Data Protection

- ✅ **Encryption at rest**: Datos sensibles encrypted en DB
- ✅ **Encryption in transit**: HTTPS/TLS 1.3 obligatorio
- ✅ **Environment secrets**: Nunca commitear .env files
- ✅ **Audit logging**: Log acceso a datos financieros

#### Multi-Tenant Security

- ✅ **Tenant isolation**: Verificar en CADA query
- ✅ **Middleware enforcement**: Tenant context en cada request

```typescript
// ✅ Always include tenant check
export async function getMembers(ctx: Context) {
  const tenantId = ctx.session.tenant.id
  
  return await db.member.findMany({
    where: { tenantId }  // CRITICAL: Filter by tenant
  })
}
```

#### Dependency Security

```bash
# Check vulnerabilities regularmente
pip-audit

# Update dependencies
pip install -U -r requirements.txt

# Automated scanning
# GitHub Dependabot: Enabled
# Snyk: Configured in CI/CD
```

#### Rate Limiting

```typescript
// Prevent brute force attacks
import { rateLimit } from '@/lib/rate-limit'

export async function POST(req: Request) {
  const identifier = req.headers.get('x-forwarded-for')
  
  const { success } = await rateLimit.check(identifier, {
    limit: 10,
    window: '1m',
  })
  
  if (!success) {
    return new Response('Too many requests', { status: 429 })
  }
  
  // Proceed
}
```

---

## Medidas de Seguridad Implementadas

### Application Security

- ✅ **HTTPS only**: Redirect HTTP → HTTPS
- ✅ **Security headers**: 
  - Content-Security-Policy
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - Referrer-Policy: strict-origin-when-cross-origin
- ✅ **CORS**: Configurado restrictivamente
- ✅ **Rate limiting**: API endpoints protegidos
- ✅ **Input sanitization**: Django Forms validation en todos los endpoints

### Database Security

- ✅ **Schema-per-tenant**: Máxima aislación de datos
- ✅ **Row-level security**: Policies adicionales en PG
- ✅ **Least privilege**: App DB user sin permisos de DROP/ALTER
- ✅ **Database backups**: Encrypted at rest
- ✅ **Connection pooling**: Con credentials rotation

### Infrastructure Security

- ✅ **Secrets management**: Nunca en código, solo env vars
- ✅ **Vercel security**: 
  - DDoS protection
  - Edge network
  - Automatic SSL
- ✅ **Database encryption**: At rest (Supabase/AWS RDS)
- ✅ **Network isolation**: DB no accesible públicamente

### Monitoring & Alerting

- ✅ **Error tracking**: Sentry captura excepciones
- ✅ **Audit logs**: Todas las operaciones críticas logged
- ✅ **Failed login attempts**: Monitoreados y alertados
- ✅ **Suspicious activity**: Automated detection (próximamente)

### Compliance

- ✅ **GDPR**: 
  - Data export capability
  - Right to erasure
  - Consent tracking
- ✅ **PCI DSS**: Manejado por Stripe (no almacenamos card data)
- 🔄 **SOC 2 Type 1**: Planificado para Fase 4

---

## Auditorías de Seguridad

### Auditorías Completadas

| Fecha | Tipo | Resultado | Issues Encontrados | Issues Resueltos |
|-------|------|-----------|-------------------|------------------|
| - | - | - | - | - |

*Actualizaremos esta tabla después de cada auditoría*

### Próximas Auditorías Planificadas

- **Q3 2026**: Penetration testing por firma externa
- **Q4 2026**: Code audit completo
- **Ongoing**: Automated scanning con Snyk

---

## Divulgación Responsable

### Nuestra Política

Creemos en **coordinated disclosure**:

1. **Reporter nos notifica** privadamente
2. **Evaluamos y desarrollamos fix**
3. **Deployamos fix** a producción
4. **Notificamos a usuarios afectados** (si aplica)
5. **Publicamos advisory** 
   - Después de que fix esté deployed
   - Con crédito al reporter (si desea)
   - Típicamente después de 30-90 días

### Security Advisories

Publicamos advisories en:
- GitHub Security Advisories
- Blog de SG Church
- Email a iglesias afectadas (si crítico)

Ejemplo de advisory:
```markdown
# Security Advisory: SQL Injection en Member Search

**CVE**: CVE-2026-XXXXX
**Severity**: High
**Affected versions**: v0.1.0 - v0.3.5
**Fixed in**: v0.4.0

## Description
SQL injection vulnerability en member search permitía...

## Impact
Usuarios con rol Teacher podían ver datos de...

## Mitigation
Actualizar a v0.4.0 o superior.

## Credit
Gracias a @researcher por el reporte responsable.
```

---

## Contacto

- **Security issues**: security@sgchurch.app
- **General contact**: support@sgchurch.app
- **PGP key**: [Coming soon]

---

## Reconocimientos

Agradecemos a los siguientes investigadores de seguridad por sus contribuciones:

*Lista será actualizada según recibamos reportes*

---

**Última actualización**: Febrero 15, 2026
