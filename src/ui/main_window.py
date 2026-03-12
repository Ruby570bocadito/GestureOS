from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QStatusBar,
    QMenuBar, QMenu, QCheckBox, QGroupBox, QSlider,
    QFrame, QSplitter, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QAction, QIcon, QFont

from src.core.config import OVERLAY_FPS
from src.core.gesture_recognizer import GestureType
from src.input.voice_assistant import VoiceState
from src.ai.desktop_agent import AgentState


class MainWindow(QMainWindow):
    start_system = pyqtSignal()
    stop_system = pyqtSignal()
    toggle_mouse = pyqtSignal()
    toggle_keyboard = pyqtSignal()
    toggle_voice = pyqtSignal()
    toggle_ai = pyqtSignal()
    speed_changed = pyqtSignal(int)   # 1–5

    def __init__(self):
        super().__init__()

        self.setWindowTitle("GestureOS - Control por Gestos")
        self.setMinimumSize(800, 600)

        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()

        self._is_running = False

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        header = self._create_header()
        main_layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._create_control_panel()
        splitter.addWidget(left_panel)

        right_panel = self._create_log_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 500])

        main_layout.addWidget(splitter)

        control_buttons = self._create_control_buttons()
        main_layout.addWidget(control_buttons)

    def _create_header(self) -> QFrame:
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        layout = QVBoxLayout(frame)

        title = QLabel("GestureOS")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Sistema de Control por Gestos con IA")
        subtitle.setFont(QFont("Arial", 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        return frame

    def _create_control_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("Controles")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        mouse_group = QGroupBox("Mouse Virtual")
        mouse_layout = QVBoxLayout(mouse_group)

        self.mouse_enabled = QCheckBox("Activar Mouse")
        self.mouse_enabled.setChecked(True)
        mouse_layout.addWidget(self.mouse_enabled)

        help_text = QLabel(
            "MANO DERECHA (cursor)\n"
            "  🖐️ Palma abierta  → Mover cursor\n"
            "  ✊ Puño          → Click izquierdo\n"
            "  ✌️ Peace (V)     → Click derecho\n"
            "  🤏 Pinch          → Arrastrar (drag)\n"
            "  ☝️ Un dedo arriba → Modo scroll\n\n"
            "MANO IZQUIERDA (atajo)\n"
            "  👍 Thumb Up       → Click izquierdo\n"
            "  👎 Thumb Down     → Click derecho\n\n"
            "AMBAS MANOS\n"
            "  👍👍 2x Thumbs Up   → Teclado ON/OFF"
        )
        help_text.setStyleSheet("color: #444; font-size: 10px; padding: 4px;")
        help_text.setWordWrap(True)
        mouse_layout.addWidget(help_text)

        # ─ Sensitivity slider ─
        sens_label = QLabel("Velocidad del ratón:")
        sens_label.setStyleSheet("font-size: 10px; color: #555; margin-top: 4px;")
        mouse_layout.addWidget(sens_label)

        slider_row = QHBoxLayout()
        slow_lbl = QLabel("Lento")
        slow_lbl.setStyleSheet("font-size: 9px; color: #888;")
        slider_row.addWidget(slow_lbl)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(5)
        self.speed_slider.setValue(3)   # default mid
        self.speed_slider.setTickInterval(1)
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_slider.setFixedHeight(24)
        self.speed_slider.valueChanged.connect(lambda v: self.speed_changed.emit(v))
        slider_row.addWidget(self.speed_slider)

        fast_lbl = QLabel("Rápido")
        fast_lbl.setStyleSheet("font-size: 9px; color: #888;")
        slider_row.addWidget(fast_lbl)
        mouse_layout.addLayout(slider_row)

        layout.addWidget(mouse_group)

        keyboard_group = QGroupBox("Teclado Virtual")
        keyboard_layout = QVBoxLayout(keyboard_group)

        self.keyboard_enabled = QCheckBox("Activar Teclado")
        keyboard_layout.addWidget(self.keyboard_enabled)

        help_text2 = QLabel(
            "👍👍 2x Thumbs Up = Activar/Desactivar\n"
            "Pinch / clic en tecla = Escribir\n"
            "Checkbox aquí = Control manual"
        )
        help_text2.setStyleSheet("color: gray; font-size: 10px;")
        keyboard_layout.addWidget(help_text2)

        layout.addWidget(keyboard_group)

        voice_group = QGroupBox("Asistente de Voz")
        voice_layout = QVBoxLayout(voice_group)

        self.voice_enabled = QCheckBox("Activar Voz")
        voice_layout.addWidget(self.voice_enabled)

        layout.addWidget(voice_group)

        ai_group = QGroupBox("Agente IA")
        ai_layout = QVBoxLayout(ai_group)

        self.ai_enabled = QCheckBox("Activar Agente IA")
        ai_layout.addWidget(self.ai_enabled)

        layout.addWidget(ai_group)

        layout.addStretch()

        return widget

    def _create_log_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("Registro de Actividad")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        self.log_list = QListWidget()
        self.log_list.setMaximumHeight(200)
        layout.addWidget(self.log_list)

        gesture_label = QLabel("Gesto Detectado:")
        layout.addWidget(gesture_label)

        self.gesture_display = QLabel("Ninguno")
        self.gesture_display.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.gesture_display.setStyleSheet("color: blue; padding: 10px;")
        self.gesture_display.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        layout.addWidget(self.gesture_display)

        layout.addStretch()

        return widget

    def _create_control_buttons(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        self.start_button = QPushButton("Iniciar Sistema")
        self.start_button.setMinimumHeight(50)
        self.start_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.start_button.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Detener Sistema")
        self.stop_button.setMinimumHeight(50)
        self.stop_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_button)

        self.settings_button = QPushButton("Configuración")
        self.settings_button.setMinimumHeight(50)
        layout.addWidget(self.settings_button)

        return widget

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Archivo")

        exit_action = QAction("Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("Ver")

        self.show_overlay_action = QAction("Mostrar Overlay", self)
        self.show_overlay_action.setCheckable(True)
        self.show_overlay_action.setChecked(True)
        view_menu.addAction(self.show_overlay_action)

        help_menu = menubar.addMenu("Ayuda")

        about_action = QAction("Acerca de", self)
        help_menu.addAction(about_action)

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sistema listo para iniciar")

    def _on_start_clicked(self):
        self._is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_bar.showMessage("Sistema ejecutándose...")
        self.start_system.emit()

    def _on_stop_clicked(self):
        self._is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("Sistema detenido")
        self.stop_system.emit()

    def log_message(self, message: str):
        item = QListWidgetItem(f"[{self._get_timestamp()}] {message}")
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def update_gesture(self, gesture: str):
        self.gesture_display.setText(gesture)

    def update_status(self, status: str):
        self.status_bar.showMessage(status)

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def set_mouse_enabled(self, enabled: bool):
        self.mouse_enabled.setChecked(enabled)

    def set_keyboard_enabled(self, enabled: bool):
        self.keyboard_enabled.setChecked(enabled)

    def set_voice_enabled(self, enabled: bool):
        self.voice_enabled.setChecked(enabled)

    def set_ai_enabled(self, enabled: bool):
        self.ai_enabled.setChecked(enabled)

    @pyqtSlot()
    def _invoke_keyboard_on(self):
        """Thread-safe slot: update UI when keyboard is activated via gesture."""
        self.keyboard_enabled.setChecked(True)
        self.log_message("Teclado activado (👍👍)")

    @pyqtSlot()
    def _invoke_keyboard_off(self):
        """Thread-safe slot: update UI when keyboard is deactivated via gesture."""
        self.keyboard_enabled.setChecked(False)
        self.log_message("Teclado cerrado (👍👍)")
