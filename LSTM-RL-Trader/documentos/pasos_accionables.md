# Pasos accionables — LSTM + RL Trading App

Complementa al [`documento_maestro_lstm_rl_trading_nicegui.md`](./documento_maestro_lstm_rl_trading_nicegui.md). Cada paso es atómico, verificable y tiene dependencias explícitas. Marca `[x]` al completar.

---

## Fase 0: Entorno y proyecto

### 0.1 Crear estructura de proyecto
- [x] Crear archivo `trading_lstm_rl_app.py` vacío.
- [x] Crear `requirements.txt` con las versiones de la sección 4.1 del documento maestro.
- [x] Crear carpetas `models/`, `runs/`, `data/` (usar `Path.mkdir(exist_ok=True)` al arrancar la app).
- **Verificación**: `ls models/ runs/ data/` muestra las tres carpetas.

### 0.2 Instalar dependencias
- [x] `pip install -r requirements.txt`
- **Verificación**: `python -c "import torch, nicegui, gymnasium, pandas; print('OK')"` no da error.

### 0.3 Obtener datos de ejemplo
- [ ] Descargar un CSV de ejemplo con datos OHLCV diarios (ej. SPY 2018-2023) y guardarlo en `data/SPY.csv`.
- [ ] Alternativa: añadir al script una función que descargue SPY automáticamente con `yfinance` si está disponible, como fallback en la UI.
- **Verificación**: `data/SPY.csv` existe y tiene al menos 1000 filas con columnas Date,Open,High,Low,Close,Volume.

---

## Fase 1: Esqueleto del script único

### 1.1 Cabecera del archivo
- [x] Crear sección de imports con la estructura de comentarios de sección 3.2 del documento maestro.
- [x] Todos los imports con detección de librerías ausentes y flags booleanos (`HAS_TORCH`, `HAS_SB3`, etc.).
- **Verificación**: `python trading_lstm_rl_app.py` importa sin errores (la app no arranca aún, solo los imports).

### 1.2 Dataclasses de configuración
- [x] `LSTMConfig` con los 9 campos y defaults de la sección 11.
- [x] `BacktestConfig` con los 6 campos y defaults de la sección 11.
- [x] `RLConfig` con los 10 campos y defaults de la sección 11 (incluye `reward_asymmetry_factor`, `max_drawdown_limit`, `max_drawdown_penalty`, `vol_action_mask_threshold`).
- [x] `AppConfig` anidando las tres anteriores + `ticker`, `csv_path`, `start_date`, `end_date`, `seed`, `train_ratio`, `val_ratio`.
- [x] Método `AppConfig.to_dict()` y `AppConfig.from_dict()` para serializar/deserializar a JSON.
- **Verificación**: instanciar `AppConfig()` y llamar a `to_dict()` devuelve un dict con todas las claves anidadas.

### 1.3 Sistema de logging
- [x] Función `log(message, level="INFO")` que escriba a consola (`print`), a un `ui.log` de NiceGUI (variable global o cola), y a `runs/{run_id}/log.txt`.
- [x] Clase `ExperimentManager` con `start_run()`, `log_metric()`, `save_config()`, `end_run()`.
- [x] `run_id` generado como `YYYYMMDD-HHMMSS-{ticker}`.
- **Verificación**: llamar `log("test")` escribe en consola. `ExperimentManager.start_run("SPY")` crea `runs/{id}/`.

### 1.4 UI mínima de NiceGUI
- [ ] Arrancar `ui.run()` en `main()`.
- [ ] Mostrar disclaimer fijo: _"Modo investigación/backtesting. No ejecuta operaciones reales. No constituye asesoramiento financiero."_
- [ ] Crear tabs: Datos, Features, LSTM, Backtest LSTM, RL, Backtest RL, Experimentos.
- [ ] Si `HAS_TORCH == False`: ocultar tab LSTM.
- [ ] Si `HAS_SB3 == False`: ocultar tab RL.
- [ ] Si `HAS_GYMNASIUM == False`: ocultar tabs RL y Backtest RL.
- [ ] Si `HAS_YFINANCE == False`: ocultar botón "Descargar" en tab Datos.
- **Verificación**: abrir `http://localhost:8080`, ver tabs + disclaimer. Forzar `HAS_TORCH=False` manualmente para probar ocultación.

---

## Fase 2: Datos

### 2.1 Clase DataManager
- [ ] `DataManager.load_csv(path)` que haga exactamente esto:
  1. Intentar `pd.read_csv(path, sep=",")`, si falla reintentar con `;` y `\t`.
  2. Intentar encoding UTF-8, si falla reintentar `latin-1`, `ISO-8859-1`.
  3. Normalizar nombres de columna a lowercase.
  4. Validar que existen `date`, `open`, `high`, `low`, `close`, `volume`.
  5. Parsear fecha con `pd.to_datetime(..., dayfirst=None)` → si falla, reintentar `dayfirst=True`.
  6. Ordenar por fecha ascendente.
  7. Eliminar filas duplicadas por fecha.
  8. Detectar huecos: `(df['date'].diff() > pd.Timedelta('1D')).sum()` → guardar conteo y mostrarlo.
  9. Eliminar filas con NaN en OHLCV.
- **Verificación**: cargar un CSV con columnas en mayúsculas y desordenado → devuelve DataFrame limpio con columnas lowercase y ordenado.

### 2.2 UI de carga de datos
- [ ] Botón "Cargar CSV" que abra diálogo de archivos (`ui.upload`).
- [ ] Al cargar, mostrar: número de filas, rango de fechas, número de huecos detectados, preview de primeras 5 filas.
- [ ] Botón "Descargar yfinance" (solo si `HAS_YFINANCE`) → input de ticker y fechas → `yf.download()` → guardar en `data/{ticker}.csv` → mismo pipeline de validación.
- **Verificación**: cargar un CSV válido → la UI muestra resumen. Cargar CSV sin columna `volume` → error descriptivo en UI.

---

## Fase 3: Features

### 3.1 Clase FeatureEngineer
- [ ] Calcular exactamente estas features sobre los datos limpios:
  1. `close_norm` — precio close normalizado (close / close.shift(1) acumulado, o close escalado).
  2. `returns` — retorno porcentual diario.
  3. `volatility` — desviación estándar rolling de 20 días de `returns`.
  4. `sma_20` — media móvil simple de 20 días del close.
  5. `sma_50` — media móvil simple de 50 días del close.
  6. `price_to_sma_20` — `(close - sma_20) / sma_20`.
  7. `rsi` — RSI de 14 días.
  8. `macd` — MACD (12, 26, 9).
  9. `high_low_range` — `(high - low) / close`.
  10. `open_close_range` — `(close - open) / open`.
  11. `volume_norm` — volumen / media móvil de 20 días del volumen.
- [ ] Tras calcular, eliminar filas con NaN (primeras `max(50, 26)` filas quedarán NaN por los indicadores rolling).
- [ ] Mostrar en UI: `N filas descartadas por bordes temporales`.
- **Verificación**: con 500 filas de datos, obtener ~450 filas con las 11 features sin NaN.

### 3.2 Split temporal
- [ ] `FeatureEngineer.split_temporal(df, train_ratio, val_ratio)` donde los defaults vienen de `AppConfig` (`train_ratio=0.7`, `val_ratio=0.15`, el resto `0.15` es test).
- [ ] Train: primeras 70% de las fechas. Val: siguientes 15%. Test: últimas 15%.
- [ ] NO hacer shuffle. El orden temporal es sacrosanto.
- **Verificación**: `train['date'].max() < val['date'].min() < test['date'].min()`.

### 3.3 Normalización sin leakage
- [ ] Ajustar `StandardScaler` solo con `train`.
- [ ] Transformar train, val, test con el scaler ajustado.
- [ ] Las columnas de features a escalar son TODAS menos `date`.
- **Verificación**: el scaler se ajusta con `train` y se aplica a `val`/`test` sin reajustar.

### 3.4 UI de features
- [ ] Botón "Generar features".
- [ ] Mostrar lista de features generadas.
- [ ] Mostrar conteo de filas descartadas.
- [ ] Vista previa de las primeras 5 filas ya normalizadas.
- **Verificación**: pulsar botón → ver features + conteo de descartadas + preview.

---

## Fase 4: Dataset LSTM

### 4.1 Clase SequenceDataset
- [ ] Heredar de `torch.utils.data.Dataset`.
- [ ] `__init__(df, feature_cols, target_col, sequence_length, prediction_horizon)`:
  - `feature_cols`: lista de 11 nombres de columna de features (sin `date`): `close_norm`, `returns`, `volatility`, `sma_20`, `sma_50`, `price_to_sma_20`, `rsi`, `macd`, `high_low_range`, `open_close_range`, `volume_norm`.
  - `target_col`: nombre de la columna target (se calcula en este paso, ver 4.2).
  - `sequence_length`: 60 por defecto.
  - `prediction_horizon`: 5 por defecto.
  - Construir `X` de forma `(N, sequence_length, num_features)` y `y` de forma `(N,)`.
- [ ] `__len__` devuelve número de secuencias.
- [ ] `__getitem__` devuelve `(torch.tensor(X[i]), torch.tensor(y[i]))`.
- **Verificación**: `len(dataset)` = `len(df) - sequence_length - prediction_horizon + 1`.

### 4.2 Target supervisado
- [ ] Calcular columna `future_return` = `(close[t+prediction_horizon] - close[t]) / close[t]`.
- [ ] Calcular columna `target` con la codificación **consistente en todo el sistema** (ver maestro §6.3):
  - Si `future_return > 0.01` → **2** (alcista).
  - Si `future_return < -0.01` → **0** (bajista).
  - Si no → **1** (neutral).
  - Umbral configurable en `LSTMConfig`.
- [ ] NOTA: los targets tienen NaN en las últimas `prediction_horizon` filas. Descartarlas.
- **Verificación**: valores de target posibles = {0, 1, 2}. Sin NaN. Longitud de target = `len(df_validas) - prediction_horizon`.

### 4.3 Crear datasets por split
- [ ] `train_dataset = SequenceDataset(train_df, ...)`.
- [ ] `val_dataset = SequenceDataset(val_df, ...)`.
- [ ] `test_dataset = SequenceDataset(test_df, ...)`.
- [ ] `train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)` (shuffle dentro de train es seguro porque las secuencias ya están aisladas).
- [ ] `val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)`.
- **Verificación**: iterar sobre `train_loader` devuelve batches de forma `(64, 60, 11)` y `(64,)`.

---

## Fase 5: Modelo LSTM

### 5.1 Clase LSTMTradingModel
- [ ] Heredar de `nn.Module`.
- [ ] Arquitectura:
  - `self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)`
  - `self.dropout = nn.Dropout(dropout)`
  - `self.fc = nn.Linear(hidden_size, 3)` (3 clases: bajista/neutral/alcista)
- [ ] `forward(x)` → LSTM → tomar solo `output[:, -1, :]` (último timestep) → dropout → linear → logits.
- [ ] `input_size` = `num_features` (11 por defecto).
- **Verificación**: `model(torch.randn(4, 60, 11)).shape == (4, 3)`.

### 5.2 Clase LSTMTrainer
- [ ] `__init__(model, config, run_dir)`:
  - `criterion = nn.CrossEntropyLoss()`.
  - `optimizer = Adam` con `lr` y `weight_decay` de config.
  - `scheduler`: opcional, no necesario para v1.
- [ ] `train_epoch(train_loader)` → devuelve loss promedio.
- [ ] `validate(val_loader)` → devuelve loss promedio + accuracy.
- [ ] `fit(train_loader, val_loader)`:
  - Loop de epochs con early stopping: si val_loss no mejora en `patience` epochs → parar.
  - Guardar mejor modelo en `run_dir / "best_model.pt"`.
  - Guardar losses en lista para graficar después.
  - Loggear cada epoch: `log(f"Epoch {e}: train_loss={:.4f}, val_loss={:.4f}, val_acc={:.2%}")`.
- **Verificación**: entrenar 3 epochs con CPU sobre dataset pequeño → val_loss decrece y se guarda `best_model.pt`.

### 5.3 UI de entrenamiento LSTM
- [ ] Inputs editables para: `sequence_length`, `prediction_horizon`, `hidden_size`, `num_layers`, `dropout`, `learning_rate`, `batch_size`, `epochs`, `early_stopping_patience`, `weight_decay`.
- [ ] Botón "Entrenar LSTM" que ejecute en un `threading.Thread` para no bloquear UI.
- [ ] Mostrar progreso en tiempo real (log de cada epoch en un `ui.log`).
- [ ] Al terminar: gráfico de train_loss vs val_loss (matplotlib inline o plotly).
- **Verificación**: pulsar entrenar → ver epochs en log → al terminar ver gráfico de loss.

---

## Fase 6: Predicciones y señales

### 6.1 Clase SignalGenerator
- [ ] `generate_predictions(model, test_loader)` → devuelve array de probabilidades softmax `(N, 3)` y array de clases predichas `(N,)`.
- [ ] `predictions_to_signals(probas, threshold_long=0.6, threshold_short=0.6)`:
  - Si `proba[clase_alcista] > threshold_long` → `"LONG"`.
  - Si `proba[clase_bajista] > threshold_short` → `"SHORT"`.
  - Si no → `"FLAT"`.
- [ ] Mostrar distribución: `{LONG: X%, SHORT: Y%, FLAT: Z%}`.
- **Verificación**: `len(signals) == len(test_df)`. Distribución suma 100%.

### 6.2 Evaluación del modelo LSTM
- [ ] Accuracy sobre test.
- [ ] Matriz de confusión 3x3.
- [ ] Classification report (precision, recall, f1 por clase).
- [ ] Mostrar en UI: tabla de métricas + matriz de confusión + distribución de señales.
- **Verificación**: accuracy > 33% (mejor que aleatorio). Señales no son 100% FLAT.

---

## Fase 7: Backtest LSTM

### 7.1 Clase Backtester
- [ ] `__init__(data, signals, config)`:
  - `data`: DataFrame con columnas `date`, `close`.
  - `signals`: array de señales (mismo largo que data).
  - `config`: `BacktestConfig`.
- [ ] Estado interno: `cash`, `position` (None, "LONG", "SHORT"), `entry_price`, `equity_history`, `trade_history`.
- [ ] `run()`:
  - Iterar fila por fila.
  - Si hay posición abierta:
    - Comprobar stop loss: si `(current_price - entry_price)/entry_price < -stop_loss` → cerrar posición.
    - Comprobar take profit: si `(current_price - entry_price)/entry_price > take_profit` → cerrar posición.
  - Si señal cambia respecto a posición actual:
    - Cerrar posición existente (si hay) → registrar trade con comisión + slippage.
    - Abrir nueva posición (si la señal no es FLAT) → deducir comisión + slippage de entrada.
  - Actualizar equity = cash + valor de posición abierta (marcada a mercado).
  - Guardar equity en `equity_history`.
- [ ] Comisión: `trade_value * commission` por operación (entrada + salida = 2x). Donde `trade_value = position_size * price`. No usar `cash * commission`.
- [ ] Slippage: precio de ejecución = `close * (1 + slippage)` para compras, `close * (1 - slippage)` para ventas/shorts.
- [ ] `compute_metrics()` devuelve dict con las 9 métricas de la sección 7.3.
- **Verificación**: backtest con señales todas FLAT → equity final = initial_cash. Con señales todas LONG en un mercado alcista → equity > initial_cash.

### 7.2 UI de backtest LSTM
- [ ] Botón "Ejecutar backtest LSTM".
- [ ] Mostrar tabla de métricas (total_return, sharpe, max_drawdown, win_rate, profit_factor, num_trades).
- [ ] Gráfico de equity curve (con línea de buy & hold superpuesta para comparar).
- [ ] Tabla de trades: fecha entrada, fecha salida, tipo, retorno, duración.
- **Verificación**: ver equity curve + métricas + tabla de trades con valores consistentes.

---

## Fase 8: Entorno RL (Gymnasium)

### 8.1 Clase TradingEnv
- [ ] Heredar de `gym.Env`.
- [ ] `__init__(data, lstm_predictions, config)`:
  - `data`: DataFrame con features + `close`.
  - `lstm_predictions`: array de probabilidades softmax `(N, 3)`.
  - Calcular `observation_dim` como en maestro §8.3 y §9.6.22: `N_features + 3 (LSTM probas) + 3 (posición one-hot) + 7 (riesgo ampliado)` = `11 + 3 + 3 + 7` = **24**.
    - `N_risk = 7`: retorno reciente, volatilidad reciente, drawdown actual, equity normalizado, equity vs equity hace 5 steps, racha de trades ganadores en últimos 10, drawdown desde pico normalizado.
  - `self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(observation_dim,), dtype=np.float32)`.
  - `self.action_space = spaces.Discrete(3)`.
- [ ] `reset(seed=None, options=None)`:
  - `current_step = 0`.
  - `cash = initial_cash`.
  - `position = 0` (0=flat, 1=long, 2=short).
  - `entry_price = None`.
  - `peak_equity = initial_cash`.
  - `trade_history = []` (lista de trades recientes para racha).
  - Construir y devolver `obs, info`.
- [ ] `_get_observation()`:
  - Vector con: features[step], lstm_probas[step], position_one_hot (3 dims: [flat, long, short]), los 7 campos de riesgo.
  - Codificación one-hot de posición: `[1,0,0]` = flat, `[0,1,0]` = long, `[0,0,1]` = short.
  - Todo `np.float32`.
- [ ] `step(action)`:
  1. Ejecutar acción (abrir/cerrar/mantener posición).
  2. Calcular costes (comisión + slippage si hay cambio).
  3. Avanzar `current_step += 1`.
  4. Calcular reward con shaping **v1** (ver maestro §9):
     - `step_return = retorno neto del paso`.
     - `asymmetric_penalty = max(0, -step_return) * config.reward_asymmetry_factor` (pérdidas pesan 1.5x).
     - `drawdown_penalty = max(0, (peak_equity - equity) / peak_equity - threshold) * penalty_weight`.
     - `position_change_penalty = 1 si cambió de posición, 0 si no`.
     - `reward = step_return - asymmetric_penalty - drawdown_penalty - position_change_penalty - transaction_cost`.
  5. Max drawdown por episodio **v1**: si `(peak_equity - equity) / peak_equity > config.max_drawdown_limit` → `terminated = True` y `reward -= config.max_drawdown_penalty`.
  6. Actualizar `peak_equity = max(peak_equity, equity)`.
  7. `terminated = (current_step >= len(data) - 1) or drawdown_excedido`.
  8. `truncated = (cash <= 0)`.
  9. Construir `obs` y devolver `obs, reward, terminated, truncated, info`.
- [ ] `action_masks()` **v1**: si `volatilidad_reciente > config.vol_action_mask_threshold` o `drawdown_actual > config.max_drawdown_limit` → solo acción flat permitida: `[True, False, False]`. En caso contrario: `[True, True, True]`.
- [ ] `info` debe contener: `equity`, `drawdown`, `num_trades`, `position`, `action_masks`.
- **Verificación**: `check_env(env)` de Stable-Baselines3 pasa sin warnings.

### 8.2 Sanity check del entorno
- [ ] Ejecutar 1000 pasos con acciones aleatorias → no crashea, `cash` y `equity` cambian, `terminated` se dispara al final.
- [ ] Verificar que `obs` no contiene NaN ni inf.
- **Verificación**: `np.isfinite(obs).all()` es True para 1000 pasos aleatorios.

---

## Fase 9: Entrenamiento RL

### 9.1 Clase RLTrainer
- [ ] `__init__(env, config, run_dir)`:
  - `model = PPO("MlpPolicy", env, learning_rate=config.learning_rate, gamma=config.gamma, n_steps=config.n_steps, batch_size=config.batch_size, verbose=0)`.
  - `total_timesteps = config.total_timesteps`.
- [ ] **Reward normalización v1** (ver maestro §9.6.20): envolver el entorno con `VecNormalize(env, norm_obs=True, norm_reward=True)` para normalizar recompensas durante el entrenamiento.
  - Guardar las estadísticas de normalización junto con el modelo para poder restaurarlas al evaluar.
  - Al evaluar en test, crear un entorno nuevo sin normalización o con estadísticas fijas.
- [ ] `train()`:
  - `model.learn(total_timesteps=total_timesteps, progress_bar=False)`.
  - Guardar modelo: `model.save(run_dir / "ppo_agent.zip")`.
  - Guardar estadísticas de normalización: `vec_normalize.save(run_dir / "vec_normalize.pkl")`.
- [ ] `evaluate(env, n_episodes=1)`:
  - Ejecutar episodio completo con `model.predict(obs, deterministic=True)`.
  - Devolver: equity_curve, métricas (total_return, sharpe, max_drawdown, num_trades).
- **Verificación**: entrenar 5000 timesteps → el agente guardado se puede cargar con `PPO.load()`.

### 9.2 UI de entrenamiento RL
- [ ] Inputs editables para: `total_timesteps`, `gamma`, `learning_rate`, `n_steps`, `batch_size`.
- [ ] Botón "Entrenar agente RL" que ejecute en thread separado.
- [ ] Mostrar log de progreso.
- [ ] Al terminar: mensaje "Agente entrenado y guardado".
- **Verificación**: pulsar entrenar → ver log → agente guardado en `runs/{id}/ppo_agent.zip`.

---

## Fase 10: Backtest RL

### 10.1 Evaluación del agente RL
- [ ] Crear un `TradingEnv` nuevo sobre el split de test.
- [ ] Cargar agente entrenado: `PPO.load(run_dir / "ppo_agent.zip")`.
- [ ] Ejecutar episodio determinista completo.
- [ ] Recolectar equity curve.
- [ ] Calcular métricas con `Backtester.compute_metrics()` (o equivalente).

### 10.2 Evaluación robusta multi-periodo **v1**
- [ ] Implementar evaluación en al menos 3 periodos no solapados del split de test:
  - Dividir el test en 3 tercios: test_1, test_2, test_3.
  - Ejecutar el agente en cada uno y calcular métricas por separado.
  - Reportar media y desviación de: total_return, sharpe, max_drawdown, win_rate.
- [ ] Si el agente funciona bien en solo 1 de 3 periodos → probablemente sobreajustado. Mostrar warning en la UI.
- **Verificación**: las métricas individuales por periodo están dentro de un rango razonable (no	varian por más de 3x entre periodos).

### 10.3 Comparativa final
- [ ] Tabla única con 3 filas:

| Estrategia | Return | Sharpe | Max DD | Win Rate | Profit Factor | Trades |
|---|---|---|---|---|---|---|
| Buy & Hold | X | X | X | — | — | 1 |
| LSTM puro | X | X | X | X | X | X |
| RL + LSTM | X | X | X | X | X | X |

- [ ] Gráfico con las 3 equity curves superpuestas.
- **Verificación**: las 3 filas tienen valores numéricos razonables. RL no necesariamente supera a las otras dos.

---

## Fase 11: Persistencia y experimentos

### 11.1 Guardado automático
- [ ] Cada run guarda en `runs/{run_id}/`:
  - `config.json` — AppConfig serializado.
  - `best_model.pt` — pesos del LSTM.
  - `ppo_agent.zip` — agente RL (si se entrenó).
  - `log.txt` — log completo.
  - `metrics.json` — métricas de backtest LSTM + RL + buy & hold.
  - `equity_lstm.csv` y `equity_rl.csv` — curvas de equity.
  - `scaler.pkl` — StandardScaler ajustado (para reproducibilidad).
- **Verificación**: tras completar un run, la carpeta contiene los 7-8 archivos.

### 11.2 UI de experimentos
- [ ] Lista de runs anteriores (leer carpetas en `runs/`).
- [ ] Botón "Cargar configuración" que rellena todos los inputs de la UI desde un `config.json`.
- [ ] Botón "Exportar resultados" que genera un CSV con todas las métricas de todos los runs.
- [ ] Botón "Comparar runs" que muestra tabla con métricas de runs seleccionados.
- **Verificación**: hacer 2 runs, verlos en la lista, cargar config de uno, exportar CSV.

---

## Fase 12: Pulido final

### 12.1 Edge cases
- [ ] CSV con menos de 100 filas → error claro: "Se necesitan al menos N filas para sequence_length=60 + prediction_horizon=5".
- [ ] CSV sin columna `Volume` → no es bloqueante. Calcular features que no dependan de volumen (saltar `volume_norm`).
- [ ] Todas las señales son FLAT → backtest muestra warning "Sin señales de trading generadas".
- [ ] Entrenamiento LSTM diverge (loss → NaN) → early stopping + mensaje "El entrenamiento divergió, prueba reducir learning_rate".
- **Verificación**: forzar cada edge case manualmente → la app no crashea y muestra mensaje descriptivo.

### 12.2 Disclaimer y límites
- [ ] Disclaimer visible siempre en la UI.
- [ ] Tooltip o sección "Acerca de" con las limitaciones de la sección 13 del documento maestro.
- **Verificación**: el disclaimer se ve al arrancar. Tooltip accesible.

### 12.3 Reproducibilidad
- [ ] `random.seed(config.seed)` al inicio de `main()`.
- [ ] `np.random.seed(config.seed)`.
- [ ] `torch.manual_seed(config.seed)`.
- [ ] `set_seed(config.seed)` de SB3 si está disponible.
- [ ] Semilla visible en UI (panel de configuración global) y guardada en `config.json`.
- **Verificación**: dos runs con misma semilla producen exactamente las mismas métricas.

---

## Orden de ejecución recomendado

```
0.1 → 0.2 → 0.3 → 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 → 3.1 → 3.2 → 3.3 → 3.4
→ 4.1 → 4.2 → 4.3 → 5.1 → 5.2 → 5.3 → 6.1 → 6.2 → 7.1 → 7.2
→ 8.1 → 8.2 → 9.1 → 9.2 → 10.1 → 10.2 → 11.1 → 11.2 → 12.1 → 12.2 → 12.3
```

Cada flecha es una dependencia estricta: lo de la izquierda debe estar completo antes de empezar lo de la derecha.

### Smoke tests por fase

Tras completar cada fase, ejecutar el smoke test correspondiente antes de pasar a la siguiente:

| Fase | Smoke test |
|---|---|
| 0 | `pip install -r requirements.txt` y `python -c "import torch, nicegui, gymnasium, pandas"` |
| 1 | `python trading_lstm_rl_app.py` abre la UI con disclaimer y tabs |
| 2 | Cargar `data/SPY.csv` desde la UI y ver resumen sin errores |
| 3 | Pulsar "Generar features" y ver las 11 features + filas descartadas |
| 4 | Crear `SequenceDataset` y verificar forma de un batch |
| 5 | Entrenar 3 epochs y ver gráfico de loss |
| 6 | Ver señales y matriz de confusión en la UI |
| 7 | Ejecutar backtest y ver equity curve comparada con buy & hold |
| 8 | `check_env(env)` sin warnings + action_masks + 1000 pasos aleatorios sin crash + max_drawdown termina episodio |
| 9 | Entrenar 5000 timesteps con VecNormalize y cargar agente con `PPO.load()` |
| 10 | Ver tabla comparativa buy & hold vs LSTM vs RL + métricas en 3 periodos de test |
| 11 | Carpeta `runs/` contiene config.json, best_model.pt, metrics.json |
| 12 | Dos runs con misma semilla producen mismas métricas |

---

## Tiempo estimado total

| Fase | Pasos | Tiempo estimado |
|---|---|---|
| 0: Entorno | 3 | 15 min |
| 1: Esqueleto | 4 | 45 min |
| 2: Datos | 2 | 30 min |
| 3: Features | 4 | 45 min |
| 4: Dataset | 3 | 30 min |
| 5: LSTM | 3 | 60 min |
| 6: Señales | 2 | 20 min |
| 7: Backtest | 2 | 45 min |
| 8: Entorno RL | 2 | 60 min |
| 9: RL Train | 2 | 30 min |
| 10: Backtest RL | 3 | 30 min |
| 11: Persistencia | 2 | 30 min |
| 12: Pulido | 3 | 30 min |
| **Total** | **35 pasos** | **~8 horas** |

---

## Troubleshooting / FAQ

### El entrenamiento LSTM tarda demasiado en CPU
- **Causa:** `epochs=50` y `sequence_length=60` con miles de filas pueden ralentizar el entrenamiento significativamente en CPU.
- **Solución:** Reduce `epochs` a 10-20 y `hidden_size` a 32 para pruebas rápidas. Si dispones de GPU, asegúrate de que PyTorch detecta CUDA: `python -c "import torch; print(torch.cuda.is_available())"`.

### NiceGUI no abre el navegador
- **Causa:** El puerto 8080 puede estar ocupado o el navegador por defecto no responde.
- **Solución:** Abre manualmente `http://localhost:8080`. Si el puerto está ocupado, cambia el puerto en `ui.run(port=8081)`.

### PPO no converge o el reward es siempre negativo
- **Causa:** Reward shaping agresivo, learning_rate muy alta, o falta de normalización de recompensas.
- **Solución:** Verifica que usas `VecNormalize` durante el entrenamiento (Fase 9.1). Reduce `learning_rate` a 1e-4. Aumenta `total_timesteps` a 50k+.

### Error de memoria (`MemoryError` o `Killed`) al generar features
- **Causa:** Dataset muy grande (>100k filas) o `sequence_length` excesivamente alto.
- **Solución:** Reduce `sequence_length` a 30. Considera procesar datos por chunks o reducir la ventana de indicadores (ej. SMA 20 → SMA 10).

### `check_env(env)` devuelve warnings
- **Causa:** El espacio de observación no coincide con lo que devuelve `reset()` o `step()`, o hay valores `NaN`/`inf`.
- **Solución:** Asegúrate de que `_get_observation()` devuelve siempre un `np.array` de forma `(observation_dim,)` y tipo `float32`. Verifica que no hay `NaN` en features después del escalado.

### Las métricas cambian ligeramente entre ejecuciones con la misma seed
- **Causa:** Algunas operaciones en PyTorch o NumPy no son deterministas por defecto, especialmente en GPU.
- **Solución:** Esto es normal dentro de una tolerancia numérica (~1e-5). Si la varianza es mayor, verifica que no hay threads en background modificando estado global.

### CSV con columnas en español (Fecha, Apertura, Cierre...)
- **Causa:** El `DataManager` espera nombres en inglés (`Date`, `Open`, `High`, `Low`, `Close`, `Volume`).
- **Solución:** Renombra las columnas antes de cargar o extiende `DataManager.load_csv()` para mapear nombres comunes en español.

### El backtest muestra retornos imposiblemente altos
- **Causa:** Posible data leakage (el scaler se ajustó con todo el dataset) o look-ahead bias en features.
- **Solución:** Revisa Fase 3.3: el `StandardScaler` debe ajustarse **solo** con `train`. Ninguna feature debe usar información futura.

### No se pueden abrir posiciones short en el backtest
- **Causa:** El motor de backtesting puede estar configurado solo para posiciones long.
- **Solución:** Verifica que `Backtester` maneja señales `"SHORT"` y calcula el PnL correctamente para posiciones cortas.

### Error al cargar modelo LSTM guardado (`best_model.pt`)
- **Causa:** Arquitectura del modelo cambió entre guardado y carga, o el archivo está corrupto.
- **Solución:** Asegúrate de que `LSTMTradingModel` se instancia con los mismos hiperparámetros (`input_size`, `hidden_size`, `num_layers`) que al guardar. Guarda la config junto al modelo.
