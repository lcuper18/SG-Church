# Sprint 5: Sistema de Notificaciones

**Período**: Semana 21-24 (Fase 1: Fundación MVP)  
**Estado**: Por iniciar  
**Revisor QA**: Por asignar

---

## Objetivo

Implementar el sistema de notificaciones por email e in-app para mejorar la comunicación con miembros y administradores de la iglesia.

---

## Entregables

| # | Módulo | Descripción | Prioridad |
|---|--------|-------------|-----------|
| 1 | Email Infrastructure | Configurar Resend API y templates de email | Alta |
| 2 | Cola de Emails | Sistema de queue con Celery para procesamiento async | Alta |
| 3 | Email Templates | Welcome email, Donation receipt, Password reset | Alta |
| 4 | In-App Notifications | Schema, API y UI para notificaciones internas | Media |
| 5 | Logging | Registro de emails enviados para auditoría | Media |

---

## 1. Email Infrastructure

### Descripción
Configurar la infraestructura de email usando Resend API como proveedor principal.

### Configuración

#### Variables de Entorno
```env
RESEND_API_KEY=re_123456789
EMAIL_FROM_ADDRESS=noreply@sgchurch.com
EMAIL_FROM_NAME=SG Church
```

#### Settings
```python
# sg_church/settings/base.py
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_FROM_ADDRESS', 'noreply@sgchurch.com')
EMAIL_BACKEND = 'sg_church.emails.backends.ResendEmailBackend'
```

### Backend de Email Custom
Crear un backend que use la API de Resend:

```python
# sg_church/emails/backends.py
class ResendEmailBackend:
    def send_messages(self, message):
        # Use Resend API to send email
```

### URLs y Paths
- **App**: `sg_church/emails/`
- **Models**: `sg_church/emails/models.py`
- **Views**: `sg_church/emails/views.py`
- **Templates**: `templates/emails/` (HTML templates)

---

## 2. Cola de Emails (Async)

### Descripción
Sistema de cola para procesar emails de forma asíncrona usando Celery.

### Estructura

```python
# config/celery.py
from celery import Celery

app = Celery('sg_church')
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
)
```

### Tasks

```python
# sg_church/emails/tasks.py
@shared_task
def send_email_task(to_email, subject, template_name, context):
    """Send email asynchronously."""
    pass

@shared_task
def send_bulk_emails_task(recipient_list, subject, template_name, context):
    """Send bulk emails."""
    pass
```

### Criterios de Aceptación

- [ ] Celery configurado y funcionando
- [ ] Redis como broker
- [ ] Tasks pueden ser encolados y procesados
- [ ] Fallback a email sync si Celery no está disponible

---

## 3. Email Templates

### Descripción
Crear templates HTML profesionales para diferentes tipos de emails.

### Templates Requeridos

#### 3.1 Welcome Email (Bienvenida)
- **Uso**: Cuando un nuevo miembro se registra
- **Contenido**:
  - Saludo personalizado
  - Nombre de la iglesia
  - Información de contacto
  - Links útiles (dashboard, profile)
- **Template**: `templates/emails/welcome.html`

#### 3.2 Donation Receipt (Recibo de Donación)
- **Uso**: Después de una donación exitosa
- **Contenido**:
  - Confirmación de donation
  - Monto, fecha, campaña
  - Información fiscal
  - Thank you message
- **Template**: `templates/emails/donation_receipt.html`

#### 3.3 Password Reset (Restablecer Contraseña)
- **Uso**: Solicitud de recuperación de contraseña
- **Contenido**:
  - Link de reset
  - Expiración del link
  - Advertencia de seguridad
- **Template**: `templates/emails/password_reset.html`

#### 3.4 Expense Notification (Notificación de Gasto)
- **Uso**: Cuando se crea un nuevo gasto
- **Contenido**:
  - Detalles del gasto
  - Link para aprobar
- **Template**: `templates/emails/expense_notification.html`

### Estructura Base del Template
```html
<!-- templates/emails/base.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; }
        .footer { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
        <div class="footer">
            <p>© 2026 SG Church</p>
        </div>
    </div>
</body>
</html>
```

### Criterios de Aceptación

- [ ] Todos los templates creados
- [ ] Responsive design (mobile-friendly)
- [ ] Links funcionan correctamente
- [ ] Imágenes/logos se cargan bien

---

## 4. In-App Notifications

### Descripción
Sistema de notificaciones internas dentro de la aplicación.

### Modelo

```python
# notifications/models.py
class Notification(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50)  # donation, expense, member, system
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    link = models.CharField(max_length=500, blank=True)  # URL to navigate
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Multi-tenant filter
    class Meta:
        ordering = ['-created_at']
```

### Tipos de Notificaciones
| Type | Descripción | Trigger |
|------|-------------|---------|
| `donation_received` | Nueva donación recibida | Webhook Stripe |
| `expense_created` | Nuevo gasto registrado | Create expense |
| `expense_approved` | Gasto aprobado | Approve expense |
| `member_added` | Nuevo miembro agregado | Create member |
| `system` | Notificaciones del sistema | Various |

### API Endpoints

```python
# notifications/urls.py
urlpatterns = [
    path('api/notifications/', NotificationListView.as_view(), name='notification_list'),
    path('api/notifications/<int:pk>/read/', mark_as_read, name='notification_read'),
    path('api/notifications/read-all/', mark_all_as_read, name='notification_read_all'),
]
```

### UI - Bell Icon with Dropdown

```html
<!-- templates/includes/notifications_dropdown.html -->
<div class="dropdown">
    <button class="btn btn-link position-relative" data-bs-toggle="dropdown">
        <i class="bi bi-bell"></i>
        <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
            {{ unread_count }}
        </span>
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
        <!-- Notification items -->
    </ul>
</div>
```

### Criterios de Aceptación

- [ ] Modelo de notifications creado
- [ ] CRUD de notificaciones funcional
- [ ] Bell icon con contador de no leídas
- [ ] Dropdown muestra últimas notificaciones
- [ ] Marcar como leído funciona
- [ ] Notificaciones filtradas por tenant

---

## 5. Email Logging

### Descripción
Sistema de auditoría para registrar todos los emails enviados.

### Modelo

```python
# emails/models.py
class EmailLog(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True)
    
    to_email = models.EmailField()
    from_email = models.EmailField()
    subject = models.CharField(max_length=500)
    
    template_name = models.CharField(max_length=100)
    context = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20)  # sent, failed, pending
    error_message = models.TextField(blank=True)
    
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Multi-tenant filter
    class Meta:
        ordering = ['-created_at']
```

### Funcionalidad

- [ ] Registrar cada email enviado
- [ ] Guardar contexto del email
- [ ] Registrar errores si fallan
- [ ] Interfaz para ver logs (admin)

---

## Checklist de Desarrollo

### Pre-requisitos
- [ ] Instalar `celery` y `redis`
- [ ] Configurar Resend API
- [ ] Agregar `django-celery-beat` para scheduling

### Email Infrastructure
- [ ] Resend API backend configurado
- [ ] Settings actualizados
- [ ] Tests de conexión

### Cola de Emails
- [ ] Celery configurado
- [ ] Redis como broker
- [ ] Task para enviar emails
- [ ] Task para emails bulk
- [ ] Fallback sync funcionando

### Email Templates
- [ ] Base template creado
- [ ] Welcome email template
- [ ] Donation receipt template
- [ ] Password reset template
- [ ] Expense notification template

### In-App Notifications
- [ ] Modelo Notification creado
- [ ] Migraciones aplicadas
- [ ] API endpoints creados
- [ ] UI: Bell icon con dropdown
- [ ] Funcionalidad mark as read

### Email Logging
- [ ] Modelo EmailLog creado
- [ ] Logging en cada send
- [ ] UI de logs básica

---

## Checklist de QA

### Email Infrastructure
- [ ] Resend API responde correctamente
- [ ] Emails se mandan desde la dirección correcta

### Cola de Emails
- [ ] Emails se encolan correctamente
- [ ] Procesamiento async funciona
- [ ] No hay pérdida de emails

### Email Templates
- [ ] Welcome email se envía al registrar miembro
- [ ] Donation receipt se envía después de donate
- [ ] Password reset funciona
- [ ] Templates se ven bien en móvil

### In-App Notifications
- [ ] Notificaciones se crean correctamente
- [ ] Bell icon muestra contador
- [ ] Dropdown lista notificaciones
- [ ] Click marca como leída
- [ ] "Mark all as read" funciona
- [ ] Aislamiento entre tenants

### Email Logging
- [ ] Cada email enviado queda registrado
- [ ] Errores se registran
- [ ] Logs visibles en admin

### General
- [ ] Datos aislados entre tenants
- [ ] Performance aceptable

---

## Notas Técnicas

### Multi-tenancy
- Todas las queries deben filtrar por `tenant`
- Email logs pueden ser null para emails sin tenant (sistema)

### Resend API
- Usar SDK oficial de Resend para Python
- Manejar rate limits
- Logging de respuestas

### Celery
- Usar `django-celery-results` para persistencia
- Configurar `celery beat` para tareas programadas
- Retry logic para emails fallidos

### Testing
- Usar `pytest-django` para tests
- Mock Resend en tests unitarios
- Tests de integración para webhooks

---

## Dependencias

```
celery[redis]>=5.3.0
django-celery-results>=2.5.0
django-celery-beat>=2.5.0
resend>=0.8.0
redis>=5.0.0
```

---

## Archivos a Crear/Modificar

### Nuevos Archivos
```
sg_church/
├── emails/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py          # EmailLog model
│   ├── tasks.py           # Celery tasks
│   ├── services.py        # Email sending service
│   └── backends.py        # Custom email backend
│
├── notifications/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py          # Notification model
│   ├── views.py          # API views
│   └── urls.py           # URLs
│
└── templates/
    └── emails/
        ├── base.html
        ├── welcome.html
        ├── donation_receipt.html
        ├── password_reset.html
        └── expense_notification.html
```

### Archivos a Modificar
```
sg_church/settings/base.py     # Add email settings, Celery config
sg_church/settings/__init__.py # Add celery app
manage.py                       # Add celery setup
templates/
└── base.html                  # Add notifications bell icon
```

---

## Notas Adicionales

1. **Resend vs SendGrid**: Resend es más moderno y tiene mejor DX. Usar Resend como proveedor principal.

2. **Fallback**: Si Resend falla, usar `console` backend para desarrollo y `smtp` como backup.

3. **Preview**: Crear página admin para previsualizar emails con datos de prueba.

4. **Unsubscribe**: Agregar link de unsubscribe en todos los emails transaccionales.

5. **SSL**: Asegurar que Redis use conexión segura en producción.

---

**Documento creado**: Sprint 5 Plan  
**Última actualización**: Marzo 28, 2026
