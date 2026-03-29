# Sprint 4: Donaciones y Finanzas Básicas

**Período**: Semana 15-20 (Fase 1: Fundación MVP)  
**Estado**: Por iniciar  
**Revisor QA**: Por asignar

---

## Objetivo

Implementar el sistema básico de donaciones con Stripe y finanzas con dashboard y registro de gastos.

---

## Entregables

| # | Módulo | Descripción | Prioridad |
|---|--------|-------------|-----------|
| 1 | Dashboard Financiero | Stats de ingresos/gastos, gráfico mensual | Alta |
| 2 | Lista de Donaciones | Ver todas las donaciones con filtros | Alta |
| 3 | Formulario de Gastos | Registrar gastos con categoría | Alta |
| 4 | Stripe Integration | Checkout para donaciones | Media |
| 5 | Reportes Básicos | Ingresos vs Gastos por mes | Media |

---

## 1. Dashboard Financiero

### Descripción
Página principal de finanzas con estadísticas y gráficos.

### Contenido

#### Stats Cards (4 cards)
| Card | Valor | Descripción |
|------|-------|-------------|
| Ingresos del Mes | $amount | Total donaciones completadas |
| Gastos del Mes | $amount | Total gastos registrados |
| Balance | $amount | Ingresos - Gastos |
| Donantes Activos | count | Donantes únicos en el mes |

#### Gráfico
- **Tipo**: Barras (ingresos vs gastos)
- **Período**: Últimos 12 meses
- **Eje X**: Meses
- **Eje Y**: Monto en dólares

#### Transacciones Recientes
- Lista de últimas 10 transacciones (donaciones + gastos)
- Tipo, monto, fecha, descripción

### URLs y Templates

- **URL**: `/finance/`
- **Template**: `finance/dashboard.html`

### Criterios de Aceptación

- [ ] Muestra ingresos del mes actual
- [ ] Muestra gastos del mes actual
- [ ] Calcula balance correctamente
- [ ] Gráfico muestra últimos 12 meses
- [ ] Lista transacciones recientes
- [ ] Solo datos del tenant actual visibles

---

## 2. Lista de Donaciones

### Descripción
Vista completa de todas las donaciones.

### Contenido

#### Filtros
- **Por estado**: Pendiente, Completado, Fallido, Reembolsado
- **Por campaña**: Diezmo, Ofrenda, Construcción, Misiones, Otro
- **Por fecha**: Desde - Hasta
- **Por miembro**: Seleccionar miembro
- **Búsqueda**: Por nombre de donante

#### Tabla
| Columna | Descripción |
|---------|-------------|
| Fecha | Fecha de donación |
| Donante | Nombre del miembro o "Anónimo" |
| Monto | Cantidad donada |
| Campaña | Tipo de campaña |
| Estado | Badge (completado/pendiente/fallido) |
| Acciones | Ver detalle |

#### Paginación
- 25 por página
- Orden por fecha descendente

### URLs y Templates

- **URL**: `/finance/donations/`
- **Template**: `finance/donations/list.html`

### Criterios de Aceptación

- [ ] Lista todas las donaciones del tenant
- [ ] Filtros funcionan correctamente
- [ ] Búsqueda funciona
- [ ] Paginación funciona
- [ ] Puede ver detalle de donación
- [ ] Solo datos del tenant actual visibles

---

## 3. Formulario de Gastos

### Descripción
Crear y gestionar gastos de la iglesia.

### Modelo (ya existe)

```python
# finance/models.py - Expense
description = models.CharField(max_length=255)
amount = models.DecimalField(max_digits=10, decimal_places=2)
category = models.CharField(max_length=20)  # operations, salaries, utilities, etc.
status = models.CharField(max_length=20)  # pending, approved, paid
vendor_name = models.CharField(max_length=200, blank=True)
expense_date = models.DateField()
receipt = models.FileField(upload_to="expenses/receipts/")
created_by = models.ForeignKey(User)
```

### Vistas

#### Lista de Gastos
- **URL**: `/finance/expenses/`
- **Template**: `finance/expenses/list.html`
- Tabla con filtros por estado, categoría, fecha

#### Crear Gasto
- **URL**: `/finance/expenses/create/`
- **Template**: `finance/expenses/form.html`
- Campos: descripción, monto, categoría, proveedor, fecha, receipt upload

#### Editar Gasto
- **URL**: `/finance/expenses/<id>/edit/`
- Template reutilizado

#### Eliminar Gasto
- **URL**: `/finance/expenses/<id>/delete/`
- Confirmación

### Criterios de Aceptación

- [ ] Puede crear nuevo gasto
- [ ] Puede editar gasto existente
- [ ] Puede eliminar gasto con confirmación
- [ ] Upload de receipt funciona
- [ ] Filtros funcionan
- [ ] Solo datos del tenant actual visibles

---

## 4. Stripe Integration (Básico)

### Descripción
Integración básica con Stripe para procesar donaciones.

### Modelo (ya existe)

```python
# finance/models.py - Donation
amount = models.DecimalField(max_digits=10, decimal_places=2)
donation_type = models.CharField()  # one_time, recurring
campaign = models.CharField()  # tithe, offering, building, etc.
status = models.CharField()  # pending, completed, failed
stripe_payment_intent_id = models.CharField(max_length=64, blank=True)
stripe_subscription_id = models.CharField(max_length=64, blank=True)
```

### Configuración

#### Variables de Entorno
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

#### Settings
```python
# sg_church/settings/base.py
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
```

### Página de Donación Pública

- **URL**: `/donate/`
- **Template**: `finance/donate.html`
- **Contenido**:
  - Información de la iglesia (logo, nombre)
  - Formulario:
    - Nombre (si no está logueado)
    - Email
    - Monto (input number)
    - Campaña (select)
    - "Cubrir fees" checkbox (opcional)
  - Botón "Donar" → Stripe Checkout

### Webhook Handler

- **URL**: `/api/v1/webhooks/stripe/`
- **Eventos a manejar**:
  - `checkout.session.completed` → Actualizar status donation a completed
  - `invoice.payment_failed` → Actualizar status a failed

### Criterios de Aceptación

- [ ] Página de donación pública accessible
- [ ] Formulario收集 datos correctamente
- [ ] Redirige a Stripe Checkout
- [ ] Webhook actualiza estado de donación
- [ ] Solo modo test (keys de test)

---

## 5. Reportes Básicos

### Descripción
Reportes financieros simples.

### Reporte: Estado de Resultados

- **URL**: `/finance/reports/income-statement/`
- **Template**: `finance/reports/income_statement.html`
- **Contenido**:
  - Período: Mes actual o seleccionar mes
  - Ingresos por campaña
  - Gastos por categoría
  - Balance neto

### Reporte: Donaciones por Miembro

- **URL**: `/finance/reports/donations-by-member/`
- **Template**: `finance/reports/donations_by_member.html`
- **Contenido**:
  - Tabla: Miembro, Total donado, Última donación
  - Filtro por período

### Criterios de Aceptación

- [ ] Reporte de ingresos/gastos muestra datos correctos
- [ ] Reporte por miembro agrupa correctamente
- [ ] Solo datos del tenant actual visibles

---

## Checklist de Desarrollo

### Pre-requisitos
- [ ] Configurar Stripe en settings
- [ ] Verificar modelos Donation y Expense existen

### Dashboard Financiero
- [ ] Template creado
- [ ] Views con queries de stats
- [ ] Gráfico implementado (Chart.js)

### Donaciones
- [ ] Template lista con filtros
- [ ] Vista detail de donación
- [ ] Tests creados

### Gastos
- [ ] Templates (list, form, delete)
- [ ] Vistas CRUD
- [ ] Upload de receipt funcional
- [ ] Tests creados

### Stripe
- [ ] Settings configurados
- [ ] Página de donate pública
- [ ] View para crear Stripe Checkout Session
- [ ] Webhook handler
- [ ] Tests con Stripe test mode

### Reportes
- [ ] Template income statement
- [ ] Template donations by member
- [ ] Queries correctas

---

## Checklist de QA

### Dashboard
- [ ] Stats muestran valores correctos
- [ ] Gráfico renderiza correctamente
- [ ] Transacciones recientes ordenadas por fecha

### Donaciones
- [ ] Lista muestra todas las donaciones del tenant
- [ ] Filtros funcionan (estado, campaña, fecha)
- [ ] Búsqueda funciona
- [ ] Ver detalle de donación

### Gastos
- [ ] CRUD completo funciona
- [ ] Upload de receipt funciona
- [ ] Filtros funcionan

### Stripe
- [ ] Página donate accesible sin login
- [ ] Formulario redirecciona a Stripe
- [ ] Webhook actualiza status correctamente
- [ ] No procesa donaciones reales (test mode)

### Reportes
- [ ] Datos correctos en income statement
- [ ] Datos correctos en donations by member

### General
- [ ] Aislamiento de datos entre tenants

---

## Notas Técnicas

### Multi-tenancy
- Todas las queries deben filtrar por `tenant`
- No usar datos hardcoded

### Estilos
- Usar Bootstrap 5
- Gráficos con Chart.js o ApexCharts

### Stripe
- Usar Stripe Checkout (no crear custom form de card)
- Verificar webhook signature
- Logging de todos los eventos

### Tests
- pytest para unit tests
- Mock Stripe en tests unitarios
- Integration tests para webhooks

---

## Dependencias

- Django 5.x
- stripe Python library
- Chart.js (para gráficos)

---

**Documento creado**: Sprint 4 Plan  
**Última actualización**: Ver commit
