# Arquitectura de SG Church

Este documento describe las decisiones arquitectónicas clave del proyecto SG Church, su justificación y las alternativas consideradas.

## Tabla de Contenidos

- [Visión General](#visión-general)
- [Principios de Diseño](#principios-de-diseño)
- [Arquitectura Multi-Tenant](#arquitectura-multi-tenant)
- [Arquitectura de la Aplicación](#arquitectura-de-la-aplicación)
- [Patrón de Datos](#patrón-de-datos)
- [API REST](#api-rest)
- [Autenticación y Autorización](#autenticación-y-autorización)
- [Procesamiento de Pagos](#procesamiento-de-pagos)
- [Sistema de Notificaciones](#sistema-de-notificaciones)
- [Tareas en Segundo Plano](#tareas-en-segundo-plano)
- [Almacenamiento de Archivos](#almacenamiento-de-archivos)
- [Caching Strategy](#caching-strategy)
- [Escalabilidad](#escalabilidad)

---

## Visión General

SG Church es una plataforma SaaS multi-tenant diseñada para escalar desde pequeñas iglesias (10-50 miembros) hasta mega-iglesias (10,000+ miembros). La arquitectura prioriza:

1. **Aislamiento de datos** entre tenants (iglesias)
2. **Simplicidad** en mantenimiento y desarrollo
3. **API-first** para permitir integraciones futuras
4. **Cost efficiency** para mantener el servicio gratuito
5. **Escalabilidad** horizontal cuando sea necesario

### Diagrama de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                     USUARIO (Browser)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   DJANGO APP (VPS/Render)                    │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │  HTML Templates │  │  Django Views │  │  DRF API    │  │
│  │  (Server-side   │  │  (HTTP)       │  │  (REST)     │  │
│  │   Rendering)    │  │               │  │              │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└──────────────┬────────────────┬───────────────┬────────────┘
               │                │               │
       ┌───────▼──────┐   ┌────▼─────┐   ┌────▼────────┐
       │ PostgreSQL    │   │  Redis   │   │  S3/Storage │
       │ (Multi-      │   │  + Celery│   │  (Images,   │
       │  Tenant DB)  │   │  (Jobs)  │   │   Files)    │
       └──────────────┘   └──────────┘   └─────────────┘
               │
               ▼
       ┌──────────────────────────────────────────┐
       │              EXTERNAL APIs                │
       │  - Stripe (Payments)                    │
       │  - SendGrid/Resend (Email)              │
       │  - Google OAuth                         │
       └──────────────────────────────────────────┘
```

---

## Principios de Diseño

### 1. Django como Monolito Modular

**Decisión**: Comenzar con Django como monolito modular.

**Justificación**:
- ✅ **Todo en uno**: ORM, Admin, Auth, Forms incluidos
- ✅ **Admin panel**: Panel de admin automático
- ✅ **Migrations**: Sistema de migraciones robusto
- ✅ **Seguridad**: Protección built-in contra ataques comunes
- ✅ **Curva de aprendizaje**: Fácil de aprender para nuevos devs
- ✅ **Comunidad**: Gran cantidad de recursos y paquetes

**Módulos claramente definidos**:
- `members/` - Gestión de membresía
- `finance/` - Contabilidad y donaciones
- `education/` - Sistema LMS
- `sacraments/` - Registros sacramentales
- `api/` - API REST

**Alternativa considerada**: Microservicios
- ❌ Complejidad operacional alta para MVP
- ❌ Mayor costo de infraestructura
- ❌ Más difícil de mantener

### 2. Server-Side Rendering con Templates

**Decisión**: Django Templates para el frontend.

**Justificación**:
- ✅ **Simplicidad**: Sin JavaScript complejo
- ✅ **SEO**: Contenido renderizado en servidor
- ✅ **Mantenimiento**: Easier para equipos pequeños
- ✅ **Velocidad**: Cargado inicial rápido
- ✅ **Progressive enhancement**: Funciona sin JS

**Frontend**: Vanilla JavaScript + Bootstrap 5
```html
<!-- Ejemplo de template -->
{% extends 'base.html' %}
{% block content %}
<div class="container">
    <h1>Miembros</h1>
    <table class="table">
        {% for member in members %}
        <tr>
            <td>{{ member.first_name }}</td>
            <td>{{ member.last_name }}</td>
            <td>{{ member.email }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endblock %}
```

### 3. API-First Architecture

**Decisión**: API REST integrada desde el inicio.

**Justificación**:
- ✅ **Integraciones**: Conexión con apps móviles, otros sistemas
- ✅ **SPA option**: Posibilidad de migrar a frontend React/Vue en el futuro
- ✅ **Third-party**: Webhooks y APIs públicas
- ✅ **Mobile**: API lista para apps nativas

**Stack API**:
- Django REST Framework
- Serializers para validación
- Token/Session auth (django-allauth)
- Throttling y permissions

---

## Arquitectura Multi-Tenant

### Estrategias Evaluadas

| Estrategia | Pros | Contras | Decisión |
|------------|------|---------|----------|
| **Database per Tenant** | Máximo aislamiento | 🔴 Muy caro (100s de DBs) | ❌ |
| **Shared DB, Row-Level Security** | Bajo costo | 🔴 Queries complejas, riesgo leaks | ❌ |
| **Schema per Tenant** | Buen aislamiento | Límite ~1000 schemas por DB | ✅ **ELEGIDO** |
| **Discriminator Column** | Simple | 🔴 Aislamiento较弱 | ❌ |

### Implementación: Schema-per-Tenant

Cada iglesia (tenant) tiene su propio schema PostgreSQL:

```sql
-- Iglesia 1
CREATE SCHEMA church_abc123;
CREATE TABLE church_abc123.members (...);
CREATE TABLE church_abc123.donations (...);

-- Iglesia 2
CREATE SCHEMA church_xyz789;
CREATE TABLE church_xyz789.members (...);
CREATE TABLE church_xyz789.donations (...);
```

### Tenant Resolution

**Middleware**:
```python
# core/middleware.py
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extraer subdominio
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0] if '.' in host else None
        
        # Buscar tenant
        try:
            tenant = Tenant.objects.get(subdomain=subdomain)
            request.tenant = tenant
            # Establecer schema
            connection.set_schema(tenant.schema_name)
        except Tenant.DoesNotExist:
            request.tenant = None
        
        response = self.get_response(request)
        return response
```

**Connection wrapper**:
```python
# core/db.py
from django.db import connection

def get_tenant_model():
    """Retorna el modelo correcto según el tenant actual."""
    schema_name = getattr(connection, 'schema_name', 'public')
    if schema_name == 'public':
        return PublicTenant
    return get_model_for_schema(schema_name)
```

### Tenant Provisioning

```python
# tenants/views.py
import uuid
from django.db import transaction

@transaction.atomic
def create_tenant(name, subdomain, email):
    schema_name = f"church_{uuid.uuid4().hex[:8]}"
    
    # 1. Crear registro en tabla tenants
    tenant = Tenant.objects.create(
        schema_name=schema_name,
        subdomain=subdomain,
        name=name,
        email=email,
    )
    
    # 2. Crear schema
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA {schema_name}")
    
    # 3. Ejecutar migraciones en nuevo schema
    call_command('migrate', 
                 schema_name=schema_name, 
                 verbosity=0)
    
    # 4. Crear cuenta Stripe Connect
    import stripe
    stripe_account = stripe.Account.create(
        type='standard',
        metadata={'tenant_id': str(tenant.id)}
    )
    tenant.stripe_account_id = stripe_account.id
    tenant.save()
    
    return tenant
```

---

## Arquitectura de la Aplicación

### Estructura de Carpetas

```
sg_church/
├── sg_church/                 # Configuración del proyecto
│   ├── __init__.py
│   ├── settings/              # Settings modular
│   │   ├── __init__.py
│   │   ├── base.py           # Settings base
│   │   ├── local.py          # Desarrollo
│   │   └── production.py     # Producción
│   ├── urls.py               # URLs principales
│   ├── wsgi.py
│   └── asgi.py
│
├── core/                      # Funcionalidad core
│   ├── models.py             # Modelos compartidos
│   ├── middleware.py          # Tenant middleware
│   ├── management/
│   │   └── commands/         # Comandos Django
│   └── utils.py
│
├── tenants/                  # Gestión de tenants
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── migrations/
│
├── members/                  # Gestión de miembros
│   ├── models.py
│   ├── views.py
│   ├── serializers.py        # DRF serializers
│   ├── urls.py
│   ├── templates/
│   │   └── members/
│   └── migrations/
│
├── finance/                  # Finanzas y donaciones
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── tasks.py             # Celery tasks
│   └── migrations/
│
├── education/                # LMS
│   ├── models.py
│   ├── views.py
│   └── migrations/
│
├── api/                      # API REST
│   ├── urls.py
│   ├── views.py
│   └── routers.py
│
├── templates/                # Templates globales
│   ├── base.html
│   ├── admin/
│   └── registration/
│
├── static/                   # CSS, JS, imágenes
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/                    # Archivos subidos (en desarrollo)
│
├── requirements.txt
├── manage.py
└── pytest.ini
```

### Flujo de Datos

**Vistas Django (Server-Side)**:
```python
# members/views.py
from django.views.generic import ListView, DetailView
from .models import Member

class MemberListView(ListView):
    model = Member
    template_name = 'members/list.html'
    context_object_name = 'members'
    paginate_by = 50
    
    def get_queryset(self):
        return Member.objects.filter(
            tenant=self.request.tenant
        ).order_by('last_name', 'first_name')
```

**API REST (DRF)**:
```python
# members/views.py (API)
from rest_framework import viewsets
from .models import Member
from .serializers import MemberSerializer

class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    
    def get_queryset(self):
        return Member.objects.filter(
            tenant=self.request.user.tenant
        )
```

---

## Patrón de Datos

### Model Django

```python
# members/models.py
from django.db import models
from django.contrib.auth.models import User

class Tenant(models.Model):
    """Modelo para cada iglesia (tenant)."""
    name = models.CharField(max_length=255)
    subdomain = models.CharField(max_length=63, unique=True)
    schema_name = models.CharField(max_length=64, unique=True)
    stripe_account_id = models.CharField(max_length=64, blank=True)
    settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'tenants'


class Member(models.Model):
    """Modelo de miembro de la iglesia."""
    STATUS_CHOICES = [
        ('visitor', 'Visitante'),
        ('attendee', 'Asistente'),
        ('member', 'Miembro'),
        ('inactive', 'Inactivo'),
    ]
    
    # Relación con tenant
    tenant = models.ForeignKey(
        'tenants.Tenant', 
        on_delete=models.CASCADE,
        related_name='members'
    )
    
    # Información básica
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Información demográfica
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    marital_status = models.CharField(max_length=20, blank=True)
    
    # Estado
    member_status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='visitor'
    )
    
    # Familia
    family = models.ForeignKey(
        'Family',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='members'
    )
    
    # Multimedia
    photo = models.ImageField(
        upload_to='members/photos/',
        null=True, blank=True
    )
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['email']),
            models.Index(fields=['member_status']),
            models.Index(fields=['tenant', 'member_status']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Family(models.Model):
    """Modelo de familia."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='families'
    )
    name = models.CharField(max_length=255)  # "Familia García"
    primary_contact = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='primary_for_families'
    )
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']


class Donation(models.Model):
    """Modelo de donaciones."""
    TYPE_CHOICES = [
        ('one_time', 'Una vez'),
        ('recurring', 'Recurrente'),
    ]
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='donations'
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='donations'
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    donation_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='one_time'
    )
    
    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=64, blank=True)
    stripe_subscription_id = models.CharField(max_length=64, blank=True)
    
    # Estado
    status = models.CharField(
        max_length=20,
        default='completed'
    )
    receipt_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['member', '-created_at']),
        ]
```

---

## API REST

### URLs de la API

```python
# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from members.views import MemberViewSet
from finance.views import DonationViewSet

router = DefaultRouter()
router.register(r'members', MemberViewSet)
router.register(r'donations', DonationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('dj_rest_auth.urls')),
]
```

### Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/members/` | Listar miembros |
| POST | `/api/members/` | Crear miembro |
| GET | `/api/members/{id}/` | Ver miembro |
| PUT | `/api/members/{id}/` | Actualizar miembro |
| DELETE | `/api/members/{id}/` | Eliminar miembro |
| GET | `/api/donations/` | Listar donaciones |
| POST | `/api/donations/` | Crear donación |

---

## Autenticación y Autorización

### Django Auth

```python
# settings.py
AUTH_USER_MODEL = 'members.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
```

### DRF Permissions

```python
# core/permissions.py
from rest_framework import permissions

class IsChurchAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        return obj.tenant == request.user.tenant

class IsReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
```

### Roles

| Rol | Permisos |
|-----|----------|
| CHURCH_ADMIN | Acceso total |
| PASTOR | Ver/editar miembros, ver finanzas |
| TREASURER | Gestionar finanzas y donaciones |
| TEACHER | Gestionar cursos |
| VOLUNTEER | Acceso limitado |
| MEMBER | Ver perfil propio |

---

## Procesamiento de Pagos

### Stripe Connect

```python
# payments/views.py
import stripe
from django.conf import settings

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
        metadata={'tenant_id': str(request.user.tenant.id)}
    )
    return Response({'session_id': session.id})
```

---

## Sistema de Notificaciones

### Email con Celery

```python
# finance/tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_donation_receipt(donation_id):
    from finance.models import Donation
    donation = Donation.objects.get(id=donation_id)
    
    send_mail(
        subject=f'Recibo de donación - ${donation.amount}',
        message=f'Gracias por tu donación...',
        from_email='noreply@sgchurch.app',
        recipient_list=[donation.member.email],
    )
```

---

## Tareas en Segundo Plano

### Celery + Redis

```python
# core/celery.py
from celery import Celery

app = Celery('sg_church')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# tasks.py
@app.task
def process_donation(donation_id):
    # Procesar donación
    pass
```

---

## Escalabilidad

### Horizontal Scaling Path

**Fase 1 (0-100 iglesias)**:
- Single Django instance
- PostgreSQL gestionado (Railway/Render/Neon)
- Redis (Railway/Upstash)

**Fase 2 (100-1,000 iglesias)**:
- Multiple Django instances (Gunicorn + Nginx)
- PostgreSQL con read replicas
- Celery workers separados

**Fase 3 (1,000+ iglesias)**:
- Database sharding
- CDN para static files
- Workers dedicados

---

## Resumen de Decisiones

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Backend** | Django 5 | ORM, Admin, Seguridad |
| **Frontend** | Django Templates + Bootstrap | Simplicidad, SEO |
| **API** | DRF | Estándar profesional |
| **Multi-tenancy** | Schema-per-tenant | Balance aislamiento/costo |
| **Database** | PostgreSQL | Confiabilidad |
| **Auth** | Django Auth + DRF | Integrado |
| **Payments** | Stripe Connect | Best-in-class |
| **Jobs** | Celery | Integración Django |
| **Hosting** | Render/VPS | Simplicidad, costo |

---

**Próximos pasos**: Ver [ROADMAP.md](./ROADMAP.md) para implementación por fases.
