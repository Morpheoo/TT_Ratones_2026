# Checkpoint M1: validacion ensemble_conditional

Fecha: 2026-05-05

## Objetivo

Validar la Mejora #1 (`ensemble_conditional`) con LOO blind real en 5 videos criticos donde SimBA Grooming falla.

## Videos evaluados

| Video | G SimBA F1 | G B-SOiD F1 | G Ensemble OR F1 | G Conditional F1 | SimBA frames positivos | T SimBA F1 |
|---|---:|---:|---:|---:|---:|---:|
| R5DZ_01mar24_v2_trimmed_0_310 | 0.060 | 0.394 | 0.333 | 0.060 | 232 | 0.603 |
| R6B20_01mar24_trimmed_0_300 | 0.000 | 0.832 | 0.813 | 0.813 | 35 | 0.736 |
| R6DZ_01mar24_full | 0.000 | 0.198 | 0.197 | 0.197 | 3 | 0.511 |
| R6YB15_01mar24 | 0.026 | 0.290 | 0.274 | 0.026 | 121 | 0.526 |
| R7YB20_02mar24 | 0.000 | 0.431 | 0.408 | 0.408 | 69 | 0.755 |

## Promedios

| Metodo Grooming | F1 promedio |
|---|---:|
| SimBA solo | 0.017 |
| B-SOiD solo | 0.429 |
| Ensemble OR siempre | 0.405 |
| Conditional actual, min_frames=100 | 0.301 |

## Resultado

La mejora queda confirmada por criterio inicial:

- `G_conditional` sube de 0.017 a 0.301 en estos 5 casos criticos.
- Ganancia absoluta: +0.284 F1.
- Criterio pedido: >= +0.10 F1.

Pero el detector de catastrofe con `CONDITIONAL_SIMBA_MIN_FRAMES = 100` es demasiado conservador. Falla en dos videos:

- R5DZ: SimBA predice 232 frames, pero F1 real es 0.060.
- R6YB15: SimBA predice 121 frames, pero F1 real es 0.026.

En ambos, SimBA produjo suficientes frames para no activar B-SOiD, pero esos frames fueron mayormente falsos positivos o no cubrieron el grooming real.

## Simulacion de umbral

Con los mismos resultados LOO:

| Min frames | Videos rescatados | F1 promedio conditional |
|---:|---|---:|
| 100 | R6B20, R6DZ, R7YB20 | 0.301 |
| 125-200 | R6B20, R6DZ, R6YB15, R7YB20 | 0.350 |
| 250 | Los 5 videos criticos | 0.405 |

## Simulacion extendida: 13 LOO disponibles

Se agregaron los 13 LOO ya existentes en `logs/` para estimar el umbral sin reentrenar. Para cada video se uso:

- `SimBA frames positivos = TP + FP` de SimBA.
- Si `SimBA frames positivos < min_frames`, conditional usa Ensemble OR.
- Si no, conditional usa SimBA solo.

| Estrategia | F1 promedio Grooming |
|---|---:|
| SimBA solo | 0.445 |
| B-SOiD solo | 0.377 |
| Ensemble OR siempre | 0.563 |
| Conditional min_frames=100 | 0.554 |
| Conditional min_frames=125 | 0.573 |
| Conditional min_frames=150 | 0.581 |
| Conditional min_frames=200 | 0.581 |
| Conditional min_frames=250 | 0.602 |
| Conditional min_frames=300 | 0.573 |
| Conditional min_frames=400 | 0.588 |

El mejor umbral simple fue `min_frames=250`: mejora el promedio 0.445 -> 0.602 y supera a Ensemble OR siempre.

## Recomendacion

Promover `bsoid_simba_min_frames` a 250 como default del codigo. No se modifico `project_config.ini`.

Cambios aplicados:

- `src/scripts/generar_video_prediccion.py`: default `--bsoid-simba-min-frames 250`.
- `src/scripts/bsoid_evaluate.py`: `CONDITIONAL_SIMBA_MIN_FRAMES = 250`.
- `src/scripts/loo_full_bsoid.py`: `CONDITIONAL_SIMBA_MIN_FRAMES = 250`.

Validacion tecnica: `py_compile` OK.

## Seguridad

- `.leaveoneout.lock`: ausente al finalizar.
- `Grooming.sav`: restaurado, 281877693 bytes.
- `Thigmotaxis.sav`: restaurado, 299868733 bytes.
- Targets CSV de los 5 videos: presentes/restaurados.

## Logs

- `logs/loo_full_conditional_R5DZ_01mar24_v2_trimmed_0_310.log`
- `logs/loo_full_conditional_R6B20_01mar24_trimmed_0_300.log`
- `logs/loo_full_conditional_R6DZ_01mar24_full.log`
- `logs/loo_full_conditional_R6YB15_01mar24.log`
- `logs/loo_full_conditional_R7YB20_02mar24.log`
