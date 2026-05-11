# Checkpoint: Edicion manual de tiempos con auditoria

Fecha: 2026-05-10

## Resumen

Se agrego la capacidad de que admins e investigadores corrijan
manualmente los tiempos conductuales (Abiertos, Cerrados, Grooming,
Thigmotaxis) directamente sobre el panel de detalle de cada
experimento en la pagina 05, con auditoria completa, posibilidad de
revertir y propagacion automatica al modulo de Comparacion (Excel).

Motivacion: el modelo no es 100% preciso en Grooming/Thigmotaxis
(F1 LOO blind 0.45-0.60). Esta feature permite al investigador
corregir falsos positivos/negativos sin tocar la salida cruda del
modelo, y deja trazabilidad para defensa de tesis.

---

## Cambios

### 1. Nueva tabla `behavior_edits` (audit log)

Migracion: `src/db/migrations/add_behavior_edits.py`
Helper: `src/db/behavior_edits.py`

Schema:
```
behavior_edits (
    id, experiment_id (FK -> experiments, ON DELETE CASCADE),
    edited_by (FK -> users, ON DELETE SET NULL),
    edited_by_email, edited_role, edited_at,
    before_open, before_closed, before_grooming, before_thigmo,
    after_open,  after_closed,  after_grooming,  after_thigmo,
    note
)
```

Indice por `(experiment_id, edited_at DESC)` para query rapido del
historial.

La tabla se auto-crea en runtime via
`ensure_behavior_edits_schema(conn)` la primera vez que la pagina 05
se abre, asi que no requiere correr la migracion manualmente.

API publica del helper:
- `record_behavior_edit(...)` — guarda snapshot before/after.
- `load_behavior_edits(engine, exp_id)` — devuelve lista, mas reciente primero.
- `revert_to_before_snapshot(engine, edit_id)` — restaura `analysis_results`
  al estado anterior a esa edicion.

### 2. Refactor de la pagina 05 (`pages/05_Resultados_y_Estadisticas.py`)

**`update_experiment_times()`** ahora:
- Captura el snapshot before del UPDATE.
- Hace el UPDATE en `analysis_results`.
- Inserta un registro en `behavior_edits` con quien (email + rol),
  cuando, before/after y nota.
- Toda la operacion en una transaccion.

**Panel de detalle (`render_detail_panel`)**:
- Por defecto muestra las KPIs grandes como antes (Abiertos 261.6s, etc.).
- Toggle "Editar" en la parte superior derecha de la seccion
  "Tiempos del registro" — solo visible si el usuario tiene permiso
  (admin o investigador dueño).
- Al activar el toggle, las KPIs se reemplazan por `number_input`
  para los 4 tiempos editables (Centro queda read-only porque se
  deriva de la trayectoria).
- Campo "Motivo de la edicion" obligatorio para activar el boton
  Guardar — refuerza trazabilidad.
- Al guardar: toggle se apaga, KPIs vuelven con el nuevo valor,
  badge naranja arriba avisa que hubo edicion.

**Badge de edicion** (`render_edit_badge`): bloque compacto naranja
arriba del panel cuando hay ediciones. Muestra autor, rol, timestamp
y total de ediciones.

**Historial completo** (`render_edit_history_expander`): expander
al final del panel, debajo del heatmap. Cada edicion muestra
`before -> after` con flechas, autor, rol, timestamp, nota y boton
"Revertir" (admin siempre, investigador solo en sus experimentos).

### 3. Fix critico: `coalesce_metric` ahora prefiere DB sobre CSV

Bug detectado: tras editar Grooming de 6.2s a 26.2s, la metrica grande
seguia mostrando 6.2s aunque el historial tenia el cambio correcto.

Causa: `coalesce_metric` priorizaba el valor calculado del trayectoria
CSV (output crudo del modelo) sobre el valor del DB.

Fix: invertir prioridad. El DB (`analysis_results`) es la fuente de
verdad para metricas mostradas. Solo cae al CSV si el DB esta vacio
(legacy / sin procesar).

Las gráficas de "Conductas acumuladas" siguen mostrando la curva del
CSV original — intencional, ahi se enseña el comportamiento crudo del
modelo.

### 4. Fix bonus: `init_db()` parser tolerante a comments

Pre-existente, descubierto en este checkpoint. `schema.sql` termina con
un bloque `-- NOTA: ...` despues del ultimo `;`. El parser hacia
`split(";")` y enviaba esos comentarios a psycopg2, que los recibia
como query vacia y rompia el boot.

Fix en `src/db/connection.py`: nuevo helper `_has_executable_sql()`
filtra statements que solo contienen lineas vacias o comentarios `--`.

---

## Permisos

| Rol | Ve KPIs | Ve toggle Editar | Edita propios | Edita ajenos | Revierte propios | Revierte ajenos | Ve historial |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| admin | sí | sí | sí | sí | sí | sí | sí |
| investigador | sí | sí (solo en propios) | sí | no | sí | no | sí |
| estudiante | sí | no | no | no | no | no | sí (read-only) |

---

## Export al modulo de Comparacion (pagina 06)

Sin cambios necesarios. La pagina 06 ya lee directamente de
`analysis_results.grooming_duration`, `time_open_arms`, etc.
(lineas 105-109, 339-340, 527-528 de `pages/06_Comparacion.py`).
Como `update_experiment_times()` actualiza esa misma tabla, los
Excels generados por la comparacion siempre reflejan la version mas
reciente — incluyendo correcciones manuales.

---

## Como probar

1. Reiniciar la app (recoge el fix del init_db).
2. Login como investigador → seleccionar un experimento propio en
   pagina 05 → activar toggle "Editar" → modificar Grooming →
   escribir motivo → Guardar.
3. La metrica grande debe actualizarse al nuevo valor.
4. Badge naranja debe aparecer arriba del panel.
5. Expander al final muestra la edicion con before -> after.
6. Login como admin → mismo experimento → boton "Revertir" → el
   tiempo vuelve al original.
7. Pagina 06 → exportar Excel → verificar que el valor editado
   aparece en la hoja "Datos_Individuales".

---

## Archivos tocados

Nuevos:
- `src/db/migrations/add_behavior_edits.py`
- `src/db/behavior_edits.py`
- `reportes/checkpoint_edicion_manual_tiempos_2026-05-10.md` (este)

Modificados:
- `pages/05_Resultados_y_Estadisticas.py` (refactor panel detalle +
  update_experiment_times con audit + nuevas funciones de UI)
- `src/db/connection.py` (parser tolerante a comments en init_db)

---

## Pendientes posibles (no bloqueantes)

- Editar tambien rangos temporales de eventos individuales (no solo
  totales). Hoy si el modelo perdio un evento de grooming, el
  investigador puede ajustar el total pero no marcar exactamente
  donde estuvo. Requeriria editor sobre el timelog CSV.
- Exportar tambien el historial de ediciones en una hoja extra del
  Excel de comparacion, para defensa metodologica.
- Mostrar diff visual en el video multimodal cuando hubo ediciones
  (overlay tipo "tiempo corregido manualmente: X -> Y").
