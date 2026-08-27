# Handoff para la próxima IA — Documentación TT (2026-06-08)

Este documento complementa `PROMPT_documentador_tesis.md`. Resume qué se hizo,
el estado actual y qué falta, para continuar sin romper consistencia.

---

## 0. Lo esencial (leer primero)

- **Archivo de trabajo (ÚNICO que se edita):**
  `reportes/reporte_tt2_portocarrero_r_habid/DocumentoTecnicoTT_Habid_V1_copia_codex.docx`
- **Herramientas:** usar `./venv_311/Scripts/python.exe` con **python-docx**, **PyMuPDF (fitz)** y **PIL** (ya instalados).
- **El archivo se bloquea si está abierto en Word** → `PermissionError` al guardar.
  Si pasa: pedir al usuario que cierre Word y reintentar. (Pasa seguido, el usuario lo olvida 🙂.)
- **Backup ANTES de cada tanda de edición:**
  `cp ... DocumentoTecnicoTT_Habid_V1_backup_YYYY-MM-DD-HHMM_<tag>.docx`
- Tras editar, recordar al usuario: en Word **Ctrl+E → F9** ("Actualizar todo") para refrescar índices/TOC.
- **No inventar datos ni referencias.** Verificar contra el código (`src/`, `pages/`) o web con **fecha de consulta**.

## 1. Convenciones del documento

- Estilos de encabezado: `Título 1 TNR`, `Título 2 TNR`, `Título 3 TNR`, `Heading 4` (ya en Times New Roman). Cuerpo: `Normal` / `Texto Normal TNR`. **Fuente = Times New Roman** en todo.
- Citas estilo **IEEE numérico `[n]`**. Las referencias llegan hasta **[115]**.
- Los **captions** ("Ilustración N", "Tabla N") usan **campos SEQ** para el número:
  **NO reconstruir el párrafo del caption** (rompe la numeración). Editar solo runs de texto.
- Tablas de contenido ya están en TNR (se normalizaron 32 tablas).

## 2. Datos canónicos (usar SIEMPRE estos; no contradecir)

- **3 roles**: `estudiante`, `investigador`, `admin`. **El Dr. Sandino (careyes@ipn.mx) es un ADMIN**, NO un 4º actor/superusuario.
- **Dataset YOLO: 3,953 imágenes** (no 1,954).
- **F1 justo (LOO N=26):** Grooming **0.523** (estrategia Conditional), Thigmotaxis **0.636** (SimBA RF).
- **YOLO mAP50 = 0.995.**
- **Stack ML:** YOLO = PyTorch/Ultralytics · RF = SimBA/scikit-learn · LSTM = **Keras/TensorFlow** (NUNCA PyTorch).
- **Ultralytics = licencia AGPL-3.0** (copyleft; NO prohíbe lucro, exige liberar código o comprar licencia Enterprise).
- **Costos:** salario junior **$18,000 MXN/mes**; laptop **$60,000**; ANY-maze **USD $7,995** perpetua; tipo de cambio Banxico FIX 5-jun-2026 **$17.4755 MXN/USD**. COCOMO Custom = 30.3 PM × $18,000 = **$545,400**.

## 3. Numeración canónica de Casos de Uso (= tabla de requerimientos 4.1.1)

| CU | Nombre | RF/RN |
|---|---|---|
| CU1 | Registrar usuario | RF1, RN1, RN2 |
| CU2 | Iniciar sesión | RF2, RN3 |
| CU3 | Gestionar tratamientos | RF3, RN4 |
| CU4 | Registrar experimento | RF4, RN5 |
| CU5 | Configurar ROIs | RF5, RN6 |
| CU6 | Ejecutar análisis de video | RF6, RN7 |
| CU7 | Agrupar comportamientos | RF7 |
| CU8 | Editar tiempos conductuales | RF8, RN8 |
| CU9 | Exportar resultados | RF9 |
| CU10 | Consultar bitácora de auditoría | RF10, RN9 |

Las 10 fichas (formato de 20 filas) ya existen, en orden, en **5.2.2**.

## 4. Lo que se HIZO en esta sesión

**Capítulo 4:**
- 4.4.4 Factibilidad legal: agregada conclusión de viabilidad + referencias [108] LGPDPPSO, [109] LFDA, [110] Ultralytics; citas [2]/[15] insertadas; typo "comercial comercial" corregido.
- 4.4.3 Económica: corregidos costos con **fuentes reales + fecha de consulta** [111]-[115]; recalculado COCOMO ($909k→$545,400), Tablas 22/23/24; licencias reales (ANY-maze/EthoVision); quitado dato inventado de "$200k".
- 4.4.1: agregada **4.4.1.4 Capacidad técnica del equipo**; corregido "PyTorch"→scikit-learn/Keras (párr. 706).
- 4.3 Riesgos: reescrita la explicación de la fórmula **RE** (era "RE = P × I" con I en letras A–E, incoherente → ahora matriz semáforo); renumerado (faltaba 4.3.5); 1,954→3,953; LSTM PyTorch→Keras (párr. 687).
- Movidas a 4.1 las secciones de requerimientos; **4.1.4 Especificaciones de CU se movió al Cap. 5**.
- Estilo `Heading 4`→TNR; tablas→TNR.

**Capítulo 5 (reorganizado al modelo C4 de la rúbrica):**
- Estructura nueva: **5.1 Arquitectura · 5.2 Casos de uso (5.2.1 diagrama, 5.2.2 especificación) · 5.3 Diagramas de secuencia · 5.4 Diagramas de código (5.4.1 clases, 5.4.2 modelo de datos, 5.4.2.1 diccionario)**.
- 5.1: insertada **arquitectura nueva de 3 capas** (render del PDF a 300 DPI, 6") + texto reescrito (3 capas) + corregido "tesis"→"prueba t de Student".
- 5.2.1: **diagrama de casos de uso CORREGIDO** (el viejo tenía a "Sandino" como 4º actor y a IA/BD como externos — todo mal). Nuevo diagrama con 3 actores + generalización + include/extend, renderizado e insertado. Texto reescrito.
- 5.2.2: creadas/alineadas las **10 fichas CU1–CU10** (trazables a RF/RN), en orden.
- 5.3: limpiados los 14 captions (comillas curvas, Ilustr. 42 mal rotulada→"Proceso de registro", Ilustr. 52 dos puntos, errata "muestran").

**Capítulo 7:**
- Agregada **7.4 Justificación técnica** (7.4.1 Random Forest, 7.4.2 F1-Score, 7.4.3 valor agregado con F1 moderado) — pedido por un sinodal.
- Corregido estilo del encabezado 7.3.7.

## 5. Lo que FALTA (pendientes priorizados)

**Capítulo 5 (lo más grande):**
1. **5.1 — Sub-diagramas C4:** la rúbrica pide 5.1.1 Contexto, 5.1.2 Contenedores, 5.1.3 Componentes. Hoy 5.1 solo tiene el diagrama de 3 capas. **Crear los 3 diagramas C4.**
2. **5.2.2 Actores:** la rúbrica pide fichas de actores (Estudiante, Investigador, Administrador) ANTES de la especificación de CU. **No existen aún** (renumerar: actores = 5.2.2, especificación = 5.2.3).
3. **5.3 Diagramas de secuencia:**
   - (#2) **Fusionar** los diagramas duplicados por rol (login inv/admin, contraseña inv/admin, perfil inv/admin, cerrar sesión inv/admin) — los 3 roles comparten flujo.
   - (#3) **Crear los faltantes** del núcleo: CU3 tratamientos, CU4 experimento, CU5 ROIs, CU7 clasificación, CU8 editar tiempos.
   - Verificar que las imágenes existentes sean UML de secuencia correctas (abrir y revisar).
4. **5.4.2 Modelo de datos:** el diccionario tiene 6 tablas; **falta `behavior_edits`** (la 7ª, que sí aparece en la arquitectura). Agregar su descripción + tabla del diccionario.

**Otros:**
- El diagrama de casos de uso usa nombres sin códigos CU; opcional agregar CU0x a los óvalos (requiere re-render en plantuml.com).
- Verificar sección 7.2 (métricas) por si conviene reforzar la justificación de F1 (ya está bien cubierta).

## 6. Cómo insertar diagramas con calidad (receta probada)

1. Si es PDF (vectorial): `fitz.open(pdf)[0].get_pixmap(matrix=fitz.Matrix(300/72,300/72)).save(png)` → insertar con `run.add_picture(png, width=Inches(6))`.
2. Si es PlantUML: el usuario lo renderiza en plantuml.com y guarda la página (HTML). Extraer el `<svg>…</svg>`, **reemplazar `fill="#00000000"` por `fill="none"`** (fitz pinta el alfa-0 como negro), luego `fitz.open(svg)` → pixmap a escala 3.0 → PNG → insertar.
3. Reemplazar imagen existente: localizar el párrafo con `<a:blip>`, limpiar sus runs y `add_picture` el nuevo PNG; actualizar el caption (sin tocar el campo SEQ).

## 7. Estilo de trabajo del usuario (Habid)

- Prefiere **ir sección por sección, pasitos chicos**, con propuestas concretas. Evitar preguntas de alcance amplias (lo abruman).
- Mostrar siempre **antes/después** y aplicar tras su OK. Backups religiosos.
- Tono cercano, en español. Confía en que la IA tome decisiones razonables ("haz lo que creas mejor") pero quiere **coherencia total, sin contradicciones**.
