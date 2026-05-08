# Checkpoint M2: mirror augmentation

Fecha: 2026-05-06

## Objetivo

Probar mirror augmentation para duplicar dataset efectivo de Grooming/Thigmotaxis:

- 26 videos originales
- 26 mirrors sinteticos
- 52 videos efectivos para training

El mirror se considera valido porque el test de espejo previo no mostro bias direccional fuerte.

## Implementacion

Scripts tocados/creados:

- `src/scripts/mirror_augmentation.py`
  - Genera `*_mirror` desde bridges YOLO/SimBA.
  - Aplica `x_new = 1280 - x`.
  - Intercambia pares left/right:
    - `Ear_left` <-> `Ear_right`
    - `Lat_left` <-> `Lat_right`
    - bodyparts raw equivalentes cuando existen.
  - Copia targets humanos sin cambio.
  - Genera features SimBA y B-SOiD para mirrors.
- `src/scripts/restore_missing_simba_rois.py`
  - Fix Windows/PyTables: cierre explicito de HDF abierto antes de reescribir ROIs.
- `src/scripts/loo_full_bsoid.py`
  - LOO ahora remueve el target original y su `*_mirror` para evitar leakage.
  - B-SOiD tambien excluye ambos.

## Generacion de dataset mirror

Validaciones:

| Recurso | Originals | Mirrors | Total |
|---|---:|---:|---:|
| `targets_inserted/` | 26 | 26 | 52 |
| `features_extracted/` | 30 | 26 | 56 |
| `input_csv/` | 28 | 26 | 54 |
| `outlier_corrected_movement_location/` | 28 | 26 | 54 |
| `data/bsoid_features/` | 28 | 26 | 54 |
| `keypoints_yolo/*_mirror/` | - | 26 | 26 |

Notas:

- `features_extracted/` tiene 4 extras no usados por training: `R5C_mar24_2`, `R5YB15_01mar24`, y dos `*_grooming_lstm`.
- `retrain_simba_models.py --yolo --dry-run` confirma dataset efectivo: 52 videos.
- Targets espejo verificados: columnas `Grooming` y `Thigmotaxis` identicas al original.

## Validacion LOO blind real

Se corrieron 5 videos criticos. En cada LOO se excluyo original + mirror:

| Video | G SimBA F1 | G B-SOiD F1 | G Ensemble F1 | G Conditional F1 | T SimBA F1 |
|---|---:|---:|---:|---:|---:|
| R5DZ_01mar24_v2_trimmed_0_310 | 0.042 | 0.326 | 0.321 | 0.321 | 0.580 |
| R6B20_01mar24_trimmed_0_300 | 0.000 | 0.055 | 0.053 | 0.053 | 0.767 |
| R6DZ_01mar24_full | 0.000 | 0.685 | 0.685 | 0.685 | 0.472 |
| R6YB15_01mar24 | 0.000 | 0.351 | 0.327 | 0.327 | 0.587 |
| R7YB20_02mar24 | 0.000 | 0.243 | 0.235 | 0.235 | 0.697 |

Promedios:

| Metodo | F1 promedio |
|---|---:|
| G SimBA | 0.008 |
| G B-SOiD | 0.332 |
| G Ensemble | 0.324 |
| G Conditional | 0.324 |
| T SimBA | 0.621 |

## Comparacion con M1

En los mismos 5 videos criticos:

| Escenario | G Conditional F1 promedio |
|---|---:|
| M1, sin mirror, min_frames=250 simulado | 0.405 |
| M2, mirror LOO real, excluyendo original+mirror | 0.324 |

## Conclusion

Mirror augmentation queda implementado y dataset 52 queda disponible, pero NO se recomienda reentrenar el modelo productivo con mirrors todavia.

Motivo:

- En esta validacion critica, mirror augmentation no mejoro el LOO blind.
- SimBA Grooming siguio fallando casi completo en los 5 casos criticos.
- B-SOiD cambio mucho con mirrors: rescato R6DZ, pero colapso en R6B20 y bajo en R7YB20.

Interpretacion probable:

- El mirror duplica geometria, pero no agrega suficientes variantes reales de micro-movimiento de grooming.
- Para B-SOiD, duplicar frames espejo puede cambiar clustering/motifs y desestabilizar algunos rescates.

## Decision

- Mantener M1 `ensemble_conditional` como mejora activa.
- Dejar `mirror_augmentation.py` disponible como herramienta experimental.
- NO entrenar `Grooming.sav`/`Thigmotaxis.sav` productivos con los 52 videos hasta investigar mas.

## Seguridad

- `.leaveoneout.lock`: ausente al finalizar.
- `Grooming.sav`: restaurado, 281877693 bytes.
- `Thigmotaxis.sav`: restaurado, 299868733 bytes.
- Targets originales y mirrors de los 5 LOO: restaurados/presentes.

## Logs

- `logs/loo_full_mirror_R5DZ_01mar24_v2_trimmed_0_310.log`
- `logs/loo_full_mirror_R6B20_01mar24_trimmed_0_300.log`
- `logs/loo_full_mirror_R6DZ_01mar24_full.log`
- `logs/loo_full_mirror_R6YB15_01mar24.log`
- `logs/loo_full_mirror_R7YB20_02mar24.log`
