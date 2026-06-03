# Checkpoint M4: bagging SimBA Grooming

Fecha: 2026-05-06

## Objetivo

Validar Mejora #4: bagging multi-semilla para SimBA Grooming.

Idea original:

- Entrenar varios RandomForest con semillas distintas.
- Promediar `predict_proba`.
- Reducir varianza y evitar catastrofes LOO donde SimBA predice casi cero grooming.

## Implementacion experimental

Se creo:

- `src/scripts/loo_bagging_grooming.py`

Características:

- No toca modelos productivos.
- Usa las mismas features del `Grooming.sav` productivo (`model.feature_names_in_`, 242 columnas).
- Excluye el video held-out y su `*_mirror`.
- Excluye mirrors por default.
- Entrena `RandomForestClassifier` sklearn con hiperparametros equivalentes al combo:
  - `criterion="entropy"`
  - `max_features="sqrt"`
  - `min_samples_leaf=10`
  - `class_weight="balanced"`
  - `bootstrap=True`
- Promedia probabilidades de N modelos.
- Threshold operativo: `0.41`.
- Smoothing: 15 frames.

## Validación

Primero se hizo smoke test:

- `R6DZ_01mar24_full`
- 2 modelos x 50 arboles
- Resultado: F1 = 0.000

Luego se corrieron 5 videos criticos con:

- 3 modelos
- 100 arboles por modelo
- total 300 arboles
- `n_jobs=-1`

| Video | Bagging F1 | Pred frames | Observacion |
|---|---:|---:|---|
| R5DZ_01mar24_v2_trimmed_0_310 | 0.051 | 232 | Parecido a SimBA baseline, no rescata |
| R6B20_01mar24_trimmed_0_300 | 0.000 | 28 | Catastrofe persiste |
| R6DZ_01mar24_full | 0.000 | 5 | Catastrofe persiste |
| R6YB15_01mar24 | 0.000 | 118 | Catastrofe persiste |
| R7YB20_02mar24 | 0.000 | 52 | Catastrofe persiste |

Promedio F1 Grooming en 5 criticos:

| Metodo | F1 promedio |
|---|---:|
| SimBA baseline M1 en mismos 5 | 0.017 |
| Bagging experimental 3x100 | 0.010 |

## Interpretacion

Bagging no resuelve el problema raiz en estos videos.

El patron observado:

- Los modelos individuales tambien dan F1 ~0.
- Promediar no recupera grooming si todos los RF ven el mismo espacio de features como negativo.
- Esto sugiere que el fallo no es varianza de semilla, sino falta de separabilidad/generalizacion de las features RF para ciertos estilos de grooming.

## Decision

- No integrar bagging al pipeline productivo.
- Mantener `src/scripts/loo_bagging_grooming.py` como herramienta diagnostica.
- Continuar a Mejora #5: calibracion de threshold por video.

## Seguridad

- No se modifico `Grooming.sav`.
- No se modifico `Thigmotaxis.sav`.
- `.leaveoneout.lock`: liberado.
- Mirrors siguen excluidos por default en retraining.

## Logs

- `logs/loo_bagging_smoke_R6DZ_01mar24_full.log`
- `logs/loo_bagging_R5DZ_3x100.log`
- `logs/loo_bagging_R6B20_01mar24_trimmed_0_300_3x100.log`
- `logs/loo_bagging_R6DZ_01mar24_full_3x100.log`
- `logs/loo_bagging_R6YB15_01mar24_3x100.log`
- `logs/loo_bagging_R7YB20_02mar24_3x100.log`
