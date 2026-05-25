# Marco Senior de Revisión Técnica para Proyectos de ML, DL y Decision Transformers

## 1) Propósito del documento
Este marco define cómo revisar, auditar y elevar la calidad de proyectos de `machine learning`, `deep learning` y `decision transformers` usando subagentes especializados, con criterios de nivel producción e investigación aplicada.

Objetivo: detectar riesgos temprano, aumentar reproducibilidad, acelerar iteraciones útiles y asegurar impacto de negocio medible.

## 2) Principios rectores de revisión
- `Reproducibilidad primero`: sin reproducción no hay evidencia.
- `Impacto antes que complejidad`: una mejora compleja sin impacto no es mejora.
- `Baseline fuerte obligatoria`: todo modelo avanzado debe superar referencias simples y robustas.
- `Trazabilidad end-to-end`: datos, features, entrenamiento, evaluación, despliegue y monitoreo deben quedar auditables.
- `No leakage, no claims`: resultados con fuga de información se invalidan.

## 3) Estructura de subagentes recomendada
- `Subagente A - Datos`: calidad, leakage, drift, sesgos, cobertura temporal, feature store.
- `Subagente B - Modelado`: arquitectura, pérdidas, regularización, estabilidad, ablations.
- `Subagente C - Evaluación`: métricas, splits, intervalos de confianza, backtesting, significancia.
- `Subagente D - MLOps`: pipelines, versionado, CI/CD, serving, observabilidad, rollback.
- `Subagente E - Riesgo y Compliance`: explicabilidad, fairness, seguridad, privacidad, normativa.
- `Subagente F - Producto/Negocio`: valor esperado, costo computacional, latencia, ROI.

## 4) Checklist maestro por fases

### 4.1 Definición del problema
- ¿La variable objetivo está claramente definida y alineada con negocio?
- ¿Se define hipótesis falsable?
- ¿Se documentan constraints: latencia, costo, memoria, interpretabilidad?
- ¿Existen criterios de éxito offline y online?

### 4.2 Datos y features
- ¿Hay diccionario de datos versionado?
- ¿Se validan nulos, duplicados, outliers, cardinalidad extrema?
- ¿Se garantiza separación temporal y prevención de leakage?
- ¿Se evalúan sesgos de muestreo y representatividad?
- ¿Features derivadas respetan causalidad temporal?

### 4.3 Entrenamiento
- ¿Baselines clásicos (LR/XGBoost/heurísticas) están implementadas?
- ¿Hay control de semillas y determinismo razonable?
- ¿Se usa tracking de experimentos (parámetros, artefactos, métricas)?
- ¿Existen curvas de aprendizaje y diagnóstico de overfitting?
- ¿Se justifican hiperparámetros y budget de búsqueda?

### 4.4 Evaluación
- ¿Métricas alineadas con costo de error real?
- ¿Se reporta performance por segmento/cohorte/región/tiempo?
- ¿Hay validación cruzada o backtest robusto según dominio?
- ¿Se incluyen intervalos de confianza / bootstrap?
- ¿Se comparan contra baseline con test estadístico apropiado?

### 4.5 Despliegue y operación
- ¿Contrato de input/output del modelo está definido?
- ¿Hay feature parity training-serving?
- ¿Monitoreo de drift de datos y drift de performance?
- ¿Alertas, SLA/SLO, circuit breaker, rollback listos?
- ¿Plan de recalibración/reentrenamiento con triggers explícitos?

## 5) Guía específica para Decision Transformers

### 5.1 Dataset offline RL
- Validar cobertura de estados-acciones-recompensas.
- Cuantificar distribución de retornos y calidad de trayectorias.
- Evaluar sesgo hacia políticas históricas subóptimas.
- Verificar consistencia de `reward-to-go` y normalización.

### 5.2 Diseño del modelo
- Revisar tokenización de estado/acción/recompensa y orden causal.
- Confirmar máscara autoregresiva correcta.
- Auditar ventanas de contexto y truncación de secuencias.
- Revisar escalado de embeddings y estabilidad numérica.

### 5.3 Evaluación offline RL
- Reportar resultados por niveles de retorno objetivo.
- Usar múltiples seeds y dispersión de resultados.
- Contrastar con behavior cloning y/o CQL/IQL según disponibilidad.
- Incluir análisis de sensibilidad al horizonte y ruido.

### 5.4 Riesgos frecuentes
- Sobreajuste a trayectorias frecuentes.
- Mejora aparente por leakage temporal.
- Retornos inflados por métrica mal definida.
- Falta de robustez OOD.

## 6) Formato estándar de reporte por subagente
Cada subagente debe emitir salida en este formato:

1. `Estado`: Verde / Amarillo / Rojo.
2. `Hallazgos críticos`: lista priorizada por severidad.
3. `Evidencia`: archivos, experimentos, métricas, gráficos.
4. `Impacto esperado`: técnico + negocio.
5. `Acciones recomendadas`: quick wins (24-72h) y estructurales (1-4 semanas).
6. `Riesgo residual`: qué puede seguir fallando tras aplicar mejoras.

## 7) Escala de severidad unificada
- `S0 - Bloqueante`: invalida conclusiones o impide deploy.
- `S1 - Crítico`: alto riesgo de fallo en producción o decisión incorrecta.
- `S2 - Mayor`: degrada calidad, costo o confianza de forma material.
- `S3 - Menor`: mejora deseable, sin urgencia inmediata.

## 8) Política de aprobación para pasar de fase
Un proyecto solo avanza si:
- No existen hallazgos `S0` abiertos.
- Hallazgos `S1` tienen mitigación implementada o plan firmado con fecha.
- Reproducibilidad mínima demostrada (script + seed + artefactos).
- Comparativa contra baseline publicada y trazable.

## 9) Preguntas de auditoría ejecutiva (reunión de 15 minutos)
- ¿Qué decisión de negocio mejora este modelo y cuánto?
- ¿Cuál es el peor escenario plausible y su costo?
- ¿Qué métrica podría estar mintiendo y por qué?
- ¿Qué evidencia prueba generalización y no memoría?
- ¿Cómo revertimos en minutos si falla en producción?

## 10) Plantilla de prompt para coordinar subagentes
```md
Contexto: Revisa el proyecto con foco en [Datos|Modelado|Evaluación|MLOps|Riesgo|Negocio].
Objetivo: Identificar hallazgos accionables priorizados por severidad S0-S3.
Entradas: [rutas de código, notebooks, experimentos, reportes].
Criterios: usar checklist maestro y reportar evidencia verificable.
Salida obligatoria:
1) Estado (Verde/Amarillo/Rojo)
2) Top 5 hallazgos con severidad
3) Evidencia concreta por hallazgo
4) Acciones recomendadas (24-72h y 1-4 semanas)
5) Riesgo residual
No inventes datos; si falta evidencia, repórtalo explícitamente.
```

## 11) Anti-patrones que este marco busca eliminar
- "Modelo SOTA" sin baseline fuerte.
- Métricas agregadas sin cortes por cohorte.
- Backtest optimista por leakage temporal.
- Deploy sin observabilidad ni rollback.
- Hiperoptimización sin hipótesis de negocio.

## 12) Criterio final de excelencia senior
Un proyecto está "listo" cuando combina:
- `Rigor científico` (evidencia reproducible)
- `Robustez ingenieril` (operable en producción)
- `Valor económico` (impacto claro y medible)
- `Gobierno del riesgo` (fallos previsibles y mitigables)

---

## Anexo A: Scorecard rápido (0-5)
- Problema y objetivo: __/5
- Calidad y gobernanza de datos: __/5
- Baselines y diseño experimental: __/5
- Validez estadística: __/5
- Robustez y generalización: __/5
- MLOps y monitoreo: __/5
- Riesgo/compliance: __/5
- Impacto de negocio: __/5

`Total` = __/40

Interpretación:
- `34-40`: Excelente, escalable.
- `26-33`: Bueno con mejoras concretas.
- `18-25`: Riesgo alto, no escalar aún.
- `<18`: Replantear diseño y datos.
