"""
Cálculo de métricas de evaluación — Módulo de extracción
TFG: Sistema de apoyo a la documentación clínica para HPTP

Este script implementa el cálculo mecánico de accuracy, precisión, recall y F1
a partir de una clasificación campo a campo ya realizada.

IMPORTANTE — lo que este script NO hace:
La clasificación de cada campo (TP/FP/FN/TN) se realiza de forma MANUAL,
emparejando semánticamente el valor del gold standard con el del modelo
evaluado. Esto es así porque los tres modelos de lenguaje evaluados no
respetan de forma estricta la nomenclatura del schema (ver capítulo 8,
sección 8.5.4 de la memoria: "falta de adherencia al schema"), lo que
impide un emparejamiento automático fiable por nombre de campo.

Este script recibe la clasificación YA REALIZADA (una lista de tuplas
(campo, valor_gold, valor_modelo, clase)) y calcula las métricas de forma
mecánica y reproducible a partir de ella.

Convención de clasificación por campo:
    - gold=true,  modelo=true          -> TP (verdadero positivo)
    - gold=true,  modelo=false/null    -> FN (falso negativo, omisión)
    - gold=false, modelo=false         -> TN (verdadero negativo)
    - gold=false, modelo=true          -> FP (falso positivo, invención)
    - gold=false, modelo=null          -> FN (omisión de negación explícita)
    - gold=null,  modelo=null          -> TN (acierto en "no mencionado")
    - gold=null,  modelo=true/false    -> FP (alucinación / invención)
"""

from collections import Counter


def calcular_metricas(pares_clasificados):
    """
    Calcula accuracy, precisión, recall y F1 a partir de una lista de
    campos ya clasificados.

    Parámetros:
        pares_clasificados: lista de tuplas (campo, valor_gold, valor_modelo, clase)
                             donde clase es una de "TP", "FP", "FN", "TN"

    Devuelve:
        dict con TP, FP, FN, TN, accuracy, precision, recall, f1 (en %)
    """
    c = Counter(p[3] for p in pares_clasificados)
    TP, FP, FN, TN = c["TP"], c["FP"], c["FN"], c["TN"]
    total = TP + FP + FN + TN

    accuracy  = (TP + TN) / total * 100 if total > 0 else 0
    precision = TP / (TP + FP) * 100 if (TP + FP) > 0 else 0
    recall    = TP / (TP + FN) * 100 if (TP + FN) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "total": total, "TP": TP, "FP": FP, "FN": FN, "TN": TN,
        "accuracy": round(accuracy, 1),
        "precision": round(precision, 1),
        "recall": round(recall, 1),
        "f1": round(f1, 1),
    }


def agregar_metricas(lista_de_resultados):
    """
    Agrega los resultados de varios diálogos sumando los recuentos de
    TP/FP/FN/TN (no promediando porcentajes ya promediados), y calcula
    las métricas globales sobre el total agregado.
    """
    TP = sum(r["TP"] for r in lista_de_resultados)
    FP = sum(r["FP"] for r in lista_de_resultados)
    FN = sum(r["FN"] for r in lista_de_resultados)
    TN = sum(r["TN"] for r in lista_de_resultados)
    total = TP + FP + FN + TN

    accuracy  = (TP + TN) / total * 100 if total > 0 else 0
    precision = TP / (TP + FP) * 100 if (TP + FP) > 0 else 0
    recall    = TP / (TP + FN) * 100 if (TP + FN) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "total": total, "TP": TP, "FP": FP, "FN": FN, "TN": TN,
        "accuracy": round(accuracy, 1),
        "precision": round(precision, 1),
        "recall": round(recall, 1),
        "f1": round(f1, 1),
    }


# ─── EJEMPLO DE USO ────────────────────────────────────────────────────────
# (fragmento real correspondiente a una porción del diálogo D01, modelo Claude)

if __name__ == "__main__":
    pares_ejemplo = [
        ("hta", True, True, "TP"),
        ("diabetes_mellitus", None, False, "FP"),
        ("litiasis_renal_previa", False, False, "TN"),
        ("fracturas_fragilidad", False, None, "FN"),
        # ... el resto de campos del diálogo se añadirían siguiendo el
        # mismo formato, tras el emparejamiento manual campo a campo
    ]

    resultado = calcular_metricas(pares_ejemplo)
    print(f"Total campos: {resultado['total']}")
    print(f"TP={resultado['TP']} FP={resultado['FP']} FN={resultado['FN']} TN={resultado['TN']}")
    print(f"Accuracy: {resultado['accuracy']}%")
    print(f"Precisión: {resultado['precision']}%")
    print(f"Recall: {resultado['recall']}%")
    print(f"F1: {resultado['f1']}%")
