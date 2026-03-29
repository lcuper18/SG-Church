# Roadmap - SG Church

Plan de desarrollo por fases con timeline estimado, prioridades y entregables.

## Resumen Ejecutivo

| Fase | Duración | Período | Estado | Funcionalidades Clave |
|------|----------|---------|--------|----------------------|
| **Fase 1: Fundación (MVP)** | 3-4 meses | Q1-Q2 2026 | 🟢 En Progreso | Auth, Membresía, Donaciones básicas |
| **Fase 2: Core Features** | 3-4 meses | Q2-Q3 2026 | ⚪ Planificado | Bautizos, LMS, Reportes avanzados |
| **Fase 3: Funciones Avanzadas** | 3-4 meses | Q3-Q4 2026 | ⚪ Planificado | Learning Paths, PWA, Workflows |
| **Fase 4: Escalamiento** | 2-3 meses | Q4 2026 | ⚪ Planificado | Performance, API pública, i18n |

**Timeline Total**: 12-18 meses para plataforma completa

### Progreso Actual (Marzo 2026)

| Sprint | Nombre | Estado | Notas |
|--------|--------|--------|-------|
| 1-2 | Setup Inicial | ✅ Completado | Django + DRF + Multi-tenant |
| 3 | Gestión de Membresía | ✅ QA Verificado | Members, Families, Tags, Onboarding |
| 4 | Donaciones y Finanzas | ✅ QA Verificado | Dashboard, Stripe, Reports |
| 5 | Sistema de Notificaciones | ✅ QA Verificado | Email + In-App notifications |
| 6 | Deploy y Testing | ✅ Completado | E2E tests, API tests (25 passed) |

---

## Fase 1: Fundación (MVP)
**Duración**: 3-4 meses | **Q1-Q2 2026** | 🟢 **En Progreso**

### Objetivos
Establecer la base arquitectónica y funcionalidades core mínimas para que una iglesia pueda:
- Registrarse y configurar su cuenta
- Gestionar membresía básica
- Recibir donaciones
- Ver reportes financieros simples

### Hitos y Entregables

#### Sprint 1-2: Setup Inicial (Semanas 1-4) ✅ COMPLETADO
- [x] **Configuración del Proyecto**
  - [x] Crear proyecto Django
  - [x] Setup Django 5 con Python 3.12
  - [x] Configurar Bootstrap 5
  - [x] Configurar Django ORM con PostgreSQL
  - [x] Configurar Django REST Framework
  - [ ] Setup CI/CD con GitHub Actions

- [x] **Infraestructura Multi-Tenant**
  - [x] Implementar tenant resolution middleware
  - [x] Crear sistema de provisioning de schemas
  - [x] Funciones helper para contexto de tenant
  - [x] Aislamiento de datos por tenant

**Entregable**: Proyecto base con multi-tenancy funcional ✅

#### Sprint 3-4: Autenticación (Semanas 5-8) ✅ COMPLETADO
- [x] **django-allauth Setup**
  - [x] Configurar providers (Email)
  - [x] Configurar Django Auth con django-allauth
  - [x] Implementar sistema de roles (RBAC)
  - [x] Páginas de login/register/forgot-password (custom templates)

- [x] **Onboarding de Iglesias**
  - [x] Wizard multi-paso (4 steps)
    - [x] Paso 1: Datos de iglesia
    - [x] Paso 2: Creación de admin
    - [x] Paso 3: Configuración básica
    - [ ] Paso 4: Welcome screen
  - [ ] API endpoint para crear tenant
  - [ ] Seedear datos default (roles, cuentas contables)
  - [ ] Email de bienvenida

**Entregable**: Sistema de autenticación y onboarding completo ✅

#### Sprint 5-7: Gestión de Membresía (Semanas 9-14) ✅ COMPLETADO
- [x] **CRUD de Miembros**
  - [x] Model Django para Members, Families, Tags
  - [x] Formulario create/edit con Django Forms
  - [x] Vista de lista con filtros y búsqueda
    - [x] Filtros (status, tags, familia)
    - [x] Búsqueda
    - [x] Paginación
  - [x] Perfil detallado de miembro
  - [x] Sistema de familias (crear, editar, miembros)
  - [x] Sistema de tags/etiquetas

- [ ] **Funciones Adicionales**
  - [ ] Upload de foto de perfil (Django Media + AWS S3/Storages)
  - [ ] Importación CSV
  - [ ] Exportación a CSV/Excel
  - [ ] Directorio público de miembros (con privacidad)

**Entregable**: Módulo de membresía funcional ✅

#### Sprint 8-10: Donaciones y Finanzas Básicas (Semanas 15-20) ✅ COMPLETADO
- [x] **Integración Stripe**
  - [ ] Setup Stripe Connect (platform model) - Pendiente
  - [ ] Crear connected account en onboarding - Pendiente
  - [x] Página pública de donaciones
    - [x] Stripe Checkout integration
    - [x] Formulario de donación única
    - [x] Opción "cover fees"
  - [x] Webhook handler `/api/webhooks/stripe`
    - [x] `checkout.session.completed`
    - [x] Crear donation record
  - [ ] Enviar recibo por email - Pendiente
  - [x] Tests con Stripe test mode

- [x] **Contabilidad Básica**
  - [x] Dashboard financiero
    - [x] Card: Ingresos del mes
    - [x] Card: Gastos del mes
    - [x] Card: Balance del mes
    - [x] Card: Donantes activos
    - [x] Gráfico: Ingresos vs Gastos (12 meses)
    - [x] Lista: Transacciones recientes
  - [x] Formulario de registro de gastos
    - [x] Categorización
    - [x] Upload de recibo (PDF/imagen)

- [x] **Reportes Iniciales**
  - [x] Lista de donaciones (filtros por fecha, miembro, estado, campaña)
  - [x] Reporte Estado de Resultados (Income Statement)
  - [x] Reporte Donaciones por Miembro

**Entregable**: Sistema de donaciones y contabilidad funcional ✅

#### Sprint 11-12: Sistema de Notificaciones (Semanas 21-24) ✅ COMPLETADO
- [x] **Email Infrastructure**
  - [x] Configurar Resend API
  - [x] Configurar templates de email con Django
  - [x] Celery queue para emails
  - [x] Worker para procesar email queue
  - [x] Templates:
    - [x] Welcome email (nuevo miembro)
    - [x] Donation receipt
    - [x] Password reset
  - [x] Logging de emails enviados (email_logs)

- [x] **Notificaciones In-App**
  - [x] Schema para notifications
  - [x] API para crear/marcar leído
  - [x] Componente UI de notificaciones (bell icon)
  - [ ] Realtime updates (polling o WebSocket básico) - Pendiente

**Entregable**: Sistema de notificaciones por email ✅

#### Sprint 13: Deploy y Testing (Semanas 25-26) ✅ COMPLETADO

**Estado**: Tests completados, pending deployment a producción

- [x] **Infraestructura de Tests**
  - [x] pytest + pytest-django configurado
  - [x] Fixtures para members, tenants, users
  - [x] Playwright instalado para E2E

- [x] **API Integration Tests**
  - [x] Members API: 13 tests passed
  - [x] Finance API: 12 tests passed, 1 skipped
  - [x] Tags API: 2 tests passed (nuevo)

- [x] **E2E Tests** (preparados)
  - [x] Onboarding flow tests
  - [x] Members CRUD tests
  - [x] Donations tests

- [ ] **Deployment a Producción** (PENDIENTE)
  - [ ] Deploy app a Railway/Render/Dokploy
  - [ ] Setup PostgreSQL (Railway/Render/Supabase)
  - [ ] Setup Redis (Railway/Upstash)
  - [ ] Configurar variables de entorno
  - [ ] Setup dominio personalizado
  - [ ] SSL certificates

**Nota**: Tests listos, requiere deployment para ejecución completa

- [ ] **Documentación**
  - [ ] User guide: Onboarding
  - [ ] User guide: Gestión de miembros
  - [ ] User guide: Donaciones

**Entregable**: 🚀 **MVP en Producción**

### Métricas de Éxito (Fase 1)
- [ ] 5-10 iglesias piloto usando la plataforma
- [ ] 500+ miembros totales registrados
- [ ] $10,000+ en donaciones procesadas
- [ ] < 2s tiempo de carga (P95)
- [ ] Zero data leaks entre tenants (audit)
- [ ] 95%+ uptime

---

## Fase 2: Core Features
**Duración**: 3-4 meses | **Q2-Q3 2026** | ⚪ **Planificado**

### Objetivos
Expandir funcionalidades para cubrir las necesidades operativas diarias de una iglesia típica.

### Hitos y Entregables

#### Sprint 14-15: Registros Sacramentales (Semanas 27-30)
- [ ] **Bautizos**
  - [ ] Schema: baptisms, sacraments
  - [ ] CRUD de bautizos
  - [ ] Formulario: fecha, oficiante, testigos, ubicación
  - [ ] Upload de múltiples fotos (galería)
  - [ ] Generación de certificado PDF
    - [ ] Template customizable (logo, firma)
    - [ ] Mail merge con datos
    - [ ] Download o email directo
  - [ ] Vista de historial de bautizos
  - [ ] Búsqueda por fecha/miembro

- [ ] **Otros Sacramentos**
  - [ ] Tabla genérica `sacraments`
  - [ ] Tipos: confirmación, matrimonio, comunión
  - [ ] CRUD básico
  - [ ] Certificados PDF

**Entregable**: Módulo sacramental completo

#### Sprint 16-18: Donaciones Recurrentes (Semanas 31-36)
- [ ] **Stripe Subscriptions**
  - [ ] UI para configurar donación recurrente
    - [ ] Frecuencia: mensual, trimestral, anual
    - [ ] Método de pago guardado
  - [ ] Crear Stripe Subscription
  - [ ] Webhook handlers
    - [ ] `customer.subscription.created`
    - [ ] `invoice.paid` (crear donation por cada pago)
    - [ ] `invoice.payment_failed` (notificar donante)
    - [ ] `customer.subscription.deleted`
  - [ ] Portal de donante
    - [ ] Ver suscripciones activas
    - [ ] Actualizar método de pago (Stripe Customer Portal)
    - [ ] Cancelar suscripción
    - [ ] Ver historial completo

- [ ] **Gestión de Donantes**
  - [ ] Dashboard de donantes
    - [ ] Total given (lifetime, year, month)
    - [ ] Último donation
    - [ ] Estado de suscripciones
  - [ ] Segmentación de donantes
    - [ ] One-time only
    - [ ] Recurring active
    - [ ] Lapsed (cancelled subscription)
  - [ ] Métricas de retención

**Entregable**: Sistema de donaciones recurrentes

#### Sprint 19-21: Sistema LMS (Semanas 37-42)
- [ ] **Cursos**
  - [ ] Schema: courses, lessons, quizzes
  - [ ] CRUD de cursos (solo instructores)
  - [ ] Editor de lecciones
    - [ ] Rich text con Tiptap
    - [ ] Embed de video (YouTube/Vimeo)
    - [ ] Upload de archivos (PDFs, slides)
  - [ ] Publicar/despublicar cursos

- [ ] **Quizzes**
  - [ ] Editor de quizzes (JSON schema)
  - [ ] Tipos de preguntas: multiple choice, true/false
  - [ ] Auto-grading
  - [ ] Passing score configurable
  - [ ] Límite de tiempo (opcional)

- [ ] **Estudiantes**
  - [ ] Vista de catálogo de cursos
  - [ ] Inscripción a curso
  - [ ] Ver lecciones secuencialmente
  - [ ] Marcar lección como completada
  - [ ] Tomar quizzes
  - [ ] Ver progreso (% completado)
  - [ ] Certificado al completar (PDF)

- [ ] **Instructor Dashboard**
  - [ ] Ver estudiantes inscritos
  - [ ] Analytics: completion rate, quiz scores
  - [ ] Exportar lista de estudiantes

**Entregable**: Sistema LMS funcional

#### Sprint 22-24: Reportes Financieros Avanzados (Semanas 43-48)
- [ ] **Reportes Contables**
  - [ ] Estado de Resultados (P&L)
    - [ ] Por período (mensual, trimestral, anual)
    - [ ] Por departamento (si clasificado)
    - [ ] Comparación año anterior
    - [ ] Export a PDF/Excel
  - [ ] Balance Sheet
  - [ ] Budget vs Actual
    - [ ] UI para crear presupuesto anual
    - [ ] Reporte de varianza

- [ ] **Reportes de Donaciones**
  - [ ] Por miembro (individual giving statement)
  - [ ] Por campaña
  - [ ] Por método de pago
  - [ ] Análisis de retención
    - [ ] New donors this month
    - [ ] Recurring vs one-time
    - [ ] Churn rate

- [ ] **Annual Giving Statements (Tax Receipts)**
  - [ ] Job automático (ejecuta en enero)
  - [ ] Generar PDF por cada donante
  - [ ] Bulk email con adjuntos
  - [ ] IRS compliance (disclaimers requeridos)
  - [ ] Portal self-service para re-descargar

**Entregable**: Reportes financieros completos

#### Sprint 25-26: Asistencia y Check-in (Semanas 49-52)
- [ ] **Check-in Manual**
  - [ ] Lista de miembros con checkboxes
  - [ ] Por servicio/evento
  - [ ] Registro de timestamp

- [ ] **Check-in con QR Codes**
  - [ ] Generar QR único por miembro
  - [ ] QR en email o printable card
  - [ ] App de scanner (camera API)
  - [ ] Modo kiosk para tablet en entrada

- [ ] **Reportes de Asistencia**
  - [ ] Tendencias por servicio
  - [ ] Asistencia por miembro (historial)
  - [ ] Identificar inactivos (X meses sin asistencia)
  - [ ] Export a CSV

**Entregable**: Sistema de check-in completo

#### Sprint 27: Portal de Miembros (Semanas 53-54)
- [ ] **Self-Service**
  - [ ] Página "My Profile"
  - [ ] Editar información personal
  - [ ] Actualizar foto
  - [ ] Ver historial de donaciones
  - [ ] Ver cursos inscritos y progreso
  - [ ] Change password

- [ ] **Directorio de Miembros**
  - [ ] Vista pública (solo miembros opt-in)
  - [ ] Búsqueda y filtros
  - [ ] Contact info (email, teléfono con protección)
  - [ ] Privacy controls (qué campos mostrar)

**Entregable**: Portal self-service para miembros

#### Sprint 28: SMS Notifications (Semanas 55-56)
- [ ] **Integración Twilio**
  - [ ] Setup account y API keys
  - [ ] Celery queue para SMS
  - [ ] Worker para enviar SMS
  - [ ] Logging (sms_logs)

- [ ] **Use Cases**
  - [ ] Recordatorio de evento (24h antes)
  - [ ] Mensajes urgentes (emergencias, cancellations)
  - [ ] Birthday wishes (opcional)

- [ ] **Preferencias de Usuario**
  - [ ] Opt-in/opt-out de SMS
  - [ ] Configurar número de teléfono móvil
  - [ ] STOP command handling (compliance)

**Entregable**: Sistema de SMS

### Métricas de Éxito (Fase 2)
- [ ] 50+ iglesias usando la plataforma
- [ ] 5,000+ miembros totales
- [ ] $100,000+ en donaciones procesadas
- [ ] 100+ cursos creados
- [ ] 1,000+ certificados emitidos
- [ ] 90%+ satisfacción de usuarios (survey)

---

## Fase 3: Funciones Avanzadas
**Duración**: 3-4 meses | **Q3-Q4 2026** | ⚪ **Planificado**

### Objetivos
Funciones que diferencian la plataforma y mejoran engagement.

### Hitos y Entregables

#### Sprint 29-30: Learning Paths (Semanas 57-60)
- [ ] **Rutas de Aprendizaje**
  - [ ] Schema: learning_paths, learning_path_courses
  - [ ] CRUD de learning paths
  - [ ] UI para agregar cursos a path
  - [ ] Definir orden y prerrequisitos
  - [ ] Vista de path para estudiantes
  - [ ] Tracking de progreso global del path
  - [ ] Certificado de completitud del path completo

**Entregable**: Sistema de learning paths

#### Sprint 31-32: Calendario y Eventos (Semanas 61-64)
- [ ] **Gestión de Eventos**
  - [ ] CRUD de eventos
  - [ ] Tipos: servicio, reunión, social, clase
  - [ ] Fecha/hora, ubicación
  - [ ] Eventos recurrentes (RRULE)
  - [ ] Registro a eventos (optional)
    - [ ] Límite de participantes
    - [ ] Deadline de registro

- [ ] **Integraciones**
  - [ ] Export iCal feed (subscribe en Google Calendar)
  - [ ] Sync bidireccional con Google Calendar (Phase 4)

- [ ] **Recordatorios**
  - [ ] Email 24h antes del evento
  - [ ] SMS para urgentes

**Entregable**: Módulo de eventos completo

#### Sprint 33-34: Grupos Pequeños (Semanas 65-68)
- [ ] **Small Groups**
  - [ ] Schema: groups, group_members, group_meetings
  - [ ] CRUD de grupos
  - [ ] Asignar líder y miembros
  - [ ] Programar reuniones
  - [ ] Asistencia a reuniones
  - [ ] Tablero de anuncios (posts simples)
  - [ ] Comentarios en posts

**Entregable**: Módulo de grupos pequeños

#### Sprint 35-37: Progressive Web App (Semanas 69-74)
- [ ] **PWA Setup**
  - [ ] Progressive Web App (PWA) con manifest
  - [ ] Manifest.json (nombre, iconos, colores)
  - [ ] Service worker para offline
    - [ ] Caché de páginas críticas
    - [ ] Caché de datos esenciales
    - [ ] Sync cuando regresa conexión

- [ ] **Push Notifications**
  - [ ] Web Push API integration
  - [ ] Backend para enviar push notifications
  - [ ] Subscription management
  - [ ] Use cases: nuevos mensajes, recordatorios

- [ ] **Mobile Optimizations**
  - [ ] Touch-friendly UI
  - [ ] Offline mode para ver datos
  - [ ] Install prompt ("Add to Home Screen")

**Entregable**: PWA funcional

#### Sprint 38-40: Workflows Automatizados (Semanas 75-80)
- [ ] **Workflow Engine**
  - [ ] Schema: workflows, workflow_steps
  - [ ] Triggers:
    - [ ] Nuevo miembro
    - [ ] Nueva donación
    - [ ] Cumpleaños
    - [ ] Aniversario de membresía
    - [ ] Inactividad (X días sin asistencia)
  - [ ] Actions:
    - [ ] Enviar email
    - [ ] Enviar SMS
    - [ ] Crear tarea para staff
    - [ ] Agregar tag al miembro

- [ ] **UI de Configuración**
  - [ ] Low-code builder (drag-drop)
  - [ ] Templates predefinidos
  - [ ] Test mode para workflows

**Entregable**: Sistema de workflows

#### Sprint 41-42: Analytics Avanzado (Semanas 81-84)
- [ ] **Dashboard Ejecutivo**
  - [ ] KPIs principales
    - [ ] Crecimiento de membresía (trend)
    - [ ] Donaciones month-over-month
    - [ ] Asistencia promedio
    - [ ] Engagement en cursos
  - [ ] Gráficos demográficos
    - [ ] Distribución por edad
    - [ ] Mapa geográfico
    - [ ] Género, estado civil
  - [ ] Funnel de conversión
    - [ ] Visitor → Attendee → Member

- [ ] **Reportes Personalizados**
  - [ ] Query builder (filtros avanzados)
  - [ ] Guardar reportes favoritos
  - [ ] Programar envío automático (email)
  - [ ] Export a PDF, Excel, CSV

- [ ] **Integración BI**
  - [ ] PostHog para product analytics
  - [ ] Plausible para web analytics

**Entregable**: Analytics completo

### Métricas de Éxito (Fase 3)
- [ ] 200+ iglesias activas
- [ ] 20,000+ miembros totales
- [ ] 10,000+ usuarios de PWA (installed)
- [ ] 500+ workflows activos
- [ ] 85%+ user retention (30 días)

---

## Fase 4: Escalamiento y Pulido
**Duración**: 2-3 meses | **Q4 2026** | ⚪ **Planificado**

### Objetivos
Optimizar performance, abrir API pública, soportar internacionalización y escalar la infraestructura.

### Hitos y Entregables

#### Sprint 43-44: Performance Optimization (Semanas 85-88)
- [ ] **Database Optimization**
  - [ ] Audit slow queries (pg_stat_statements)
  - [ ] Agregar índices faltantes
  - [ ] Implementar database read replicas
  - [ ] Particionar tablas grandes (audit_logs por mes)

- [ ] **Caching Agresivo**
  - [ ] Redis para queries frecuentes
  - [ ] Cache de configuración de tenant (TTL 1h)
  - [ ] Cache de permisos de usuario
  - [ ] Invalidación inteligente

- [ ] **Frontend Optimization**
  - [ ] Code splitting agresivo
  - [ ] Lazy load de componentes pesados
  - [ ] Image optimization (django-imagekit + CDN)
  - [ ] Prefetch de rutas críticas

- [ ] **Infrastructure**
  - [ ] CDN (Cloudflare) para assets estáticos
  - [ ] Connection pooling (PgBouncer)
  - [ ] Horizontal scaling de workers

**Targets**: 
- < 1s page load (P95)
- < 300ms API response (P95)
- Soportar 1,000 tenants simultáneos

**Entregable**: Performance optimizado

#### Sprint 45-46: API Pública (Semanas 89-92)
- [ ] **REST API**
  - [ ] Documentación OpenAPI/Swagger
  - [ ] API keys system
  - [ ] Rate limiting por tenant
  - [ ] Webhooks salientes
    - [ ] new_member
    - [ ] new_donation
    - [ ] event_created

- [ ] **Developer Portal**
  - [ ] Docs interactivos (Postman/Swagger UI)
  - [ ] API key management
  - [ ] Logs de API calls
  - [ ] Ejemplos en varios lenguajes

**Entregable**: API pública documentada

#### Sprint 47-48: Internacionalización (Semanas 93-96)
- [ ] **i18n Setup**
  - [ ] Configurar next-intl
  - [ ] Extraer strings a archivos JSON
  - [ ] Traducciones:
    - [ ] Español (prioritario)
    - [ ] Inglés (default)
    - [ ] Portugués (Brasil)

- [ ] **Localization**
  - [ ] Formatos de fecha (locale-aware)
  - [ ] Formatos de moneda (Dinero.js)
  - [ ] Números, percentages
  - [ ] RTL support (árabe, hebreo) - futuro

- [ ] **Content**
  - [ ] Templates de email en múltiples idiomas
  - [ ] UI traducida
  - [ ] Docs en español

**Entregable**: Plataforma multi-idioma

#### Sprint 49-50: Mobile Native Apps (Semanas 97-100)
- [ ] **Mobile App** (Flutter)
  - [ ] Setup con Expo
  - [ ] Compartir código con web (packages)
  - [ ] Pantallas principales:
    - [ ] Login
    - [ ] Directory de miembros
    - [ ] Donaciones
    - [ ] Ver cursos
    - [ ] Check-in (QR scanner)
    - [ ] Calendario de eventos

- [ ] **Native Features**
  - [ ] Push notifications (Firebase)
  - [ ] Camera para QR check-in
  - [ ] Offline mode (AsyncStorage)
  - [ ] Biometric auth (Face ID, Fingerprint)

- [ ] **Deploy**
  - [ ] Apple App Store
  - [ ] Google Play Store

**Entregable**: Apps nativas iOS/Android

#### Sprint 51: Security Audit y Compliance (Semanas 101-102)
- [ ] **Security**
  - [ ] Penetration testing (contratar firma)
  - [ ] Dependency scanning (Snyk)
  - [ ] Secrets scanning (GitGuardian)
  - [ ] OWASP Top 10 audit

- [ ] **GDPR Compliance**
  - [ ] Data export (member request)
  - [ ] Right to erasure (soft + hard delete)
  - [ ] Consent tracking
  - [ ] Privacy policy generator
  - [ ] Cookie consent banner

- [ ] **Certifications**
  - [ ] SOC 2 Type 1 (inicio del proceso)
  - [ ] PCI DSS (Stripe ya maneja)

**Entregable**: Security hardened, GDPR compliant

#### Sprint 52: Polish y Launch (Semanas 103-104)
- [ ] **UI/UX Polish**
  - [ ] Accessibility audit (WCAG 2.1 AA)
  - [ ] Keyboard navigation
  - [ ] Screen reader support
  - [ ] Error messages mejorados

- [ ] **Documentation**
  - [ ] Video tutorials para cada módulo
  - [ ] Knowledge base (FAQs)
  - [ ] Admin guides
  - [ ] Changelog público

- [ ] **Marketing Site**
  - [ ] Landing page profesional
  - [ ] Features showcase
  - [ ] Pricing page (free + donations)
  - [ ] Testimonials
  - [ ] Blog (content marketing)
  - [ ] SEO optimization

- [ ] **Launch**
  - [ ] Product Hunt launch
  - [ ] Press release
  - [ ] Social media campaign
  - [ ] Outreach a denominaciones

**Entregable**: 🚀 **Lanzamiento Público v1.0**

### Métricas de Éxito (Fase 4)
- [ ] 500+ iglesias activas
- [ ] 50,000+ miembros totales
- [ ] $1M+ en donaciones procesadas anualmente
- [ ] 99.9% uptime
- [ ] 500+ API consumers
- [ ] 4.8+ rating en app stores

---

## Backlog Futuro (Post-v1.0)

### Funciones Consideradas para Fases Posteriores

#### Engagement y Comunicación
- [ ] **Feed Social Interno**
  - [ ] Posts de la iglesia
  - [ ] Comentarios y reacciones
  - [ ] Grupos de discusión
- [ ] **Live Streaming Integration**
  - [ ] Embed desde YouTube/Vimeo
  - [ ] Chat en vivo durante servicios
- [ ] **Prayer Requests**
  - [ ] Submit prayer requests
  - [ ] Privacy levels (public, leaders only, private)
  - [ ] Prayer tracking

#### Operaciones Avanzadas
- [ ] **Volunteer Management**
  - [ ] Scheduling de voluntarios
  - [ ] Shifts y rotaciones
  - [ ] Tracking de horas
  - [ ] Background checks
- [ ] **Facility Booking**
  - [ ] Calendario de facilities
  - [ ] Reservas de rooms/equipment
  - [ ] Aprobaciones
- [ ] **Inventory Management**
  - [ ] Track equipment
  - [ ] Check-out/check-in
  - [ ] Maintenance tracking

#### Multi-Campus y Avanzado
- [ ] **Multi-Campus Support**
  - [ ] Gestión de múltiples locations
  - [ ] Reportes consolidados
  - [ ] Campus-specific events
- [ ] **White-Label**
  - [ ] Custom domains completos
  - [ ] Branding personalizado
  - [ ] Custom email domains
- [ ] **Advanced Integrations**
  - [ ] Mailchimp sync
  - [ ] QuickBooks integration
  - [ ] Zoom para online meetings
  - [ ] Zapier integration

#### Analytics y BI
- [ ] **Predictive Analytics**
  - [ ] Churn prediction (members likely to leave)
  - [ ] Donation forecasting
  - [ ] Attendance trends ML
- [ ] **Data Warehouse**
  - [ ] Export a BigQuery/Snowflake
  - [ ] Custom BI dashboards (Metabase)

---

## Proceso de Desarrollo

### Metodología
- **Agile/Scrum** con sprints de 2 semanas
- Daily standups (async via Slack/Discord)
- Sprint planning al inicio de cada sprint
- Sprint review/demo al final
- Retrospective para mejora continua

### Definition of Done
Una feature está "Done" cuando:
- [ ] Code implementado y type-safe
- [ ] Tests escritos (unit + integration según aplique)
- [ ] Code review aprobado
- [ ] Documentación actualizada
- [ ] Deploy a staging y QA pasado
- [ ] Merged a main branch

### Release Cycle
- **Main branch**: Siempre deployable
- **Feature branches**: Para cada feature/fix
- **Staging environment**: Testing antes de producción
- **Production deploys**: Viernes (para tener fin de semana para monitorear)
- **Hotfixes**: Deploy immediately si es crítico

### Versionado (Semantic Versioning)
- **v0.x.x**: MVP y desarrollo (Fase 1)
- **v1.0.0**: Lanzamiento público inicial (fin de Fase 4)
- **v1.x.x**: Nuevas features (minor versions)
- **v1.x.y**: Bug fixes (patch versions)

---

## Dependencias y Riesgos

### Dependencias Críticas

| Dependencia | Impacto si Falla | Mitigación |
|-------------|------------------|------------|
| **Stripe API** | No se pueden procesar donaciones | Tener alternativa (PayPal), buffer de cash |
| **PostgreSQL** | Plataforma completa down | Multi-region, backups diarios, replica de lectura |
| **Railway/Render** | App down | Tener deploy alternativo configurado |
| **Redis** | Background jobs fallan | Cola puede usar SQL como fallback |
| **Resend/SendGrid** | Emails no se envían | Tener provider de backup configurado |
| **AWS S3** | Archivos multimedia no disponibles | Cloudflare R2 como alternativa |

### Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Plan de Mitigación |
|--------|--------------|---------|-------------------|
| **Complejidad de Multi-Tenancy** | Media | Alto | POC temprano, tests exhaustivos de aislamiento |
| **Escalabilidad de DB** | Media | Alto | Monitoring desde día 1, plan de sharding documentado |
| **Precisión en Contabilidad** | Baja | Crítico | Code review por contador, tests extensivos, audit by accountant |
| **Data Breach** | Baja | Crítico | Security audit, penetration testing, bug bounty |
| **Donantes no confían en nuevo sistema** | Alta | Alto | Partner con iglesias conocidas, testimonios, certificaciones |
| **Funding insuficiente** | Media | Alto | Buscar grants de fundaciones cristianas, crowdfunding |

---

## Track Record y KPIs

### Métricas a Trackear por Fase

| Métrica | Fase 1 Target | Fase 2 Target | Fase 3 Target | Fase 4 Target |
|---------|--------------|--------------|--------------|--------------|
| Iglesias Activas | 10 | 50 | 200 | 500 |
| Miembros Totales | 500 | 5,000 | 20,000 | 50,000 |
| Donaciones Procesadas | $10K | $100K | $500K | $1M |
| Uptime | 95% | 98% | 99% | 99.9% |
| Page Load (P95) | <2s | <1.5s | <1s | <1s |
| User Satisfaction | N/A | 85% | 90% | 95% |

### Reporting
- **Weekly**: Team sync, metrics dashboard review
- **Monthly**: Board update, financial review
- **Quarterly**: Roadmap adjust, stakeholder update

---

## Recursos Necesarios

### Equipo Estimado

**Fase 1 (MVP)**:
- 1-2 Full-Stack Developers (Django, Python, DRF)
- 1 Designer/UI Dev (part-time)
- 1 Product Manager (25% time)

**Fases 2-3**:
- 2-3 Full-Stack Developers
- 1 Mobile Developer (Flutter)
- 1 Designer
- 1 Product Manager (50% time)
- 1 QA Engineer (part-time)

**Fase 4**:
- Team completo (5-6 devs)
- 1 DevOps Engineer
- 1 Marketing Lead
- 1 Customer Success Manager

### Presupuesto Operacional Mensual

| Item | Costo Estimado |
|------|----------------|
| Hosting (Railway/Render) | $100-500 |
| PostgreSQL | $50-200 |
| Email (Resend) | $50-200 |
| SMS (Twilio) | $100-500 |
| Stripe fees (2.9% + 30¢) | Variable (pass to donors) |
| Monitoring (Sentry, etc.) | $50-100 |
| **Total** | **$350-1,500/mes** |

*Scaling: Con 100 iglesias, esperaríamos ~$2-3K/mes. Sostenible con donaciones voluntarias.*

---

## Conclusión

Este roadmap provee una ruta clara hacia el lanzamiento de SG Church como una plataforma SaaS completa para gestión de iglesias. Con 12-18 meses de desarrollo enfocado, podemos entregar una solución que compita con plataformas comerciales mientras permanecemos 100% gratuitos para las iglesias.

**Próximo paso**: Aprobar Fase 1 y comenzar Sprint 1.

---

**Última actualización**: Febrero 15, 2026
**Versión**: 1.0
**Mantenido por**: Equipo de Producto SG Church
