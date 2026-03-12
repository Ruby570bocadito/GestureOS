# GestureOS 🖐️ 🎙️ 🤖

> Controla tu ordenador con **gestos de mano**, **voz** e **IA** — sin tocar el teclado ni el ratón.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Latest-orange)
![Estado](https://img.shields.io/badge/Estado-En%20Desarrollo-yellow)

---

## ¿Qué es GestureOS?

GestureOS es un sistema de control del escritorio por gestos de mano en tiempo real, control por voz en español y un agente de IA con visión. Usa la cámara web, MediaPipe, reconocimiento de voz y Ollama para traducir gestos y palabras en acciones reales del sistema operativo.

---

## ✨ Funcionalidades

| Módulo | Estado | Descripción |
|---|---|---|
| 🖱️ Mouse Virtual | ✅ Funcional | Controla el cursor con la mano izquierda |
| ⌨️ Teclado Virtual | ✅ Funcional | Teclado flotante activado por gestos o voz |
| ⏳ Dwell-click | ✅ Funcional | Auto-click al mantener la palma quieta 1.5s |
| 🔍 Zoom dos manos | ✅ Funcional | Separar/juntar palmas = Ctrl+scroll |
| ⌨️ Atajos por gesto | ✅ Funcional | Doble puño = Ctrl+C, etc. |
| 🎚️ Slider velocidad | ✅ Funcional | Ajusta sensibilidad del ratón en tiempo real |
| 🤌 Wink click | ✅ Funcional | Índice cerrado = click suave |
| 🎙️ Control por Voz | ✅ Funcional | 50+ comandos en español |
| 🤖 Agente IA | ✅ Funcional | Ollama + visión de pantalla |

---

## 🖐️ Gestos del Ratón

### Mano Izquierda — Cursor
| Gesto | Acción |
|---|---|
| 🖐️ Palma abierta | Mover cursor |
| 👍 Thumb Up | También mueve cursor |
| 🤏 Pinch | Arrastrar (drag) |
| ✌️ Dos dedos | Scroll natural (trackpad) |
| 🖐️ **Quieta 1.5s** | ⏳ **Dwell-click automático** |

### Mano Derecha — Acciones
| Gesto | Acción |
|---|---|
| ✊ Puño | Click izquierdo |
| 👍 Thumb Up | Click izquierdo |
| 👎 Thumb Down | Click derecho |
| 🤌 Índice cerrado | Click suave (wink) |
| ✌️ Peace + mover | Seleccionar texto (drag) |
| ☝️ Un dedo arriba | Scroll clásico |
| ✊→✊ Doble puño | Ctrl+C |
| 👎→👎 Doble thumbs down | Ctrl+Z |
| 👎→👍 Down then Up | Ctrl+V |

### Ambas Manos
| Gesto | Acción |
|---|---|
| 🖐️+🖐️ Ambas palmas abiertas | 🔍 Zoom in/out (Ctrl+scroll) |
| 👍+👍 Ambas thumbs up (1s) | ⌨️ Activar/desactivar teclado |

---

## 🎙️ Comandos de Voz

Activa el micrófono en el panel (checkbox "Activar Voz"), luego habla en español:

### Aplicaciones
| Comando | Acción |
|---|---|
| "abrir navegador" | Abre el navegador |
| "abrir bloc de notas" | Abre Notepad |
| "abrir explorador" | Abre el explorador de archivos |
| "abrir calculadora" | Abre la calculadora |
| "abrir terminal" | Abre CMD |

### Ventanas
| Comando | Acción |
|---|---|
| "cerrar ventana" | Alt+F4 |
| "minimizar ventana" | Minimiza |
| "maximizar ventana" | Maximiza |
| "cambiar ventana" | Alt+Tab |
| "mostrar escritorio" | Win+D |

### Edición
| Comando | Acción |
|---|---|
| "copiar" | Ctrl+C |
| "pegar" | Ctrl+V |
| "cortar" | Ctrl+X |
| "deshacer" | Ctrl+Z |
| "seleccionar todo" | Ctrl+A |
| "guardar" | Ctrl+S |
| "buscar" | Ctrl+F |

### Sistema
| Comando | Acción |
|---|---|
| "subir volumen" | Volumen +5 |
| "bajar volumen" | Volumen -5 |
| "silenciar" | Mute |
| "captura" | Screenshot |
| "scroll arriba / abajo" | Scroll |
| "zoom in / out" | Ctrl +/- |
| "apagar voz" | Desactiva el micrófono |

### Agente IA
| Comando | Acción |
|---|---|
| "agente [pregunta]" | Pregunta al agente IA |
| "¿qué hay en mi pantalla?" | IA analiza la pantalla |
| Cualquier frase no reconocida | Se envía al agente IA |

---

## 🤖 Agente IA

Requiere [Ollama](https://ollama.ai/) instalado y corriendo localmente.

```bash
# Instalar modelo (una sola vez)
ollama pull llama3.2
ollama pull llava   # para visión de pantalla
```

El agente puede:
- Ejecutar cualquier acción del sistema (abrir apps, hacer clic, escribir...)
- Analizar la pantalla con visión (`"¿qué hay en mi pantalla?"`)
- Mantener conversación contextual
- Responder con TTS (texto a voz)

---

## ⌨️ Teclado Virtual

El teclado flotante aparece en la **parte inferior** y **nunca roba el foco**:

| Acción | Cómo |
|---|---|
| Activar | 👍+👍 (gestos) **ó** "activar teclado" (voz) **ó** checkbox |
| Escribir | Clic en teclas → se escribe en la app activa |
| Mayúsculas | ⇧ SHIFT (una tecla) |
| Números | Botón 123 |
| Borrar | ⌫ |
| Cerrar | ✕ |

---

## 🚀 Instalación

```bash
# 1. Clonar
git clone https://github.com/tu-usuario/GestureOS.git
cd GestureOS

# 2. Dependencias
pip install -r requirements.txt

# 3. Ejecutar
python main.py
```

**Para el agente IA:**
```bash
# Instalar Ollama desde https://ollama.ai/
ollama pull llama3.2
```

---

## ⚙️ Configuración (`src/core/config.py`)

| Parámetro | Valor | Descripción |
|---|---|---|
| `MOUSE_SMOOTHING` | 0.30 | Suavizado (0=mínimo, 1=máximo lag) |
| `MOUSE_SPEED_MULTIPLIER` | 2.2 | Velocidad del cursor |
| `MOUSE_DEADZONE` | 8px | Zona muerta de movimiento |
| `MEDIAPIPE_DETECTION_CONFIDENCE` | 0.8 | Confianza detección |
| `MEDIAPIPE_TRACKING_CONFIDENCE` | 0.7 | Confianza seguimiento |
| `VOICE_LANGUAGE` | es | Idioma reconocimiento de voz |
| `OLLAMA_MODEL` | llama3.2 | Modelo de texto para el agente |
| `OLLAMA_VISION_MODEL` | llava | Modelo con visión |

También puedes ajustar la velocidad del ratón **en tiempo real** desde el slider en el panel principal (1=lento, 5=rápido).

---

## 🗂️ Estructura

```
GestureOS/
├── main.py
├── src/
│   ├── core/
│   │   ├── config.py
│   │   ├── gesture_recognizer.py   ← incluye INDEX_CLICK (wink)
│   │   └── gesture_tracker.py
│   ├── input/
│   │   ├── virtual_mouse.py        ← dwell, zoom, two-finger scroll
│   │   ├── virtual_keyboard.py
│   │   └── voice_assistant.py      ← 50+ comandos en español
│   ├── ui/
│   │   ├── main_window.py          ← slider velocidad
│   │   ├── overlay.py              ← icono gesto + dwell ring + mode badge
│   │   └── virtual_keyboard_widget.py
│   ├── ai/
│   │   ├── desktop_agent.py        ← Ollama JSON actions
│   │   └── vision_helper.py
│   └── utils/
│       ├── action_executor.py      ← ejecuta acciones SO (voz+IA)
│       └── system_control.py
└── hand_landmarker.task
```
