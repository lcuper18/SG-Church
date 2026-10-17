# Guía de Usuario: Gestión de Miembros

Aprende a gestionar los miembros de tu iglesia usando SG Church.

---

## 📋 Introducción

El módulo de **Miembros** te permite:

- ✅ Registrar nuevos miembros
- ✅ Actualizar información de contacto
- ✅ Organizar miembros en familias
- ✅ Etiquetar miembros para segmentación
- ✅ Buscar y filtrar miembros

---

## 👥 Ver Lista de Miembros

### Acceder al módulo

1. Inicia sesión en SG Church
2. Click en **"Miembros"** en el menú principal
3. Verás la lista de todos los miembros

### Información mostrada

| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre completo del miembro |
| Email | Correo electrónico |
| Teléfono | Número de teléfono |
| Estado | Activo, Inactivo, Pendiente |
| Fecha de ingreso | Cuándo se unió |

### Filtrar miembros

Puedes filtrar por:

- **Estado**: Activo, Inactivo, Pendiente
- **Familia**: Miembros de una familia específica
- **Etiquetas**: Miembros con etiquetas específicas

### Buscar miembros

Usa el campo de **búsqueda** para encontrar miembros por:
- Nombre
- Apellido
- Email
- Teléfono

---

## ➕ Agregar Nuevo Miembro

### Paso a paso

1. En la lista de miembros, click en **"+ Nuevo Miembro"**
2. Completa el formulario:

#### Información Personal

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| Nombre | ✅ | Primer nombre |
| Apellido | ✅ | Apellido |
| Email | ✅ | Correo electrónico |
| Teléfono | Opcional | Número con código de país |
| Fecha de nacimiento | Opcional | Para envíos de cumpleaños |

#### Información de Dirección

| Campo | Opcional |
|-------|-----------|
| Dirección | Dirección completa |
| Ciudad | Ciudad de residencia |
| Provincia/Estado | Provincia o estado |
| Código Postal | Código postal |
| País | País de residencia |

#### Información Adicional

| Campo | Descripción |
|-------|-------------|
| Estado | Activo, Inactivo, Pendiente |
| Fecha de ingreso | Cuándo se unió a la iglesia |
| Notas | Información adicional relevante |

3. Click en **"Guardar"**

---

## ✏️ Editar Miembro

### Desde la lista

1. Busca el miembro en la lista
2. Click en el **nombre** del miembro
3. En la página de detalle, click en **"Editar"**
4. Modifica los campos necesarios
5. Click en **"Guardar cambios"**

### Cambios comunes

- **Actualizar teléfono**: Para mantener comunicación
- **Cambiar estado**: Si el miembro ya no asiste
- **Agregar notas**: Información importante sobre el miembro

---

## 👨‍👩‍👧‍👦 Gestionar Familias

### ¿Qué es una familia?

Una **Familia** agrupa miembros que viven en el mismo hogar.

### Crear una familia

1. Ve al módulo **"Familias"**
2. Click en **"+ Nueva Familia"**
3. Ingresa el **nombre de la familia** (ej: "Familia Pérez")
4. Click en **"Guardar"**

### Agregar miembros a una familia

1. Edita el miembro
2. En el campo **"Familia"**, selecciona la familia
3. Guarda los cambios

### Ver miembros de una familia

1. Ve a **"Familias"**
2. Click en el nombre de la familia
3. Verás todos los miembros asociados

---

## 🏷️ Usar Etiquetas

### ¿Qué son las etiquetas?

Las **etiquetas** te permiten categorizar miembros:
- Voluntario
- Líder de célula
- Tesorero
- Equipo de bienvenida
- Y cualquier otra que necesites

### Crear una etiqueta

1. Ve al módulo **"Etiquetas"**
2. Click en **"+ Nueva Etiqueta"**
3. Ingresa:
   - **Nombre**: ej: "Voluntario"
   - **Color**: Elige un color para identificar
4. Click en **"Guardar"**

### Asignar etiquetas a miembros

1. Edita el miembro
2. En el campo **"Etiquetas"**, selecciona las etiquetas
3. Guarda los cambios

### Filtrar por etiqueta

1. En la lista de miembros
2. Selecciona la etiqueta en el filtro
3. Verás solo miembros con esa etiqueta

---

## 📤 Exportar Miembros

### Identificación (cédula)

En el formulario de miembro hay un campo con el nombre del documento de tu país (Cédula, DNI,
RUT...; puedes cambiarlo en Configuración). Sirve para distinguir a dos personas que se llaman
igual: **no se puede repetir** dentro de la iglesia (`1-1234-5678` y `112345678` cuentan como
el mismo número) y puede quedar vacío, por ejemplo para menores. Se puede buscar por él, se
incluye al exportar e importar CSV y aparece en los certificados.

### Exportar a CSV

1. En la lista de miembros (con los filtros que quieras aplicar)
2. Click en **"Exportar CSV"**
3. El archivo se descarga y abre bien en Excel

---

## 📥 Importar Miembros desde CSV

Sirve para pasar a tu iglesia una lista que ya tienes en Excel o Google Sheets.

1. En la lista de miembros, click en **"Importar CSV"**
2. Descarga la **plantilla** (o usa un archivo exportado desde aquí) y llénala. Solo
   *Nombre* y *Apellido* son obligatorios
3. Guarda la hoja como **CSV** y súbela
4. Elige qué hacer con quienes ya existen: **omitirlos** o **actualizar** sus datos
5. Click en **"Revisar archivo"**: verás cuántos son nuevos, cuántos se omiten y cuáles
   filas tienen errores (con el número de fila y el motivo). **Todavía no se guarda nada**
6. Si todo está bien, click en **"Importar N personas"**

**Cosas que conviene saber**

- Las filas con errores no se importan; las demás sí. Corrige el archivo y vuelve a subirlo
  si quieres incluirlas (las ya importadas se omitirán como duplicadas)
- Los duplicados se detectan por correo electrónico, o por nombre más teléfono o fecha de nacimiento
- Las familias y etiquetas que no existan se crean; las que existen se reutilizan
- Las fechas pueden ir como `2026-10-17` o `17/10/2026`; *Bautizado* como Sí o No
- Las notas pastorales solo las importan administradores y pastores
- Todo queda en la **Bitácora** como una sola línea de importación

---

## 🗑️ Eliminar Miembro

### Consideraciones importantes

⚠️ **Antes de eliminar**:
- El miembro va a la **Papelera** (menú de usuario → Papelera, solo administradores), donde
  puedes restaurarlo con sus cursos e inscripciones; se borra definitivamente a los 90 días
- Sus donaciones se conservan siempre
- Considera cambiar el estado a "Inactivo" si solo dejó de asistir

### Cómo eliminar

1. En la lista de miembros
2. Click en el miembro
3. Click en **"Eliminar"**
4. Confirma la eliminación

---

## 📊 Estados de Miembro

| Estado | Descripción |
|--------|-------------|
| **Activo** | Miembro regular que asiste activamente |
| **Inactivo** | Miembro que ya no asiste |
| **Pendiente** | En proceso de verificación |

---

## 💡 Mejores Prácticas

### Registrar miembros

1. **Información completa**: Llena todos los campos posibles
2. **Verificación**: Confirma el email y teléfono
3. **Etiquetas**: Usa etiquetas para organización

### Mantener actualizado

1. **Revisión mensual**: Verifica datos antiguos
2. **Actualizar estado**: Cambia a "Inactivo" si ya no asiste
3. **Notas**: Documenta información relevante

### Comunicación

1. **Grupos de emails**: Usa etiquetas para enviar correos
2. **Segmentación**: Agrupa por familia o rol

---

## ❓ Preguntas Frecuentes

### ¿Cómo busco un miembro específico?

Usa el campo de búsqueda en la lista de miembros. Puedes buscar por nombre, email o teléfono.

### ¿Puedo importar miembros desde Excel?

Sí, contacta a soporte para configurar importación masiva.

### ¿Un miembro puede pertenecer a dos familias?

No, cada miembro pertenece a una sola familia.

### ¿Pueden los miembros actualizar su propia información?

Próximamente estará disponible el portal de miembros.

### ¿Cómo veo el historial de un miembro?

En la página de detalle del miembro, toda la información se muestra allí.

---

## 📞 Soporte

¿Necesitas ayuda adicional?

- **Email**: soporte@sgchurch.com
- **WhatsApp**: +506 8888 8888

---

**Documento creado**: Marzo 2026  
**Versión**: 1.0
