# Guía de Configuración de GitHub

Esta guía te ayudará a subir el proyecto SG Church a GitHub y configurar el MCP de GitHub para trabajar más eficientemente.

## ✅ Estado Actual

- ✅ Repositorio Git inicializado localmente
- ✅ Commit inicial creado con toda la documentación (26 archivos, 8,652 líneas)
- ✅ Rama principal: `main`
- ⏳ **Pendiente**: Crear repositorio en GitHub y hacer push

## 📋 Opción 1: Usando GitHub CLI (Recomendado)

### Instalar GitHub CLI

**Linux (Ubuntu/Debian):**
```bash
# Agregar repositorio de GitHub CLI
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y
```

**macOS:**
```bash
brew install gh
```

### Autenticar con GitHub
```bash
gh auth login
# Selecciona:
# - GitHub.com
# - HTTPS
# - Login with a web browser (pega el código de 8 dígitos)
```

### Crear el Repositorio y Hacer Push
```bash
cd /home/dw/workspace/SG_Church

# Crear repositorio público
gh repo create sg-church --public --source=. --remote=origin --push

# O crear repositorio privado
gh repo create sg-church --private --source=. --remote=origin --push
```

¡Listo! Tu código ya está en GitHub.

### Agregar Descripción y Temas
```bash
# Agregar descripción
gh repo edit --description "Free church management SaaS platform - Multi-tenant system for membership, donations, events, LMS, and more"

# Agregar topics (keywords)
gh repo edit --add-topic church,saas,nextjs,typescript,prisma,multi-tenant,nonprofit,donations,lms
```

---

## 📋 Opción 2: Manualmente (Interfaz Web de GitHub)

### Paso 1: Crear el Repositorio en GitHub

1. Ve a [GitHub](https://github.com)
2. Haz clic en el botón **"+"** en la esquina superior derecha
3. Selecciona **"New repository"**
4. Llena la información:
   - **Repository name**: `sg-church`
   - **Description**: `Free church management SaaS platform - Multi-tenant system`
   - **Visibility**: Public o Private (tu elección)
   - ⚠️ **NO** marques "Initialize with README" (ya tenemos uno)
   - ⚠️ **NO** agregues .gitignore ni license (ya los tenemos)
5. Haz clic en **"Create repository"**

### Paso 2: Conectar el Repositorio Local

Copia el URL del repositorio que acabas de crear. Luego ejecuta:

```bash
cd /home/dw/workspace/SG_Church

# Conectar con el repositorio remoto (reemplaza con tu URL)
git remote add origin https://github.com/TU_USUARIO/sg-church.git

# O si usas SSH:
git remote add origin git@github.com:TU_USUARIO/sg-church.git

# Verificar que se agregó correctamente
git remote -v
```

### Paso 3: Hacer Push del Código

```bash
# Push al repositorio remoto
git push -u origin main
```

### Paso 4: Configurar el Repositorio (Opcional)

1. Ve a tu repositorio en GitHub
2. Haz clic en **"Settings"**
3. En la sección **"About"** (lado derecho del repo):
   - Agrega descripción
   - Agrega topics: `church`, `saas`, `nextjs`, `typescript`, `prisma`, `multi-tenant`
   - Marca "Releases" y "Packages" si planeas usarlos

---

## 🔧 Instalar MCP de GitHub

El Model Context Protocol (MCP) de GitHub te permitirá interactuar con GitHub directamente desde VS Code con Copilot.

### Opción A: Instalación Automática (Si está disponible)

El MCP de GitHub puede estar disponible como servidor MCP oficial. Verifica en:

1. **VS Code Command Palette** (`Ctrl+Shift+P` o `Cmd+Shift+P`)
2. Escribe: `MCP: Install Server`
3. Busca: `GitHub MCP Server`
4. Si está disponible, instálalo

### Opción B: Instalación Manual del MCP Server

Si el MCP de GitHub no está disponible en el marketplace, puedes instalarlo manualmente:

1. **Instalar Node.js** (si no está instalado):
```bash
node --version  # Debe ser v20+
```

2. **Instalar el MCP Server de GitHub** (cuando esté disponible):
```bash
# El paquete oficial podría ser algo como:
npm install -g @modelcontextprotocol/server-github
# o
npx @modelcontextprotocol/server-github
```

3. **Configurar en VS Code**:

Crea/edita el archivo de configuración de MCP en VS Code:

**Linux:**
```bash
mkdir -p ~/.config/Code/User/
nano ~/.config/Code/User/mcp-settings.json
```

**macOS:**
```bash
mkdir -p ~/Library/Application\ Support/Code/User/
nano ~/Library/Application\ Support/Code/User/mcp-settings.json
```

**Agrega la configuración:**
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_TOKEN": "tu_token_de_github_aqui"
      }
    }
  }
}
```

4. **Crear GitHub Personal Access Token**:
   - Ve a [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens)
   - Haz clic en **"Generate new token (classic)"**
   - Selecciona los scopes necesarios:
     - `repo` (acceso completo a repositorios)
     - `workflow` (actualizar GitHub Actions)
     - `read:org` (leer información de organizaciones)
   - Copia el token y agrégalo en `mcp-settings.json`

5. **Reiniciar VS Code**

### Opción C: Usar GitHub Copilot Chat Directamente

GitHub Copilot Chat ya tiene integración básica con GitHub. Puedes usar comandos como:

```
@workspace ¿cuáles son los issues abiertos?
@github crea un issue para...
```

---

## 🚀 Comandos Git Útiles

### Ver el Estado del Repositorio
```bash
git status                    # Ver archivos modificados
git log --oneline -10        # Ver últimos 10 commits
git remote -v                # Ver repositorios remotos configurados
```

### Hacer Cambios y Subirlos
```bash
# Después de hacer cambios en archivos
git add .                    # Agregar todos los cambios
git add archivo.ts           # Agregar archivo específico
git commit -m "feat: descripción del cambio"
git push origin main         # Subir al repositorio
```

### Sincronizar Cambios
```bash
git pull origin main         # Traer cambios del repositorio remoto
git fetch origin            # Traer cambios sin hacer merge
```

### Crear y Cambiar Ramas
```bash
git branch feature/nueva-funcionalidad    # Crear nueva rama
git checkout feature/nueva-funcionalidad  # Cambiar a la rama

# O en un solo comando:
git checkout -b feature/nueva-funcionalidad

# Volver a main
git checkout main

# Fusionar rama
git merge feature/nueva-funcionalidad
```

---

## 📝 Convenciones de Commits (Conventional Commits)

Este proyecto usa Conventional Commits para mensajes claros y automación:

```bash
# Formato: <tipo>(<scope>): <descripción>

# Tipos de commits:
feat:     # Nueva funcionalidad
fix:      # Corrección de bug
docs:     # Cambios en documentación
style:    # Formato (no afecta código)
refactor: # Refactorización
test:     # Agregar/modificar tests
chore:    # Tareas de mantenimiento
perf:     # Mejora de performance
ci:       # Cambios en CI/CD

# Ejemplos:
git commit -m "feat(members): add member search functionality"
git commit -m "fix(donations): correct Stripe webhook validation"
git commit -m "docs(readme): update installation instructions"
git commit -m "refactor(auth): simplify NextAuth configuration"
```

---

## 🔒 Configurar Protección de Ramas (Opcional)

Para proteger la rama `main` y requerir pull requests:

1. Ve a tu repositorio en GitHub
2. **Settings** > **Branches**
3. **Add rule** para `main`:
   - ✅ Require pull request before merging
   - ✅ Require status checks to pass
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings

---

## 📊 Próximos Pasos Después del Push

1. **Configurar GitHub Actions** (CI/CD):
   - Crear `.github/workflows/ci.yml`
   - Tests automáticos en cada PR
   - Type checking y linting

2. **Configurar Protección de Secretos**:
   - **Settings** > **Secrets and variables** > **Actions**
   - Agregar secretos necesarios (Stripe keys, database URLs, etc.)

3. **Habilitar GitHub Discussions**:
   - **Settings** > **General** > **Features**
   - ✅ Discussions

4. **Configurar GitHub Projects** (Opcional):
   - Crear proyecto para trackear el desarrollo
   - Vincular issues al roadmap

5. **Invitar Colaboradores** (si aplica):
   - **Settings** > **Collaborators**
   - Agregar miembros del equipo

---

## ❓ Troubleshooting

### Error: "failed to push some refs"
```bash
# Si el remoto tiene cambios que no tienes localmente:
git pull origin main --rebase
git push origin main
```

### Error: "authentication failed"
```bash
# Si usas HTTPS, es posible que necesites un Personal Access Token en lugar de contraseña
# Genera uno en: https://github.com/settings/tokens
# Úsalo como contraseña cuando Git te lo pida
```

### Error: "remote origin already exists"
```bash
# Eliminar y volver a agregar:
git remote remove origin
git remote add origin https://github.com/TU_USUARIO/sg-church.git
```

---

## 📚 Recursos Adicionales

- [GitHub CLI Documentación](https://cli.github.com/manual/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

¿Necesitas ayuda con algún paso? ¡Pregunta sin problema!
