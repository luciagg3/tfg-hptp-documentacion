"""
Pipeline ASR — Transcripción con openai-whisper + Cálculo de WER/CER
TFG: Sistema de apoyo a la documentación clínica para HPTP
Hospital Virgen de la Arrixaca

Uso desde la terminal (estando en la misma carpeta que el script):

    Paso 1 - Generar referencias (solo una vez):
        python pipeline_asr_wer_openai.py --generar-referencias

    Paso 2 - Ejecutar el pipeline completo:
        python pipeline_asr_wer_openai.py

Estructura de carpetas esperada:
    06_modelo_asr/
    ├── grabaciones/
    │   ├── audio_dialogo_01_tts.mp3
    │   └── ...
    ├── dialogos_entrenamiento_v4_revisado.docx
    └── pipeline_asr_wer_openai.py
"""

import os
import sys
import json
import re
import whisper
from pathlib import Path
from jiwer import wer, cer


# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

MODELO_WHISPER = "small"   # Opciones: tiny, base, small, medium, large
IDIOMA         = "es"

# Rutas relativas a la carpeta donde está el script
DIR_AUDIO      = Path("grabaciones")
DIR_REFERENCIA = Path("transcripciones_referencia")
DIR_RESULTADOS = Path("resultados_real_small")
RUTA_DOCX      = Path("dialogos_entrenamiento_v4_revisado.docx")

DIALOGOS = [4, 6, 12]


# ─── UTILIDADES ───────────────────────────────────────────────────────────────

def normalizar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r'\b(médico|medico|paciente|hija|cuidadora|acompañante)\s*:', '', texto)
    texto = re.sub(r'[^\w\sáéíóúüñàèìòùâêîôûäëïöü]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def buscar_audio(n):
    for ext in ['.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.flac']:
        for sufijo in ['_tts', '_real', '']:
            ruta = DIR_AUDIO / f"audio_dialogo_{n:02d}{sufijo}{ext}"
            if ruta.exists():
                return ruta
    return None


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def ejecutar_pipeline():
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)

    print(f"\nCargando modelo Whisper '{MODELO_WHISPER}'...")
    print("(La primera vez descarga el modelo, puede tardar unos minutos)\n")
    modelo = whisper.load_model(MODELO_WHISPER)
    print("Modelo cargado.\n")

    resultados = {}
    wer_valores = []

    for n in DIALOGOS:
        print(f"{'─'*50}")
        print(f"DIÁLOGO {n:02d}")

        ruta_audio = buscar_audio(n)
        if not ruta_audio:
            print(f"  ⚠  Audio no encontrado — omitiendo")
            continue

        print(f"  Transcribiendo: {ruta_audio.name} ...")
        resultado = modelo.transcribe(str(ruta_audio), language=IDIOMA)
        transcripcion = resultado["text"].strip()
        print(f"  Idioma detectado: {resultado.get('language', 'es')}")

        ruta_salida = DIR_RESULTADOS / f"transcripcion_dialogo_{n:02d}_whisper.txt"
        ruta_salida.write_text(transcripcion, encoding="utf-8")
        print(f"  Guardada: {ruta_salida.name}")

        ruta_ref = DIR_REFERENCIA / f"referencia_dialogo_{n:02d}.txt"
        metricas = None
        if ruta_ref.exists():
            referencia = ruta_ref.read_text(encoding="utf-8")
            ref_norm   = normalizar_texto(referencia)
            hip_norm   = normalizar_texto(transcripcion)
            wer_val    = wer(ref_norm, hip_norm)
            cer_val    = cer(ref_norm, hip_norm)
            metricas   = {
                "wer_pct":          round(wer_val * 100, 2),
                "cer_pct":          round(cer_val * 100, 2),
                "palabras_ref":     len(ref_norm.split()),
                "palabras_whisper": len(hip_norm.split()),
            }
            wer_valores.append(wer_val)
            print(f"  WER: {metricas['wer_pct']}%  |  CER: {metricas['cer_pct']}%")
        else:
            print(f"  ⚠  Sin referencia — WER no calculado")

        resultados[f"dialogo_{n:02d}"] = {
            "audio":               ruta_audio.name,
            "tipo":                "tts" if "tts" in ruta_audio.name else "real",
            "transcripcion_inicio": transcripcion[:150] + "...",
            "metricas":            metricas,
        }

    print(f"\n{'═'*50}")
    print("RESUMEN FINAL")
    print(f"{'═'*50}")
    print(f"Diálogos evaluados: {len(wer_valores)}/{len(DIALOGOS)}")
    if wer_valores:
        wer_medio = sum(wer_valores) / len(wer_valores)
        print(f"WER medio:   {wer_medio*100:.2f}%")
        print(f"WER mínimo:  {min(wer_valores)*100:.2f}%")
        print(f"WER máximo:  {max(wer_valores)*100:.2f}%")
        resultados["_resumen"] = {
            "wer_medio_pct":      round(wer_medio * 100, 2),
            "wer_minimo_pct":     round(min(wer_valores) * 100, 2),
            "wer_maximo_pct":     round(max(wer_valores) * 100, 2),
            "dialogos_evaluados": len(wer_valores),
        }

    ruta_json = DIR_RESULTADOS / "resultados_wer.json"
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en: {ruta_json}")


# ─── GENERAR REFERENCIAS DESDE DOCX ──────────────────────────────────────────

def generar_referencias():
    try:
        from docx import Document
    except ImportError:
        print("Instala python-docx: python -m pip install python-docx")
        return

    if not RUTA_DOCX.exists():
        print(f"No se encuentra: {RUTA_DOCX}")
        print("Asegúrate de que el docx está en la misma carpeta que este script.")
        return

    DIR_REFERENCIA.mkdir(parents=True, exist_ok=True)

    doc = Document(RUTA_DOCX)
    patron_dialogo = re.compile(r'Di[áa]logo\s+(\d+)', re.IGNORECASE)
    patron_turno   = re.compile(
        r'(MÉDICO|PACIENTE|Médico|Paciente|ACOMPAÑANTE|HIJA|CUIDADORA)', re.IGNORECASE
    )

    dialogo_actual = None
    lineas = []

    for para in doc.paragraphs:
        texto = para.text.strip()
        if not texto:
            continue

        m = patron_dialogo.match(texto)
        if m:
            # Guardar diálogo anterior
            if dialogo_actual is not None and lineas:
                ruta = DIR_REFERENCIA / f"referencia_dialogo_{dialogo_actual:02d}.txt"
                ruta.write_text("\n".join(lineas), encoding="utf-8")
                print(f"  ✓ referencia_dialogo_{dialogo_actual:02d}.txt ({len(lineas)} turnos)")
            dialogo_actual = int(m.group(1))
            lineas = []
        elif dialogo_actual is not None and patron_turno.match(texto):
            lineas.append(texto)

    # Guardar último diálogo
    if dialogo_actual is not None and lineas:
        ruta = DIR_REFERENCIA / f"referencia_dialogo_{dialogo_actual:02d}.txt"
        ruta.write_text("\n".join(lineas), encoding="utf-8")
        print(f"  ✓ referencia_dialogo_{dialogo_actual:02d}.txt ({len(lineas)} turnos)")

    print(f"\nReferencias generadas en: {DIR_REFERENCIA}/")


# ─── ENTRADA ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--generar-referencias" in sys.argv:
        print("Generando archivos de referencia desde el docx...\n")
        generar_referencias()
    else:
        ejecutar_pipeline()
