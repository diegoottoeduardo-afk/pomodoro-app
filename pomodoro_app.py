"""
Pomodoro Focus - Aplicación de escritorio moderna con CustomTkinter
Desarrollada para Windows con soporte de notificaciones nativas, sonidos y gestión de tareas.
"""

import os
import sys
import json
import math
import wave
import struct
import winsound
import datetime
import tkinter as tk
import customtkinter as ctk
from PIL import Image

# Intentar importar winotify para notificaciones nativas de Windows
try:
    from winotify import Notification, audio
    HAS_WINOTIFY = True
except Exception:
    HAS_WINOTIFY = False


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "pomodoro_data.json")
CHIME_WORK_FILE = os.path.join(APP_DIR, "chime_work.wav")
CHIME_BREAK_FILE = os.path.join(APP_DIR, "chime_break.wav")
ICON_FILE = os.path.join(APP_DIR, "pomodoro.ico")
ASSETS_TREE_DIR = os.path.join(APP_DIR, "assets", "tree")




def generate_audio_files():
    """Genera alarmas audibles rítmicas de duración extendida (~7.5 segundos)."""
    sample_rate = 44100

    # 1. Alarma de finalización de trabajo (Secuencia enérgica de campanadas de ~7.5 segundos)
    if not os.path.exists(CHIME_WORK_FILE):
        try:
            total_duration = 7.5
            num_samples = int(sample_rate * total_duration)
            samples = [0.0] * num_samples
            
            num_cycles = 6
            cycle_len = 1.25
            
            for c in range(num_cycles):
                start_t = c * cycle_len
                notes = [
                    (0.00, 1046.50, 0.15, 0.45, 12.0),  # C6
                    (0.18, 1318.51, 0.15, 0.45, 12.0),  # E6
                    (0.36, 1567.98, 0.15, 0.50, 12.0),  # G6
                    (0.54, 2093.00, 0.50, 0.65, 4.5),   # C7 sostenido
                ]
                for note_offset, freq, dur, amp, decay in notes:
                    note_start = int((start_t + note_offset) * sample_rate)
                    dur_samples = int(sample_rate * dur)
                    for i in range(dur_samples):
                        idx = note_start + i
                        if idx < num_samples:
                            t = i / sample_rate
                            env = math.exp(-decay * t)
                            val = amp * (math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t)) * env
                            samples[idx] += val

            with wave.open(CHIME_WORK_FILE, 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                for val in samples:
                    clamped = int(max(-32768, min(32767, val * 32767.0 * 0.75)))
                    wav.writeframes(struct.pack('<h', clamped))
        except Exception as e:
            print(f"Error generando alarma de trabajo: {e}")

    # 2. Alarma de finalización de descanso (Secuencia melódica de ~7.0 segundos)
    if not os.path.exists(CHIME_BREAK_FILE):
        try:
            total_duration = 7.0
            num_samples = int(sample_rate * total_duration)
            samples = [0.0] * num_samples
            
            num_cycles = 5
            cycle_len = 1.4
            
            for c in range(num_cycles):
                start_t = c * cycle_len
                notes = [
                    (0.00, 698.46, 0.22, 0.45, 8.0),   # F5
                    (0.25, 880.00, 0.22, 0.45, 8.0),   # A5
                    (0.50, 1046.50, 0.60, 0.60, 3.8),  # C6 sostenido
                ]
                for note_offset, freq, dur, amp, decay in notes:
                    note_start = int((start_t + note_offset) * sample_rate)
                    dur_samples = int(sample_rate * dur)
                    for i in range(dur_samples):
                        idx = note_start + i
                        if idx < num_samples:
                            t = i / sample_rate
                            env = math.exp(-decay * t)
                            val = amp * (math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t)) * env
                            samples[idx] += val

            with wave.open(CHIME_BREAK_FILE, 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                for val in samples:
                    clamped = int(max(-32768, min(32767, val * 32767.0 * 0.75)))
                    wav.writeframes(struct.pack('<h', clamped))
        except Exception as e:
            print(f"Error generando alarma de descanso: {e}")


def play_sound(mode):
    """Reproduce la alarma rítmica de forma asíncrona en Windows."""
    try:
        sound_path = CHIME_WORK_FILE if mode == "work" else CHIME_BREAK_FILE
        if os.path.exists(sound_path):
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception as e:
        print(f"Error al reproducir sonido: {e}")


def stop_sound():
    """Detiene cualquier sonido o alarma en curso inmediatamente."""
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception as e:
        print(f"Error al detener sonido: {e}")



class PomodoroApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Generar audios si no existen
        generate_audio_files()

        # Cargar datos persistentes
        self.load_data()

        # Configuración de ventana
        self.title("Pomodoro Focus")
        if os.path.exists(ICON_FILE):
            try:
                self.iconbitmap(ICON_FILE)
            except Exception:
                pass
        self.geometry("450x660")
        self.minsize(380, 520)
        self.is_mini_mode = False
        self.normal_geometry = "450x660"

        # Aplicar tema
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))
        ctk.set_default_color_theme("blue")

        # Configurar siempre visible si estaba activo
        if self.settings.get("always_on_top", False):
            self.attributes("-topmost", True)

        # Variables de estado del temporizador
        self.current_mode = "work"  # "work", "short_break", "long_break"
        self.is_running = False
        self.remaining_seconds = self.settings["work_duration"] * 60
        self.total_seconds = self.remaining_seconds
        self.active_task_id = None
        self.completed_pomodoros = getattr(self, "completed_pomodoros", self.stats.get("today_pomodoros", 0))
        self.timer_id = None
        self.is_alarm_ringing = False
        self.is_testing_sound = False
        self.alarm_timer_id = None


        # Paleta de colores temáticos
        self.theme_colors = {
            "work": {
                "accent": "#FF5252",
                "accent_hover": "#E04848",
                "bg_card": ("#F9EAEA", "#2B1D1D"),
                "badge": ("#FFD8D8", "#4A2525"),
                "name": "Enfoque",
                "icon": "🍅"
            },
            "short_break": {
                "accent": "#2ECC71",
                "accent_hover": "#27AE60",
                "bg_card": ("#EAF9F1", "#1D2B22"),
                "badge": ("#D5F5E3", "#1B432E"),
                "name": "Pausa Corta",
                "icon": "☕"
            },
            "long_break": {
                "accent": "#3498DB",
                "accent_hover": "#2980B9",
                "bg_card": ("#EBF5FB", "#1C2430"),
                "badge": ("#D4E6F1", "#1F3A52"),
                "name": "Pausa Larga",
                "icon": "🌴"
            }
        }

        # Construir interfaz gráfica
        self.create_widgets()
        self.setup_keyboard_shortcuts()

        # Restaurar tarea activa si existe o seleccionar la primera pendiente
        if self.active_task_id:
            active_task = next((t for t in self.tasks if t["id"] == self.active_task_id), None)
            if active_task:
                self.active_task_label.configure(text=f"🎯 Tarea actual: {active_task['text']}")
        elif self.tasks:
            incomplete = [t for t in self.tasks if not t.get("completed", False)]
            if incomplete:
                self.set_active_task(incomplete[0])

        # Activar Pausa Larga automáticamente si el último bloque completado completó un ciclo (ej. 4, 8, 12...)
        total_cycles = self.settings.get("cycles_for_long_break", 4)
        if self.completed_pomodoros > 0 and (self.completed_pomodoros % total_cycles == 0):
            self.switch_to_mode("long_break")
        else:
            self.update_timer_display()

        # Chequeo periódico de medianoche cada 30 segundos
        self.after(30000, self.periodic_check)

        # Manejar cierre seguro
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_data(self):
        """Carga configuraciones, tareas y estadísticas guardadas."""
        today_str = datetime.date.today().isoformat()
        default_data = {
            "settings": {
                "work_duration": 25,
                "short_break": 5,
                "long_break": 15,
                "cycles_for_long_break": 4,
                "sound_enabled": True,
                "notifications_enabled": True,
                "auto_start_breaks": False,
                "auto_start_work": False,
                "always_on_top": False,
                "theme": "dark"
            },
            "stats": {
                "date": today_str,
                "today_pomodoros": 0,
                "today_minutes": 0,
                "total_pomodoros": 0,
                "total_minutes": 0
            },
            "tasks": [],
            "active_task_id": None
        }

        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings = {**default_data["settings"], **data.get("settings", {})}
                    self.stats = {**default_data["stats"], **data.get("stats", {})}
                    self.tasks = data.get("tasks", [])
                    self.active_task_id = data.get("active_task_id", None)

                    # Reiniciar contador diario si es un día nuevo
                    if self.stats.get("date") != today_str:
                        self.stats["date"] = today_str
                        self.stats["today_pomodoros"] = 0
                        self.stats["today_minutes"] = 0
                        self.completed_pomodoros = 0
                    else:
                        self.completed_pomodoros = self.stats.get("today_pomodoros", 0)

                    default_streak_data = {
                        "current_streak": 1 if self.stats.get("today_pomodoros", 0) > 0 else 0,
                        "best_streak": 1 if self.stats.get("today_pomodoros", 0) > 0 else 0,
                        "last_study_date": today_str if self.stats.get("today_pomodoros", 0) > 0 else "",
                        "protectors": 1,
                        "is_frozen": False
                    }
                    self.streak_data = {**default_streak_data, **data.get("streak_data", {})}
            except Exception as e:
                print(f"Error leyendo {DATA_FILE}: {e}")
                self.settings = default_data["settings"]
                self.stats = default_data["stats"]
                self.tasks = default_data["tasks"]
                self.active_task_id = None
                self.streak_data = {
                    "current_streak": 0,
                    "best_streak": 0,
                    "last_study_date": "",
                    "protectors": 1,
                    "is_frozen": False
                }
                self.completed_pomodoros = 0
        else:
            self.settings = default_data["settings"]
            self.stats = default_data["stats"]
            self.tasks = default_data["tasks"]
            self.active_task_id = None
            self.streak_data = {
                "current_streak": 0,
                "best_streak": 0,
                "last_study_date": "",
                "protectors": 1,
                "is_frozen": False
            }
            self.completed_pomodoros = 0

        self.update_streak_on_startup()

    def save_data(self):
        """Guarda configuraciones, estadísticas, racha y tareas en el archivo JSON."""
        data = {
            "settings": self.settings,
            "stats": self.stats,
            "streak_data": self.streak_data,
            "tasks": self.tasks,
            "active_task_id": self.active_task_id
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando {DATA_FILE}: {e}")

    def create_widgets(self):
        """Crea todos los contenedores principales y widgets."""
        # Frame principal contenedor
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=16, pady=12)

        # 1. Barra Superior (Header & Quick Actions)
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 10))

        # Título y logotipo
        self.app_title_lbl = ctk.CTkLabel(
            self.header_frame,
            text="🍅 Pomodoro Focus",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        self.app_title_lbl.pack(side="left")

        # Badge de racha diaria en cabecera
        self.header_streak_lbl = ctk.CTkLabel(
            self.header_frame,
            text="🔥 1 día",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FF9F43",
            fg_color=("gray88", "gray22"),
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.header_streak_lbl.pack(side="left", padx=(10, 0))

        # Botón para modo Mini
        self.mini_btn = ctk.CTkButton(
            self.header_frame,
            text="🗖 Mini",
            width=54,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color=("gray85", "gray25"),
            text_color=("black", "white"),
            command=self.toggle_mini_mode
        )
        self.mini_btn.pack(side="right", padx=(4, 0))

        # Botón para fijar ventana (Always on Top)
        topmost_active = self.settings.get("always_on_top", False)
        self.topmost_btn = ctk.CTkButton(
            self.header_frame,
            text="📌 Fijar" if not topmost_active else "📌 Fijado",
            width=65,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color=("#3B8ED0", "#1F6AA5") if topmost_active else ("gray85", "gray25"),
            text_color=("black", "white"),
            command=self.toggle_always_on_top
        )
        self.topmost_btn.pack(side="right", padx=(4, 0))

        # 2. Selector de Modos (Pestañas Enfoque / Pausa Corta / Pausa Larga)
        self.mode_frame = ctk.CTkSegmentedButton(
            self.main_container,
            values=["🍅 Enfoque", "☕ Pausa Corta", "🌴 Pausa Larga"],
            command=self.on_mode_selected,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            selected_color="#FF5252",
            selected_hover_color="#E04848"
        )
        self.mode_frame.set("🍅 Enfoque")
        self.mode_frame.pack(fill="x", pady=(0, 12))

        # 3. Tarjeta del Temporizador (Card Central)
        self.timer_card = ctk.CTkFrame(
            self.main_container,
            corner_radius=16,
            fg_color=self.theme_colors["work"]["bg_card"],
            border_width=1,
            border_color=("gray80", "gray30")
        )
        self.timer_card.pack(fill="x", pady=(0, 12), ipady=10)

        # Indicador de Ciclos (● ● ○ ○)
        self.cycle_label = ctk.CTkLabel(
            self.timer_card,
            text="Ciclo: 1 de 4  •  ○ ○ ○ ○",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray40", "gray70")
        )
        self.cycle_label.pack(pady=(6, 0))

        # Reloj Gigante (MM:SS)
        self.time_label = ctk.CTkLabel(
            self.timer_card,
            text="25:00",
            font=ctk.CTkFont(family="Consolas", size=64, weight="bold"),
            text_color=self.theme_colors["work"]["accent"]
        )
        self.time_label.pack(pady=(2, 4))

        # Barra de progreso suave
        self.progress_bar = ctk.CTkProgressBar(
            self.timer_card,
            orientation="horizontal",
            mode="determinate",
            height=10,
            corner_radius=5,
            progress_color=self.theme_colors["work"]["accent"],
            fg_color=("gray80", "gray25")
        )
        self.progress_bar.set(1.0)
        self.progress_bar.pack(fill="x", padx=30, pady=(0, 10))

        # Indicador de Tarea Activa
        self.active_task_label = ctk.CTkLabel(
            self.timer_card,
            text="🎯 Sin tarea seleccionada (haz clic abajo para elegir una)",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("gray35", "gray65"),
            wraplength=380
        )
        self.active_task_label.pack(pady=(0, 6), padx=16)

        # 4. Botones de Control Principal
        self.controls_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.controls_frame.pack(fill="x", pady=(0, 14))

        self.btn_reset = ctk.CTkButton(
            self.controls_frame,
            text="↺ Reiniciar",
            width=90,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray80", "gray25"),
            text_color=("gray20", "gray90"),
            command=self.reset_timer
        )
        self.btn_reset.pack(side="left", expand=True, padx=4)

        self.btn_toggle = ctk.CTkButton(
            self.controls_frame,
            text="▶ INICIAR",
            width=150,
            height=44,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.theme_colors["work"]["accent"],
            hover_color=self.theme_colors["work"]["accent_hover"],
            command=self.toggle_timer
        )
        self.btn_toggle.pack(side="left", expand=True, padx=6)

        self.btn_skip = ctk.CTkButton(
            self.controls_frame,
            text="⏭ Saltar",
            width=90,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray80", "gray25"),
            text_color=("gray20", "gray90"),
            command=self.skip_timer
        )
        self.btn_skip.pack(side="left", expand=True, padx=4)

        # 5. Pestañas Inferiores (Tareas, Estadísticas, Ajustes)
        self.tabview = ctk.CTkTabview(self.main_container, height=220)
        self.tabview.pack(fill="both", expand=True)

        self.tab_tasks = self.tabview.add("📋 Tareas")
        self.tab_tree = self.tabview.add("🌳 Mi Árbol")
        self.tab_stats = self.tabview.add("📊 Estadísticas")
        self.tab_settings = self.tabview.add("⚙️ Ajustes")

        self.setup_tasks_tab()
        self.setup_tree_tab()
        self.setup_stats_tab()
        self.setup_settings_tab()

        # 6. Mini Mode Frame (Oculto inicialmente)
        self.mini_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.setup_mini_mode_ui()

    def setup_mini_mode_ui(self):
        """Prepara el widget compacto flotante en una fila horizontal estilizada."""
        self.mini_row = ctk.CTkFrame(self.mini_frame, fg_color="transparent")
        self.mini_row.pack(fill="both", expand=True, padx=4, pady=2)

        # Icono del modo actual (🍅 / ☕ / 🌴)
        self.mini_icon_label = ctk.CTkLabel(
            self.mini_row,
            text="🍅",
            font=ctk.CTkFont(size=18)
        )
        self.mini_icon_label.pack(side="left", padx=(4, 2))

        # Reloj digital compacto
        self.mini_time_label = ctk.CTkLabel(
            self.mini_row,
            text="25:00",
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color=self.theme_colors["work"]["accent"]
        )
        self.mini_time_label.pack(side="left", padx=(2, 6))

        # Botón Iniciar / Pausar
        self.mini_toggle_btn = ctk.CTkButton(
            self.mini_row,
            text="▶",
            width=36,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.theme_colors["work"]["accent"],
            hover_color=self.theme_colors["work"]["accent_hover"],
            command=self.toggle_timer
        )
        self.mini_toggle_btn.pack(side="left", padx=2)

        # Botón Reiniciar
        self.mini_reset_btn = ctk.CTkButton(
            self.mini_row,
            text="↺",
            width=28,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray85", "gray25"),
            text_color=("gray20", "gray90"),
            command=self.reset_timer
        )
        self.mini_reset_btn.pack(side="left", padx=2)

        # Botón Expandir a tamaño completo
        self.mini_expand_btn = ctk.CTkButton(
            self.mini_row,
            text="⤢",
            width=28,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color=("gray85", "gray25"),
            text_color=("black", "white"),
            command=self.toggle_mini_mode
        )
        self.mini_expand_btn.pack(side="left", padx=(2, 4))


    def setup_tasks_tab(self):
        """Construye el gestor de tareas pendientes con contador de pomodoros."""
        # Campo para añadir tarea
        input_frame = ctk.CTkFrame(self.tab_tasks, fg_color="transparent")
        input_frame.pack(fill="x", pady=(4, 8), padx=6)

        self.task_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Escribe una tarea nueva y presiona Enter...",
            height=34
        )
        self.task_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.task_entry.bind("<Return>", lambda event: self.add_task())

        add_btn = ctk.CTkButton(
            input_frame,
            text="+ Añadir",
            width=75,
            height=34,
            command=self.add_task
        )
        add_btn.pack(side="right")

        # Lista deslizable de tareas
        self.tasks_scroll = ctk.CTkScrollableFrame(self.tab_tasks, height=130)
        self.tasks_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.render_tasks()

    def render_tasks(self):
        """Renderiza las tareas dinámicamente en el scroll frame."""
        for widget in self.tasks_scroll.winfo_children():
            widget.destroy()

        if not self.tasks:
            empty_lbl = ctk.CTkLabel(
                self.tasks_scroll,
                text="No hay tareas aún. ¡Añade tu objetivo de hoy arriba!",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color=("gray50", "gray50")
            )
            empty_lbl.pack(pady=20)
            return

        for task in self.tasks:
            task_frame = ctk.CTkFrame(self.tasks_scroll, corner_radius=8, fg_color=("gray92", "gray20"))
            task_frame.pack(fill="x", pady=3, padx=2)

            is_active = (task["id"] == self.active_task_id)

            # Checkbox de completado
            is_done_var = tk.BooleanVar(value=task.get("completed", False))
            chk = ctk.CTkCheckBox(
                task_frame,
                text="",
                width=24,
                checkbox_width=20,
                checkbox_height=20,
                variable=is_done_var,
                command=lambda t=task, v=is_done_var: self.toggle_task_completed(t, v)
            )
            chk.pack(side="left", padx=(8, 4), pady=6)

            # Texto de la tarea
            text_font = ctk.CTkFont(
                size=12,
                weight="bold" if is_active else "normal",
                overstrike=task.get("completed", False)
            )
            title_text = task["text"]
            if is_active:
                title_text = f"⭐ {title_text}"

            txt_lbl = ctk.CTkLabel(
                task_frame,
                text=title_text,
                font=text_font,
                anchor="w",
                text_color=self.theme_colors["work"]["accent"] if is_active else ("gray15", "gray85")
            )
            txt_lbl.pack(side="left", fill="x", expand=True, padx=4)

            # Badge de pomodoros hechos en esta tarea
            pomo_badge = ctk.CTkLabel(
                task_frame,
                text=f"🍅 {task.get('pomodoros_done', 0)}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray40", "gray60")
            )
            pomo_badge.pack(side="left", padx=6)

            # Botón para activar tarea
            act_btn = ctk.CTkButton(
                task_frame,
                text="Elegir" if not is_active else "Activa",
                width=52,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color=("#3B8ED0", "#1F6AA5") if is_active else ("gray80", "gray30"),
                text_color=("black", "white"),
                command=lambda t=task: self.set_active_task(t)
            )
            act_btn.pack(side="left", padx=4)

            # Botón de eliminar
            del_btn = ctk.CTkButton(
                task_frame,
                text="✕",
                width=26,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color=("#FFD6D6", "#4A2525"),
                text_color=("red", "#FF6B6B"),
                command=lambda t=task: self.delete_task(t)
            )
            del_btn.pack(side="right", padx=(2, 6))

    def add_task(self):
        """Añade una nueva tarea a la lista."""
        text = self.task_entry.get().strip()
        if not text:
            return
        new_task = {
            "id": int(datetime.datetime.now().timestamp() * 1000),
            "text": text,
            "completed": False,
            "pomodoros_done": 0
        }
        self.tasks.append(new_task)
        if self.active_task_id is None:
            self.set_active_task(new_task)
        self.task_entry.delete(0, "end")
        self.render_tasks()
        self.save_data()

    def set_active_task(self, task):
        """Establece la tarea activa sobre la que se está enfocando el usuario."""
        if self.active_task_id == task["id"]:
            self.active_task_id = None
            self.active_task_label.configure(text="🎯 Sin tarea seleccionada (haz clic abajo para elegir una)")
        else:
            self.active_task_id = task["id"]
            self.active_task_label.configure(text=f"🎯 Tarea actual: {task['text']}")
        self.render_tasks()

    def toggle_task_completed(self, task, var):
        """Marca una tarea como completada o pendiente."""
        task["completed"] = var.get()
        self.render_tasks()
        self.save_data()

    def delete_task(self, task):
        """Elimina una tarea de la lista."""
        if self.active_task_id == task["id"]:
            self.active_task_id = None
            self.active_task_label.configure(text="🎯 Sin tarea seleccionada")
        self.tasks = [t for t in self.tasks if t["id"] != task["id"]]
        self.render_tasks()
        self.save_data()

    def check_day_rollover(self):
        """Detecta el cambio de día a medianoche mientras la app sigue abierta."""
        today_str = datetime.date.today().isoformat()
        if self.stats.get("date") != today_str:
            self.stats["date"] = today_str
            self.stats["today_pomodoros"] = 0
            self.stats["today_minutes"] = 0
            self.completed_pomodoros = 0
            self.update_streak_on_startup()
            self.refresh_stats_ui()
            self.refresh_tree_ui()
            self.update_cycle_label()
            self.save_data()

    def periodic_check(self):
        """Verificación periódica en segundo plano para cambio de fecha a medianoche."""
        try:
            self.check_day_rollover()
        except Exception:
            pass
        if self.winfo_exists():
            self.after(30000, self.periodic_check)

    def update_streak_on_startup(self):
        """Evalúa la racha diaria y el protector al iniciar la app o en nuevo día."""
        today = datetime.date.today()
        today_str = today.isoformat()
        last_str = self.streak_data.get("last_study_date")

        # Si hoy ya se completaron pomodoros
        if self.stats.get("today_pomodoros", 0) > 0:
            if not self.streak_data.get("last_study_date"):
                self.streak_data["last_study_date"] = today_str
            if self.streak_data.get("current_streak", 0) == 0:
                self.streak_data["current_streak"] = 1
            if self.streak_data.get("best_streak", 0) < self.streak_data["current_streak"]:
                self.streak_data["best_streak"] = self.streak_data["current_streak"]
            self.streak_data["is_frozen"] = False
            return

        if not last_str:
            self.streak_data["current_streak"] = 0
            self.streak_data["is_frozen"] = False
            return

        try:
            last_date = datetime.date.fromisoformat(last_str)
        except Exception:
            last_date = today

        days_diff = (today - last_date).days

        if days_diff <= 1:
            # Estudió ayer o hoy: la racha sigue viva
            self.streak_data["is_frozen"] = False
        elif days_diff == 2:
            # Se saltó 1 día (ayer no hubo estudio):
            if self.streak_data.get("is_frozen", False):
                # Ya estaba congelado protegiendo la racha durante este día
                pass
            elif self.streak_data.get("protectors", 0) > 0:
                # Consumir protector y congelar el árbol en hielo para proteger la racha
                self.streak_data["protectors"] -= 1
                self.streak_data["is_frozen"] = True
            else:
                # Sin protector: la racha se rompe
                self.streak_data["current_streak"] = 0
                self.streak_data["is_frozen"] = False
        else:
            # Se saltó más de 1 día: racha rota
            self.streak_data["current_streak"] = 0
            self.streak_data["is_frozen"] = False

    def update_streak_on_work_completed(self):
        """Actualiza la racha y el estado del árbol al terminar un pomodoro de estudio."""
        today = datetime.date.today()
        today_str = today.isoformat()
        last_str = self.streak_data.get("last_study_date")
        was_frozen = self.streak_data.get("is_frozen", False)

        # Si ya se registró el estudio de hoy (ej. segundo o posterior pomodoro del día)
        if last_str == today_str and not was_frozen:
            return

        if was_frozen:
            # Si estaba congelado, se descongela y suma el estudio de hoy a la racha
            self.streak_data["is_frozen"] = False
            self.streak_data["current_streak"] = self.streak_data.get("current_streak", 0) + 1
        else:
            if last_str:
                try:
                    last_date = datetime.date.fromisoformat(last_str)
                    diff = (today - last_date).days
                except Exception:
                    diff = 99
            else:
                diff = 99

            if diff == 1:
                # Día consecutivo
                self.streak_data["current_streak"] = self.streak_data.get("current_streak", 0) + 1
            else:
                # Inicio o reinicio de racha tras haberse roto
                self.streak_data["current_streak"] = 1

        self.streak_data["last_study_date"] = today_str

        # Actualizar récord histórico
        cur = self.streak_data["current_streak"]
        if cur > self.streak_data.get("best_streak", 0):
            self.streak_data["best_streak"] = cur

        # Recompensa: cada 7 días de racha, ganar un protector (máximo 2)
        if cur > 0 and cur % 7 == 0:
            if self.streak_data.get("protectors", 0) < 2:
                self.streak_data["protectors"] = self.streak_data.get("protectors", 0) + 1

        self.save_data()
        self.refresh_tree_ui()

    def get_tree_info(self):
        """Devuelve (sprite_filename, stage_title, description_text, state_type)."""
        streak = self.streak_data.get("current_streak", 0)
        is_frozen = self.streak_data.get("is_frozen", False)

        # Si está congelado por protector de racha:
        if is_frozen:
            if streak >= 7:
                sprite = "tree_stage4_frozen.png"
                title = "Árbol Místico (Congelado 🧊)"
            elif streak >= 4:
                sprite = "tree_stage3_frozen.png"
                title = "Árbol Frondoso (Congelado 🧊)"
            elif streak >= 2:
                sprite = "tree_stage2_frozen.png"
                title = "Árbol Joven (Congelado 🧊)"
            else:
                sprite = "tree_stage1_frozen.png"
                title = "Brote Pequeño (Congelado 🧊)"

            desc = "🧊 ¡Protector de racha activado! Tu árbol está en hielo protegiendo tu racha.\n¡Completa 1 sesión de estudio hoy para descongelarlo y continuar!"
            return sprite, title, desc, "frozen"

        # Si la racha está rota / en cero:
        if streak == 0:
            sprite = "tree_withered.png"
            title = "Árbol Marchito / Seco 🥀"
            desc = "La racha se rompió por inactividad.\n¡Completa al menos 1 pomodoro hoy para sembrar un nuevo brote!"
            return sprite, title, desc, "withered"

        # Árbol vivo y creciendo según racha:
        if streak == 1:
            sprite = "tree_stage1.png"
            title = "🌱 Nivel 1: Brote Pequeño"
            next_step = "Falta 1 día más de racha para evolucionar a Árbol Joven."
        elif 2 <= streak <= 3:
            sprite = "tree_stage2.png"
            title = "🌿 Nivel 2: Árbol Joven"
            rem = 4 - streak
            next_step = f"Faltan {rem} día(s) para evolucionar a Árbol Frondoso."
        elif 4 <= streak <= 6:
            sprite = "tree_stage3.png"
            title = "🌳 Nivel 3: Árbol Frondoso"
            rem = 7 - streak
            next_step = f"Faltan {rem} día(s) para alcanzar la forma Mística Legendaria."
        else:  # 7+ días
            sprite = "tree_stage4.png"
            title = "✨ Nivel 4: Árbol Místico Legendario"
            next_step = "¡Forma legendaria máxima alcanzada! Sigue cuidando tu racha diaria."

        studied_today = (self.streak_data.get("last_study_date") == datetime.date.today().isoformat())
        if studied_today:
            desc = f"✨ Tu árbol está sano y feliz. ¡Racha de hoy asegurada!\n{next_step}"
        else:
            desc = f"⏳ Tu árbol te espera. Completa 1 pomodoro hoy para alimentar su crecimiento.\n{next_step}"

        return sprite, title, desc, "healthy"

    def setup_tree_tab(self):
        """Construye el panel interactivo del árbol virtual (mascota pixel art)."""
        self.tree_scroll = ctk.CTkScrollableFrame(self.tab_tree, fg_color="transparent")
        self.tree_scroll.pack(fill="both", expand=True, padx=2, pady=2)

        # 1. Tarjeta principal del árbol
        self.tree_card = ctk.CTkFrame(
            self.tree_scroll,
            corner_radius=14,
            fg_color=("gray94", "gray18"),
            border_width=1,
            border_color=("gray85", "gray28")
        )
        self.tree_card.pack(fill="x", pady=(2, 6), padx=4, ipady=4)

        # Label de la imagen del árbol
        self.tree_img_lbl = ctk.CTkLabel(self.tree_card, text="", image=None)
        self.tree_img_lbl.pack(pady=(6, 2))

        # Nombre y etapa del árbol
        self.tree_stage_lbl = ctk.CTkLabel(
            self.tree_card,
            text="Nivel 1: Brote Pequeño",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#27AE60", "#2ECC71")
        )
        self.tree_stage_lbl.pack(pady=(0, 2))

        # Mensaje de estado / salud
        self.tree_msg_lbl = ctk.CTkLabel(
            self.tree_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "gray75"),
            justify="center",
            wraplength=350
        )
        self.tree_msg_lbl.pack(pady=(0, 6), padx=8)

        # 2. Fila de Métricas: Racha y Protector
        stats_row = ctk.CTkFrame(self.tree_scroll, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 6), padx=4)

        # Tarjeta Racha
        racha_card = ctk.CTkFrame(stats_row, corner_radius=10, fg_color=("gray92", "gray20"))
        racha_card.pack(side="left", fill="both", expand=True, padx=(0, 3))

        self.tree_streak_num = ctk.CTkLabel(
            racha_card,
            text="🔥 1 día",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FF9F43"
        )
        self.tree_streak_num.pack(pady=(6, 0))
        self.tree_record_lbl = ctk.CTkLabel(
            racha_card,
            text="Récord: 1 día",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60")
        )
        self.tree_record_lbl.pack(pady=(0, 6))

        # Tarjeta Protector de Racha
        prot_card = ctk.CTkFrame(stats_row, corner_radius=10, fg_color=("gray92", "gray20"))
        prot_card.pack(side="left", fill="both", expand=True, padx=(3, 0))

        self.tree_prot_num = ctk.CTkLabel(
            prot_card,
            text="🛡️ 1 / 2",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#2980B9", "#3498DB")
        )
        self.tree_prot_num.pack(pady=(6, 0))
        self.tree_prot_status = ctk.CTkLabel(
            prot_card,
            text="Protector activo",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60")
        )
        self.tree_prot_status.pack(pady=(0, 6))

        # 3. Explicación de cómo funciona el árbol y el protector
        info_frame = ctk.CTkFrame(self.tree_scroll, corner_radius=10, fg_color=("gray90", "gray22"))
        info_frame.pack(fill="x", pady=2, padx=4)

        ctk.CTkLabel(
            info_frame,
            text="📖 Reglas de tu Mascota:",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w"
        ).pack(fill="x", padx=8, pady=(4, 1))

        rules_text = (
            "• Haz al menos 1 pomodoro al día para mantener tu racha y hacer crecer tu árbol.\n"
            "• Etapas: Brote (Día 1) ➜ Joven (Día 2-3) ➜ Frondoso (Día 4-6) ➜ Místico (Día 7+).\n"
            "• 🛡️ Si no estudias un día, tu protector congelará el árbol en hielo salvando tu racha.\n"
            "• Si falta más de 1 día y no tienes protector, el árbol se marchitará."
        )
        ctk.CTkLabel(
            info_frame,
            text=rules_text,
            font=ctk.CTkFont(size=10),
            text_color=("gray35", "gray65"),
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=8, pady=(0, 6))

        self.refresh_tree_ui()

    def refresh_tree_ui(self):
        """Actualiza la imagen, estados y textos del árbol virtual."""
        if not hasattr(self, "tree_img_lbl"):
            return

        sprite_name, stage_name, status_msg, state_type = self.get_tree_info()
        sprite_path = os.path.join(ASSETS_TREE_DIR, sprite_name)

        if os.path.exists(sprite_path):
            try:
                pil_img = Image.open(sprite_path)
                self.current_tree_ctk_img = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(140, 140)
                )
                self.tree_img_lbl.configure(image=self.current_tree_ctk_img, text="")
            except Exception as e:
                print(f"Error cargando sprite del árbol: {e}")
                self.tree_img_lbl.configure(image=None, text="🌳")
        else:
            self.tree_img_lbl.configure(image=None, text="🌳")

        # Configurar colores y textos según estado
        if state_type == "frozen":
            color = ("#2980B9", "#3498DB")
            badge_text = "🧊 Racha Congelada"
        elif state_type == "withered":
            color = ("#C0392B", "#E74C3C")
            badge_text = "🥀 Racha Rota"
        else:
            color = ("#27AE60", "#2ECC71")
            streak = self.streak_data.get("current_streak", 0)
            badge_text = f"🔥 {streak} {'día' if streak == 1 else 'días'}"

        self.tree_stage_lbl.configure(text=stage_name, text_color=color)
        self.tree_msg_lbl.configure(text=status_msg)

        cur_streak = self.streak_data.get("current_streak", 0)
        best_streak = self.streak_data.get("best_streak", 0)
        self.tree_streak_num.configure(text=f"🔥 {cur_streak} {'día' if cur_streak == 1 else 'días'}")
        self.tree_record_lbl.configure(text=f"Récord: {best_streak} {'día' if best_streak == 1 else 'días'}")

        prots = self.streak_data.get("protectors", 1)
        self.tree_prot_num.configure(text=f"🛡️ {prots} / 2")
        self.tree_prot_status.configure(
            text="Listo para proteger" if prots > 0 else "Sin protectores (gana 1 a los 7 días)"
        )

        # Actualizar badge de la cabecera
        if hasattr(self, "header_streak_lbl"):
            self.header_streak_lbl.configure(text=badge_text)

    def setup_stats_tab(self):
        """Construye el panel de estadísticas y productividad."""
        stats_frame = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Tarjetas de resumen
        grid_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 10))

        # Tarjeta 1: Pomodoros Hoy
        c1 = ctk.CTkFrame(grid_frame, corner_radius=10, fg_color=("gray92", "gray20"))
        c1.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.stat_today_pomos = ctk.CTkLabel(
            c1,
            text=str(self.stats.get("today_pomodoros", 0)),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#FF5252"
        )
        self.stat_today_pomos.pack(pady=(8, 0))
        ctk.CTkLabel(c1, text="🍅 Pomodoros Hoy", font=ctk.CTkFont(size=11)).pack(pady=(0, 8))

        # Tarjeta 2: Tiempo de enfoque hoy
        c2 = ctk.CTkFrame(grid_frame, corner_radius=10, fg_color=("gray92", "gray20"))
        c2.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        mins = self.stats.get("today_minutes", 0)
        self.stat_today_time = ctk.CTkLabel(
            c2,
            text=f"{mins} min",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#2ECC71"
        )
        self.stat_today_time.pack(pady=(8, 0))
        ctk.CTkLabel(c2, text="⏱ Enfoque Hoy", font=ctk.CTkFont(size=11)).pack(pady=(0, 8))

        # Tarjeta 3: Total Histórico
        c3 = ctk.CTkFrame(grid_frame, corner_radius=10, fg_color=("gray92", "gray20"))
        c3.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        total_p = self.stats.get("total_pomodoros", 0)
        self.stat_total_pomos = ctk.CTkLabel(
            c3,
            text=str(total_p),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#3498DB"
        )
        self.stat_total_pomos.pack(pady=(8, 0))
        ctk.CTkLabel(c3, text="🏆 Total Sesiones", font=ctk.CTkFont(size=11)).pack(pady=(0, 8))

        # Frase motivacional
        self.quote_label = ctk.CTkLabel(
            stats_frame,
            text="✨ «El secreto para salir adelante es comenzar». Cada ciclo cuenta.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("gray40", "gray65"),
            wraplength=380
        )
        self.quote_label.pack(pady=10)

    def refresh_stats_ui(self):
        """Actualiza los valores mostrados en el panel de estadísticas."""
        self.stat_today_pomos.configure(text=str(self.stats.get("today_pomodoros", 0)))
        self.stat_today_time.configure(text=f"{self.stats.get('today_minutes', 0)} min")
        self.stat_total_pomos.configure(text=str(self.stats.get("total_pomodoros", 0)))

    def setup_settings_tab(self):
        """Construye el panel de ajustes y configuración de tiempos."""
        scroll = ctk.CTkScrollableFrame(self.tab_settings, height=140)
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        # Fila: Duración de Enfoque
        f_work = ctk.CTkFrame(scroll, fg_color="transparent")
        f_work.pack(fill="x", pady=4)
        ctk.CTkLabel(f_work, text="🍅 Tiempo de Enfoque (minutos):", font=ctk.CTkFont(size=12)).pack(side="left")
        self.spin_work = ctk.CTkEntry(f_work, width=60, height=28)
        self.spin_work.insert(0, str(self.settings.get("work_duration", 25)))
        self.spin_work.pack(side="right")

        # Fila: Pausa Corta
        f_short = ctk.CTkFrame(scroll, fg_color="transparent")
        f_short.pack(fill="x", pady=4)
        ctk.CTkLabel(f_short, text="☕ Pausa Corta (minutos):", font=ctk.CTkFont(size=12)).pack(side="left")
        self.spin_short = ctk.CTkEntry(f_short, width=60, height=28)
        self.spin_short.insert(0, str(self.settings.get("short_break", 5)))
        self.spin_short.pack(side="right")

        # Fila: Pausa Larga
        f_long = ctk.CTkFrame(scroll, fg_color="transparent")
        f_long.pack(fill="x", pady=4)
        ctk.CTkLabel(f_long, text="🌴 Pausa Larga (minutos):", font=ctk.CTkFont(size=12)).pack(side="left")
        self.spin_long = ctk.CTkEntry(f_long, width=60, height=28)
        self.spin_long.insert(0, str(self.settings.get("long_break", 15)))
        self.spin_long.pack(side="right")

        # Fila: Ciclos para Pausa Larga
        f_cycles = ctk.CTkFrame(scroll, fg_color="transparent")
        f_cycles.pack(fill="x", pady=4)
        ctk.CTkLabel(f_cycles, text="🔄 Ciclos para pausa larga:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.spin_cycles = ctk.CTkEntry(f_cycles, width=60, height=28)
        self.spin_cycles.insert(0, str(self.settings.get("cycles_for_long_break", 4)))
        self.spin_cycles.pack(side="right")

        # Separador visual
        sep = ctk.CTkFrame(scroll, height=1, fg_color=("gray80", "gray30"))
        sep.pack(fill="x", pady=6)

        # Switches de audio y notificaciones con prueba sonora
        f_sound = ctk.CTkFrame(scroll, fg_color="transparent")
        f_sound.pack(fill="x", pady=4)
        self.sw_sound = ctk.CTkSwitch(f_sound, text="🔔 Alarma sonora al finalizar (~7.5 seg)")
        if self.settings.get("sound_enabled", True):
            self.sw_sound.select()
        self.sw_sound.pack(side="left")

        self.btn_test_sound = ctk.CTkButton(
            f_sound,
            text="▶ Probar",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray85", "gray30"),
            text_color=("black", "white"),
            command=self.toggle_test_alarm
        )
        self.btn_test_sound.pack(side="right")

        self.sw_notif = ctk.CTkSwitch(scroll, text="💬 Notificaciones de Windows")
        if self.settings.get("notifications_enabled", True):
            self.sw_notif.select()
        self.sw_notif.pack(anchor="w", pady=4)

        self.sw_auto_break = ctk.CTkSwitch(scroll, text="⚡ Iniciar descansos automáticamente")
        if self.settings.get("auto_start_breaks", False):
            self.sw_auto_break.select()
        self.sw_auto_break.pack(anchor="w", pady=4)

        self.sw_auto_work = ctk.CTkSwitch(scroll, text="⚡ Iniciar pomodoro automáticamente")
        if self.settings.get("auto_start_work", False):
            self.sw_auto_work.select()
        self.sw_auto_work.pack(anchor="w", pady=4)

        # Switch de tema (Oscuro / Claro)
        self.sw_theme = ctk.CTkSwitch(
            scroll,
            text="🌙 Modo Oscuro (desactivar para Modo Claro)",
            command=self.toggle_theme
        )
        if self.settings.get("theme", "dark") == "dark":
            self.sw_theme.select()
        self.sw_theme.pack(anchor="w", pady=4)

        # Botón Guardar Ajustes
        save_btn = ctk.CTkButton(
            scroll,
            text="💾 Guardar Cambios en Ajustes",
            fg_color="#2ECC71",
            hover_color="#27AE60",
            command=self.save_settings_from_ui
        )
        save_btn.pack(fill="x", pady=(10, 4))

    def save_settings_from_ui(self):
        """Aplica los cambios realizados en el panel de ajustes."""
        try:
            self.settings["work_duration"] = max(1, int(self.spin_work.get().strip()))
            self.settings["short_break"] = max(1, int(self.spin_short.get().strip()))
            self.settings["long_break"] = max(1, int(self.spin_long.get().strip()))
            self.settings["cycles_for_long_break"] = max(1, int(self.spin_cycles.get().strip()))
            self.settings["sound_enabled"] = bool(self.sw_sound.get())
            self.settings["notifications_enabled"] = bool(self.sw_notif.get())
            self.settings["auto_start_breaks"] = bool(self.sw_auto_break.get())
            self.settings["auto_start_work"] = bool(self.sw_auto_work.get())
            self.save_data()

            # Si el temporizador está pausado, reajustar al nuevo tiempo; si corre, actualizar ciclo
            if not self.is_running:
                self.reset_timer()
            else:
                self.update_cycle_label()

            # Feedback visual
            prev_text = self.quote_label.cget("text")
            self.quote_label.configure(text="✅ ¡Ajustes guardados correctamente!", text_color="#2ECC71")
            self.after(2500, lambda: self.quote_label.configure(text=prev_text, text_color=("gray40", "gray65")) if self.winfo_exists() and hasattr(self, "quote_label") else None)
        except ValueError:
            self.quote_label.configure(text="⚠️ Por favor ingresa números válidos para los minutos.", text_color="#FF5252")

    def toggle_theme(self):
        """Cambia entre modo oscuro y claro."""
        new_theme = "dark" if self.sw_theme.get() else "light"
        self.settings["theme"] = new_theme
        ctk.set_appearance_mode(new_theme)
        self.save_data()

    def toggle_test_alarm(self):
        """Prueba o detiene la alarma sonora desde el panel de ajustes."""
        if getattr(self, "is_testing_sound", False):
            stop_sound()
            self.reset_test_alarm_btn()
        else:
            self.is_testing_sound = True
            self.btn_test_sound.configure(text="⏹ Detener", fg_color=("#FF5252", "#E04848"))
            play_sound(self.current_mode)
            self.after(8000, self.reset_test_alarm_btn)

    def reset_test_alarm_btn(self):
        """Restaura el botón de prueba de alarma a su estado normal."""
        if getattr(self, "is_testing_sound", False):
            self.is_testing_sound = False
            try:
                self.btn_test_sound.configure(text="▶ Probar", fg_color=("gray85", "gray30"))
            except Exception:
                pass


    def setup_keyboard_shortcuts(self):
        """Atajos de teclado rápidos para conveniencia (deshabilitados al escribir en inputs)."""
        def is_user_typing(event):
            widgets = [self.focus_get()]
            if event and hasattr(event, "widget"):
                widgets.append(event.widget)
            for w in widgets:
                if w is None:
                    continue
                try:
                    if isinstance(w, (tk.Entry, tk.Text)) or w.winfo_class() in ("Entry", "Text", "TEntry"):
                        return True
                except Exception:
                    pass
            return False

        self.bind("<space>", lambda event: self.toggle_timer() if not is_user_typing(event) else None)
        self.bind("<r>", lambda event: self.reset_timer() if not is_user_typing(event) else None)
        self.bind("<R>", lambda event: self.reset_timer() if not is_user_typing(event) else None)
        self.bind("<s>", lambda event: self.skip_timer() if not is_user_typing(event) else None)
        self.bind("<S>", lambda event: self.skip_timer() if not is_user_typing(event) else None)
        self.bind("<m>", lambda event: self.toggle_mini_mode() if not is_user_typing(event) else None)
        self.bind("<M>", lambda event: self.toggle_mini_mode() if not is_user_typing(event) else None)

    def on_mode_selected(self, mode_name):
        """Maneja el cambio de pestaña en el SegmentedButton."""
        if "Enfoque" in mode_name:
            self.switch_to_mode("work")
        elif "Pausa Corta" in mode_name:
            self.switch_to_mode("short_break")
        elif "Pausa Larga" in mode_name:
            self.switch_to_mode("long_break")

    def switch_to_mode(self, mode):
        """Cambia el modo del temporizador y actualiza estilos visuales."""
        self.stop_alarm_state()
        if self.is_running:
            self.pause_timer()

        self.current_mode = mode
        if mode == "work":
            mins = self.settings["work_duration"]
            seg_val = "🍅 Enfoque"
        elif mode == "short_break":
            mins = self.settings["short_break"]
            seg_val = "☕ Pausa Corta"
        else:
            mins = self.settings["long_break"]
            seg_val = "🌴 Pausa Larga"

        self.mode_frame.set(seg_val)
        self.remaining_seconds = mins * 60
        self.total_seconds = self.remaining_seconds

        theme = self.theme_colors[mode]

        # Actualizar colores
        self.mode_frame.configure(
            selected_color=theme["accent"],
            selected_hover_color=theme["accent_hover"]
        )
        self.timer_card.configure(fg_color=theme["bg_card"])
        self.time_label.configure(text_color=theme["accent"])
        self.progress_bar.configure(progress_color=theme["accent"])
        self.btn_toggle.configure(
            fg_color=theme["accent"],
            hover_color=theme["accent_hover"],
            text="▶ INICIAR" if not self.is_running else "⏸ PAUSAR"
        )
        self.mini_icon_label.configure(text=theme["icon"])
        self.mini_time_label.configure(text_color=theme["accent"])
        self.mini_toggle_btn.configure(
            fg_color=theme["accent"],
            hover_color=theme["accent_hover"],
            text="▶" if not self.is_running else "⏸"
        )

        self.update_cycle_label()
        self.update_timer_display()

    def update_cycle_label(self):
        """Actualiza la visualización clara del ciclo y descansos."""
        total_cycles = max(1, self.settings.get("cycles_for_long_break", 4))

        if self.current_mode == "long_break":
            dots = "● " * total_cycles
            self.cycle_label.configure(
                text=f"🌴 ¡Ciclo completado! Pausa Larga  •  {dots.strip()}"
            )
            return

        pos_in_cycle = self.completed_pomodoros % total_cycles
        dots = ""
        for i in range(total_cycles):
            if i < pos_in_cycle:
                dots += "● "
            else:
                dots += "○ "

        if self.current_mode == "work":
            pomo_num = pos_in_cycle + 1
            self.cycle_label.configure(
                text=f"🍅 Pomodoro {pomo_num} de {total_cycles}  •  {dots.strip()}"
            )
        else:
            self.cycle_label.configure(
                text=f"☕ Pausa Corta ({pos_in_cycle} de {total_cycles})  •  {dots.strip()}"
            )


    def toggle_timer(self):
        """Inicia o pausa la cuenta regresiva, o silencia la alarma si está sonando."""
        if getattr(self, "is_alarm_ringing", False):
            self.stop_alarm_state()
            return

        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        """Inicia el temporizador."""
        self.check_day_rollover()
        self.stop_alarm_state()
        self.is_running = True
        self.btn_toggle.configure(text="⏸ PAUSAR")
        self.mini_toggle_btn.configure(text="⏸")
        self.run_timer_tick()

    def pause_timer(self):
        """Pausa el temporizador."""
        self.is_running = False
        self.btn_toggle.configure(text="▶ INICIAR")
        self.mini_toggle_btn.configure(text="▶")
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

    def reset_timer(self):
        """Reinicia el temporizador actual a su tiempo completo."""
        self.stop_alarm_state()
        self.pause_timer()
        if self.current_mode == "work":
            mins = self.settings["work_duration"]
        elif self.current_mode == "short_break":
            mins = self.settings["short_break"]
        else:
            mins = self.settings["long_break"]

        self.remaining_seconds = mins * 60
        self.total_seconds = self.remaining_seconds
        self.update_cycle_label()
        self.update_timer_display()

    def skip_timer(self):
        """Salta al siguiente bloque del ciclo."""
        self.stop_alarm_state()
        self.pause_timer()
        self.advance_to_next_block()

    def trigger_alarm(self, chime_mode=None):
        """Dispara la alarma sonora de 7.5 segundos y permite detenerla con un clic."""
        self.is_alarm_ringing = True
        sound_mode = chime_mode if chime_mode is not None else self.current_mode
        play_sound(sound_mode)

        # Mostrar botón interactivo para silenciar la alarma
        self.btn_toggle.configure(
            text="🔔 DETENER ALARMA",
            fg_color=("#E67E22", "#D35400"),
            hover_color=("#D35400", "#A04000")
        )
        self.mini_toggle_btn.configure(
            text="🔔",
            fg_color=("#E67E22", "#D35400"),
            hover_color=("#D35400", "#A04000")
        )
        if self.alarm_timer_id:
            try:
                self.after_cancel(self.alarm_timer_id)
            except Exception:
                pass
        self.alarm_timer_id = self.after(8000, self.stop_alarm_state)

    def stop_alarm_state(self):
        """Detiene la alarma sonora y restaura el estado visual de los controles."""
        if getattr(self, "is_alarm_ringing", False):
            stop_sound()
            self.is_alarm_ringing = False

        if self.alarm_timer_id:
            try:
                self.after_cancel(self.alarm_timer_id)
            except Exception:
                pass
            self.alarm_timer_id = None

        if hasattr(self, "btn_toggle") and self.winfo_exists():
            theme = self.theme_colors[self.current_mode]
            self.btn_toggle.configure(
                text="▶ INICIAR" if not self.is_running else "⏸ PAUSAR",
                fg_color=theme["accent"],
                hover_color=theme["accent_hover"]
            )
            self.mini_toggle_btn.configure(
                text="▶" if not self.is_running else "⏸",
                fg_color=theme["accent"],
                hover_color=theme["accent_hover"]
            )

    def run_timer_tick(self):
        """Ejecuta cada segundo de la cuenta regresiva."""
        if not self.is_running:
            return

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_timer_display()
            self.timer_id = self.after(1000, self.run_timer_tick)
        else:
            self.on_timer_complete()

    def update_timer_display(self):
        """Actualiza los dígitos MM:SS, el título de la ventana y la barra de progreso."""
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        self.time_label.configure(text=time_str)
        self.mini_time_label.configure(text=time_str)

        # Actualizar título de la ventana para que sea visible en la barra de tareas
        mode_icon = self.theme_colors[self.current_mode]["icon"]
        self.title(f"{time_str} {mode_icon} Pomodoro Focus")

        # Actualizar barra de progreso
        if self.total_seconds > 0:
            fraction = self.remaining_seconds / self.total_seconds
            self.progress_bar.set(max(0.0, min(1.0, fraction)))

    def on_timer_complete(self):
        """Maneja el evento cuando el tiempo llega a cero."""
        self.pause_timer()

        # Verificar si cambió la fecha calendario
        self.check_day_rollover()

        finished_mode = self.current_mode

        # Registrar estadísticas si era tiempo de trabajo
        if finished_mode == "work":
            mins_added = self.settings["work_duration"]
            self.completed_pomodoros += 1
            self.stats["today_pomodoros"] = self.completed_pomodoros
            self.stats["today_minutes"] += mins_added
            self.stats["total_pomodoros"] += 1
            self.stats["total_minutes"] += mins_added

            # Incrementar pomodoro en tarea activa
            if self.active_task_id:
                for t in self.tasks:
                    if t["id"] == self.active_task_id:
                        t["pomodoros_done"] = t.get("pomodoros_done", 0) + 1
                        break
            # Actualizar racha diaria y mascota árbol
            self.update_streak_on_work_completed()

            self.refresh_stats_ui()
            self.refresh_tree_ui()
            self.save_data()

            notif_title = "🍅 ¡Sesión de Pomodoro completada!"
            notif_msg = f"¡Gran trabajo! Completaste {mins_added} minutos de enfoque. Tómate un merecido descanso."
        else:
            notif_title = "☕ ¡Pausa finalizada!"
            notif_msg = "Tu descanso ha terminado. ¿Listo para otra ronda productiva?"

        # Notificación
        if self.settings.get("notifications_enabled", True):
            self.show_notification(notif_title, notif_msg)

        # Traer ventana al frente si no está fijada
        self.lift()
        self.focus_force()

        # Avanzar al siguiente modo
        self.advance_to_next_block()

        # Disparar alarma audible prolongada (~7.5 segundos) usando el sonido del bloque finalizado
        if self.settings.get("sound_enabled", True):
            self.trigger_alarm(chime_mode=finished_mode)

    def advance_to_next_block(self):
        """Decide y activa el siguiente bloque en la secuencia Pomodoro."""
        total_cycles = max(1, self.settings.get("cycles_for_long_break", 4))

        if self.current_mode == "work":
            # Toca descanso
            if self.completed_pomodoros > 0 and (self.completed_pomodoros % total_cycles == 0):
                self.switch_to_mode("long_break")
            else:
                self.switch_to_mode("short_break")

            if self.settings.get("auto_start_breaks", False):
                self.start_timer()
        else:
            # Toca volver al trabajo
            self.switch_to_mode("work")
            if self.settings.get("auto_start_work", False):
                self.start_timer()

    def show_notification(self, title, message):
        """Muestra una notificación nativa de Windows con winotify o fallback."""
        if HAS_WINOTIFY:
            try:
                toast = Notification(
                    app_id="Pomodoro Focus",
                    title=title,
                    msg=message,
                    duration="short"
                )
                toast.show()
                return
            except Exception as e:
                print(f"Error mostrando winotify: {e}")

        # Fallback si winotify falla o no está disponible
        self.attributes("-topmost", True)
        if not self.settings.get("always_on_top", False) and not self.is_mini_mode:
            self.after(4000, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)

    def toggle_always_on_top(self):
        """Alterna el anclaje de la ventana por encima de las demás."""
        current = self.settings.get("always_on_top", False)
        new_state = not current
        self.settings["always_on_top"] = new_state
        self.attributes("-topmost", new_state)

        if new_state:
            self.topmost_btn.configure(
                text="📌 Fijado",
                fg_color=("#3B8ED0", "#1F6AA5")
            )
        else:
            self.topmost_btn.configure(
                text="📌 Fijar",
                fg_color=("gray85", "gray25")
            )
        self.save_data()

    def toggle_mini_mode(self):
        """Alterna entre la vista completa y el widget compacto minimalista."""
        if not self.is_mini_mode:
            # Guardar tamaño antes de contraer
            self.normal_geometry = self.geometry()
            self.main_container.pack_forget()
            self.mini_frame.pack(fill="both", expand=True, padx=4, pady=2)
            # Permitir que la ventana encoja tanto en ancho como en alto
            self.minsize(220, 44)
            self.geometry("250x52")
            self.attributes("-topmost", True)  # En modo mini siempre flota en la pantalla
            self.is_mini_mode = True
        else:
            # Restaurar vista completa
            self.mini_frame.pack_forget()
            self.main_container.pack(fill="both", expand=True, padx=16, pady=12)
            # Restaurar límites de tamaño normal
            self.minsize(380, 520)
            self.geometry(self.normal_geometry)
            self.attributes("-topmost", self.settings.get("always_on_top", False))
            self.is_mini_mode = False

    def on_close(self):
        """Guarda los datos y cierra la aplicación de forma limpia."""
        self.pause_timer()
        stop_sound()
        if self.alarm_timer_id:
            try:
                self.after_cancel(self.alarm_timer_id)
            except Exception:
                pass
            self.alarm_timer_id = None
        self.save_data()
        self.destroy()


if __name__ == "__main__":
    app = PomodoroApp()
    app.mainloop()
