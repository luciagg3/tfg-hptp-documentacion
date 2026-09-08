"""
Pipeline completo extremo a extremo — TFG HPTP
Audio → Whisper → transcripción → extracción → verificación → validación → informe

Ubicación esperada:  C:\\tfe_hptp\\07_evaluacion\\pipeline_completo.py

Uso desde la terminal (situada en 07_evaluacion):

    # 1. Comprobar que todo está en su sitio, SIN gastar API
    python pipeline_completo.py --check

    # 2. Ejecutar el pipeline completo sobre un diálogo
    python pipeline_completo.py --dialogo 04

    # 3. Reutilizar una transcripción ya generada (salta Whisper, más rápido)
    python pipeline_completo.py --dialogo 04 --sin-asr

    # 4. Sobre un audio cualquiera fuera del corpus
    python pipeline_completo.py --audio "C:\\ruta\\a\\mi_audio.mp3"

Requiere:  pip install openai-whisper anthropic jiwer
Clave:     $env:ANTHROPIC_API_KEY="tu_clave"      (PowerShell)
"""

import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# ─── RUTAS ────────────────────────────────────────────────────────────────────
# Relativas a 07_evaluacion. No hace falta mover ningún archivo.

RAIZ = Path(__file__).resolve().parent
DIR_ASR = RAIZ.parent / "06_modelo_asr"
DIR_EXT = RAIZ.parent / "05_modulo_extraccion" / "paquete_piloto_v2"

DIR_GRABACIONES = DIR_ASR / "grabaciones"
DIR_REFERENCIA = DIR_ASR / "transcripciones_referencia"
RUTA_PROMPT_V4 = DIR_EXT / "prompt_extraccion_v4.txt"
RUTA_SKILL = DIR_EXT / "skill_validacion_informe_hptp.md"

DIR_SALIDA = RAIZ / "resultados_pipeline"

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

MODELO_WHISPER = "medium"
IDIOMA = "es"

MODELO_LLM = "claude-sonnet-5"
MAX_TOKENS = 25000
PRECIO_ENTRADA_POR_MILLON = 2.00   # USD
PRECIO_SALIDA_POR_MILLON = 10.00   # USD

PROMPT_VERIFICACION = """Vas a revisar una extracción de ítems clínicos ya realizada, comparándola de nuevo contra la transcripción original. Tu única tarea es corregir un tipo específico de error: campos marcados como null que en realidad deberían ser false porque el paciente respondió con una negación general a una pregunta que mencionaba varios elementos a la vez.

Ejemplo del patrón a buscar:
MÉDICO: "¿Antecedentes de calcio alto, paratiroides, piedras en el riñón o tumores de glándulas en la familia?"
PACIENTE: "No, nada de eso."
→ Los CUATRO campos mencionados en la pregunta deben marcarse como false, no solo uno.

Instrucciones:
1. Repasa la transcripción completa buscando preguntas compuestas (que mencionan varios ítems) respondidas con una negación general del paciente ("no", "nada de eso", "que yo sepa no", "sano", etc.).
2. Para cada campo del JSON que estaba marcado como null, comprueba si pertenece a una de esas preguntas compuestas negadas. Si es así, cambia su valor a false.
3. NO cambies ningún otro campo. No toques valores que ya sean true o false. No añadas ni quites campos.
4. Devuelve el JSON completo corregido, con la misma estructura exacta que el original.

TRANSCRIPCIÓN ORIGINAL:
{transcripcion}

JSON A REVISAR (salida del paso 1 de extracción):
{json_extraccion}

Devuelve ÚNICAMENTE el JSON corregido, sin explicaciones adicionales antes o después.
"""


# ─── UTILIDADES ───────────────────────────────────────────────────────────────

def leer_robusto(ruta):
    for cod in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return ruta.read_text(encoding=cod)
        except UnicodeDecodeError:
            continue
    return ruta.read_text(encoding="utf-8", errors="replace")


def normalizar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r'\b(médico|medico|paciente|hija|cuidadora|acompañante)\s*:', '', texto)
    texto = re.sub(r'[^\w\sáéíóúüñàèìòùâêîôûäëïöü]', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def extraer_json(texto):
    texto = texto.strip()
    m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', texto, re.DOTALL)
    if m:
        return m.group(1).strip()
    ini, fin = texto.find('{'), texto.rfind('}')
    if ini != -1 and fin > ini:
        return texto[ini:fin + 1].strip()
    return texto


def buscar_audio(n):
    for carpeta in (DIR_GRABACIONES, DIR_ASR):
        for ext in ('.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.flac'):
            for sufijo in ('_real', '_tts', ''):
                ruta = carpeta / f"audio_dialogo_{n}{sufijo}{ext}"
                if ruta.exists():
                    return ruta
    return None


def coste(t_in, t_out):
    return (t_in / 1_000_000) * PRECIO_ENTRADA_POR_MILLON + \
           (t_out / 1_000_000) * PRECIO_SALIDA_POR_MILLON


def barra(txt):
    print(f"\n{'─' * 64}\n{txt}\n{'─' * 64}")


# ─── COMPROBACIÓN PREVIA ──────────────────────────────────────────────────────

def comprobar(dialogo=None, audio=None, sin_asr=False):
    """Verifica que todo está en su sitio SIN gastar ni un token de API."""
    barra("COMPROBACIÓN DEL ENTORNO")
    ok = True

    def chk(cond, texto, detalle=""):
        nonlocal ok
        print(f"  {'✓' if cond else '✗'}  {texto}")
        if not cond:
            ok = False
            if detalle:
                print(f"       → {detalle}")
        return cond

    # Dependencias
    for mod, paquete in (("whisper", "openai-whisper"), ("anthropic", "anthropic"), ("jiwer", "jiwer")):
        try:
            __import__(mod)
            chk(True, f"Librería {mod}")
        except ImportError:
            chk(False, f"Librería {mod}", f"pip install {paquete}")

    # Archivos de configuración
    chk(RUTA_PROMPT_V4.exists(), f"prompt_extraccion_v4.txt", str(RUTA_PROMPT_V4))
    chk(RUTA_SKILL.exists(), f"skill_validacion_informe_hptp.md", str(RUTA_SKILL))

    # Clave de API
    clave = os.environ.get("ANTHROPIC_API_KEY")
    chk(bool(clave), "ANTHROPIC_API_KEY definida",
        'PowerShell:  $env:ANTHROPIC_API_KEY="tu_clave"')

    # Entrada
    if dialogo:
        if sin_asr:
            ruta = DIR_REFERENCIA / f"referencia_dialogo_{dialogo}.txt"
            chk(ruta.exists(), f"Transcripción de referencia D{dialogo}", str(ruta))
        else:
            ruta = buscar_audio(dialogo)
            chk(ruta is not None, f"Audio del diálogo {dialogo}",
                f"Buscado en {DIR_GRABACIONES}")
    elif audio:
        chk(Path(audio).exists(), f"Audio {audio}")

    print()
    print("  ENTORNO LISTO" if ok else "  FALTAN COSAS — revisa lo marcado con ✗")
    return ok


# ─── ETAPAS ───────────────────────────────────────────────────────────────────

def etapa_asr(ruta_audio, dir_run, ruta_referencia=None):
    import whisper

    barra(f"ETAPA 1 · TRANSCRIPCIÓN  ({MODELO_WHISPER}, local, sin salida de datos)")
    print(f"  Audio: {ruta_audio.name}")
    t0 = time.time()

    print(f"  Cargando modelo Whisper '{MODELO_WHISPER}'...")
    modelo = whisper.load_model(MODELO_WHISPER)
    print("  Transcribiendo...")
    resultado = modelo.transcribe(str(ruta_audio), language=IDIOMA)
    transcripcion = resultado["text"].strip()
    dur = time.time() - t0

    ruta_txt = dir_run / "1_transcripcion.txt"
    ruta_txt.write_text(transcripcion, encoding="utf-8")

    print(f"  Tiempo: {dur/60:.1f} min  |  {len(transcripcion.split())} palabras")
    print(f"  Guardada: {ruta_txt.name}")

    metricas = None
    if ruta_referencia and ruta_referencia.exists():
        try:
            from jiwer import wer
            ref = normalizar_texto(leer_robusto(ruta_referencia))
            hip = normalizar_texto(transcripcion)
            w = wer(ref, hip) * 100
            metricas = {"wer_pct": round(w, 2),
                        "palabras_ref": len(ref.split()),
                        "palabras_whisper": len(hip.split())}
            print(f"  WER frente a la referencia: {w:.2f}%")
        except Exception as e:
            print(f"  (WER no calculado: {e})")

    return transcripcion, dur, metricas


def etapa_llm(client, transcripcion, dir_run):
    prompt_v4 = leer_robusto(RUTA_PROMPT_V4)
    skill = leer_robusto(RUTA_SKILL)
    registro = {}

    def llamar(prompt, etiqueta, n):
        print(f"  [{n}] {etiqueta}...")
        t0 = time.time()
        texto = ""
        with client.messages.stream(
            model=MODELO_LLM, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for parcial in stream.text_stream:
                texto += parcial
            final = stream.get_final_message()
        t_in, t_out = final.usage.input_tokens, final.usage.output_tokens
        c = coste(t_in, t_out)
        print(f"       {t_in} tokens entrada / {t_out} salida  |  {c:.5f} $  |  {time.time()-t0:.0f}s")
        registro[etiqueta] = {"tokens_in": t_in, "tokens_out": t_out, "coste": round(c, 5)}
        return texto

    barra("ETAPA 2 · EXTRACCIÓN DE ÍTEMS  (API externa — salen datos clínicos)")
    texto1 = llamar(prompt_v4.replace("[INSERTAR_TRANSCRIPCIÓN_AQUÍ]", transcripcion),
                    "extraccion", "1/3")
    json_extraccion = extraer_json(texto1)
    (dir_run / "2_extraccion.json").write_text(json_extraccion, encoding="utf-8")

    barra("ETAPA 3 · VERIFICACIÓN DE NEGACIONES")
    texto2 = llamar(PROMPT_VERIFICACION.format(transcripcion=transcripcion,
                                               json_extraccion=json_extraccion),
                    "verificacion", "2/3")
    json_corregido = extraer_json(texto2)
    (dir_run / "3_verificado.json").write_text(json_corregido, encoding="utf-8")

    barra("ETAPA 4 · VALIDACIÓN DEL INFORME")
    texto3 = llamar(f"{skill}\n\n---\n\nJSON A VALIDAR:\n{json_corregido}",
                    "validacion", "3/3")
    (dir_run / "4_informe_validacion.txt").write_text(texto3.strip(), encoding="utf-8")

    return json_corregido, texto3.strip(), registro


# ─── PRINCIPAL ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Pipeline completo HPTP")
    ap.add_argument("--dialogo", help="Número de diálogo del corpus, p. ej. 04")
    ap.add_argument("--audio", help="Ruta a un audio concreto")
    ap.add_argument("--sin-asr", action="store_true",
                    help="Salta Whisper y usa la transcripción de referencia")
    ap.add_argument("--check", action="store_true",
                    help="Solo comprueba el entorno, sin llamar a la API")
    args = ap.parse_args()

    if not args.dialogo and not args.audio and not args.check:
        ap.print_help()
        return

    if args.check:
        comprobar(args.dialogo, args.audio, args.sin_asr)
        return

    if not comprobar(args.dialogo, args.audio, args.sin_asr):
        print("\nCorrige lo anterior antes de ejecutar.")
        return

    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    etiqueta = f"dialogo_{args.dialogo}" if args.dialogo else Path(args.audio).stem
    marca = datetime.now().strftime("%Y%m%d_%H%M")
    dir_run = DIR_SALIDA / f"{etiqueta}_{marca}"
    dir_run.mkdir(parents=True, exist_ok=True)

    t_inicio = time.time()
    dur_asr, metricas_asr = 0, None
    ruta_ref = DIR_REFERENCIA / f"referencia_dialogo_{args.dialogo}.txt" if args.dialogo else None

    if args.sin_asr:
        barra("ETAPA 1 · TRANSCRIPCIÓN  (omitida: se usa la de referencia)")
        transcripcion = leer_robusto(ruta_ref)
        print(f"  {ruta_ref.name}  |  {len(transcripcion.split())} palabras")
        (dir_run / "1_transcripcion.txt").write_text(transcripcion, encoding="utf-8")
    else:
        ruta_audio = Path(args.audio) if args.audio else buscar_audio(args.dialogo)
        transcripcion, dur_asr, metricas_asr = etapa_asr(ruta_audio, dir_run, ruta_ref)

    json_final, informe, registro = etapa_llm(client, transcripcion, dir_run)

    # ── Resumen ──
    coste_total = sum(v["coste"] for v in registro.values())
    dur_total = time.time() - t_inicio

    barra("RESUMEN DE LA EJECUCIÓN")
    print(f"  Transcripción     {dur_asr/60:5.1f} min" if dur_asr else "  Transcripción      (omitida)")
    if metricas_asr:
        print(f"  WER                {metricas_asr['wer_pct']:5.2f} %")
    for k, v in registro.items():
        print(f"  {k:<18} {v['coste']:.5f} $")
    print(f"  {'─'*40}")
    print(f"  COSTE TOTAL        {coste_total:.5f} $")
    print(f"  TIEMPO TOTAL       {dur_total/60:.1f} min")
    print(f"\n  Resultados en: {dir_run}")

    resumen = {
        "entrada": etiqueta,
        "fecha": datetime.now().isoformat(),
        "modelo_asr": None if args.sin_asr else MODELO_WHISPER,
        "modelo_llm": MODELO_LLM,
        "duracion_asr_s": round(dur_asr, 1),
        "duracion_total_s": round(dur_total, 1),
        "metricas_asr": metricas_asr,
        "llamadas": registro,
        "coste_total_usd": round(coste_total, 5),
    }
    (dir_run / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Vista previa del informe de validación ──
    barra("INFORME DE VALIDACIÓN (primeras líneas)")
    for linea in informe.splitlines()[:25]:
        print(f"  {linea}")
    print(f"\n  Informe completo en: 4_informe_validacion.txt")


if __name__ == "__main__":
    main()
