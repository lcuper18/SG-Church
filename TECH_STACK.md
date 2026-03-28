# Stack Tecnológico - SG Church

Documentación completa de todas las tecnologías, herramientas y servicios utilizados en el proyecto.

## Tabla de Contenidos

- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Backend](#backend)
- [Frontend](#frontend)
- [Base de Datos](#base-de-datos)
- [API REST](#api-rest)
- [Autenticación y Autorización](#autenticación-y-autorización)
- [Pagos y Procesamiento](#pagos-y-procesamiento)
- [Almacenamiento y Archivos](#almacenamiento-y-archivos)
- [Email y Comunicaciones](#email-y-comunicaciones)
- [Tareas en Segundo Plano](#tareas-en-segundo-plano)
- [Infraestructura y Hosting](#infraestructura-y-hosting)
- [Monitoreo y Analytics](#monitoreo-y-analytics)
- [Herramientas de Desarrollo](#herramientas-de-desarrollo)
- [Versiones y Compatibilidad](#versiones-y-compatibilidad)

---

## Resumen Ejecutivo

### Decisión Clave: Python Django + REST API

**Ventajas**:
- ✅ Framework maduro y estable (18+ años)
- ✅ ORM potente con migrate automático
- ✅ Admin panel incluido
- ✅ Django REST Framework (estándar profesional)
- ✅ Seguridad robusta built-in
- ✅ Perfecto para APIs REST
- ✅ Gran comunidad y documentación

### Stack Principal

```
┌──────────────────────────────────────┐
│         FRONTEND                     │
│  HTML5 + CSS3 + JavaScript (ES6+)   │
│  Bootstrap 5 + Vanilla JS            │
└──────────────┬───────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│         BACKEND                      │
│  Python 3.x + Django 5.x             │
│  Django REST Framework               │
└──────────────┬───────────────────────┘
                │
         ┌──────┴──────┬───────────┐
         │             │           │
 ┌───────▼─────┐ ┌────▼────┐ ┌────▼────┐
 │ PostgreSQL  │ │  Redis  │ │  S3/    │
 │ + Django    │ │ + Celery│ │   AWS   │
 │    ORM      │ │         │ │         │
 └─────────────┘ └─────────┘ └─────────┘
```

---

## Backend

### Framework Principal

#### **Django 5.x**
![Django](https://img.shields.io/badge/Django-5.x-092E20)

**Versión**: 5.0+

**Por qué Django**:
- ✅ **ORM incluido**: Modelos, migraciones, queries
- ✅ **Admin panel**: Panel de administración automático
- ✅ **Seguridad**: Protección CSRF, XSS, SQL injection built-in
- ✅ **Forms**: Sistema de formularios robusto
- ✅ **Auth**: Sistema de autenticación completo
- ✅ **Middleware**: Arquitectura extensible
- ✅ **Internationalization**: i18n integrado

**Configuración básica**:
```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'members',
    'finance',
    'education',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**Alternativas consideradas**:
- ❌ Flask: Muy minimal, requiere más setup
- ❌ FastAPI: Más moderno pero menos maduro para proyectos grandes
- ❌ Pyramid: Comunidad más pequeña

---

### Runtime

#### **Python 3.12+**
![Python](https://img.shields.io/badge/Python-3.12+-3776AB)

**Versión**: 3.12+ LTS

**Por qué Python 3.12**:
- ✅ Performance improvements
- ✅ Better error messages
- ✅ Mayor velocidad que versiones anteriores
- ✅ Soporte hasta 2028

---

## Frontend

### Tecnologías

#### **HTML5**
- Semántico (header, nav, main, footer)
- Accesibilidad (ARIA labels)
- SEO-friendly

#### **CSS3**
- **Bootstrap 5**: Framework CSS responsive
- Custom properties (variables CSS)
- Flexbox y Grid layout
- Animaciones CSS

#### **JavaScript (ES6+)**
- Vanilla JavaScript (sin framework)
- Fetch API para llamadas AJAX
- Webpack/Vite para bundling
- ES Modules

**Estructura de templates**:
```html
<!-- templates/base.html -->
{% load static %}
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}SG Church{% endblock %}</title>
    <link href="{% static 'css/bootstrap.min.css' %}" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% include 'partials/navbar.html' %}
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <script src="{% static 'js/bootstrap.bundle.min.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**Alternativas consideradas**:
- ❌ React/Vue: Overkill para este proyecto
- ❌ Tailwind: Bootstrap es más rápido de aprender para el equipo

---

## Base de Datos

### Database

#### **PostgreSQL 16+**
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791)

**Versión**: 16.1+

**Por qué PostgreSQL**:
- ✅ **Multi-schema support**: Perfecto para multi-tenancy
- ✅ **JSONB**: Flexible storage para configuraciones
- ✅ **Full-text search**: Built-in
- ✅ **Row-level security**: Seguridad adicional
- ✅ **Transacciones ACID**: Crítico para finanzas
- ✅ **Extensible**: PostGIS, pg_cron, etc.
- ✅ **Open source y gratis**

**Extensiones usadas**:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

---

### ORM

#### **Django ORM**

**Por qué Django ORM**:
- ✅ **Integración nativa**: Sin librerías externas
- ✅ **Migrations**: Versionadas y aplicables automáticamente
- ✅ **Query Builder**: API fluida para queries complejas
- ✅ **Relaciones**: Fácil trabajo con FK, M2M
- ✅ **Admin**: Panel de admin automático

**Modelo ejemplo**:
```python
# models.py
from django.db import models
from django.contrib.auth.models import User

class Member(models.Model):
    STATUS_CHOICES = [
        ('visitor', 'Visitante'),
        ('attendee', 'Asistente'),
        ('member', 'Miembro'),
        ('inactive', 'Inactivo'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    member_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='visitor')
    photo = models.ImageField(upload_to='members/photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['email']),
            models.Index(fields=['member_status']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
```

**Alternativas**:
- ❌ SQLAlchemy: Más flexible pero más complejo
- ❌ Peewee: Muy minimal
- ❌ Prisma: Solo para Node.js

---

## API REST

### Django REST Framework (DRF)
![DRF](https://img.shields.io/badge/Django_REST_Framework-3.14+-092E20)

**Versión**: 3.14+

**Por qué DRF**:
- ✅ **Estándar de la industria**: Más usado en Python
- ✅ **Serializers**: Conversión JSON automática
- ✅ **ViewSets**: CRUD rápido
- ✅ **Authentication**: Token, Session, JWT
- ✅ **Permissions**: Control de acceso granular
- ✅ **Throttling**: Rate limiting
- ✅ **Documentation**: Auto-generated Swagger

**Serializer ejemplo**:
```python
# serializers.py
from rest_framework import serializers
from .models import Member

class MemberSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Member
        fields = ['id', 'first_name', 'last_name', 'full_name', 
                  'email', 'phone', 'date_of_birth', 'member_status', 
                  'created_at']
        read_only_fields = ['id', 'created_at']
```

**ViewSet ejemplo**:
```python
# views.py
from rest_framework import viewsets, permissions
from .models import Member
from .serializers import MemberSerializer

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Member.objects.filter(
            tenant=self.request.user.tenant
        )
```

**URLs con router**:
```python
# urls.py
from rest_framework import routers
from .views import MemberViewSet

router = routers.DefaultRouter()
router.register(r'members', MemberViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

**API disponible**:
- `GET /api/members/` - Listar miembros
- `POST /api/members/` - Crear miembro
- `GET /api/members/{id}/` - Ver miembro
- `PUT /api/members/{id}/` - Actualizar miembro
- `DELETE /api/members/{id}/` - Eliminar miembro

---

## Autenticación y Autorización

### Django Authentication

#### **Django Auth + django-allauth**
![Django](https://img.shields.io/badge/Django_Auth-Built--in-092E20)

**Por qué**:
- ✅ Integrado en Django
- ✅ Manejo de usuarios, grupos, permisos
- ✅ Password management incluido
- ✅ django-allauth para OAuth (Google, etc.)

**Configuración**:
```python
# settings.py
AUTH_USER_MODEL = 'members.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# django-allauth
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_SECRET'),
            'key': ''
        }
    }
}
```

### Permissions (DRF)

```python
# permissions.py
from rest_framework import permissions

class IsChurchAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'CHURCH_ADMIN'

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_staff
```

---

## Pagos y Procesamiento

### Payment Processor

#### **Stripe**
![Stripe](https://img.shields.io/badge/Stripe-Latest-008CDD)

**Por qué Stripe**:
- ✅ **Best-in-class API**: Excelente documentación
- ✅ **Stripe Connect**: Perfecto para plataformas multi-tenant
- ✅ **Subscriptions**: Para donaciones recurrentes
- ✅ **Compliance**: PCI DSS handled
- ✅ **Webhooks**: Eventos en tiempo real

**Librería**:
```
stripe>=7.0.0
```

**Backend**:
```python
# payments/views.py
import stripe
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def create_checkout_session(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'Donación'},
                'unit_amount': int(request.data['amount'] * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.data['success_url'],
        cancel_url=request.data['cancel_url'],
        metadata={'tenant_id': request.user.tenant.id}
    )
    return Response({'session_id': session.id})
```

**Webhooks**:
```python
# payments/webhooks.py
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import stripe

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    if event['type'] == 'checkout.session.completed':
        # Procesar donación
        handle_donation(event['data']['object'])
    
    return HttpResponse(status=200)
```

---

## Almacenamiento y Archivos

### Storage

#### **AWS S3 + django-storages**

**Por qué**:
- ✅ Durable y escalable
- ✅ CDN integrado (CloudFront)
- ✅ Coste eficiente a escala

**Configuración**:
```python
# settings.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_DEFAULT_ACL = 'private'
AWS_S3_SIGNATURE_VERSION = 's3v4'
```

**Modelo con archivo**:
```python
class Document(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

---

## Email y Comunicaciones

### Transactional Email

#### **Django + SendGrid/Resend**

**Por qué**:
- ✅ Integración simple con Django
- ✅ Envío de emails transaccionales
- ✅ Tracking de aperturas y clicks

**Configuración**:
```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'noreply@sgchurch.app'
```

**Enviar email**:
```python
from django.core.mail import send_mail

def send_donation_receipt(donation):
    send_mail(
        subject=f'Recibo de donación - {donation.amount}',
        message=f'Gracias por tu donación de ${donation.amount}',
        from_email='noreply@sgchurch.app',
        recipient_list=[donation.member.email],
        html_message=render_to_string('emails/receipt.html', {'donation': donation})
    )
```

---

## Tareas en Segundo Plano

### Celery + Redis

#### **Celery 5.x**
![Celery](https://img.shields.io/badge/Celery-5.x-003F8B)

**Por qué**:
- ✅ Integración perfecta con Django
- ✅ Scheduling con beat
- ✅ Retry automático
- ✅ Monitoreo con Flower

**Configuración**:
```python
# settings.py
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

**Tarea**:
```python
# tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_donation_email(donation_id):
    from .models import Donation
    donation = Donation.objects.get(id=donation_id)
    send_mail(
        'Recibo de donación',
        f'Gracias por tu donación de ${donation.amount}',
        'noreply@sgchurch.app',
        [donation.member.email]
    )
```

**Llamar tarea**:
```python
from .tasks import send_donation_email

# En views.py
send_donation_email.delay(donation.id)
```

---

## Infraestructura y Hosting

### Application Hosting

#### **Render / Railway / VPS**
![Render](https://img.shields.io/badge/Render-46E3B7)

**Por qué**:
- ✅ Soporte nativo para Django
- ✅ Deploy desde Git
- ✅ SSL automático
- ✅ PostgreSQL incluido

**Alternativas**:
- AWS EC2: Más control, más complejo
- DigitalOcean App Platform: Similar a Render
- VPS (Linode, DigitalOcean Droplet): Máxima flexibilidad

---

### Database Hosting

#### **Railway / Render / Neon**

**Por qué**:
- ✅ PostgreSQL gestionado
- ✅ Backups automáticos
- ✅ Fácil setup
- ✅ Buenos planes gratuitos para desarrollo

---

## Monitoreo y Analytics

### Error Tracking

#### **Sentry**
![Sentry](https://img.shields.io/badge/Sentry-362D59)

**Configuración**:
```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
)
```

### Logging

```python
# logging.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'logs/error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
        },
    },
}
```

---

## Herramientas de Desarrollo

### Python Environment

#### **uv / pipenv / venv**

**Por qué uv**:
- ✅ Mucho más rápido que pip
- ✅ Gestión de dependencias moderna
- ✅ Entornos virtuales livianos

**Alternativas**:
- pipenv: Más lento pero estable
- poetry: Excelente pero diferente paradigma

---

### Testing

#### **pytest + pytest-django**
![pytest](https://img.shields.io/badge/pytest-0A9ED9)

**Configuración**:
```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = sg_church.settings
python_files = tests.py test_*.py *_tests.py

# requirements.txt
pytest>=7.0.0
pytest-django>=4.5.0
pytest-cov>=4.0.0
```

**Test ejemplo**:
```python
# members/tests.py
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_member_list_view(client):
    response = client.get('/members/')
    assert response.status_code == 200
```

---

### CI/CD

#### **GitHub Actions**

```yaml
name: Django CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run tests
        run: pytest
      
      - name: Check code style
        run: flake8 .
```

---

## Versiones y Compatibilidad

### Versiones Mínimas Requeridas

| Herramienta | Versión Mínima | Versión Recomendada |
|-------------|----------------|---------------------|
| Python | 3.11.0 | 3.12+ |
| Django | 5.0 | 5.1+ |
| PostgreSQL | 14.0 | 16.1+ |
| Redis | 6.2 | 7.2+ |
| DRF | 3.14 | 3.15+ |

### Dependencias Principales

```
Django>=5.0,<6.0
djangorestframework>=3.14,<4.0
psycopg2-binary>=2.9,<3.0
celery>=5.3,<6.0
redis>=5.0,<6.0
django-cors-headers>=4.0,<5.0
django-allauth>=0.61,<1.0
django-storages>=1.14,<2.0
boto3>=1.34,<2.0
stripe>=7.0,<8.0
gunicorn>=21.0,<22.0
whitenoise>=6.0,<7.0
```

---

## Costos Estimados (Mensual)

### Fase 1 (10 iglesias, <1,000 miembros totales)
- **VPS/Render**: **$0-20** (Free tier o $15/mes)
- **PostgreSQL**: **$0** (incluido en hosting o $0-15)
- **Redis**: **$0** (Free tier Upstash)
- **Dominio + SSL**: **$10-15**
- **Stripe fees**: Solo pasan a iglesias
- **Total: ~$15-50/mes** ✅

### Fase 2 (50 iglesias, 5,000 miembros)
- **VPS/Render**: **$25-50/mes**
- **PostgreSQL**: **$20-50/mes**
- **Redis**: **$0-10/mes**
- **Dominio + SSL**: **$15**
- **Sentry**: **$0-20/mes**
- **Total: ~$80-145/mes**

### Fase 3 (200 iglesias, 20,000 miembros)
- **VPS/Dedicated**: **$100-200/mes**
- **PostgreSQL (managed)**: **$50-100/mes**
- **Redis**: **$20-50/mes**
- **CDN + Storage**: **$30-50/mes**
- **Total: ~$200-400/mes**

---

## Resumen de Decisiones

| Aspecto | Tecnología | Alternativa Principal | Por Qué Elegimos |
|---------|-----------|----------------------|------------------|
| **Backend** | Django 5 | Flask, FastAPI | ORM, Admin, Seguridad |
| **Frontend** | HTML/CSS/JS | - | Simplicidad, mantenimiento |
| **API** | DRF | Graphene, Ninja | Estándar profesional |
| **Database** | PostgreSQL | MySQL | Multi-schema, JSONB |
| **ORM** | Django ORM | SQLAlchemy | Integrado, Admin built-in |
| **Auth** | Django Auth | JWTonly | Integrado, Admin |
| **Payments** | Stripe | PayPal | Best API, Connect |
| **Email** | SendGrid | SES | Easier setup |
| **Jobs** | Celery | Dramatiq | Integración Django |
| **Hosting** | Render/VPS | AWS | Simplicidad, costo |

---

**Última actualización**: Marzo 27, 2026
**Mantenido por**: Equipo Técnico SG Church
