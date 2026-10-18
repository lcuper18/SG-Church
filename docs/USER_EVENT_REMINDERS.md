# Recordatorios automáticos de eventos

Cada evento avisa por correo a las **personas inscritas**, sin que tengas que hacer nada:

- **1 día antes** de la hora de inicio de ese evento.
- **1 hora antes** de la hora de inicio.

Se calcula con la hora de cada evento (un culto a las 5 p. m. avisa a las 5 p. m. del día anterior y
a las 4 p. m.; uno a las 7 p. m. avisa a las 7 p. m. y a las 6 p. m.), en la zona horaria de la iglesia.
En iglesias con varias sedes el correo incluye el nombre y la dirección de la sede.

## Quién lo recibe

- Solo quien está **inscrito** en el evento y tiene un correo válido. No se avisa a toda la iglesia.
- Quien se inscribe **dentro** del plazo (por ejemplo, 30 minutos antes de empezar) no recibe el aviso de
  «1 día antes»: ya sabe del evento. Lo mismo si el evento se creó con menos de un día de anticipación.
- Los correos de prueba (`@demo.sgchurch.test`, `example.com`…) se omiten.

## Apagarlos en un evento

En el formulario del evento, desmarca **Recordatorios automáticos**. El detalle muestra si están
activados. Un evento cancelado (inactivo) tampoco envía recordatorios.

## Detalles útiles

- Nunca se envía el mismo aviso dos veces, aunque el servidor se reinicie.
- Si el servidor estuvo caído, los avisos pendientes salen al volver, hasta 6 horas tarde (el de 1 día) o
  30 minutos tarde (el de 1 hora). Pasado eso se descartan para no avisar tarde.
- Si cambias la fecha u hora de un evento en **más de una hora**, sus recordatorios se reprograman de nuevo
  para la nueva hora.
- Requiere que el servicio `beat` y el correo (SMTP) estén configurados; ver `docs/DEPLOYMENT.md`.

## Anuncios personalizados

Además de los automáticos, quien gestiona el evento puede enviar su propio mensaje desde la tarjeta
**Anuncios** del detalle del evento:

1. Escribe el **asunto** y el **mensaje**.
2. Elige los **destinatarios**: las personas **inscritas** al evento o los miembros con una **etiqueta**
   (no hace falta que estén inscritos).
3. Elige **enviar ahora** o **programar** una fecha y hora (siempre antes de que termine el evento).

Reglas:

- Un anuncio programado se puede **cancelar** hasta que salga. Después ya no.
- Máximo **1000 destinatarios** por anuncio; solo cuenta gente con correo válido. Si no hay nadie, no se crea.
- Solo para eventos activos que no han terminado. Si el evento se cancela antes de la hora programada,
  el anuncio se omite.
- Cada persona recibe un anuncio una sola vez, aunque el servidor se interrumpa a mitad del envío.
- Los programados salen en el siguiente ciclo de 5 minutos tras su hora.

## Darse de baja

Los recordatorios y anuncios llevan al pie un enlace **«Dejar de recibir recordatorios y anuncios»** (y
los programas de correo muestran su botón «Cancelar suscripción»). La persona entra sin iniciar sesión,
confirma, y puede arrepentirse desde la misma página.

- Deja de recibir **solo** recordatorios y anuncios. Los correos sobre sus inscripciones, cancelaciones,
  certificados, recibos y su cuenta se siguen enviando.
- También se puede marcar desde **Mi ficha → Actualizar mis datos de contacto**, o por el personal en la
  ficha del miembro (útil si lo pidió por teléfono). En la ficha aparece «Sin avisos por correo».
- Quien se dio de baja no cuenta como destinatario de un anuncio.
- El enlace solo aparece si el servidor tiene configurada `SITE_URL`.
