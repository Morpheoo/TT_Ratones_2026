# Checkpoint M3: LSTM Grooming

Fecha: 2026-05-06

## Objetivo

Revisar Mejora #3: LSTM Grooming con 26 videos y su integracion al pipeline de rescue.

## Hallazgo principal

La documentacion base decia que la LSTM seguia entrenada con 11 videos, pero el `metadata.json` actual muestra otra cosa:

- `data/models/lstm_grooming_yolo/grooming_lstm.keras`
- Fecha del modelo: 2026-05-04 17:22
- Training videos: 21
- Validation videos: 5
- Total: 26 videos
- Keras/TensorFlow compatible en `venv_310`: TensorFlow 2.10.0, Keras 2.10.0

Conclusion: la LSTM ya estaba reentrenada con 26 videos. No se reemplazo el modelo.

## Fix aplicado

Se encontro un bug de integracion en `src/scripts/run_behavior_pipeline.py`.

Antes:

- El pipeline leia `best_threshold` de la metadata LSTM (`0.75`).
- Usaba ese mismo valor como:
  - `--lstm-rescue-threshold`
  - `--lstm-confident-threshold`

Eso hacia que el rescue fuera demasiado estricto. La lógica documentada en `02_PIPELINE_TECNICO.md` dice:

- rescue LSTM bajo: `0.11`
- LSTM confiada: `0.50`

Ahora:

- `--lstm-rescue-threshold 0.11`
- `--lstm-confident-threshold 0.50`

## Guardias de seguridad

Como M2 dejo mirrors disponibles en el repo, se agrego proteccion para evitar reentrenar SimBA con mirrors por accidente:

- `src/scripts/retrain_simba_models.py`
  - default: excluye `*_mirror.csv`
  - nuevo flag: `--include-mirrors`
  - dry-run normal confirma dataset efectivo: 26 videos
  - dry-run con `--include-mirrors` permite 52 videos

Tambien se actualizo:

- `src/scripts/train_grooming_lstm.py`
  - default: excluye `*_mirror`
  - nuevo flag: `--include-mirrors`

## Evaluacion rápida de la LSTM actual

Se corrio inferencia LSTM actual sobre 5 videos criticos y se comparo contra las etiquetas humanas reales.

Importante: esto NO es blind, porque la LSTM actual ya vio estos videos en training/validación. Sirve para confirmar que el backend LSTM reconoce bien esos patrones cuando esta disponible.

| Video | GT Grooming | LSTM frames @0.75 | P @0.75 | R @0.75 | F1 @0.75 | F1 @0.50 | F1 @0.11 |
|---|---:|---:|---:|---:|---:|---:|---:|
| R5DZ_01mar24_v2_trimmed_0_310 | 203 | 198 | 0.874 | 0.852 | 0.863 | 0.830 | 0.743 |
| R6B20_01mar24_trimmed_0_300 | 619 | 632 | 0.978 | 0.998 | 0.988 | 0.963 | 0.899 |
| R6DZ_01mar24_full | 698 | 681 | 0.984 | 0.960 | 0.972 | 0.965 | 0.919 |
| R6YB15_01mar24 | 572 | 564 | 0.991 | 0.977 | 0.984 | 0.976 | 0.899 |
| R7YB20_02mar24 | 903 | 882 | 1.000 | 0.977 | 0.988 | 0.997 | 0.966 |

Promedios:

| Threshold | F1 promedio |
|---:|---:|
| 0.75 | 0.959 |
| 0.50 | 0.946 |
| 0.11 | 0.885 |

## Interpretacion

La LSTM no parece ser el cuello de botella en videos ya conocidos. El problema era que el pipeline la estaba usando con thresholds demasiado altos para rescue.

Con el fix, la LSTM vuelve a cumplir su rol:

- rescate moderado cuando RF titubea y LSTM >= 0.11
- rescate fuerte cuando LSTM >= 0.50 aunque RF este bajo

## Decision

- No reentrenar/reemplazar LSTM ahora, porque ya esta en versión 26 videos.
- Mantener el fix de integracion del pipeline.
- Si se quiere medir aporte blind real de LSTM, crear después un LOO específico LSTM; no se hizo en este checkpoint.

## Archivos de evaluacion

- `logs/m3_lstm/R5DZ_01mar24_v2_trimmed_0_310_grooming_lstm.csv`
- `logs/m3_lstm/R6B20_01mar24_trimmed_0_300_grooming_lstm.csv`
- `logs/m3_lstm/R6DZ_01mar24_full_grooming_lstm.csv`
- `logs/m3_lstm/R6YB15_01mar24_grooming_lstm.csv`
- `logs/m3_lstm/R7YB20_02mar24_grooming_lstm.csv`

## Seguridad

- No se reemplazo `grooming_lstm.keras`.
- `Grooming.sav` y `Thigmotaxis.sav` no fueron modificados.
- Mirrors quedan presentes, pero excluidos por default en retraining SimBA/LSTM.
