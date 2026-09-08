# 06 — Pipeline completo extremo a extremo

Orquestador que encadena los dos módulos del sistema y la capa de validación en una sola ejecución:

```
audio → Whisper → transcripción → extracción → verificación → validación → informe
```

Sustituye al paso manual de llevar la transcripción generada por el módulo ASR a la carpeta del módulo de extracción.

## Requisitos

```bash
pip install openai-whisper anthropic jiwer
```

Y una clave de la API de Anthropic en la variable de entorno `ANTHROPIC_API_KEY`:

```powershell
# PowerShell
$env:ANTHROPIC_API_KEY="tu_clave"
```

```cmd
:: CMD
set ANTHROPIC_API_KEY=tu_clave
```

La clave no se almacena en ningún archivo del repositorio. Cada usuario debe emplear la suya.

## Uso

```bash
# Comprobar que el entorno está listo, sin gastar API
python pipeline_completo.py --check

# Ejecución completa sobre un diálogo del corpus
python pipeline_completo.py --dialogo 04

# Reutilizar una transcripción existente (omite Whisper, ~2 min en lugar de ~12)
python pipeline_completo.py --dialogo 04 --sin-asr

# Sobre un audio externo al corpus
python pipeline_completo.py --audio "ruta/al/audio.mp3"
```

## Salida

Cada ejecución crea una carpeta con marca temporal en `resultados_pipeline/`:

| Archivo | Contenido |
| --- | --- |
| `1_transcripcion.txt` | Salida de Whisper (o transcripción de referencia si se usó `--sin-asr`) |
| `2_extraccion.json` | Informe estructurado tras la primera llamada |
| `3_verificado.json` | Informe tras la verificación de negaciones |
| `4_informe_validacion.txt` | Avisos de la capa de validación |
| `resumen.json` | Tokens, coste por etapa, duración y WER si hay referencia disponible |

## Configuración de rutas

El bloque `RUTAS` del script apunta a la estructura de trabajo local empleada durante el desarrollo. Antes de ejecutarlo, ajusta estas cuatro variables a la ubicación real de los archivos:

| Variable | Contenido esperado |
| --- | --- |
| `DIR_GRABACIONES` | Audios `audio_dialogo_NN_tts.mp3` / `_real.mp3` |
| `DIR_REFERENCIA` | Transcripciones de referencia `referencia_dialogo_NN.txt` |
| `RUTA_PROMPT_V4` | `prompt_extraccion_v4.txt` (carpeta `05_modulo_extraccion`) |
| `RUTA_SKILL` | `skill_validacion_informe_hptp.md` (carpeta `08_skill_validacion_informe`) |

## Notas

- Whisper se ejecuta en local: el audio no sale del equipo en ningún momento. Las llamadas de extracción, verificación y validación sí transmiten la transcripción a la API del proveedor.
- La transcripción con el modelo `medium` sobre CPU tarda unos 10 minutos por consulta. La primera ejecución descarga el modelo.
- Los precios por token están fijados en el bloque de configuración y corresponden a la tarifa vigente durante el desarrollo. Verifícalos antes de interpretar los costes que reporta el script.
- Los audios no forman parte de este repositorio, por las razones expuestas en la memoria del trabajo.
