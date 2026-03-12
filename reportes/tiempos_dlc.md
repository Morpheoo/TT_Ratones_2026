# Registro Semántico de Tiempos de Cómputo (DeepLabCut + GPU)

**Fecha de Ejecución:** 23 de febrero de 2026
**Hardware Utilizado:** NVIDIA GeForce RTX 5070 Ti (Laptop GPU)
**Arquitectura Topológica:** *SuperAnimal TopViewMouse* (ResNet50) - 8 Body Parts

Este documento lleva el registro oficializado de los tiempos reales de *Inferencia Masiva* requerida para consolidar el modelo supervisado de ansiedad (Tigmotaxis). Es fundamental para reportar los tiempos computacionales metodológicos dentro del Trabajo Terminal (TT).

## Inferencia de Video: `DZP-R1.mov`
* **Especificaciones del video:** 5 minutos (11,105 fotogramas totales), resolución 720p sin recortar, 30 FPS.
* **Tiempo Total Estimado de Extracción de Posturas (H5):** ~4 horas y 20 minutos.
* **Tasa de Rendimiento Constante:** ~1.2 a 1.4 fotogramas procesados por segundo, utilizando tamaños de lotes estables (`batch_size=16`).

--- 
**(Este archivo será actualizado a medida que progresemos con los demás videos: C1, C2, C56, C7, R5B20 y R5DZ)*.*
