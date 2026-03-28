# Sprint 3: Gestión de Membresía + Onboarding

**Período**: Semana 5-8 (Fase 1: Fundación MVP)  
**Estado**: Por iniciar  
**Revisor QA**: Por asignar

---

## Objetivo

Implementar el sistema de gestión de membresía completo y el wizard de onboarding para nuevas iglesias.

---

## Entregables

| # | Módulo | Descripción | Prioridad |
|---|--------|-------------|-----------|
| 1 | Onboarding Wizard | Wizard 4 pasos para registrar nueva iglesia | Alta |
| 2 | CRUD Miembros | Create/Read/Update/Delete de miembros | Alta |
| 3 | Sistema Familias | Gestión de unidades familiares | Media |
| 4 | Dashboard | Página principal tras login | Media |

---

## 1. Onboarding Wizard

### Descripción
Wizard multi-paso para que una nueva iglesia configure su cuenta.

### Pasos del Wizard

#### Paso 1: Datos de la Iglesia
- **URL**: `/onboarding/church/`
- **Campos**:
  - Nombre de la iglesia (required)
  - Denominación (select: Católica, Bautista, Metodista, Presbiteriana, Evangélica, Otra)
  - País (select)
  - Ciudad
  - Estado/Provincia
  - Dirección
  - Código postal
  - Teléfono
  - Logo (upload de imagen)
- **Botón**: "Continuar"

#### Paso 2: Configuración del Admin
- **URL**: `/onboarding/admin/`
- **Campos**:
  - Nombre completo (required)
  - Email (required, unique)
  - Teléfono
  - Contraseña (required, con confirmación)
  - Aceptar términos y condiciones (checkbox)
- **Botón**: "Crear Cuenta"

#### Paso 3: Configuración Básica
- **URL**: `/onboarding/settings/`
- **Campos**:
  - Moneda predeterminada (select: USD, EUR, MXN, etc.)
  - Zona horaria (select)
  - Formato de fecha (DD/MM/YYYY, MM/DD/YYYY)
  - Habilitarfamilias (checkbox, default: true)
  - Habilitar etiquetas (checkbox, default: true)
- **Botón**: "Continuar"

#### Paso 4: Welcome Screen
- **URL**: `/onboarding/complete/`
- **Contenido**:
  - Mensaje de bienvenida
  - Links rápidos: "Agregar Miembro", "Ver Dashboard", "Configurar Donaciones"
- **Botón**: "Ir al Dashboard"

### Modelos Necesarios

```python
# tenants/models.py - Agregar a Tenant
church_name = models.CharField(max_length=255)
denomination = models.CharField(max_length=50, choices=DENOMINATION_CHOICES)
country = models.CharField(max_length=2)  # ISO code
city = models.CharField(max_length=100)
state = models.CharField(max_length=100)
address = models.TextField()
phone = models.CharField(max_length=20)
logo = models.ImageField(upload_to='church_logos/')
currency = models.CharField(max_length=3, default='USD')
timezone = models.CharField(max_length=50, default='America/New_York')
date_format = models.CharField(max_length=20, default='DD/MM/YYYY')
enable_families = models.BooleanField(default=True)
enable_tags = models.BooleanField(default=True)
onboarding_completed = models.BooleanField(default=False)
```

### URLs a Crear

```python
# core/urls.py
path('onboarding/', include([
    path('church/', views.OnboardingChurchView.as_view(), name='onboarding_church'),
    path('admin/', views.OnboardingAdminView.as_view(), name='onboarding_admin'),
    path('settings/', views.OnboardingSettingsView.as_view(), name='onboarding_settings'),
    path('complete/', views.OnboardingCompleteView.as_view(), name='onboarding_complete'),
]))
```

### Templates a Crear

| Template | Descripción |
|----------|-------------|
| `onboarding/church.html` | Paso 1: Datos de iglesia |
| `onboarding/admin.html` | Paso 2: Crear admin |
| `onboarding/settings.html` | Paso 3: Configuración |
| `onboarding/complete.html` | Paso 4: Bienvenida |

### Criterios de Aceptación

- [ ] Wizard inicia en `/onboarding/` redirige al paso actual
- [ ] Usuario no puede saltar pasos (redirect si no ha completado anterior)
- [ ] Validación de campos con mensajes de error claros
- [ ] Contraseña: mínimo 8 caracteres, 1 mayúscula, 1 número
- [ ] Email debe ser único en el sistema
- [ ] Al completar, se crea: Tenant + User admin + settings
- [ ] Usuario queda logueado automáticamente
- [ ] Redirige a `/dashboard/` tras completar
- [ ] Tests unitarios para cada view

---

## 2. CRUD de Miembros

### Descripción
Sistema completo de gestión de miembros con lista, búsqueda, filtros y operaciones CRUD.

### Vistas Necesarias

#### Lista de Miembros
- **URL**: `/members/`
- **Template**: `members/list.html`
- **Funcionalidades**:
  - Tabla con columnas: Foto, Nombre, Email, Teléfono, Status, Familia, Acciones
  - Paginación (25 por página)
  - Búsqueda por nombre, email, teléfono
  - Filtros por:
    - Status (Miembro, Visitante, Asistente, Inactivo)
    - Familia
    - Tags
  - Ordenar por: Apellido, Nombre, Fecha de creación
  - Acciones bulk: Exportar, Eliminar, Cambiar status
  - Botón: "Agregar Miembro"

#### Crear Miembro
- **URL**: `/members/create/`
- **Template**: `members/form.html`
- **Campos**:
  - Información Personal
    - Nombre (required)
    - Apellido (required)
    - Email
    - Teléfono
    - Fecha de nacimiento
    - Género (Masculino, Femenino, Otro)
    - Estado civil (Soltero, Casado, Viudo, Divorciado)
    - Foto (upload)
  - Información de Membresía
    - Status (Miembro, Visitante, Asistente, Inactivo)
    - Fecha de membresía
    - Notas
  - Familia
    - Seleccionar familia existente o crear nueva
  - Dirección
    - Dirección
    - Ciudad
    - Estado
    - Código postal
  - Etiquetas
    - Seleccionar/crear etiquetas

#### Editar Miembro
- **URL**: `/members/<id>/edit/`
- **Template**: `members/form.html` (reutilizar)
- Mismos campos que crear, valores previos cargados

#### Ver Miembro (Detalle)
- **URL**: `/members/<id>/`
- **Template**: `members/detail.html`
- **Tabs**:
  - Información personal
  - Familia
  - Donaciones
  - Asistencia

#### Eliminar Miembro
- **URL**: `/members/<id>/delete/`
- **Template**: `members/confirm_delete.html`
- Confirmación antes de eliminar

### Modelos Necesarios (ya creados)

```python
# members/models.py - Member
first_name = models.CharField(max_length=100)
last_name = models.CharField(max_length=100)
email = models.EmailField()
phone = models.CharField(max_length=20)
date_of_birth = models.DateField(null=True, blank=True)
gender = models.CharField(max_length=20)
marital_status = models.CharField(max_length=20)
member_status = models.CharField(max_length=20)  # member, visitor, attendee, inactive
membership_date = models.DateField()
family = models.ForeignKey('Family', null=True, blank=True)
address = models.TextField()
city = models.CharField(max_length=100)
state = models.CharField(max_length=100)
postal_code = models.CharField(max_length=20)
photo = models.ImageField(upload_to='members/')
notes = models.TextField()
tags = models.ManyToManyField('Tag', blank=True)
```

### URLs a Crear/Actualizar

```python
# members/urls.py
path('members/', views.MemberListView.as_view(), name='member_list'),
path('members/create/', views.MemberCreateView.as_view(), name='member_create'),
path('members/<int:pk>/', views.MemberDetailView.as_view(), name='member_detail'),
path('members/<int:pk>/edit/', views.MemberUpdateView.as_view(), name='member_update'),
path('members/<int:pk>/delete/', views.MemberDeleteView.as_view(), name='member_delete'),
```

### Templates a Crear

| Template | Descripción |
|----------|-------------|
| `members/list.html` | Lista con filtros y búsqueda |
| `members/form.html` | Formulario crear/editar (reutilizable) |
| `members/detail.html` | Detalle con tabs |
| `members/confirm_delete.html` | Confirmación de eliminación |

### Criterios de Aceptación

- [ ] Lista muestra todos los miembros del tenant actual
- [ ] Búsqueda encuentra por nombre, email, teléfono
- [ ] Filtros funcionan correctamente (status, familia, tags)
- [ ] Paginación funciona (25 por página)
- [ ] Crear miembro guarda correctamente en base de datos
- [ ] Editar miembro actualiza correctamente
- [ ] Eliminar miembro requiere confirmación
- [ ] foto se sube a media/members/
- [ ] Solo usuarios autenticados pueden acceder
- [ ] Datos de otros tenants no son visibles (middleware)
- [ ] Tests unitarios para views

---

## 3. Sistema de Familias

### Descripción
Gestión de unidades familiares para agrupar miembros.

### Modelos

```python
# members/models.py
class Family(models.Model):
    name = models.CharField(max_length=200)  # e.g., "Familia García"
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    head_of_family = models.ForeignKey(
        'Member', 
        null=True, 
        blank=True,
        related_name='family_head',
        on_delete=models.SET_NULL
    )
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    home_phone = models.CharField(max_length=20)
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Tag(models.Model):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7)  # Hex color
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
```

### Vistas

#### Lista de Familias
- **URL**: `/families/`
- **Template**: `families/list.html`
- Tabla: Nombre, Cabeza de familia, Miembros, Teléfono, Acciones
- Botón: "Agregar Familia"

#### Crear/Editar Familia
- **URL**: `/families/create/` y `/families/<id>/edit/`
- **Template**: `families/form.html`

#### Lista de Etiquetas
- **URL**: `/tags/`
- **Template**: `tags/list.html`
- Crear/editar/eliminar etiquetas

### URLs

```python
# members/urls.py
path('families/', views.FamilyListView.as_view(), name='family_list'),
path('families/create/', views.FamilyCreateView.as_view(), name='family_create'),
path('families/<int:pk>/edit/', views.FamilyUpdateView.as_view(), name='family_update'),
path('families/<int:pk>/delete/', views.FamilyDeleteView.as_view(), name='family_delete'),
path('tags/', views.TagListView.as_view(), name='tag_list'),
path('tags/create/', views.TagCreateView.as_view(), name='tag_create'),
path('tags/<int:pk>/edit/', views.TagUpdateView.as_view(), name='tag_update'),
path('tags/<int:pk>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),
```

### Criterios de Aceptación

- [ ] Familia agrupa múltiples miembros
- [ ] Miembro puede pertencer a una familia
- [ ] Tags pueden asignarse a miembros
- [ ] Solo datos del tenant actual visibles

---

## 4. Dashboard

### Descripción
Página principal que el usuario ve tras iniciar sesión.

### Contenido del Dashboard

#### Header
- Logo de la iglesia
- Nombre de la iglesia
- Menú: Dashboard, Miembros, Familias, Finanzas, Configuración
- Usuario: Nombre + dropdown (Perfil, Cerrar sesión)

#### Stats Cards (4 cards)
| Card | Valor | Color |
|------|-------|-------|
| Total Miembros | count | Primary |
| Nuevos este mes | count | Success |
| Donaciones este mes | $amount | Warning |
| Asistencia promedio | % | Info |

#### Acciones Rápidas
- Agregar Miembro
- Registrar Donación
- Ver Reportes

#### Actividad Reciente (lista)
- 5 últimas actividades (miembros agregados, donaciones, etc.)

### Template

- **URL**: `/dashboard/`
- **Template**: `core/dashboard.html`

### Criterios de Aceptación

- [ ] Muestra stats del tenant actual
- [ ] Links de navegación funcionan
- [ ] Dropdown de usuario funciona
- [ ] Actividad reciente muestra últimos registros

---

## Checklist de Desarrollo

### Pre-requisitos
- [ ] Modelos actualizados en `tenants/models.py`
- [ ] Modelos actualizados en `members/models.py`
- [ ] Migraciones creadas y aplicadas (`python manage.py makemigrations`)

### Onboarding
- [ ] Templates creados
- [ ] Vistas creadas
- [ ] URLs configuradas
- [ ] Tests creados

### Miembros
- [ ] Templates creados
- [ ] Vistas CRUD creadas
- [ ] Búsqueda implementada
- [ ] Filtros implementados
- [ ] Upload de foto funcional
- [ ] Tests creados

### Familias
- [ ] Templates creados
- [ ] Vistas CRUD creadas
- [ ] Tests creados

### Dashboard
- [ ] Template creado
- [ ] Stats implementados
- [ ] Tests creados

---

## Checklist de QA

### Onboarding Wizard
- [ ] Wizard inicia correctamente
- [ ] No permite saltar pasos
- [ ] Validaciones funcionan
- [ ] Crea tenant y usuario correctamente
- [ ] Redirige a dashboard al completar

### Miembros
- [ ] Lista muestra datos correctos
- [ ] Búsqueda funciona
- [ ] Filtros funcionan
- [ ] CRUD completo funciona
- [ ] Aislamiento de datos entre tenants

### Dashboard
- [ ] Muestra stats correctos
- [ ] Navegación funciona

---

## Notas Técnicas

### Multi-tenancy
- Usar `TenantMiddleware` existente
- Todas las queries filtran por `tenant` automáticamente
- Templates muestran solo datos del tenant del usuario

### Estilos
- Usar Bootstrap 5 clases existentes en templates
- Mantener consistencia con `base.html`

### Formularios
- Usar Django Forms
- Reutilizar `members/form.html` para create y update

### Tests
- pytest para unit tests
- pytest-django para integration tests
- Coverage mínimo: 80%

---

## Dependencias

- Django 5.x
- django-crispy-forms
- crispy-bootstrap4
- Pillow (para upload de imágenes)

---

**Documento creado**: Sprint 3 Plan  
**Última actualización**: Ver commit
