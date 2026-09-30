# Guía de Configuración de GitHub

## Estado Actual

El repositorio ya está publicado en GitHub:
`https://github.com/lcuper18/SG-Church`

Si estás leyendo esto porque vas a **transferir el proyecto a otra cuenta u
organización** (por ejemplo, la iglesia a la que se dona el proyecto), la
sección [Transferir el repositorio](#transferir-el-repositorio) es la que
te interesa. Si en cambio estás **empezando de cero con tu propio fork**,
seguí la sección [Crear tu propio repositorio](#crear-tu-propio-repositorio).

---

## Transferir el repositorio

Para mover la propiedad del repositorio existente a otra cuenta u
organización de GitHub, sin perder el historial, issues, ni estrellas:

1. En GitHub, andá a **Settings** del repositorio → sección **Danger Zone**
   → **Transfer ownership**
2. Escribí el nombre de la cuenta/organización destino
3. La organización destino debe aceptar la transferencia

Después de transferir, actualizá el remoto local:

```bash
git remote set-url origin https://github.com/<nueva-cuenta>/SG-Church.git
git remote -v   # confirmar que apunta al lugar correcto
```

Y revisá que no queden referencias a la cuenta/organización anterior en la
documentación (README.md, CONTRIBUTING.md, package metadata, etc.).

---

## Crear tu propio repositorio

### Opción 1: Con GitHub CLI

```bash
# Instalar GitHub CLI
brew install gh   # macOS
# o ver https://cli.github.com/ para Linux/Windows

# Autenticarse
gh auth login

# Desde la carpeta del proyecto
gh repo create SG-Church --public --source=. --remote=origin --push
```

### Opción 2: Manualmente

1. En GitHub, **New repository** — nombre `SG-Church`, sin inicializar con
   README/license/.gitignore (este repo ya los tiene)
2. Conectar el remoto local:

```bash
git remote add origin https://github.com/<tu-usuario>/SG-Church.git
git push -u origin main
```

---

## Comandos Git Útiles

```bash
# Estado
git status
git log --oneline -10
git remote -v

# Cambios
git add .
git commit -m "feat: descripción del cambio"
git push origin main

# Sincronizar
git pull origin main
git fetch origin

# Ramas
git checkout -b feature/nueva-funcionalidad
git checkout main
git merge feature/nueva-funcionalidad
```

## Convenciones de Commits

Este proyecto usa [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:     Nueva funcionalidad
fix:      Corrección de bug
docs:     Cambios en documentación
style:    Formato (no afecta código)
refactor: Refactorización
test:     Agregar/modificar tests
chore:    Mantenimiento
ci:       Cambios en CI/CD

git commit -m "feat(members): add member search functionality"
git commit -m "fix(donations): correct Stripe webhook validation"
```

## Protección de Ramas (recomendado antes de aceptar contribuciones externas)

**Settings** → **Branches** → regla para `main`:
- Require pull request before merging
- Require status checks to pass (el workflow `Django CI/CD` de
  `.github/workflows/django.yml`)
- Require conversation resolution before merging

## Troubleshooting

**"failed to push some refs"**
```bash
git pull origin main --rebase
git push origin main
```

**"authentication failed"** — con HTTPS necesitás un Personal Access Token
(no tu contraseña): generalo en
[github.com/settings/tokens](https://github.com/settings/tokens) y usalo
como contraseña cuando Git lo pida.

**"remote origin already exists"**
```bash
git remote remove origin
git remote add origin https://github.com/<usuario-o-org>/SG-Church.git
```
