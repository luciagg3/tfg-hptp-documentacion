# Sistema de apoyo a la documentación clínica con IA para hiperparatiroidismo primario

Material completo del Trabajo de Fin de Grado del Grado en Ingeniería Biomédica de la Escuela Técnica Superior de Ingeniería Industrial (Universidad Politécnica de Cartagena), desarrollado en colaboración con la Unidad de Cirugía Endocrina del Servicio de Cirugía General del Hospital Clínico Universitario Virgen de la Arrixaca.

El sistema transcribe automáticamente una consulta médica y genera un informe clínico estructurado que el facultativo revisa y valida antes de incorporarlo a la documentación.

```
audio → Whisper (local) → transcripción → extracción con LLM → verificación → validación → revisión facultativa
```

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `01_schema` | Schema de extracción en JSON Schema, versiones v1 (16 ítems) y v2 (18 ítems) |
| `02_corpus_dialogos` | Los doce diálogos sintéticos del corpus de evaluación, validados clínicamente |
| `03_gold_standard` | Anotación de referencia campo a campo, en su versión auditada |
| `04_modulo_asr` | Scripts de transcripción con Whisper y cálculo de WER |
| `05_modulo_extraccion` | Prompt de extracción y scripts de las llamadas a la API |
| `06_pipeline_completo` | Orquestador extremo a extremo de las cuatro etapas |
| `07_analisis` | Scripts de evaluación, métricas y generación de figuras |
| `08_skill_validacion_informe` | Especificación de la capa de validación del informe generado |

## Cómo empezar

La ejecución completa del sistema se lanza desde `06_pipeline_completo`. Consulta el README de esa carpeta para los requisitos, la configuración de rutas y las opciones de ejecución.

## Requisitos

```bash
pip install openai-whisper anthropic jiwer
```

Se necesita además una clave propia de la API de Anthropic, definida en la variable de entorno `ANTHROPIC_API_KEY`. El repositorio no contiene ninguna credencial.

## Qué no está aquí

- **Los archivos de audio** de las grabaciones empleadas en la validación del módulo ASR. La voz constituye un dato personal por permitir la identificación indirecta de los participantes, por lo que no se publican. Sí se incluyen las transcripciones de referencia, que no contienen datos identificativos.
- **Datos de pacientes reales.** El corpus es enteramente sintético: ninguno de los diálogos corresponde a una consulta real ni a un paciente identificable.

## Licencia

⚠ *Elige y sustituye esta sección.* Para material académico reutilizable, lo habitual es MIT para el código y CC BY 4.0 para el corpus y las anotaciones. Si prefieres no licenciarlo explícitamente, indica al menos que el material se publica con fines académicos y de reproducibilidad.

## Cita

Si utilizas el corpus, el gold standard o la taxonomía de errores de este trabajo, cita la memoria del TFG:

> [Apellidos, Nombre] (2026). *Sistema de apoyo a la documentación clínica basado en inteligencia artificial: transcripción de voz y extracción automática de ítems relevantes para informes de hiperparatiroidismo primario.* Trabajo de Fin de Grado, Universidad Politécnica de Cartagena.
