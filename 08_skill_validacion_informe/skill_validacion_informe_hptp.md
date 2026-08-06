---
name: validacion-informe-hptp
description: Valida el JSON generado por el módulo de extracción del sistema HPTP (TFG). Comprueba que cumple el schema de 18 ítems, detecta contradicciones clínicas internas, y avisa de campos clínicamente relevantes que han quedado sin mencionar (null), dejando la decisión final al médico. Úsala siempre que el usuario pida "validar el informe", "revisar el informe generado", "contrastar contra el estándar de validación", o pegue un JSON de salida del sistema HPTP pidiendo una revisión de calidad.
---

# Validación del informe HPTP

Esta skill implementa la etapa de validación posterior a la extracción, sugerida como mejora del sistema: antes de que el informe llegue al médico, se comprueba que el JSON es estructuralmente correcto, que no contiene contradicciones clínicas internas, y que no faltan campos que normalmente deberían tener respuesta. La skill **no modifica el JSON ni decide nada por el médico** — solo señala qué merece una revisión humana.

## Cuándo usarla

Actívate cuando el usuario pida validar, revisar o contrastar un informe generado por el sistema, o pegue directamente un JSON de salida pidiendo feedback de calidad.

## Proceso

Ejecuta los tres bloques en orden y genera un informe único al final con el formato de la sección "Salida".

### Bloque 1 — Cumplimiento del schema

Comprueba:
- Que los 18 ítems del schema (`item_01` a `item_18`, o su nomenclatura equivalente) están presentes.
- Que cada campo tiene un valor válido: `true`, `false`, `null`, o el tipo esperado en campos no booleanos (número, string, lista).
- Que no hay campos inventados fuera del schema (esto es un patrón de error ya documentado: los modelos a veces generan campos adicionales no solicitados).
- Que el campo `alergias` (o equivalente), cuando existe como lista, se evalúa por separado: lista vacía `[]` no es lo mismo que campo ausente o `null` — indica alergias exploradas y negadas.

Si hay campos fuera del schema, señálalos como "campos adicionales no solicitados" — no es necesariamente un error grave, pero conviene que el médico sepa que están ahí y no son parte del schema oficial.

### Bloque 2 — Detección de contradicciones

Revisa el JSON en busca de estos patrones conocidos de contradicción interna (lista no exhaustiva; usa también tu propio criterio clínico para detectar otras incoherencias evidentes):

1. **Diagnóstico pendiente + indicación quirúrgica cerrada.** Si `diagnostico_principal` (o equivalente) es `"pendiente_estudio"` y al mismo tiempo `cirugia_indicada` o `indicacion_quirurgica` es `true` sin matización — contradicción: no puede indicarse cirugía con diagnóstico aún no confirmado.

2. **Riesgos "no explicados" pero detallados.** Si `riesgos_explicados` es `false` pero luego hay riesgos individuales (`hipocalcemia_transitoria`, `lesion_nervio_recurrente`, etc.) marcados como `true` — contradicción: si se marcaron individualmente como explicados, el campo general no puede ser `false`.

3. **Indicación quirúrgica sin criterio que la sustente.** Si `cirugia_indicada` o `indicacion_quirurgica` es `true`, comprueba que al menos uno de los criterios de la sección de indicación quirúrgica (`calcio_sobre_umbral`, `t_score_bajo`, `litiasis_renal`, `fractura_fragilidad`, `edad_menor_50`, etc.) es también `true`. Si todos son `false` o `null`, señala la falta de justificación clínica explícita.

4. **Consentimiento explicado pero no entregado, o al revés.** Si `explicado_verbalmente` es `true` pero `entregado` es `false` (o viceversa de forma inconsistente con el resto del contexto), señálalo para revisión — puede ser correcto (explicado hoy, entrega pendiente) pero merece que el médico lo confirme.

5. **Naturaleza benigna confirmada junto con sospecha de malignidad activa.** Si `naturaleza_benigna` es `true` y en el bloque de diagnóstico diferencial hay indicios de sospecha de malignidad no descartada, señala la incoherencia.

6. **Expectativa de curación en un caso de persistencia o recidiva.** Si el contexto del informe indica persistencia o recidiva de la enfermedad (revisión con diagnóstico de persistencia) y `expectativa_curacion` es `true`, señala la posible incoherencia — es un patrón de error ya observado en las evaluaciones del sistema.

### Bloque 3 — Campos clínicamente relevantes sin mencionar

Primero, identifica el tipo de consulta. Si el JSON incluye un campo explícito de tipo de consulta, úsalo directamente. **En la mayoría de los casos no existirá ese campo** — el prompt de extracción no lo solicita — así que infiérelo con esta regla de prioridad:

1. Si el bloque de seguimiento postoperatorio (`revision_herida`, `analitica_postop`, `anatomia_patologica`, `control_densitometria`) tiene **algún campo con valor `true` o `false`** (no todos `null`), es **revisión postquirúrgica**.
2. Si `cirugia_cervical_previa` (antecedentes personales) es `true`, o hay una cicatriz previa registrada en la exploración física, es **revisión postquirúrgica**.
3. Si ninguna de las anteriores se cumple, y en cambio hay contenido activo en los criterios de indicación quirúrgica o el diagnóstico aparece como pendiente de confirmar, es **primera visita**.
4. Si el resultado es ambiguo tras aplicar estas reglas, indícalo explícitamente en el informe de salida ("tipo de consulta no determinado con certeza — aplicando el conjunto de campos relevantes de primera visita por defecto, revisar manualmente") en lugar de asumir silenciosamente uno de los dos tipos.

**Si es primera visita**, revisa si estos campos están en `null` y avisa si lo están:
`edad_menor_50`, `inclusion_lista_espera`, `diagnostico_explicado`, `riesgos_explicados`, `entregado` y `explicado_verbalmente` (consentimiento), `dudas` (mencionadas y resueltas), `ecografia_cervical`, `mibi`, `hidratacion`, `explicados` (síntomas de alarma), `cansancio_astenia`, `densitometria`, `vitamina_d`, `riesgo_renal_oseo`, `finalidad_pruebas`.

**Si es revisión postquirúrgica**, revisa estos:
`cirugia_cervical_previa`, `cicatrices_previas`, `densitometria`, `vitamina_d`, `diagnostico_explicado`, `necesidad_controles`, `revision_herida`, `analitica_postop`, `control_densitometria`, `seguimiento_renal`, `suplementos_calcio_vitd`, `dudas` (mencionadas, expectativa, resueltas), `litiasis_renal_previa`, `osteoporosis_osteopenia`, `litiasis_renal` (síntoma), `naturaleza_benigna`, `explicados` (síntomas alarma), `anatomia_patologica`, `control_endocrinologico`.

**Independientemente del tipo de consulta**, revisa siempre estos campos de seguridad clínica, aunque tengan baja frecuencia de aparición en el corpus de referencia — se incluyen por criterio de seguridad del paciente, no por frecuencia estadística:
`alergias`, `anticoagulacion`, `hta`, y cualquier campo de medicación con potencial de interacción.

Para cada campo en `null` de estas listas, indica en qué bloque del schema se ubica y una nota breve de por qué conviene revisarlo (ej. "alergias: no mencionado — confirmar con el paciente antes de cualquier decisión terapéutica, especialmente si hay indicación quirúrgica").

## Salida

Devuelve el informe en este formato:

```
VALIDACIÓN DEL INFORME — [fecha/diálogo si se conoce]

✅ CUMPLIMIENTO DEL SCHEMA
[OK, o lista de problemas: campos faltantes, tipos incorrectos, campos adicionales no solicitados]

⚠️ CONTRADICCIONES DETECTADAS
[Ninguna, o lista numerada con: qué campos entran en contradicción, por qué, y la cita textual de ambos valores]

🔍 CAMPOS RELEVANTES SIN MENCIONAR (tipo de consulta: [primera_visita / revisión])
[Ninguno, o lista con el campo, su ubicación en el schema, y la nota de revisión]

Esta validación es un apoyo a la revisión del médico, no sustituye su criterio clínico. La decisión final sobre cada campo señalado corresponde al facultativo.
```

Sé conciso: si un bloque no tiene hallazgos, dilo en una línea y pasa al siguiente. No repitas el JSON completo en la respuesta.
