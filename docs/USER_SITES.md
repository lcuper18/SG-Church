# Sedes

Si tu iglesia se reúne en más de un lugar, registra cada uno como una **sede**. Así cada culto o
evento queda ligado al lugar donde ocurrió y se pueden sacar los datos de cada sede por separado.

## Crear y administrar sedes

1. Menú de usuario → **Sedes** (solo administradores).
2. **Nueva sede**: nombre, dirección y teléfono. El orden solo cambia cómo se listan.
3. Toda iglesia tiene una **sede principal** («Sede principal», puedes renombrarla). No se puede
   eliminar ni desactivar.
4. **Desactivar** una sede la oculta al crear eventos o miembros, pero conserva sus reportes.
5. **Eliminar** va a la papelera, y solo si no tiene eventos próximos ni miembros asignados; si los
   tiene, el sistema te dice cuáles y te sugiere desactivarla.

## Qué cambia en el resto del sistema

Mientras tengas **una sola sede activa** no verás nada de esto. Con dos o más:

- **Eventos**: al crear o editar eliges la sede (por omisión, la principal); el listado tiene una
  columna y un filtro de sede, y el detalle la muestra.
- **Miembros**: campo opcional **Sede de origen** (dónde asiste normalmente), con filtro en el
  listado y columna en la exportación. No limita nada: los eventos y la asistencia llevan su propia sede.
- **Importar CSV**: columna opcional **Sede**; si el nombre no existe, la persona se importa sin
  sede y la revisión te lo avisa.
- **API**: `/api/v1/sites/` (solo lectura), y los eventos y miembros incluyen su sede.

La asistencia **por sede** (resúmenes, visitas) llega en la siguiente entrega.
