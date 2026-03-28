# SG Church - Plataforma SaaS de Gestión Integral para Iglesias

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Django](https://img.shields.io/badge/Django-5.x-092E20)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791)

## 🙏 Visión

SG Church es una plataforma SaaS **gratuita** diseñada para ayudar a iglesias de todos los tamaños a gestionar eficientemente sus operaciones diarias. El proyecto se financia mediante donaciones voluntarias y está comprometido con proveer herramientas de administración de clase mundial para el cuerpo de Cristo.

## ✨ Características Principales

### 📋 Gestión de Membresía
- **Perfiles completos** de miembros con fotos y datos personales
- **Gestión de familias** con relaciones (padres, hijos, cónyuges)
- **Registro de asistencia** a servicios y eventos
- **Importación masiva** desde CSV/Excel
- **Directorio de miembros** con controles de privacidad

### 💰 Gestión Financiera y Donaciones
- **Procesamiento de donaciones** con Stripe (únicas y recurrentes)
- **Contabilidad de doble entrada** con categorización de gastos
- **Reportes financieros** (Estado de Resultados, Balance)
- **Declaraciones anuales de donaciones** para impuestos
- **Dashboard financiero** con visualizaciones

### 🎓 Sistema Educativo (LMS)
- **Creación de cursos** con lecciones multimedia
- **Rutas de aprendizaje** con prerrequisitos
- **Quizzes y evaluaciones** con auto-calificación
- **Certificados de completitud** generados automáticamente
- **Tracking de progreso** por estudiante

### ⛪ Registros Sacramentales
- **Bautizos** con certificados PDF
- **Matrimonios** y confirmaciones
- **Galerías de fotos** de eventos
- **Búsqueda histórica** de registros

### 📊 Reportes y Analytics
- **KPIs de crecimiento** y retención
- **Análisis demográfico** de membresía
- **Reportes de donaciones** por período/campaña
- **Identificación de miembros inactivos**
- **Exportación** a PDF y Excel

### 🔔 Comunicaciones
- **Emails transaccionales** (recibos, bienvenidas)
- **Notificaciones SMS** (recordatorios, urgentes)
- **Recordatorios automáticos** de cumpleaños y aniversarios
- **Mensajería a grupos** (próximamente)

## 🏗️ Arquitectura

### Multi-Tenancy
- **Schema-per-tenant**: Cada iglesia tiene su propio esquema PostgreSQL
- **Aislamiento completo** de datos entre iglesias
- **Subdominios personalizados**: `tunombredeiglesia.sgchurch.app`
- **Escalable** desde 10 hasta 10,000+ miembros por iglesia

### Stack Tecnológico
- **Backend**: Python 3.12 + Django 5.x
- **API**: Django REST Framework (REST APIs)
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla + Bootstrap 5)
- **Base de Datos**: PostgreSQL 16 + Django ORM
- **Autenticación**: Django Auth + django-allauth
- **Pagos**: Stripe Connect
- **Almacenamiento**: AWS S3
- **Email**: SendGrid / Resend
- **Tareas async**: Redis + Celery
- **Hosting**: Render / VPS

Ver [TECH_STACK.md](./TECH_STACK.md) para detalles completos.

## 📁 Estructura del Proyecto

```
SG_Church/
├── sg_church/                  # Proyecto Django
│   ├── settings/              # Configuración
│   ├── core/                  # App core
│   ├── tenants/               # Multi-tenancy
│   ├── members/               # Gestión de miembros
│   ├── finance/               # Finanzas
│   ├── education/             # LMS
│   └── api/                   # API REST
├── templates/                  # Templates HTML
├── static/                    # CSS, JS, imágenes
├── requirements.txt            # Dependencias Python
├── manage.py                  # CLI de Django
└── pytest.ini                 # Tests
```

Ver [ARCHITECTURE.md](./ARCHITECTURE.md) para decisiones arquitectónicas detalladas.

## 🚀 Inicio Rápido

### Prerrequisitos

- **Python** 3.11+ (recomendado: 3.12)
- **PostgreSQL** 14+ (recomendado: 16)
- **Redis** 6+ (para Celery)
- **PostgreSQL** 16+ (o cuenta en Supabase)
- **Redis** 7+ (para queues y cache)
- **Cuenta Stripe** (modo test para desarrollo)

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-org/sg-church.git
cd sg-church

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp apps/web/.env.example apps/web/.env.local
# Editar .env.local con tus credenciales

# Ejecutar migraciones de base de datos
python manage.py migrate

# Sembrar datos de desarrollo (opcional)
python manage.py loaddata fixtures/sample_data.json

# Iniciar servidor de desarrollo
python manage.py runserver
```

La aplicación estará disponible en `http://localhost:3000`

### Variables de Entorno Requeridas

```env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/sgchurch"

# Authentication
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="genera-un-secreto-seguro-aqui"

# Stripe
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_test_..."

# Email
RESEND_API_KEY="re_..."

# Redis
REDIS_URL="redis://localhost:6379"

# Storage (Supabase o S3)
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_ANON_KEY="eyJ..."
```

Ver [DEPLOYMENT.md](./docs/DEPLOYMENT.md) para configuración de producción.

## 📖 Documentación

- **[ROADMAP.md](./ROADMAP.md)** - Fases de desarrollo y timeline
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Decisiones arquitectónicas
- **[DATABASE.md](./DATABASE.md)** - Esquema de base de datos
- **[TECH_STACK.md](./TECH_STACK.md)** - Stack tecnológico detallado
- **[API.md](./docs/API.md)** - Documentación de API
- **[DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Guía de deployment
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Guía para contribuidores
- **[SECURITY.md](./SECURITY.md)** - Políticas de seguridad

## 🗺️ Roadmap

### Fase 1: Fundación (MVP) - Q1-Q2 2026 ✅ En Progreso
- [x] Configuración de monorepo
- [x] Autenticación multi-tenant
- [ ] Gestión de membresía (CRUD completo)
- [ ] Donaciones básicas con Stripe
- [ ] Dashboard financiero
- [ ] Sistema de notificaciones por email

### Fase 2: Core Features - Q2-Q3 2026
- [ ] Registros de bautizos y sacramentos
- [ ] Donaciones recurrentes
- [ ] Sistema LMS básico
- [ ] Reportes financieros avanzados
- [ ] Asistencia y check-in
- [ ] Portal de miembros

### Fase 3: Funciones Avanzadas - Q3-Q4 2026
- [ ] Rutas de aprendizaje
- [ ] Calendario y eventos
- [ ] Grupos pequeños
- [ ] PWA (Progressive Web App)
- [ ] Workflows automatizados
- [ ] Analytics avanzado

### Fase 4: Escalamiento - Q4 2026
- [ ] Optimización de performance
- [ ] API pública
- [ ] Internacionalización (i18n)
- [ ] Mobile apps nativas (Flutter)

Ver [ROADMAP.md](./ROADMAP.md) para detalles completos de cada fase.

## 🧪 Testing

```bash
# Tests unitarios
pytest

# Tests con coverage
pytest --cov=. --cov-report=html

# Tests específicos
pytest -k "test_member"
```

## 🤝 Contribuir

Este es un proyecto **open source** y las contribuciones son bienvenidas. Ver [CONTRIBUTING.md](./CONTRIBUTING.md) para guías de contribución.

### Código de Conducta

Estamos comprometidos con proveer un ambiente acogedor y respetuoso para todos. Por favor lee nuestro [Código de Conducta](./CODE_OF_CONDUCT.md).

## 🔒 Seguridad

La seguridad es crítica para nosotros. Si encuentras una vulnerabilidad, por favor revisa nuestra [Política de Seguridad](./SECURITY.md) para reportarla responsablemente.

### Características de Seguridad
- ✅ Row-Level Security en PostgreSQL
- ✅ Encriptación en tránsito (TLS 1.3)
- ✅ Encriptación en reposo para datos sensibles
- ✅ Auditoría completa de operaciones financieras
- ✅ GDPR compliant (exportación y eliminación de datos)
- ✅ Rate limiting y protección DDoS
- ✅ Penetration testing regular

## 💝 Donaciones

SG Church es **100% gratuito** para todas las iglesias. Si este proyecto ha sido de bendición para tu congregación, considera hacer una donación para mantener el desarrollo y los servidores.

**[Donar ahora →](https://donate.sgchurch.app)**

Las donaciones nos permiten:
- 🖥️ Mantener servidores y infraestructura
- 🚀 Desarrollar nuevas características
- 🐛 Corregir bugs y mejorar estabilidad
- 📚 Crear mejor documentación y tutoriales
- 🌍 Traducir la plataforma a más idiomas

## 📄 Licencia

Este proyecto está licenciado bajo la [Licencia MIT](./LICENSE).

## 🌟 Agradecimientos

- A todas las iglesias que confían en SG Church
- A los contribuidores open source
- A las comunidades de Django, Python, y PostgreSQL
- A Dios por la inspiración y guía para este proyecto

---

**Hecho con ❤️ para el cuerpo de Cristo**

Para preguntas, soporte o feedback: support@sgchurch.app

[Website](https://sgchurch.app) • [Documentación](https://docs.sgchurch.app) • [Blog](https://blog.sgchurch.app) • [Twitter](https://twitter.com/sgchurch)
