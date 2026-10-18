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

## Qué no hace (todavía)

- No hay anuncios personalizados ni envíos a una etiqueta (llegan en la siguiente fase).
- Todavía no existe un enlace para darse de baja de los correos.
