# Sistema de apoyo a la documentación clínica con IA para hiperparatiroidismo primario

TFG — Ingeniería Biomédica. Hospital Clínico Universitario Virgen de la Arrixaca (HCUVA).

## Descripción

Sistema de dos módulos para automatizar la documentación clínica de consultas de
hiperparatiroidismo primario (HPTP):

1. **Módulo ASR** — transcripción automática del habla mediante Whisper (OpenAI),
   ejecutado en local.
2. **Módulo de extracción** — extracción estructurada de 18 ítems clínicos mediante
   un modelo de lenguaje de gran escala (LLM), a partir de un prompt diseñado
   específicamente para el dominio.

El sistema entrega un informe estructurado en formato JSON que el médico revisa
antes de incorporarlo a la historia clínica.

## Estructura del repositorio

- `01_schema/` — schema JSON de los 18 ítems clínicos
- `02_corpus_dialogos/` — corpus de 12 diálogos sintéticos, validados clínicamente
- `03_gold_standard/` — anotación de referencia de los 12 diálogos, auditada
- `04_modulo_asr/` — script de transcripción y cálculo de WER/CER
- `05_modulo_extraccion/` — prompts de extracción (v1 a v4) y resultados de evaluación
- `06_piloto_extraccion_iterativa/` — pipeline de verificación de negaciones y
  skill de validación del informe
- `07_analisis/` — scripts de cálculo de métricas (accuracy, precisión, recall, F1)

## Contexto académico

Proyecto desarrollado en colaboración con el servicio de Cirugía Endocrina del HCUVA.
La memoria completa del TFG describe con detalle la metodología, los experimentos
de evaluación y los resultados obtenidos.
