# SG Church - Plataforma SaaS de Gestión Integral para Iglesias

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Django](https://img.shields.io/badge/Django-5.x-092E20)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791)

## 🙏 Visión

SG Church es una plataforma SaaS **gratuita** diseñada para ayudar a iglesias de todos los tamaños a gestionar eficientemente sus operaciones diarias. El proyecto se financia mediante donaciones voluntarias y está comprometido con proveer herramientas de administración de clase mundial para el cuerpo de Cristo.

## ✨ Características

### Disponibles hoy

**📋 Gestión de Membresía**
- Perfiles de miembros con fotos y datos personales
- Gestión de familias (padres, hijos, cónyuges) y etiquetas
- Directorio de miembros
- Onboarding de una iglesia nueva (wizard web o línea de comandos)

**💰 Gestión Financiera y Donaciones**
- Donaciones únicas vía Stripe Checkout, con webhook verificado por firma
- Registro y categorización de gastos, con adjunto de recibo
- Dashboard financiero (ingresos/gastos del mes, gráfico de 12 meses)
- Estado de resultados y reporte de donaciones por miembro

**🔔 Notificaciones**
- Notificaciones in-app
- Emails transaccionales (vía Resend, con registro de auditoría)

**🔐 Control de acceso**
- Roles (admin, tesorero, pastor, voluntario, miembro) aplicados tanto en
  las vistas web como en la API

### En el roadmap (no implementado todavía)

Ver [ROADMAP.md](./ROADMAP.md) para el detalle sprint a sprint. Entre lo
planeado: registros sacramentales (bautizos, matrimonios), donaciones
recurrentes, sistema LMS de cursos, reportes financieros avanzados,
asistencia/check-in, notificaciones SMS, importación/exportación masiva
CSV, y más.

## 🏗️ Arquitectura

### Dos formas de usar SG Church
- **Autoinstalable**: una iglesia, una instalación propia (SQLite, sin
  servicios externos) — pensado para correr en una computadora o un
  servidor chico. Ver `docker-compose.standalone.yml`.
- **SaaS multi-iglesia**: una instalación centralizada que aloja a varias
  iglesias (PostgreSQL + Redis), cada una con sus propios usuarios y datos
  aislados por fila (`tenant_id`) en cada tabla. Ver `docker-compose.yml`.

Ver [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) para instrucciones de ambos
modos.

### Stack Tecnológico
- **Backend**: Python 3.12 + Django 5.x
- **API**: Django REST Framework (REST APIs)
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla + Bootstrap 5)
- **Base de Datos**: PostgreSQL 16 (SaaS) o SQLite (autoinstalable) + Django ORM
- **Autenticación**: Django Auth + django-allauth
- **Pagos**: Stripe
- **Almacenamiento**: Sistema de archivos local, o AWS S3 en producción
- **Email**: SendGrid / Resend
- **Tareas async**: Celery (Redis en modo SaaS, síncrono en modo autoinstalable)
- **Hosting**: Docker (cualquier proveedor), Dokploy, Render, o VPS manual

Ver [TECH_STACK.md](./TECH_STACK.md) para detalles completos.

## 📁 Estructura del Proyecto

```
SG_Church/
├── sg_church/                  # Proyecto Django
│   ├── settings/              # Configuración (base, local, production)
│   └── urls.py                # URLs principales
├── core/                      # App core (home page)
├── tenants/                   # Multi-tenancy (Tenant, TenantDomain)
├── members/                   # Gestión de miembros (User, Member, Family)
│   └── api/                   # API REST (serializers, views, urls)
├── finance/                   # Finanzas (Donation, Expense, Campaign)
│   └── api/                   # API REST
├── templates/                  # Templates HTML (Bootstrap 5)
├── fixtures/                  # Datos de ejemplo
├── requirements.txt            # Dependencias Python
├── manage.py                  # CLI de Django
└── pytest.ini                 # Tests
```

Ver [ARCHITECTURE.md](./ARCHITECTURE.md) para decisiones arquitectónicas detalladas.

## 🚀 Inicio Rápido

### Con Docker (recomendado)

Si tu iglesia solo necesita su propia instalación, sin depender de
PostgreSQL ni Redis:

```bash
git clone <url-de-este-repositorio>
cd SG-Church
docker compose -f docker-compose.standalone.yml up -d
```

Eso levanta la app en `http://localhost:8000` con una iglesia y un usuario
admin ya creados. Ver [QUICKSTART.md](./QUICKSTART.md) y
[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) para el detalle (incluido el modo
SaaS multi-iglesia, con `docker-compose.yml`).

### Sin Docker (entorno de desarrollo)

### Prerrequisitos

- **Python** 3.12+
- **PostgreSQL** 14+ (recomendado: 16) — no hace falta si usás el modo
  autoinstalable con SQLite
- **Redis** 6+ (para Celery) — tampoco hace falta en modo autoinstalable
- **Cuenta Stripe** (modo test para desarrollo)

### Instalación

```bash
# Clonar el repositorio
git clone <url-de-este-repositorio>
cd SG-Church

# Instalar dependencias
pip install -r requirements-dev.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar migraciones de base de datos
python manage.py migrate

# Iniciar servidor de desarrollo
python manage.py runserver
```

La aplicación estará disponible en `http://localhost:8000`. Ver
[QUICKSTART.md](./QUICKSTART.md) para el paso a paso completo, incluida la
creación del primer usuario y la primera iglesia.

Ver [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) para configuración de producción.

## 📖 Documentación

- **[QUICKSTART.md](./QUICKSTART.md)** - Guía paso a paso para arrancar
- **[ROADMAP.md](./ROADMAP.md)** - Fases de desarrollo y timeline
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Decisiones arquitectónicas
- **[DATABASE.md](./DATABASE.md)** - Esquema de base de datos
- **[TECH_STACK.md](./TECH_STACK.md)** - Stack tecnológico detallado
- **[docs/API.md](./docs/API.md)** - Documentación de la API REST
- **[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Guía de deployment
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Guía para contribuidores
- **[SECURITY.md](./SECURITY.md)** - Políticas de seguridad

## 🗺️ Roadmap

El desarrollo avanza por sprints documentados en detalle en
[ROADMAP.md](./ROADMAP.md), agrupados en 4 fases: Fundación (MVP),
Core Features (bautizos, LMS, reportes avanzados), Funciones Avanzadas
(learning paths, PWA, workflows) y Escalamiento (performance, API pública,
i18n). Ese archivo es la fuente de verdad del progreso — evitamos
duplicarlo acá para que no se desactualice.

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
- ✅ Aislamiento de datos por iglesia (`tenant_id`) en cada consulta
- ✅ Control de acceso por rol (admin, tesorero, pastor, voluntario, miembro)
- ✅ Verificación de firma en los webhooks de Stripe
- ✅ Validación de tipo y tamaño en todo archivo subido (fotos, recibos)
- ✅ HTTPS forzado y cookies seguras en el modo de producción
- ✅ Sin credenciales ni claves con valores por defecto inseguros

TLS, encriptación en reposo, cumplimiento GDPR y rate limiting dependen de
cómo despliegues la instancia (proxy/CDN, proveedor de base de datos, etc.)
— no son garantías automáticas de la aplicación en sí.

## 💝 Donaciones

SG Church es **100% gratuito** para todas las iglesias. Si este proyecto ha sido de bendición para tu congregación, considera hacer una donación para mantener el desarrollo y los servidores.

> La página de donaciones todavía no está publicada. Este README se
> actualizará con el enlace real en cuanto exista.

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

Para preguntas, soporte o feedback, abrí un issue en este repositorio. El
sitio web, la documentación pública y las redes sociales del proyecto
todavía no existen — este pie de página se actualizará cuando estén.
