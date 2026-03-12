# GestureOS - Control de Mouse por Gestos

## Activar Teclado Virtual
Para activar el teclado virtual, haz **thumbs up con ambas manos** al mismo tiempo.

Una vez activado, usa **pinch** (dedo índice + pulgar juntos) sobre las teclas para escribir.

Para cerrar el teclado, vuelve a hacer **thumbs up con ambas manos**.

## Gestos del Mouse

### Mano Derecha (Mover) - Mostrada como "Mover" en el overlay
| Gesto | Acción |
|-------|--------|
| 🖐️ Palma abierta | Mover el mouse por la pantalla |
| ✊ Puño | Detener movimiento |

### Mano Izquierda (Clicks) - Mostrada como "Click" en el overlay
| Gesto | Acción |
|-------|--------|
| 👍 Thumb up | Click izquierdo |
| 👍👍 Thumb up doble (2 veces rápido) | Click derecho |
| ✊ Puño | Click izquierdo |
| ☝️ Dedo índice arriba | Scroll (mover hacia arriba/abajo) |
| ✌️ Peace | Click derecho |
| 🖐️→✊ Abrir y cerrar mano | Arrastrar (drag) |

## Configuración

El archivo `src/core/config.py` contiene los parámetros de configuración:

```python
MOUSE_SMOOTHING = 0.15      # Suavizado del movimiento (0-1)
MOUSE_SPEED_MULTIPLIER = 1.5 # Velocidad del mouse
MOUSE_DEADZONE = 15          # Zona sin movimiento
```

## Solución de Problemas

- **El mouse solo se mueve en una dirección**: Verifica que la cámara esté funcionando correctamente
- **No detecta la mano**: Asegúrate de tener buena iluminación
- **Clicks no funcionan**: Verifica que el gesto sea reconocido correctamente en el overlay
