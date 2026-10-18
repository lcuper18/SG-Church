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

**Si pierdes el teléfono y los códigos:** un administrador de la iglesia no puede saltarse el paso; hay que
quitarla desde el servidor (`manage.py shell`, borrando los `Authenticator` del usuario). Por eso conviene
guardar los códigos de recuperación.

Desactivarla, ver los códigos o generar nuevos pide confirmar la contraseña si iniciaste sesión hace más
de 5 minutos.

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
