# Guía de Contribución - SG Church

¡Gracias por tu interés en contribuir a SG Church! Este proyecto existe para servir a iglesias de todos los tamaños de forma gratuita, y tu ayuda es muy valiosa.

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Puedo Contribuir](#cómo-puedo-contribuir)
- [Setup de Desarrollo](#setup-de-desarrollo)
- [Proceso de Desarrollo](#proceso-de-desarrollo)
- [Guías de Estilo](#guías-de-estilo)
- [Proceso de Pull Request](#proceso-de-pull-request)
- [Reportar Bugs](#reportar-bugs)
- [Sugerir Features](#sugerir-features)

---

## Código de Conducta

Este proyecto adhiere al [Contributor Covenant Code of Conduct](./CODE_OF_CONDUCT.md). Al participar, se espera que mantengas este código. Reportá comportamientos inaceptables abriendo un issue, o de forma privada usando el contacto de [SECURITY.md](./SECURITY.md).

---

## Cómo Puedo Contribuir

Hay muchas formas de contribuir a SG Church:

### 1. 🐛 Reportar Bugs

Si encontrás un bug:
- Buscá en los issues existentes del repositorio para ver si ya fue reportado
- Si no existe, creá uno nuevo con la información de [Reportar Bugs](#reportar-bugs)

### 2. 💡 Sugerir Features

Si tenés una idea para mejorar SG Church:
- Revisá [ROADMAP.md](./ROADMAP.md) para ver si ya está planificada
- Creá un issue describiendo la propuesta (ver [Sugerir Features](#sugerir-features))

### 3. 📝 Mejorar Documentación

La documentación siempre puede mejorar: corregir typos, agregar ejemplos,
aclarar pasos confusos, o mejorar la [FAQ](./docs/FAQ.md).

### 4. 💻 Contribuir Código

- **Bug fixes**: buscá issues etiquetados `bug`, comentá que vas a trabajar en él
- **Features**: buscá issues etiquetados `enhancement`, discutí el enfoque antes de escribir código
- **Tests**: agregar cobertura donde falte, o mejorar tests existentes

### 5. 🎨 Diseño y UX

Sugerencias de UI/UX, mockups, o auditorías de accesibilidad sobre los
templates Bootstrap 5 existentes.

---

## Setup de Desarrollo

### Prerequisitos

- **Python** 3.12+ ([descarga](https://www.python.org/downloads/))
- **PostgreSQL** 14+ ([descarga](https://www.postgresql.org/download/)) — no
  hace falta si solo vas a tocar el modo autoinstalable (SQLite)
- **Redis** 6+ ([descarga](https://redis.io/download)) — tampoco hace falta
  en modo autoinstalable
- **Docker** (opcional, pero la forma más rápida de levantar el proyecto —
  ver [QUICKSTART.md](./QUICKSTART.md))
- **Git**

### Clonar el Repositorio

```bash
# Fork el repositorio primero, luego:
git clone <url-de-tu-fork>
cd SG-Church

# Agregar el repositorio original como upstream
git remote add upstream <url-del-repositorio-original>
```

### Instalar Dependencias

```bash
pip install -r requirements-dev.txt
```

### Configurar y Levantar

Seguí [QUICKSTART.md](./QUICKSTART.md) — con Docker es un solo comando; sin
Docker, son los pasos habituales de Django (`.env`, `migrate`,
`create_tenant`, `runserver`).

### Verificar Setup

```bash
# Ejecutar tests
pytest

# Ejecutar linter
flake8 .

# Formatear (black e isort están configurados en pyproject.toml/setup.cfg)
black .
isort .
```

Si todo pasa, estás listo para contribuir.

---

## Proceso de Desarrollo

### 1. Sincronizar tu Fork

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

### 2. Crear Branch de Feature

```bash
git checkout -b feat/member-bulk-delete
git checkout -b fix/donation-receipt-email
git checkout -b docs/update-api-guide
```

**Tipos de branch**: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`

### 3. Hacer Cambios

- Seguí las [Guías de Estilo](#guías-de-estilo)
- Commits pequeños y descriptivos
- Escribí tests para tu código
- Actualizá documentación si corresponde

### 4. Commit Guidelines

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

feat(members): add bulk delete functionality
fix(donations): correct receipt email template
docs: update API documentation
refactor(auth): extract permission logic to utility
test(members): add unit tests for family relationships
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
**Scope** (opcional): módulo afectado (`members`, `finance`, `tenants`, etc.)

### 5. Push y Crear Pull Request

```bash
git push origin feat/member-bulk-delete
```

Y creá el Pull Request desde tu branch hacia `main` del repositorio
original.

---

## Guías de Estilo

### Python / Django

- **PEP 8**, aplicado con `flake8` (`max-line-length = 120`, ver `setup.cfg`)
- **Formateo**: `black` (config en `pyproject.toml`) e `isort`
  (`profile = django`, ver `setup.cfg`)
- **Type hints** donde aporten claridad, no obligatorios en todo el código
  existente
- **Docstrings** en funciones y clases no triviales
- **Vistas**: Class-Based Views para CRUD; función simple cuando alcanza
- **Formularios**: usar Django Forms para validación
- **API**: ViewSets de DRF, con `permission_classes` explícito — ver
  `core/permissions.py` para los de este proyecto (`CanManageFinance`,
  `CanManageMembers`)
- **Aislamiento por tenant**: cualquier vista o queryset nuevo sobre datos
  de una iglesia debe filtrar por `tenant` (normalmente
  `request.user.tenant`) — es el único mecanismo real de aislamiento entre
  iglesias en este proyecto (no hay separación por schema de base de datos)

```python
# Bien
def get_member(member_id: str) -> Member | None:
    """Retrieve a member by ID, scoped to the caller's tenant."""
    return Member.objects.filter(id=member_id, tenant=request.user.tenant).first()

# Mal — no filtra por tenant, expondría datos de otras iglesias
def get_member(member_id: str) -> Member | None:
    return Member.objects.filter(id=member_id).first()
```

### Naming Conventions

- **Python**: `snake_case` (`get_member_by_id`)
- **Clases/Modelos**: `PascalCase` (`Member`, `DonationView`)
- **Constantes**: `UPPER_SNAKE_CASE` (`MAX_UPLOAD_SIZE`)
- **Templates**: `snake_case` (`member_list.html`)

### Organización de una app Django

```
members/
├── models.py
├── views.py
├── forms.py
├── urls.py
├── admin.py
├── migrations/
├── api/
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
└── ...
```

### Orden de imports

```python
# 1. Stdlib
import os
import re
from datetime import datetime

# 2. Django
from django.db import models
from django.views.generic import ListView

# 3. Terceros
from rest_framework import viewsets

# 4. Locales
from core.mixins import ManageMembersRequiredMixin
from .models import Member
```

### Comentarios

Solo cuando el código por sí solo no explica el *por qué* (una restricción
no obvia, un workaround, una decisión que sorprendería a quien lo lea
después). Evitar comentarios que repiten lo que el código ya dice.

### Mensajes de Commit

- Primera línea: máximo ~72 caracteres, imperativo ("Add feature", no "Added feature")
- Cuerpo opcional con el *por qué* del cambio
- Referenciar issues: `Closes #123`

---

## Proceso de Pull Request

### Antes de Crear el PR

- [ ] Sync con `upstream/main` (sin conflictos)
- [ ] Tests pasan (`pytest`)
- [ ] Linter pasa (`flake8 .`, `black --check .`, `isort --check .`)
- [ ] Si cambiaste modelos, generaste y commiteaste las migraciones
      (`python manage.py makemigrations`)
- [ ] Documentación actualizada si aplica

### Crear el PR

Título descriptivo (mismo formato que los commits), y una descripción que
explique el *por qué* del cambio, no solo el *qué*. Si cierra un issue,
incluí `Closes #123`.

### Durante Code Review

- Respondé a los comentarios de forma constructiva
- Empujá nuevos commits al mismo branch en vez de hacer force-push
  (mantiene el historial de la revisión legible)

---

## Reportar Bugs

Antes de reportar: confirmá que es un bug (no una feature faltante) y que
se reproduce en la última versión de `main`.

Información útil al reportar:

```markdown
**Descripción del bug**
Qué pasó.

**Cómo reproducirlo**
1. Ir a '...'
2. Hacer click en '...'
3. Ver el error

**Comportamiento esperado**
Qué esperabas que pasara.

**Entorno**
- Modo: autoinstalable / SaaS
- OS / navegador
- Versión / commit
```

---

## Sugerir Features

1. Revisá [ROADMAP.md](./ROADMAP.md) — puede estar ya planificada
2. Abrí un issue describiendo el problema que resuelve, la solución
   propuesta, y alternativas que consideraste

---

## Recursos Adicionales

- [Architecture Guide](./ARCHITECTURE.md)
- [Database Schema](./DATABASE.md)
- [Tech Stack](./TECH_STACK.md)
- [API Documentation](./docs/API.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Django Docs](https://docs.djangoproject.com)
- [Django REST Framework Docs](https://www.django-rest-framework.org)

---

## Licencia

Al contribuir a SG Church, aceptás que tus contribuciones serán licenciadas bajo la [Licencia MIT](./LICENSE).

---

**¡Gracias por hacer de SG Church un mejor proyecto para servir a iglesias alrededor del mundo! 🙏**
