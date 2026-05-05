# LSTM + RL Trading App

Aplicacion de investigacion y backtesting que combina modelos LSTM para prediccion de precios con agentes de Reinforcement Learning para toma de decisiones de trading. Interfaz web via NiceGUI.

> **ADVERTENCIA:** Este proyecto es solo para investigacion y backtesting. No ejecuta operaciones reales ni constituye asesoramiento financiero.

## Requisitos

- Python >= 3.11
- pip

## Instalacion rapida

```bash
# Clonar repositorio
git clone <repo-url>
cd LSTM-RL-Trader

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python trading_lstm_rl_app.py
```

Abre tu navegador en `http://localhost:8080`.

## Flujo rapido

1. **Carga datos** — CSV local o descarga via yfinance
2. **Feature engineering** — Indicadores tecnicos
3. **Entrena LSTM** — Prediccion de direccion (alcista/neutral/bajista)
4. **Backtesting** — Evalua estrategia LSTM
5. **Entrena RL** — Agente PPO con entorno Gymnasium
6. **Evalua RL** — Metricas de rendimiento

## Estructura del proyecto

```
LSTM-RL-Trader/
├── trading_lstm_rl_app.py   # Aplicacion principal (single-file)
├── requirements.txt          # Dependencias
├── pyproject.toml           # Configuracion de herramientas
├── Dockerfile               # Imagen Docker multi-stage
├── docker-compose.yml       # Despliegue local
├── .env.example             # Variables de entorno
├── .gitignore               # Exclusiones de git
├── .dockerignore            # Exclusiones de Docker
├── CHANGELOG.md             # Historial de cambios
├── LICENSE                  # Licencia MIT
├── REVIEW_MASTER.md         # Registro de code reviews
├── tests/                   # Suite de tests (pytest)
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_coverage.py     # Edge cases y coverage boost
│   ├── test_experiment.py
│   └── test_logging.py
├── data/                    # Datos de ejemplo (CSV)
├── models/                  # Modelos entrenados
├── runs/                    # Experimentos y logs
└── documentos/              # Documentacion tecnica
    ├── AGENTS.md            # Guia para desarrolladores
    ├── documento_maestro_lstm_rl_trading_nicegui.md
    └── pasos_accionables.md
```

## Tests

```bash
python -m pytest tests/ -v --cov=trading_lstm_rl_app --cov-fail-under=80
```

Suite actual: **101 tests**, **84% coverage** (umbral mínimo: 80%).

## Linting

```bash
python -m ruff check .
python -m ruff format .
```

## Docker

```bash
docker-compose up --build
```

## Documentacion tecnica

- [AGENTS.md](documentos/AGENTS.md) — Guia para desarrolladores y agentes de IA
- [Documento maestro](documentos/documento_maestro_lstm_rl_trading_nicegui.md) — Especificacion completa del sistema
- [Pasos accionables](documentos/pasos_accionables.md) — Plan de implementacion por fases

## Licencia

[MIT](LICENSE)
