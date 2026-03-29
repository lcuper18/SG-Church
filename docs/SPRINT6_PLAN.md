# Sprint 6: Deploy y Testing

**Período**: Semana 25-26 (Fase 1: Fundación MVP)  
**Estado**: Por iniciar  
**Revisor QA**: Por asignar

---

## Objetivo

Preparar la aplicación para producción y establecer流程 de testing que garanticen la calidad del código.

---

## Entregables

| # | Módulo | Descripción | Prioridad |
|---|--------|-------------|-----------|
| 1 | Deploy a Producción | Configurar Dokploy/Railway/Render | Alta |
| 2 | Base de Datos | PostgreSQL en producción | Alta |
| 3 | Redis | Configurar para Celery | Alta |
| 4 | Variables de Entorno | Configuración segura | Alta |
| 5 | Dominio y SSL | Dominio personalizado con HTTPS | Media |
| 6 | E2E Tests | Tests críticos con Playwright | Alta |
| 7 | Integration Tests | Tests de APIs | Media |

---

## 1. Deployment a Producción

### Opciones de Hosting

| Proveedor | Ventajas | Desventajas |
|----------|----------|--------------|
| **Dokploy** | Auto-deploy, Docker, gratis | Necesita servidor VPS |
| **Railway** | Fácil setup, pay-per-use | Limitado en tier gratuito |
| **Render** | Buena integración Django | Cold starts |

### Configuración Recomendada: Dokploy

```yaml
# dokploy.yaml o configuración
services:
  - name: sg-church
    build:
      language: python
      version: "3.12"
      buildCommand: pip install -r requirements.txt
      startCommand: gunicorn sg_church.wsgi:application
    environment:
      - DATABASE_URL
      - REDIS_URL
      - SECRET_KEY
    domains:
      - sgchurch.com
    healthCheck:
      path: /health/
      interval: 30
```

### Pre-requisitos del Servidor

```bash
# Instalar dependencias del sistema
sudo apt update
sudo apt install python3.12 python3.12-venv postgresql redis-server nginx

# Instalar Docker (si se usa Dokploy)
curl -fsSL https://get.docker.com | sh
```

### Archivos de Producción Necesarios

```
# gunicorn.config.py (ya existe o crear)
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120

# Procfile (para Railway/Render)
web: gunicorn sg_church.wsgi:application --workers 2 --bind 0.0.0.0:$PORT
worker: celery -A sg_church worker -l info -c 2
beat: celery -A sg_church beat -l info
```

---

## 2. Base de Datos PostgreSQL

### Configuración en Producción

```python
# settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME'),
        'USER': os.environ.get('DATABASE_USER'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD'),
        'HOST': os.environ.get('DATABASE_HOST'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'sslmode': 'require',
        }
    }
}
```

### Migraciones

```bash
# En producción
python manage.py migrate --noinput
python manage.py collectstatic --noinput --optimize
```

### Variables de Entorno Requeridas

```env
# Database
DATABASE_NAME=sgchurch_prod
DATABASE_USER=postgres
DATABASE_PASSWORD=secure_password
DATABASE_HOST=db.example.com
DATABASE_PORT=5432

# Redis
REDIS_URL=redis://redis.example.com:6379/0
CELERY_BROKER_URL=redis://redis.example.com:6379/0
CELERY_RESULT_BACKEND=redis://redis.example.com:6379/0

# Django
SECRET_KEY=super-secure-random-key
DEBUG=False
ALLOWED_HOSTS=sgchurch.com,www.sgchurch.com

# Email
RESEND_API_KEY=re_xxx

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
```

---

## 3. Redis para Celery

### Configuración

```env
# Usar servicio gestionado o instalar local
REDIS_URL=redis://localhost:6379/0
```

### Verificación

```bash
# Test de conexión
redis-cli ping
# Debe responder: PONG

# Test de Celery
celery -A sg_church inspect ping
```

---

## 4. Dominio y SSL

### Configuración con Nginx (si es necesario)

```nginx
# /etc/nginx/sites-available/sgchurch
server {
    server_name sgchurch.com www.sgchurch.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/static/;
    }

    location /media/ {
        alias /var/www/media/;
    }
}
```

### SSL con Let's Encrypt

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d sgchurch.com -d www.sgchurch.com

# Renew automático
sudo certbot renew --dry-run
```

---

## 5. E2E Tests con Playwright

### Instalación

```bash
pip install playwright
playwright install chromium
```

### Configuración

```python
# conftest.py
import pytest
from django.test import LiveServerTestCase
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    page = browser.new_page()
    yield page
    page.close()
```

### Tests Críticos

```python
# tests/e2e/test_onboarding.py
def test_onboarding_flow(page):
    """Test completo del flujo de onboarding."""
    # 1. Ir a página de registro
    page.goto("http://localhost:8000/onboarding/")
    
    # 2. Step 1: Datos de iglesia
    page.fill("#id_church_name", "Iglesia Test")
    page.fill("#id_subdomain", "iglesia-test")
    page.click("button[type=submit]")
    
    # 3. Step 2: Crear admin
    page.fill("#id_email", "admin@test.com")
    page.fill("#id_password1", "testpassword123")
    page.fill("#id_password2", "testpassword123")
    page.click("button[type=submit]")
    
    # 4. Verificar que llegó al dashboard
    assert "Dashboard" in page.title()

# tests/e2e/test_members.py
def test_create_member(page):
    """Test de crear miembro."""
    # Login primero
    page.goto("http://localhost:8000/accounts/login/")
    page.fill("#id_email", "admin@test.com")
    page.fill("#id_password", "testpassword123")
    page.click("button[type=submit]")
    
    # Ir a miembros
    page.click("a[href='/members/']")
    
    # Crear miembro
    page.click("a[href='/members/create/']")
    page.fill("#id_first_name", "Juan")
    page.fill("#id_last_name", "Pérez")
    page.fill("#id_email", "juan@test.com")
    page.click("button[type=submit]")
    
    # Verificar
    assert "Juan Pérez" in page.content()

# tests/e2e/test_donations.py
def test_donation_flow(page):
    """Test del flujo de donación."""
    # Ir a página de donación
    page.goto("http://localhost:8000/donate/?church=testchurch")
    
    # Llenar formulario
    page.fill("#id_amount", "100")
    page.select_option("#id_campaign", "offering")
    page.fill("#id_donor_name", "Test Donor")
    page.fill("#id_donor_email", "donor@test.com")
    
    # Click en donate
    page.click("#donate-btn")
    
    # Should redirect to Stripe (en test mode)
    assert "checkout.stripe.com" in page.url
```

---

## 6. Integration Tests

### Setup

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = sg_church.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = --reuse-db --cov=. --cov-report=html
```

### Tests de APIs

```python
# tests/api/test_members_api.py
import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(db, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client

def test_member_list_api(authenticated_client, member):
    response = authenticated_client.get('/api/v1/members/')
    assert response.status_code == 200
    assert len(response.data['results']) >= 1

def test_member_create_api(authenticated_client):
    data = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'test@example.com',
    }
    response = authenticated_client.post('/api/v1/members/', data)
    assert response.status_code == 201
```

---

## Checklist de Desarrollo

### Pre-requisitos
- [ ] Cuenta en proveedor de hosting (Dokploy/Railway/Render)
- [ ] Dominio registrado
- [ ] Cuenta en Resend API
- [ ] Cuenta en Stripe (live mode)

### Deployment
- [ ] Repository conectado al hosting
- [ ] Dockerfile o build config
- [ ] Variables de entorno configuradas
- [ ] Deploy exitoso

### Base de Datos
- [ ] PostgreSQL configurado
- [ ] Migraciones aplicadas
- [ ] Datos seed opcionales

### Redis/Celery
- [ ] Redis instalado/configurado
- [ ] Celery worker funcionando
- [ ] Tasks se ejecutan correctamente

### SSL
- [ ] HTTPS funcionando
- [ ] Redirect HTTP → HTTPS
- [ ] Certificado auto-renovable

### Testing
- [ ] Playwright instalado
- [ ] E2E tests críticos escritos
- [ ] Tests pasan localmente
- [ ] Integration tests de APIs

### Documentación
- [ ] User guide: Onboarding
- [ ] User guide: Gestión de miembros
- [ ] User guide: Donaciones

---

## Checklist de QA

### Deployment
- [ ] App accessible en producción
- [ ] Páginas cargan correctamente
- [ ] Assets estáticos servidos

### Base de Datos
- [ ] Datos se guardan correctamente
- [ ] Multi-tenancy funciona
- [ ] Aislamiento entre tenants

### Autenticación
- [ ] Login funciona
- [ ] Logout funciona
- [ ] Password reset funciona
- [ ] Acceso a páginas protegidas

### Miembros
- [ ] Crear miembro funciona
- [ ] Editar miembro funciona
- [ ] Lista de miembros carga
- [ ] Búsqueda funciona

### Finanzas
- [ ] Dashboard carga
- [ ] Crear gasto funciona
- [ ] Lista de donaciones carga
- [ ] Gráficos se renderizan

### Donaciones
- [ ] Página de donate accesible
- [ ] Formulario redirecciona a Stripe
- [ ] Webhook actualiza estado

### Notificaciones
- [ ] Bell icon visible
- [ ] Notificaciones se crean
- [ ] Marcar como leído funciona

### SSL
- [ ] HTTPS funciona
- [ ] No hay warnings de seguridad
- [ ] Certificado válido

### E2E Tests
- [ ] Test: Onboarding completo
- [ ] Test: Crear miembro
- [ ] Test: Procesar donación test
- [ ] Test: Login/Logout

---

## Notas Técnicas

### Variables de Entorno de Producción

```bash
# NUNCA commitear valores reales
# Usar .env en local, env vars en producción

# Obligatorias
SECRET_KEY=<generar-con-openssl-rand-base64-32>
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
CELERY_BROKER_URL=redis://:password@host:6379/0

# Email (Resend)
RESEND_API_KEY=re_xxx

# Stripe (SOLO para testing en prod)
STRIPE_SECRET_KEY=sk_test_xxx
```

### Comandos de Deploy

```bash
# Railway
railway init
railway up
railway variables set DATABASE_URL=...

# Render
render-blueprint.yaml

# Dokploy
dokploy deploy

# Manual (VPS)
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl restart celery
```

### Health Check

```python
# health check endpoint ya existe
# GET /health/ debe retornar 200 OK
```

---

## Dependencias

```
# Production
gunicorn>=21.0
psycopg2-binary>=2.9

# Testing
playwright>=1.40
pytest>=7.0
pytest-django>=4.5
pytest-cov>=4.0
pytest-playwright>=0.4

# Monitoring (opcional)
sentry-sdk>=1.40
```

---

## Archivos a Modificar

### Nuevos Archivos
```
tests/
├── conftest.py                 # Pytest fixtures
├── e2e/
│   ├── __init__.py
│   ├── test_onboarding.py
│   ├── test_members.py
│   └── test_donations.py
├── api/
│   ├── __init__.py
│   ├── test_members_api.py
│   └── test_finance_api.py
└── test_settings.py          # Test settings

gunicorn.config.py            # Production config
Procfile                      # For some platforms
```

### Archivos a Modificar
```
pytest.ini                   # Pytest config
.env.example                # Add production vars
docs/
├── USER_ONBOARDING.md      # New
├── USER_MEMBERS.md         # New
└── USER_DONATIONS.md       # New
```

---

## User Guides a Crear

### 1. USER_ONBOARDING.md

```markdown
# Guía de Usuario: Onboarding

## Registrar tu Iglesia

1. Ve a [URL de registro]
2. Ingresa el nombre de tu iglesia
3. Elige un subdominio
4. Crea la cuenta de administrador
5. Completa la configuración básica
6. ¡Listo! Ya puedes usar SG Church

## Configuración Inicial

- Logo de la iglesia
- Información de contacto
- Moneda predeterminada
```

### 2. USER_MEMBERS.md

```markdown
# Guía de Usuario: Gestión de Miembros

## Agregar Miembro

1. Ve a Miembros
2. Click en "Nuevo Miembro"
3. Llena el formulario
4. Guarda

## Editar Miembro

1. Click en el miembro
2. Click en "Editar"
3. Modifica datos
4. Guarda
```

### 3. USER_DONATIONS.md

```markdown
# Guía de Usuario: Donaciones

## Recibir Donaciones

1. Comparte el link de donate: /donate/?church=tusubdominio
2. Los donantes pueden pagar con tarjeta
3. Las donaciones aparecen automáticamente

## Ver Reportes

1. Ve a Finanzas
2. Consulta el dashboard
3. Exporta reportes
```

---

## Métricas de Éxito

- [ ] App deployada y accessible
- [ ] HTTPS funcionando
- [ ] E2E tests pasando
- [ ] 0 errores críticos
- [ ] Documentación completa

---

**Documento creado**: Sprint 6 Plan  
**Última actualización**: Marzo 28, 2026
