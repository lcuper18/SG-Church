# Política de Seguridad

## Versiones Soportadas

El proyecto todavía no tiene versiones etiquetadas (`v1.0`, etc.) — se da
soporte de seguridad sobre la rama `main`.

---

## Reportar una Vulnerabilidad

**La seguridad de los datos de las iglesias es nuestra máxima prioridad.**

### ⚠️ NO Crear Issue Público

Por favor **NO** reportes vulnerabilidades de seguridad a través de issues
públicos de GitHub, ya que esto podría poner en riesgo a iglesias que ya
estén usando la plataforma.

### ✅ Proceso de Reporte Responsable

Si este repositorio es público en GitHub, usá **"Report a vulnerability"**
en la pestaña Security del repositorio (GitHub Private Vulnerability
Reporting) — es privado entre vos y quien mantiene el proyecto.

> TODO antes de publicar este proyecto: reemplazar esta sección con un
> email de seguridad real si se prefiere ese canal en vez de (o además de)
> GitHub Security Advisories.

Incluí en tu reporte:
- Descripción detallada de la vulnerabilidad
- Pasos para reproducirla
- Impacto potencial (qué datos quedarían expuestos)
- Severidad estimada
- Prueba de concepto, si la tenés

### Severidad de referencia

| Severidad | Descripción | Ejemplo |
|-----------|-------------|---------|
| **Crítica** | Acceso no autorizado a datos de otra iglesia | Un bug que rompe el filtrado por `tenant` |
| **Alta** | Un usuario ve/modifica datos que su rol no debería permitirle | Bypass de `can_manage_finance`/`can_manage_members` |
| **Media** | Exposición de información sensible sin acceso directo a datos | Información filtrada en un mensaje de error |
| **Baja** | Configuración o información de bajo impacto | Versión de software expuesta en un header |

No hay un programa de bug bounty (el proyecto es gratuito, financiado por
donaciones) — sí ofrecemos reconocimiento público en el historial de
cambios, con tu permiso.

---

## Qué está implementado hoy

Esta sección refleja el estado real del código (auditado y verificado), no
una lista de aspiraciones:

- **Aislamiento por iglesia**: cada modelo con datos de una iglesia (Member,
  Donation, Expense, Notification, etc.) tiene un campo `tenant`, y toda
  vista/endpoint filtra por él — no hay separación por schema de base de
  datos, es aislamiento a nivel de fila, reforzado por `request.user.tenant`.
- **Control de acceso por rol**: `admin`, `treasurer`, `pastor`,
  `volunteer`, `member` — aplicado tanto en las vistas web
  (`core/mixins.py`) como en la API REST (`core/permissions.py`). Un
  superusuario de Django tiene acceso completo.
- **CSRF**: protección estándar de Django en todos los formularios; el
  único endpoint exento es el webhook de Stripe, que en cambio valida la
  firma de la petición (`stripe.Webhook.construct_event`) como mecanismo
  de confianza.
- **Validación de archivos subidos**: extensión y tamaño máximo en fotos de
  miembros, logos y recibos de gastos (`core/validators.py`).
- **Configuración sin defaults inseguros**: `SECRET_KEY` y
  `DATABASE_PASSWORD` son obligatorios (la app no arranca sin ellos, no hay
  fallback débil); `DEBUG` es `False` por defecto salvo en desarrollo local.
- **Cookies seguras y HSTS** en el modo de producción
  (`sg_church/settings/production.py`): `SESSION_COOKIE_SECURE`,
  `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS.
- **Contraseñas**: hasheadas con los validadores/hashers estándar de
  Django (nunca en texto plano).
- **SQL**: se usa el ORM de Django en prácticamente todo el código (queries
  parametrizadas); no hay SQL crudo con interpolación de strings.

## Qué NO está implementado todavía

Para ser honestos sobre las limitaciones actuales:

- **Sin autenticación de dos factores (2FA)**
- **Sin rate limiting** en login ni en la API (mitigación: usar contraseñas
  fuertes; considerar un proxy/WAF si se expone públicamente)
- **Sin auditoría/logging estructurado** de accesos a datos financieros más
  allá de los logs estándar de la aplicación
- **Sin cifrado a nivel de aplicación** de datos sensibles en la base de
  datos (depende de que el proveedor de hosting/base de datos cifre en
  reposo)
- **Sin auditoría de seguridad externa realizada todavía**
- **Sin herramientas de cumplimiento GDPR** (exportación/borrado de datos)
  implementadas como feature — son operaciones manuales hoy vía Django
  admin o la base de datos directamente

Si tu iglesia maneja datos especialmente sensibles, tenelo en cuenta al
decidir cómo desplegar (self-host detrás de tu propia infraestructura vs.
depender de terceros) y quién tiene acceso administrativo.

---

## Buenas prácticas para quien administra una instancia

- Usá una contraseña fuerte y única para la cuenta admin
- Asigná roles según el principio de mínimo privilegio (no todos necesitan
  ser `admin`)
- Desactivá usuarios que ya no forman parte del staff
- No compartas credenciales de login
- Si desplegás el modo SaaS, restringí el acceso a la base de datos
  Postgres y a Redis — no deben quedar expuestos a internet
- Configurá `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con tu dominio real,
  nunca `*` en producción

---

**Última actualización**: Septiembre 2026 (revisado junto con la auditoría
de seguridad que corrigió el aislamiento por tenant y el control de
acceso por rol).
