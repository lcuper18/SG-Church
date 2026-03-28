# Quick Start Guide - SG Church

Esta guía te ayudará a comenzar con el desarrollo de SG Church en minutos.

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
git clone https://github.com/your-org/sg-church.git
cd sg-church
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
uv pip install -r requirements.txt

# O con pip
pip install -r requirements.txt
```

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
DEBUG=True
SECRET_KEY=tu-secret-key-aqui-muy-larga
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sgchurch

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (desarrollo - usa console backend)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Stripe (test mode)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 5. Configurar Base de Datos

```bash
# Crear la base de datos
createdb sgchurch

# Ejecutar migraciones
python manage.py migrate

# (Opcional) Crear superusuario
python manage.py createsuperuser

# (Opcional) Poblar con datos de prueba
python manage.py loaddata fixtures/sample_data.json
```

### 6. Iniciar Servidor de Desarrollo

```bash
# Servidor Django
python manage.py runserver

# En otra terminal: Iniciar Celery (para tareas async)
celery -A sg_chorld worker -l info
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
python manage.py create_tenant <name> <subdomain>  # Crear tenant
python manage.py list_tenants                       # Listar tenants
python manage.py generate_fixtures                   # Generar datos de prueba
```

---

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
├── sg_church/              # Proyecto Django
│   ├── settings/          # Configuración
│   ├── core/              # App core
│   ├── tenants/           # Multi-tenancy
│   ├── members/           # Gestión de miembros
│   ├── finance/           # Finanzas
│   ├── education/         # LMS
│   └── api/               # API REST
│
├── templates/              # Templates HTML
├── static/                # CSS, JS, imágenes
├── requirements.txt        # Dependencias Python
├── manage.py              # CLI de Django
└── pytest.ini             # Configuración de tests
```

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

## 🎯 Próximos Pasos en el Desarrollo

Una vez aprobada la planificación, se implementará:

1. **Setup del Proyecto**
   - Crear proyecto Django
   - Configurar apps (members, finance, education)
   - Setup de Django REST Framework

2. **Configuración Inicial**
   - Modelado de datos (Tenant, Member, Family, etc.)
   - Sistema de autenticación
   - Admin Django

3. **Primera Funcionalidad (Sprint 1)**
   - Registro de iglesias (tenants)
   - Gestión básica de miembros
   - Dashboard

---

## 🤝 Obtener Ayuda

Si tienes problemas:

1. **Revisa la [FAQ](./docs/FAQ.md)** - Respuestas a preguntas comunes
2. **Busca en [Issues](https://github.com/your-org/sg-church/issues)** - Problemas conocidos
3. **Pregunta en [Discussions](https://github.com/your-org/sg-church/discussions)** - Foro
4. **Email**: support@sgchurch.app

---

## 📝 Estado Actual

> ⚠️ **IMPORTANTE**: Este proyecto está actualmente en **fase de planificación**.
>
> Se ha actualizado el stack tecnológico de Next.js a Django + DRF.
> El código se implementará una vez que se apruebe la planificación.

**Documentos completados:**
- ✅ Stack tecnológico (Django + DRF)
- ✅ Arquitectura definida
- ✅ Esquema de base de datos diseñado
- ✅ Guías de contribución y seguridad
- ✅ Templates de GitHub

**Próximo paso**: Iniciar implementación del código

---

**¿Listo para contribuir?** Lee [CONTRIBUTING.md](./CONTRIBUTING.md) para empezar.

**¿Tienes preguntas?** Consulta la [FAQ](./docs/FAQ.md) o abre una [Discussion](https://github.com/your-org/sg-church/discussions).
