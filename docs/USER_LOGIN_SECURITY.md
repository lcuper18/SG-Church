# Seguridad del inicio de sesión

## Verificación en dos pasos (recomendada)

Además de la contraseña se pide un código de 6 dígitos que genera una aplicación en tu teléfono
(Google Authenticator, Microsoft Authenticator, Aegis, 1Password…). Si alguien conoce tu contraseña pero no
tiene tu teléfono, no puede entrar. Es opcional para cada usuario; a administradores, pastores y tesoreros
(quienes ven datos privados y dinero) se les recuerda en el panel principal.

**Activarla:** menú de tu usuario → **Seguridad (2 pasos)** → *Activar*. Escanea el código QR con la
aplicación e ingresa el código que muestra. Al activarla se generan **códigos de recuperación**: guárdalos
(descárgalos o imprímelos) en un lugar seguro. Cada uno sirve **una sola vez** si pierdes el teléfono.

**Entrar:** contraseña como siempre y, después, el código de la aplicación (o un código de recuperación).

**La verificación en dos pasos no necesita correo ni internet en el teléfono:** el código lo calcula la
aplicación sola.

**Si pierdes el teléfono:** entra con uno de tus **códigos de recuperación**. Si tampoco los tienes, un
administrador de tu iglesia abre **Usuarios**, pulsa el escudo con la X junto a tu nombre
(«Quitar su verificación en dos pasos») y vuelves a entrar solo con tu contraseña para configurarla de nuevo.
Queda anotado en la bitácora. Un administrador no puede quitarse la suya: debe usar sus códigos o pedírselo a
otro administrador.

Desactivarla, ver los códigos o generar nuevos pide confirmar la contraseña si iniciaste sesión hace más
de 5 minutos.

## Olvidé mi contraseña

- **Por correo:** en «¿Olvidaste tu contraseña?» pones tu correo y recibes un enlace para elegir una nueva.
  **Esto requiere que el servidor tenga correo configurado** (ver `docs/DEPLOYMENT.md`, «Correo»); sin eso el
  mensaje solo se imprime en el registro del servidor y nunca llega a nadie.
- **Con ayuda de un administrador (no necesita correo):** en **Usuarios**, el botón de la llave junto a la
  persona genera un **enlace de restablecimiento** que el administrador le pasa por WhatsApp o en persona. La
  persona lo abre, elige su propia contraseña (el administrador nunca la ve), y el enlace funciona 3 días o
  hasta que se use. Queda anotado en la bitácora. Cualquiera que tenga el enlace puede cambiar esa contraseña,
  así que no se publica en grupos.
- **Si eres el único administrador** y olvidaste tu contraseña sin correo configurado, hay que hacerlo desde el
  servidor: `docker compose exec web python manage.py changepassword tu@correo.com`.

## Límites contra adivinar contraseñas

- **5 contraseñas incorrectas** para un mismo correo en 5 minutos bloquean ese correo por unos minutos
  (aunque se acierte después). Los intentos desde direcciones distintas cuentan para el mismo correo.
- **10 intentos fallidos por minuto** desde una misma dirección.
- **Códigos de dos pasos** equivocados también tienen límite.
- **Restablecer contraseña:** máximo 3 correos por minuto para una dirección y 10 por minuto desde una misma
  conexión. Al pasarse aparece una página de «Demasiados intentos».

## Para quien administra el servidor

- Los contadores viven en Redis (base 1) para que los comparta cada proceso web. Si cambias de Redis,
  define `CACHE_URL`.
- `TRUSTED_PROXY_COUNT` es el número de proxies delante de la aplicación (1 con Traefik/nginx, el valor
  por defecto en producción). Si fuera incorrecto, los límites por dirección contarían la del proxy y
  bloquearían a todos a la vez, o serían fáciles de evadir.
- Si Redis se cae, el inicio de sesión también falla (igual que las tareas en segundo plano).

## Qué no hace (todavía)

- No se puede **exigir** la verificación en dos pasos a toda la iglesia; hoy es voluntaria.
- Solo aplicación de autenticación y códigos de recuperación (no llaves físicas ni SMS).
