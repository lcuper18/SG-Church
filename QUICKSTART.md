# Quick Start Guide - SG Church

Esta guía te ayudará a comenzar con el desarrollo de SG Church en minutos.

## 🐳 La forma más rápida: Docker

Si solo querés levantar la app para una sola iglesia (sin instalar Python,
PostgreSQL ni Redis en tu máquina):

```bash
git clone <url-de-este-repositorio>
cd SG-Church
docker compose -f docker-compose.standalone.yml up -d
```

Eso corre las migraciones, crea una iglesia y un usuario admin, y deja la
app en `http://localhost:8000`. Ver
[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) para personalizar el nombre de
la iglesia/admin o para el modo SaaS multi-iglesia con Postgres.

El resto de esta guía es para quien quiera correr el proyecto directamente
con Python (para desarrollo/contribuir código).

## 📋 Prerequisitos

Antes de comenzar, asegúrate de tener instalado:

- **Python**: 3.11+ (recomendado: 3.12)
- **PostgreSQL**: 14+ (recomendado: 16)
- **Redis**: 6+ (para Celery en desarrollo local)
- **Git**: Para control de versiones
- **uv** o **pip**: Gestor de paquetes Python

### Instalación de Prerequisitos

#### Linux (Ubuntu/Debian)

```bash
# Python 3.12
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-venv python3.12-dev

# PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Redis
sudo apt install redis-server

# Herramientas de desarrollo
sudo apt install build-essential libpq-dev
```

#### macOS

```bash
# Python (vía pyenv - recomendado)
brew install pyenv
pyenv install 3.12.0

# PostgreSQL
brew install postgresql@16
brew services start postgresql@16

# Redis
brew install redis
brew services start redis

# uv (gestor de paquetes moderno)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows

```bash
# Instalar Python desde python.org
# Descargar e instalar PostgreSQL desde postgresql.org
# Instalar Redis desde redis.io o usar WSL
```

---

## 🚀 Inicio Rápido

### 1. Clonar el Repositorio

```bash
git clone <url-de-este-repositorio>
cd SG-Church
```

### 2. Crear Entorno Virtual

```bash
# Con uv (recomendado - más rápido)
uv venv
source .venv/bin/activate  # Linux/Mac
# En Windows: .venv\Scripts\activate

# O con pip
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
```

### 3. Instalar Dependencias

```bash
# Con uv (más rápido)
uv pip install -r requirements-dev.txt

# O con pip
pip install -r requirements-dev.txt
```

(`requirements-dev.txt` incluye `requirements.txt` más pytest, flake8,
black, isort y demás herramientas de desarrollo.)

### 4. Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar con tus valores
nano .env
```

**Variables mínimas requeridas para desarrollo:**

```env
# Django
DJANGO_SETTINGS_MODULE=sg_church.settings.local
SECRET_KEY=tu-secret-key-aqui-muy-larga

# Database (settings.local usa Postgres; no hay valores por defecto
# inseguros, hay que setear estos cuatro sí o sí)
DATABASE_NAME=sgchurch
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=localhost

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (desarrollo - usa console backend)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Stripe (test mode, opcional para desarrollo)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

(`DEBUG` y `ALLOWED_HOSTS` ya los fuerza `settings.local` — no hace falta
setearlos a mano para desarrollo. Ver `.env.example` para la lista
completa.)

### 5. Configurar Base de Datos

```bash
# Crear la base de datos
createdb sgchurch

# Ejecutar migraciones
python manage.py migrate

# Crear tu primera iglesia y su admin
python manage.py create_tenant "Mi Iglesia" miiglesia \
  --admin-email admin@miiglesia.com --admin-password changeme123

# (Opcional) Crear también un superusuario de Django (para /admin/)
python manage.py createsuperuser
```

### 6. Iniciar Servidor de Desarrollo

```bash
# Servidor Django
python manage.py runserver

# En otra terminal: Iniciar Celery (para tareas async)
celery -A sg_church worker -l info
```

La aplicación estará disponible en: http://localhost:8000

Admin Django: http://localhost:8000/admin

---

## 🛠️ Comandos Disponibles

### Desarrollo

```bash
python manage.py runserver              # Iniciar servidor
python manage.py runserver 8080         # Puerto específico
python manage.py shell                  # Shell interactivo
```

### Base de Datos

```bash
python manage.py makemigrations        # Crear migraciones
python manage.py migrate                 # Ejecutar migraciones
python manage.py showmigrations          # Ver estado de migraciones
python manage.py migrate <app> zero     # Revertir migraciones

python manage.py dbshell                # Shell de PostgreSQL
python manage.py dumpdata > backup.json  # Exportar datos
python manage.py loaddata backup.json    # Importar datos
```

### Django Admin

```bash
python manage.py createsuperuser         # Crear superusuario
python manage.py changepassword <user>  # Cambiar contraseña
python manage.py shell                   # Shell de Django
```

### Testing

```bash
pytest                                   # Ejecutar tests
pytest -v                                # Verbose
pytest --cov=.                           # Con coverage
pytest --cov-report=html                 # Reporte HTML
pytest -k "test_member"                  # Tests específicos
```

### Comandos Personalizados

```bash
python manage.py create_tenant <name> <subdomain> [--admin-email E --admin-password P]
python manage.py list_tenants       # Listar iglesias/tenants
python manage.py bootstrap_tenant   # Idempotente: crea la iglesia única
                                     # de una instalación autoinstalable si
                                     # todavía no existe ninguna (usa las
                                     # env vars CHURCH_NAME/CHURCH_SUBDOMAIN/
                                     # ADMIN_EMAIL/ADMIN_PASSWORD)
```

---

## 📁 Estructura del Proyecto

```
SG-Church/
├── sg_church/               # Proyecto Django (settings, urls, wsgi, celery)
│   └── settings/            # base.py, local.py, test.py, standalone.py, production.py
├── core/                    # Utilidades compartidas (validators, mixins, permissions)
├── tenants/                 # Multi-tenancy (Tenant, middleware, comandos create_tenant/list_tenants/bootstrap_tenant)
├── members/                 # Miembros, familias, tags, onboarding, User
│   └── api/                 # API REST de members/families/tags
├── finance/                 # Donaciones, gastos, campañas
│   └── api/                 # API REST de finance
├── notifications/           # Notificaciones in-app
├── emails/                  # Registro/envío de emails transaccionales
├── templates/                # Templates HTML (Bootstrap 5)
├── tests/                   # pytest (api/, e2e/)
├── docs/                    # Documentación detallada (DEPLOYMENT, API, FAQ, GLOSSARY)
├── requirements.txt          # Dependencias de producción
├── requirements-dev.txt      # + herramientas de desarrollo
├── manage.py
└── pytest.ini
```

No hay app `education`/LMS todavía — está en el roadmap, no implementada.

---

## 🐛 Solución de Problemas

### Error de conexión a PostgreSQL

```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql  # Linux
brew services list               # macOS

# Iniciar PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql@16  # macOS

# Crear base de datos
createdb sgchurch
```

### Error con Python

```bash
# Verificar versión de Python
python --version

# Usar pyenv para cambiar versión
pyenv versions
pyenv local 3.12.0
```

### Error con Redis

```bash
# Verificar que Redis esté corriendo
redis-cli ping

# Iniciar Redis
redis-server
```

### Error de migraciones

```bash
# Si hay problemas con migraciones
python manage.py migrate --fake-initial
python manage.py showmigrations
```

---

## 📖 Recursos Útiles

### Documentación Esencial
- [README Principal](./README.md) - Visión general del proyecto
- [Arquitectura](./ARCHITECTURE.md) - Decisiones técnicas
- [Stack Tecnológico](./TECH_STACK.md) - Tecnologías usadas
- [Contributing](./CONTRIBUTING.md) - Cómo contribuir

### Enlaces Externos
- [Documentación Django](https://docs.djangoproject.com)
- [Django REST Framework](https://www.django-rest-framework.org)
- [Documentación PostgreSQL](https://www.postgresql.org/docs/)
- [Bootstrap 5](https://getbootstrap.com/docs/5.3/)

---

## 🤝 Obtener Ayuda

Si tienes problemas:

1. **Revisa la [FAQ](./docs/FAQ.md)** - Respuestas a preguntas comunes
2. **Busca o abrí un Issue** en este repositorio

---

## 📝 Estado Actual

Ver [ROADMAP.md](./ROADMAP.md) para el estado sprint a sprint (qué está
hecho y qué falta) — no lo duplicamos acá para que no se desactualice.

---

**¿Listo para contribuir?** Lee [CONTRIBUTING.md](./CONTRIBUTING.md) para empezar.
