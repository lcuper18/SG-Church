# API REST

Documentación de la API REST de SG Church (Django REST Framework).

## Base URL

Todos los endpoints cuelgan de `/api/v1/`. Por ejemplo, en un desarrollo
local: `http://localhost:8000/api/v1/members/`.

## Autenticación

La API usa autenticación por **sesión de Django** (`SessionAuthentication`),
no tokens ni JWT — está pensada para el propio frontend de la app, no como
API pública para integraciones de terceros todavía. Para llamarla necesitás
una sesión autenticada (cookie de sesión) y, en peticiones que mutan datos
(`POST`/`PUT`/`PATCH`/`DELETE`), el header `X-CSRFToken` con el valor de la
cookie `csrftoken`.

Una API pública con autenticación por token/API key es una posible mejora
futura (ver ROADMAP.md, Fase 4 — API pública).

## Aislamiento por iglesia

Todo endpoint filtra automáticamente por la iglesia (`tenant`) del usuario
autenticado — nunca vas a ver ni poder tocar datos de otra iglesia a través
de la API, salvo que seas superusuario de Django.

## Permisos por rol

- **`/members/`, `/families/`, `/tags/`**: cualquier usuario autenticado
  puede leer (`GET`); crear/editar/borrar requiere rol `admin`, `pastor` o
  `volunteer` (ver `User.can_manage_members`).
- **`/donations/`, `/expenses/`, `/campaigns/`**: requieren rol `admin` o
  `treasurer` para cualquier operación, incluida la lectura (ver
  `User.can_manage_finance`).
- **`/notifications/`**: cada usuario solo ve sus propias notificaciones.

Un usuario autenticado sin el rol requerido recibe `403 Forbidden`; un
usuario no autenticado recibe `401`/`403` según el endpoint.

## Recursos

### Members — `/api/v1/members/`

CRUD estándar (`GET`, `POST`, `GET /{id}/`, `PATCH /{id}/`, `DELETE /{id}/`)
más:
- `GET /members/stats/` — conteos por estado (miembro, visitante, asistente, inactivo)
- `GET /members/search/?q=...` — búsqueda por nombre/email/teléfono (máx. 10 resultados)

Filtros de búsqueda/orden: `?search=`, `?ordering=` (por `last_name`,
`first_name`, `created_at`).

### Families — `/api/v1/families/`

CRUD estándar. Filtros de búsqueda: `?search=` (nombre, jefe de familia).

### Tags — `/api/v1/tags/`

CRUD estándar. Filtro de búsqueda: `?search=` (nombre).

### Donations — `/api/v1/donations/`

CRUD estándar más:
- `GET /donations/stats/?start_date=&end_date=` — totales por campaña,
  cantidad de donaciones completadas/pendientes
- `GET /donations/by_member/?member_id=...` — donaciones de un miembro

### Expenses — `/api/v1/expenses/`

CRUD estándar más:
- `GET /expenses/stats/?start_date=&end_date=` — totales por categoría y
  por estado (pendiente/aprobado/pagado)

### Campaigns — `/api/v1/campaigns/`

CRUD estándar más:
- `GET /campaigns/active/` — solo campañas con estado `active`

### Notifications — `/api/v1/notifications/`

CRUD estándar, siempre acotado a las notificaciones del usuario autenticado.

## Webhooks

### Stripe — `/api/v1/webhooks/stripe/`

`POST` público (exento de CSRF — la firma de Stripe es el mecanismo de
confianza). Maneja `checkout.session.completed` e `invoice.payment_failed`.
Requiere `STRIPE_WEBHOOK_SECRET` configurado para validar la firma.
