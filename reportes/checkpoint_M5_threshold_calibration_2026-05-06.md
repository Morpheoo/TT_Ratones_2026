# Checkpoint M5: threshold calibration

Fecha: 2026-05-06

## Objetivo

Validar Mejora #5: calibracion dinamica del threshold de Grooming por video.

Idea original:

- SimBA usa threshold fijo `0.41`.
- En videos criticos, SimBA a veces predice casi cero frames positivos.
- Si eso pasa, bajar automaticamente el threshold usando la distribucion de probabilidades del video.

## Implementacion experimental

Se modifico:

- `src/scripts/loo_full_bsoid.py`

Se agrego una metrica adicional llamada `dynamic`, solo para validacion LOO.

Regla implementada:

- Si SimBA predice `>= 250` frames Grooming con threshold `0.41`, mantener `0.41`.
- Si SimBA predice `< 250` frames, usar el percentil 97 de `proba_g`.
- El threshold dinamico queda limitado a `[0.20, 0.41]`.

Constantes:

- `DYNAMIC_MIN_FRAMES = 250`
- `DYNAMIC_LOW_QUANTILE = 0.97`
- `DYNAMIC_MIN_THRESHOLD = 0.20`
- `DYNAMIC_MAX_THRESHOLD = 0.41`

Importante: esta mejora no se integro al renderer productivo. Solo se probo dentro del LOO.

## Validacion

Se corrieron 5 videos criticos donde SimBA habia fallado y un smoke test adicional con cero Grooming real.

### Videos criticos

| Video | G SimBA F1 | G Dynamic F1 | G B-SOiD F1 | G Conditional F1 | Dynamic thr | Dynamic frames |
|---|---:|---:|---:|---:|---:|---:|
| R5DZ_01mar24_v2_trimmed_0_310 | 0.073 | 0.137 | 0.326 | 0.294 | 0.374 | 279 |
| R6B20_01mar24_trimmed_0_300 | 0.000 | 0.286 | 0.353 | 0.340 | 0.318 | 270 |
| R6DZ_01mar24_full | 0.000 | 0.060 | 0.685 | 0.684 | 0.200 | 96 |
| R6YB15_01mar24 | 0.020 | 0.113 | 0.351 | 0.324 | 0.276 | 280 |
| R7YB20_02mar24 | 0.000 | 0.122 | 0.243 | 0.228 | 0.208 | 280 |

Promedios:

| Metodo | F1 promedio |
|---|---:|
| SimBA | 0.019 |
| Dynamic threshold | 0.144 |
| Conditional ensemble | 0.374 |

### Smoke test con cero Grooming real

Video:

- `R8YB20_02mar24`

Ground truth:

- Grooming real: `0` frames

Resultado:

- SimBA ya generaba `873` falsos positivos.
- Dynamic mantuvo threshold `0.410` porque SimBA ya superaba `250` frames positivos.
- Dynamic no empeoro el caso, pero tampoco resolvio el falso positivo basal.

## Interpretacion

Dynamic threshold si rescata algo cuando SimBA colapsa:

- Mejora promedio en criticos: `0.019 -> 0.144`
- La mejora es real, pero insuficiente.

Sin embargo, sigue muy por debajo del ensemble condicional:

- Dynamic: `0.144`
- Conditional: `0.374`

Esto indica que bajar threshold no basta cuando el RF no separa bien el comportamiento. B-SOiD aporta informacion complementaria y sigue siendo la mejor mejora productiva.

## Decision

- No integrar dynamic threshold como default productivo.
- Mantenerlo como herramienta diagnostica dentro de `loo_full_bsoid.py`.
- Si B-SOiD no estuviera disponible, dynamic podria ser fallback experimental para videos donde SimBA predice casi cero Grooming.
- El pipeline productivo recomendado sigue siendo:
  - SimBA para Thigmotaxis.
  - Grooming con `ensemble_conditional` de M1.
  - LSTM rescue con thresholds corregidos (`0.11` rescue, `0.50` confident).

## Logs usados

- `logs/loo_full_dynamic_smoke_R5DZ_01mar24_v2_trimmed_0_310.log`
- `logs/loo_full_dynamic_smoke_R8YB20_02mar24.log`
- `logs/loo_full_dynamic_R6B20_01mar24_trimmed_0_300.log`
- `logs/loo_full_dynamic_R6DZ_01mar24_full.log`
- `logs/loo_full_dynamic_R6YB15_01mar24.log`
- `logs/loo_full_dynamic_R7YB20_02mar24.log`

