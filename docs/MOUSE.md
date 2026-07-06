# HandsControl - Control de Mouse por Gestos

## Activar Teclado Virtual
Para activar el teclado virtual, haz **thumbs up con ambas manos** al mismo tiempo.

Una vez activado, usa **pinch** (dedo indice + pulgar juntos) sobre las teclas para escribir.

Para cerrar el teclado, vuelve a hacer **thumbs up con ambas manos**.

## Gestos del Mouse

### Mano Izquierda (Mover) - Mostrada como "Mover" en el overlay
| Gesto | Accion |
|-------|--------|
| 🖐️ Palma abierta | Mover el cursor por la pantalla |
| 🤏 Pinch | Arrastrar (drag) |
| ✌️ Dos dedos | Scroll natural (trackpad) |
| 🖐️ Quieta 1.5s | Dwell click automatico |

### Mano Derecha (Acciones) - Mostrada como "Accion" en el overlay
| Gesto | Accion |
|-------|--------|
| ✊ Puño | Click izquierdo |
| 👎 Thumb Down | Click derecho |
| 🤌 Index wink | Click suave |
| ☝️ Un dedo arriba | Scroll clasico |
| ✌️ Peace + mover | Seleccionar texto |
| ✊→✊ Doble puño | Ctrl+C |
| 👎→👎 Doble thumb down | Ctrl+Z |
| 👎→👍 Down then Up | Ctrl+V |

### Ambas Manos
| Gesto | Accion |
|-------|--------|
| 🖐️+🖐️ Ambas palmas | Zoom in/out (Ctrl+scroll) |
| 👍+👍 Ambas thumbs up (1s) | Teclado ON/OFF |

## Configuracion

El archivo `src/core/config.py` contiene los parametros de configuracion:

```python
MOUSE_SMOOTHING = 0.30          # Suavizado del movimiento (0-1)
MOUSE_SPEED_MULTIPLIER = 2.2    # Velocidad del cursor
MOUSE_DEADZONE = 8               # Zona sin movimiento (pixels)
DWELL_THRESHOLD = 1.5            # Segundos para dwell click
DWELL_DEADZONE = 25              # Zona muerta para dwell (pixels)
```

Tambien puedes ajustar la velocidad del cursor en tiempo real desde el slider en el panel principal (1=lento, 5=rapido).

## Seguridad

- **PyAutoGUI FAILSAFE** esta habilitado: mueve el cursor a la esquina superior izquierda para detener cualquier accion automatica.
- Los logs se guardan en `logs/handscontrol.log` para debugging.

## Solucion de Problemas

- **El cursor solo se mueve en una direccion**: Verifica que la camara este funcionando correctamente
- **No detecta la mano**: Asegurate de tener buena iluminacion
- **Clicks no funcionan**: Verifica que el gesto sea reconocido correctamente en el overlay
- **Error de Qt xcb**: Instala `sudo apt install libxcb-cursor0`
- **Error de PyAudio**: Instala `sudo apt install portaudio19-dev`
