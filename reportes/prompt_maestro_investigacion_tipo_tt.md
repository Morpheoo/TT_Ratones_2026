# Prompt maestro para investigación tipo Trabajo Terminal

```text
Actúa como asesor experto de Trabajo Terminal / tesis de ingeniería en computación, con enfoque en documentación técnica formal, investigación aplicada, metodología de desarrollo, análisis de sistemas, validación experimental y redacción académica.

Necesito desarrollar una investigación completa con el mismo nivel de profundidad que un Trabajo Terminal. El tema es:

[TEMA DE LA INVESTIGACIÓN]

Contexto general:
[Describe el problema, institución, usuarios, tecnología o área de aplicación]

Objetivo general preliminar:
[Escribe el objetivo si ya existe; si no, propón uno]

Restricciones o condiciones:
[Tiempo, herramientas, datos disponibles, alcance, usuarios, plataforma, hardware, software, normas, etc.]

Quiero que construyas el documento con una estructura profesional y defendible ante sinodales/directores, organizada de la siguiente forma:

1. Resumen
- Redacta un resumen técnico claro.
- Incluye problema, propuesta, metodología, herramientas principales, resultados esperados y aportación.
- Evita frases genéricas.

2. Introducción
- Presenta el contexto del problema.
- Explica por qué es relevante.
- Conecta el problema con la solución propuesta.
- Mantén tono académico, técnico y natural.

3. Antecedentes
- Explica trabajos, métodos o sistemas previos relacionados.
- Distingue entre antecedentes científicos, tecnológicos y metodológicos.
- Señala limitaciones de enfoques anteriores.

4. Planteamiento del problema
- Formula el problema central con claridad.
- Describe síntomas, causas, consecuencias y población afectada.
- Evita redactarlo como una simple falta de software; debe verse como problema técnico, operativo o científico.

5. Propuesta de solución
- Describe la solución propuesta como sistema, metodología, prototipo, modelo o análisis.
- Explica sus componentes principales.
- Justifica por qué atiende el problema.

6. Objetivo general y objetivos específicos
- Redacta un objetivo general medible y alcanzable.
- Propón objetivos específicos ordenados por etapas: análisis, diseño, implementación, validación y documentación.
- Cada objetivo debe iniciar con verbo en infinitivo.

7. Justificación
- Justifica desde lo técnico, social/institucional, económico, operativo y académico.
- Explica beneficios concretos y aportación esperada.

8. Alcance y limitaciones
- Define qué sí incluye el proyecto.
- Define qué queda fuera.
- Distingue limitaciones técnicas, metodológicas, de datos, tiempo y validación.

9. Metodología
- Propón una metodología adecuada.
- Si aplica, usa espiral de Boehm, incremental, CRISP-DM, experimental, mixta o la más adecuada.
- Divide la metodología en fases.
- Explica entradas, actividades y salidas de cada fase.
- Incluye cómo se hará la validación.

10. Estado del arte
- Propón una revisión comparativa de trabajos relacionados.
- Para cada trabajo/sistema/método incluye:
  - Nombre
  - Año
  - Propósito
  - Tecnología o método
  - Ventajas
  - Limitaciones
  - Relación con esta investigación
- Cierra con una tabla comparativa.
- Explica la brecha que justifica el proyecto.

11. Marco teórico
- Desarrolla los conceptos fundamentales necesarios.
- No hagas definiciones aisladas; conecta cada concepto con el proyecto.
- Incluye fundamentos técnicos, científicos y metodológicos.
- Sugiere subsecciones relevantes según el tema.

12. Análisis
- Define requerimientos funcionales.
- Define requerimientos no funcionales.
- Define reglas de negocio o reglas operativas.
- Analiza herramientas candidatas.
- Justifica la selección tecnológica.
- Incluye análisis de riesgos.
- Incluye factibilidad tecnológica, operativa, económica y legal.
- Incluye sostenibilidad si aplica.

13. Diseño
- Propón arquitectura del sistema o modelo conceptual.
- Describe capas, módulos, componentes y flujo de información.
- Incluye diseño de base de datos si aplica.
- Incluye diccionario de datos si aplica.
- Incluye casos de uso principales.
- Propón diagramas UML necesarios, pero descríbelos primero en texto.

14. Desarrollo / Implementación
- Describe cómo se construye la solución.
- Divide por módulos.
- Explica herramientas, librerías, dependencias, configuración y entorno.
- Describe decisiones técnicas importantes.
- Incluye pipeline o flujo de procesamiento si aplica.
- Explica cómo se almacenan, procesan y visualizan los datos.

15. Pruebas y validación
- Propón pruebas funcionales.
- Propón pruebas técnicas.
- Propón pruebas de usuario o validación experta si aplica.
- Define métricas de evaluación.
- Incluye tablas para registrar pruebas.
- Distingue entre validación del software y validación del resultado científico/técnico.

16. Resultados
- Propón cómo presentar resultados preliminares y finales.
- Incluye tablas de métricas.
- Incluye evidencias visuales o capturas sugeridas.
- Explica cómo interpretar resultados sin exagerarlos.
- Señala campos que deben completarse con datos reales.

17. Conclusiones
- Redacta conclusiones ligadas a objetivos.
- Explica qué se logró, qué se validó y qué queda pendiente.
- No inventes resultados.
- Mantén tono profesional y defendible.

18. Trabajo futuro
- Propón mejoras realistas.
- Divide en mejoras técnicas, metodológicas, científicas y operativas.

19. Referencias
- Sugiere referencias académicas y técnicas confiables.
- Prioriza papers, documentación oficial, normas y libros reconocidos.
- Usa formato APA o IEEE, según convenga.

20. Anexos
- Sugiere anexos útiles:
  - Manual técnico
  - Manual de usuario
  - Evidencias de pruebas
  - Entrevistas
  - Tablas completas
  - Configuración de entorno
  - Capturas
  - Código relevante
  - Diagramas extendidos

Instrucciones de redacción:
- Escribe en español académico claro.
- Evita sonar genérico.
- Redacta como documento de ingeniería aplicada, no como ensayo.
- No inventes resultados experimentales.
- Cuando falte información, coloca campos como [Completar] y explica qué dato debe ir ahí.
- Mantén trazabilidad entre problema, objetivos, metodología, desarrollo y validación.
- Si una sección está débil, indícalo y propón cómo fortalecerla.
- Sugiere tablas cuando ayuden a defender mejor el proyecto.
- Cuida que todo sea defendible ante un comité académico.

Primero entrega:
1. Índice completo propuesto.
2. Breve explicación de cada capítulo.
3. Lista de información que necesitas de mí para redactarlo con precisión.
4. Riesgos o puntos débiles que podrían cuestionar los sinodales.
5. Plan de trabajo para construir el documento por etapas.

Además de redactar, actúa como sinodal crítico. Señala contradicciones, afirmaciones no demostradas, objetivos no medibles, secciones débiles, falta de evidencia, riesgos metodológicos y partes que podrían ser cuestionadas en defensa. Propón correcciones concretas.
```

