# Project State — LSTM RL

## Meta
- **Última actualización:** 2026-05-28
- **Rating:** 9.6/10

## Stack
- Python, TensorFlow, Keras, NiceGUI, Alpaca API

## Tests
- **Total:** (ver feature_list.json)

## Bugs
| ID | Descripción | Estado |
|----|-------------|--------|
| 1 | Modelo LSTM colapsado — predice "neutral" | pendiente |
| 2 | Falta balanceo de clases en dataset | pendiente |
| 3 | Features de regime no implementadas | pendiente |

## Deuda Técnica
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| 1 | Monolito ~77K líneas | Importante |
| 2 | Falta class weighting en loss | Moderado |
| 3 | No hay ensemble LSTM + RF | Moderado |

## Próximo
Implementar balanceo de clases, añadir features de regime, re-entrenar.
