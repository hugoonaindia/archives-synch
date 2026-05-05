# LSTM + RL Trading App

Aplicación local de trading algorítmico con **modelo LSTM supervisado** + **agente de aprendizaje por refuerzo (RL)** y una interfaz visual con **NiceGUI**.

> ⚠️ **Modo investigación/backtesting.** No ejecuta operaciones reales. No constituye asesoramiento financiero.

---

## ¿Qué hace esta aplicación?

1. **Carga y valida** datos históricos OHLCV (CSV local o descarga via `yfinance`).
2. **Ingeniería de features** técnicas (RSI, MACD, volatilidad, medias móviles, etc.).
3. **Entrena un modelo LSTM** supervisado para clasificar dirección del mercado (bajista / neutral / alcista).
4. **Backtesta la estrategia LSTM** pura con comisiones, slippage, stop loss y take profit.
5. **Entrena un agente RL** (PPO con Stable-Baselines3) que utiliza las señales del LSTM + estado del mercado para decidir cuándo operar.
6. **Compara** resultados: Buy & Hold vs LSTM puro vs RL + LSTM.
7. **Persiste** modelos, configuraciones, métricas y logs por experimento.

Todo en **un único script Python** (`trading_lstm_rl_app.py`) con arquitectura interna limpia (clases, dataclasses y secciones delimitadas).

---

## Requisitos

- Python >= 3.11
- pip

### Dependencias principales

```text
pandas>=2.0,<3.0
numpy>=1.24,<2.0
scikit-learn>=1.3,<1.6
torch>=2.0,<3.0
matplotlib>=3.7,<4.0
nicegui>=1.4,<3.0
gymnasium>=0.29,<1.1
stable-baselines3>=2.0,<3.0
yfinance>=0.2,<1.0
```

Ver [`requirements.txt`](./requirements.txt) para la lista completa.

---

## Instalación rápida

```bash
# 1. Clonar o descargar el repositorio
cd LSTM-RL-Trader

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la aplicación
python trading_lstm_rl_app.py
```

La aplicación se abrirá automáticamente en tu navegador (por defecto en `http://localhost:8080`).

---

## Flujo mínimo verificable (Quick Start)

Para validar que todo funciona en menos de 2 minutos:

```
1. Arrancar la app           → python trading_lstm_rl_app.py         (~2s)
2. Cargar CSV de ejemplo     → pestaña Datos → Cargar CSV             (~1s)
3. Generar features          → pestaña Features → Generar             (~2s)
4. Entrenar LSTM (rápido)    → pestaña LSTM → epochs=10 → Entrenar    (~30s con CPU)
5. Backtest LSTM             → pestaña Backtest LSTM → Ejecutar       (~2s)
6. Ver equity curve y Sharpe → comparar contra buy & hold             (~1s)
```

> El RL se añade como etapa opcional después de verificar que el flujo base funciona.

---

## Estructura del proyecto

```
LSTM-RL-Trader/
├── trading_lstm_rl_app.py          # Script principal único
├── requirements.txt                # Dependencias
├── README.md                       # Este archivo
├── AGENTS.md                       # Guía para agentes de IA / desarrolladores
├── documento_maestro_lstm_rl_trading_nicegui.md   # Especificación completa
├── pasos_accionables.md            # Plan de implementación paso a paso
├── data/                           # Datos CSV de ejemplo
├── models/                         # Modelos entrenados (LSTM / RL)
└── runs/                           # Experimentos: config, logs, métricas, equity curves
```

---

## Documentación técnica

- **[Documento maestro](documento_maestro_lstm_rl_trading_nicegui.md)** — Especificación completa del sistema: arquitectura, modelo LSTM, entorno RL, interfaz NiceGUI, políticas de reward shaping, criterios de aceptación.
- **[Pasos accionables](pasos_accionables.md)** — Plan de implementación atómico, verificable y con dependencias explícitas.
- **[AGENTS.md](AGENTS.md)** — Convenciones de código, decisiones arquitectónicas y guía para modificar el proyecto.

---

## Limitaciones importantes

1. **No predice mercados reales.** Un LSTM sobre features OHLCV no captura la complejidad de los mercados financieros. Los resultados positivos en backtest **no implican rentabilidad futura**.
2. **Backtest ≠ realidad.** No se modelan: impacto de mercado, liquidez intradía, restricciones de short-selling, costes de financiación, horarios, noticias ni eventos corporativos.
3. **El RL puede sobreajustar brutalmente.** Sin walk-forward validation, el agente PPO puede memorizar patrones espurios. Las métricas en test deben tomarse con escepticismo.
4. **No es software de producción.** No tiene tests automatizados, no maneja concurrencia real, no tiene autenticación, no escala a múltiples tickers sin modificaciones.
5. **Las decisiones de inversión son responsabilidad del usuario.** Esta herramienta no sustituye el criterio de un profesional financiero.

---

## Requisitos de hardware

| Componente | Mínimo recomendado | Notas |
|---|---|---|
| RAM | 4 GB | Suficiente para datasets de ~5 años diarios |
| CPU | 2 cores | Entrenamiento LSTM lento pero viable en CPU |
| GPU | Opcional | PyTorch con CUDA acelera entrenamiento LSTM y RL |
| Disco | 500 MB | Cada run genera ~5-20 MB (modelos + logs) |

---

## Contribuir

Este proyecto es principalmente una herramienta educativa y de prototipado personal. Si deseas extenderlo:

- Revisa [`AGENTS.md`](AGENTS.md) para entender las convenciones.
- Consulta el [documento maestro](documento_maestro_lstm_rl_trading_nicegui.md) para ver funcionalidades planificadas (v2+).
- Asegúrate de no romper el flujo mínimo verificable.

---

## Licencia

[MIT](LICENSE) — Uso bajo tu propia responsabilidad. Este software es con fines educativos e investigativos únicamente.
