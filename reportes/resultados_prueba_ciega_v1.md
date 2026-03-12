# Análisis Clínico (Prueba Ciega: DZP-R1)

**Modelo Utilizado:** Clasificador inicial Random Forest base (`Thigmotaxis.sav`)
**Anotador Experto:** Chavi
**Video:** `DZP-R1_THIGMO_TEST_CIEGO.mp4` (Bajo efecto de Diacepam)

## Evaluación Visual Cualitativa

El modelo fue puesto a prueba bajo un escenario de validación ciega (un dataset inédito de 5 minutos, post-anotación original del proyecto piloto). Los resultados del escrutinio clínico son los siguientes:

### Métricas Observadas:
*   ✅ **Eventos correctamente detectados (True Positives):** 8
*   ❌ **Falsos positivos (False Positives):** 14
*   🛑 **Falsos negativos (False Negatives - Omitidos por la IA):** 6
*   ⏱️ **Micro-detecciones (Problema de Continuidad Temporal):** 4 eventos donde el clasificador "parpadeó" (la barra se activaba solo $\sim$0.2s y la predicción se cortaba abruptamente a pesar de que la conducta se mantenía).

### Conclusión Preliminar y Diagnóstico Técino
El modelo tiene una capacidad inferencial **decente** para detectar la naturaleza de la Tigmotaxis, pero exhibe demasiada varianza (alta tasa de falsos positivos) y carece de suavidad temporal (micro-detecciones o cortes). 

### Solución Algorítmica Propuesta para la Siguiente Iteración Computacional:
El diagnóstico indica que el "umbral rígido" framewise actual y la carencia de los hiperparámetros *Minimum bout lengths* en nuestro modelo actual están provocando este nerviosismo (flickering). 

**Para contrarrestarlo (en el siguiente entrenamiento en SimBA):**
1. Añadir masivamente experiencia en los 5 nuevos videos (`C1`, `C56`, `C7`, `C2`, `R5DZ`) etiquetados a mano como planeamos. ¡Esto desplomará esos 14 falsos positivos!
2. Configuraremos un hiperparámetro en SimBA llamado `Min. Bout Length` (Duración Mínima de Evento) a $\sim$ 0.3 segundos. Esto eliminará mágicamente esas detecciones defectuosas de "0.2s" forzando a la red a dictaminar una conducta sólo si hay consistencia temporal, mejorando la métrica.
