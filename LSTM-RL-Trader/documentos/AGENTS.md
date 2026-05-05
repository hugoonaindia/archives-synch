# AGENTS.md — Guía para agentes de IA y desarrolladores

## Propósito

Este archivo complementa al `README.md` y al documento maestro con instrucciones específicas para agentes de programación, desarrolladores y cualquier persona que modifique el código. Si vas a editar `trading_lstm_rl_app.py` o los documentos, **lee esto primero**.

---

## Arquitectura fundamental

### Un solo archivo

Todo el sistema está contenido en `trading_lstm_rl_app.py`. Aunque sea un único archivo, la arquitectura interna está dividida en secciones claras:

```
1. Imports and global configuration
2. Dataclasses and configuration schemas
3. Data loading and validation
4. Feature engineering
5. Dataset creation for LSTM
6. PyTorch LSTM model
7. Supervised training loop
8. Prediction and signal generation
9. Backtesting engine
10. Gymnasium trading environment
11. RL training and evaluation
12. Experiment persistence and logging
13. NiceGUI interface
14. Main entry point
```

**Regla de oro:** si añades código, colócalo en la sección correspondiente. No mezcles lógica de backtesting dentro del modelo LSTM.

### Estado global mínimo

La app mantiene un estado global mínimo compartido entre la UI y los procesos de entrenamiento:
- `AppConfig` (instancia única de configuración) ✅
- `AppState` (encapsula config, current_run_dir, ui_log) ✅
- `ExperimentManager` (gestión de runs y métricas) ✅
- Datos cargados (`DataFrame` limpio) ⬜ Pendiente (Fase 2)
- Features generadas (`DataFrame` con train/val/test) ⬜ Pendiente (Fase 3)
- Modelo LSTM entrenado (`nn.Module` + pesos) ⬜ Pendiente (Fase 5-6)
- Predicciones del LSTM (`np.ndarray`) ⬜ Pendiente (Fase 8)
- Agente RL entrenado (`BaseAlgorithm` de SB3) ⬜ Pendiente (Fase 9)

**No introduzcas variables globales adicionales** sin justificación. Prefiere pasar estado como argumentos entre clases.

---

## Convenciones de código

### Estilo
- **PEP 8** como base.
- **Type hints** obligatorios en funciones públicas y métodos de clases.
- **Docstrings** en clases y métodos públicos con formato Google-style o NumPy-style.
- **Nombres descriptivos:** `sequence_length`, no `seq_len`. `prediction_horizon`, no `ph`.

### Imports
- Agrupar por: stdlib → terceros → locales (aunque no haya locales en un solo archivo).
- Todos los imports opcionales deben tener detección `HAS_X` con mensaje claro al usuario.

```python
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
```

### Logging
Usar siempre la función central:
```python
log(message: str, level: Literal["INFO", "WARNING", "ERROR", "DEBUG"] = "INFO")
```
Nunca uses `print()` directamente en código nuevo.

---

## Decisiones arquitectónicas ya tomadas (no cambiar sin consenso)

1. **Un solo archivo Python.** No modularizar en paquete/carpeta salvo que sea absolutamente necesario.
2. **NiceGUI es la única dependencia irrenunciable.** Todo lo demás puede degradarse gracefulmente.
3. **Split temporal sacrosanto.** Train solo contiene fechas anteriores a val, y val anteriores a test. Nunca shuffle entre splits.
4. **Codificación de target consistente:** 0=bajista, 1=neutral, 2=alcista. En todo el sistema, siempre.
5. **Posición one-hot en RL:** `[1,0,0]`=flat, `[0,1,0]`=long, `[0,0,1]`=short. Nunca escalar.
6. **Comisión sobre valor de operación, no sobre capital total.** `trade_value * commission` por cada operación (entrada + salida = 2x).
7. **Slippage:** compras a `close * (1 + slippage)`, ventas/shorts a `close * (1 - slippage)`.

---

## Cómo extender el sistema

### Añadir un nuevo indicador técnico

1. Ir a la sección **4. Feature engineering**.
2. Añadir cálculo en `FeatureEngineer.compute_features()`.
3. Añadir nombre a la lista de `feature_cols` si es parte del conjunto base.
4. Actualizar `N_features` en documentación si cambia la dimensión de observación RL.
5. Verificar que no introduce NaN donde no se esperan.

### Añadir un nuevo algoritmo RL

1. Ir a la sección **11. RL training and evaluation**.
2. En `RLTrainer.__init__`, añadir lógica condicional según `config.algorithm`.
3. Mantener la interfaz `train()` / `evaluate()` idéntica.
4. Si usa acciones continuas (SAC), actualizar `TradingEnv.action_space` y la lógica de `step()`.

### Añadir soporte para datos intradía

1. Modificar `DataManager` para aceptar frecuencias distintas a diaria.
2. Revisar que la detección de huecos temporales use la frecuencia correcta (`1H`, `15min`, etc.).
3. Ajustar `sequence_length` y `prediction_horizon` en defaults o UI, ya que los valores por defecto (60 días) no tienen sentido en intradía.

### Añadir soporte multi-ticker

1. Extender `AppConfig.ticker` a una lista.
2. Modificar `DataManager` para manejar múltiples DataFrames o un MultiIndex.
3. Considerar que el entrenamiento RL debería correr por ticker o compartir política. **Complejidad alta.**

---

## Testing

El proyecto cuenta con suite de tests automatizada en `tests/`. Ejecutar con `pytest tests/` antes de entregar cambios. Adicionalmente, verifica:

1. **Flujo mínimo verificable:** Carga CSV → Features → Entrena LSTM (3 epochs) → Backtest LSTM. Debe completarse sin errores.
2. **No regression en UI:** La app arranca y las pestañas se muestran correctamente.
3. **Check Gymnasium:** `check_env(env)` pasa sin warnings si tocaste el entorno RL.
4. **Reproducibilidad:** Dos ejecuciones con la misma `seed` producen las mismas métricas (dentro de tolerancia numérica).

---

## Errores comunes a evitar

| Error | Por qué ocurre | Cómo evitarlo |
|---|---|---|
| Data leakage | Escalar features con todo el dataset | Ajustar scaler SOLO en train, transformar val/test |
| Look-ahead bias | Usar información futura en features | Features rolling deben usar `.shift()` correctamente |
| UI bloqueada | Entrenamiento en hilo principal | Usar `threading.Thread` o `asyncio` para entrenamiento |
| RL inestable | Reward sin normalizar o sin penalización | Usar `VecNormalize` y reward shaping de §9 |
| Overfitting brutal | Test usado para ajustar hiperparámetros | Nunca mirar test hasta la evaluación final |

---

## Flujo de trabajo recomendado para modificaciones

```
1. Leer el documento maestro § relevante
2. Localizar la sección en trading_lstm_rl_app.py
3. Implementar el cambio
4. Verificar flujo mínimo (Quick Start)
5. Verificar check_env si tocaste RL
6. Actualizar este AGENTS.md si cambiaste decisiones arquitectónicas
```

---

## Contacto / Contexto

Este proyecto fue diseñado con asistencia de IA. Los documentos maestro y pasos accionables son la fuente de verdad. Cuando exista conflicto entre este AGENTS.md y el documento maestro, **gana el documento maestro**.
