import asyncio
import importlib.util
import inspect
import json
import math
import multiprocessing
import os
import queue
import random
import sqlite3
import sys
import threading

import numpy as np
import openwakeword
import pyaudio
import qdarktheme
from dotenv import load_dotenv
from google import genai
from google.genai.types import FunctionResponse, Part
from openwakeword.model import Model
from PyQt6.QtCore import QPointF, QRectF, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def load_dynamic_plugins(plugins_dir="plugins"):
    dynamic_tools_list = []
    dynamic_tools_mapping = {}

    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)

    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            filepath = os.path.join(plugins_dir, filename)

            try:
                # Dynamic loading of the python file as a module
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Looking for the plugin entry point
                if hasattr(module, "register_plugin"):
                    # Plugin returns its tools and mapping
                    t_list, t_map = module.register_plugin()
                    dynamic_tools_list.extend(t_list)
                    dynamic_tools_mapping.update(t_map)
                    print(f"📦 Plugin loaded: {module_name}")
            except Exception as e:
                print(f"❌ Error loading plugin {module_name}: {e}")

    return dynamic_tools_list, dynamic_tools_mapping


try:
    from commands import (
        TOOLS_LIST,
        TOOLS_MAPPING,
        WAITING_PHRASES,
        get_city_time_info,
        get_random_waiting_phrase,
    )
except ImportError:
    TOOLS_LIST = []
    TOOLS_MAPPING = {}
    WAITING_PHRASES = {"EN": ["One moment..."]}

    try:
        from main import load_dynamic_plugins

        dyn_tools, dyn_mapping = load_dynamic_plugins()
        TOOLS_LIST.extend(dyn_tools)
        TOOLS_MAPPING.update(dyn_mapping)
    except Exception:
        pass

    def get_city_time_info(city):
        return {"hour": 12, "period": "day", "formatted_time": "12:00", "city": city}

    def get_random_waiting_phrase(lang="EN"):
        return "One moment..."

    print("⚠️ Warning: commands.py not found. Tools disabled.")

try:
    dyn_tools, dyn_mapping = load_dynamic_plugins()
    TOOLS_LIST.extend(dyn_tools)
    TOOLS_MAPPING.update(dyn_mapping)
except Exception as e:
    print(f"Warning: Failed to load dynamic plugins: {e}")

load_dotenv()
CURRENT_API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"
API_VERSION = "v1beta"
SETTINGS_FILE = "settings.json"
ENV_FILE = ".env"
MEMORY_DB = "memory.db"

AUDIO_IN_RATE = 16000
AUDIO_OUT_RATE = 48000
CHUNK = 1024

# Translations for UI and Settings
TRANSLATIONS = {
    "EN": {
        "win_settings": "Settings",
        "tab_ai": "Neural Network",
        "tab_appearance": "Appearance",
        "tab_advanced": "Advanced",
        "tab_about": "About",
        "lbl_voice": "Voice Module",
        "lbl_key": "API Key (Gemini)",
        "chk_show": "Show Key",
        "lbl_lang": "Language",
        "lbl_theme": "Theme",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_gray": "Gray",
        "lbl_dev": "Debug Mode",
        "btn_save": "Save Changes",
        "about_title": "Py mycroft 2.0",
        "about_desc": "AI Voice Assistant powered by Google Gemini.\nReal-time voice interaction with tool execution.",
        "btn_support": "Support Project",
        "city_label": "Default City",
        "city_placeholder": "Los Angeles",
        "status_offline": "System Offline",
        "status_online": "System Online",
        "status_listening": "Listening...",
        "status_processing": "Processing...",
        "status_speaking": "Speaking...",
        "no_api_key": "No API Key",
        "btn_init": "INIT",
        "btn_stop": "STOP",
    },
    "RU": {
        "win_settings": "Настройки",
        "tab_ai": "Нейросеть",
        "tab_appearance": "Внешний вид",
        "tab_advanced": "Дополнительно",
        "tab_about": "О проекте",
        "lbl_voice": "Голосовой модуль",
        "lbl_key": "API Ключ (Gemini)",
        "chk_show": "Показать ключ",
        "lbl_lang": "Язык",
        "lbl_theme": "Тема",
        "theme_dark": "Тёмная",
        "theme_light": "Светлая",
        "theme_gray": "Серая",
        "lbl_dev": "Режим отладки",
        "btn_save": "Сохранить",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Голосовой ИИ-ассистент на базе Google Gemini.\nГолосовое взаимодействие в реальном времени.",
        "btn_support": "Поддержать проект",
        "city_label": "Город по умолчанию",
        "city_placeholder": "Москва",
        "status_offline": "Система офлайн",
        "status_online": "Система онлайн",
        "status_listening": "Слушаю...",
        "status_processing": "Обработка...",
        "status_speaking": "Говорю...",
        "no_api_key": "Нет API ключа",
        "btn_init": "СТАРТ",
        "btn_stop": "СТОП",
    },
    "UA": {
        "win_settings": "Налаштування",
        "tab_ai": "Нейромережа",
        "tab_appearance": "Зовнішній вигляд",
        "tab_advanced": "Додатково",
        "tab_about": "Про проект",
        "lbl_voice": "Голосовий модуль",
        "lbl_key": "API Ключ (Gemini)",
        "chk_show": "Показати ключ",
        "lbl_lang": "Мова",
        "lbl_theme": "Тема",
        "theme_dark": "Темна",
        "theme_light": "Світла",
        "theme_gray": "Сіра",
        "lbl_dev": "Режим відлагодження",
        "btn_save": "Зберегти",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Голосовий ШІ-асистент на базі Google Gemini.\nГолосова взаємодія в реальному часі.",
        "btn_support": "Підтримати проект",
        "city_label": "Місто за замовчуванням",
        "city_placeholder": "Київ",
        "status_offline": "Система офлайн",
        "status_online": "Система онлайн",
        "status_listening": "Слухаю...",
        "status_processing": "Обробка...",
        "status_speaking": "Говорю...",
        "no_api_key": "Немає API ключа",
        "btn_init": "СТАРТ",
        "btn_stop": "СТОП",
    },
    "DE": {
        "win_settings": "Einstellungen",
        "tab_ai": "Neuronales Netzwerk",
        "tab_appearance": "Aussehen",
        "tab_advanced": "Erweitert",
        "tab_about": "Über",
        "lbl_voice": "Sprachmodul",
        "lbl_key": "API-Schlüssel (Gemini)",
        "chk_show": "Schlüssel anzeigen",
        "lbl_lang": "Sprache",
        "lbl_theme": "Thema",
        "theme_dark": "Dunkel",
        "theme_light": "Hell",
        "lbl_dev": "Debug-Modus",
        "btn_save": "Speichern",
        "about_title": "Py mycroft 2.0",
        "about_desc": "KI-Sprachassistent mit Google Gemini.\nEchtzeit-Sprachinteraktion.",
        "btn_support": "Projekt unterstützen",
        "city_label": "Standardstadt",
        "city_placeholder": "Berlin",
        "city_placeholder": "Berlin",
    },
    "ES": {
        "win_settings": "Configuración",
        "tab_ai": "Red Neuronal",
        "tab_appearance": "Apariencia",
        "tab_advanced": "Avanzado",
        "tab_about": "Acerca de",
        "lbl_voice": "Módulo de Voz",
        "lbl_key": "Clave API (Gemini)",
        "chk_show": "Mostrar clave",
        "lbl_lang": "Idioma",
        "lbl_theme": "Tema",
        "theme_dark": "Oscuro",
        "theme_light": "Claro",
        "lbl_dev": "Modo depuración",
        "btn_save": "Guardar",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Asistente de voz IA con Google Gemini.\nInteracción de voz en tiempo real.",
        "btn_support": "Apoyar proyecto",
        "city_label": "Ciudad predeterminada",
        "city_placeholder": "Madrid",
        "city_placeholder": "Madrid",
    },
    "FR": {
        "win_settings": "Paramètres",
        "tab_ai": "Réseau Neuronal",
        "tab_appearance": "Apparence",
        "tab_advanced": "Avancé",
        "tab_about": "À propos",
        "lbl_voice": "Module Vocal",
        "lbl_key": "Clé API (Gemini)",
        "chk_show": "Afficher la clé",
        "lbl_lang": "Langue",
        "lbl_theme": "Thème",
        "theme_dark": "Sombre",
        "theme_light": "Clair",
        "lbl_dev": "Mode débogage",
        "btn_save": "Enregistrer",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Assistant vocal IA avec Google Gemini.\nInteraction vocale en temps réel.",
        "btn_support": "Soutenir le projet",
        "city_label": "Ville par défaut",
        "city_placeholder": "Paris",
        "city_placeholder": "Paris",
    },
    "ZH": {
        "win_settings": "设置",
        "tab_ai": "神经网络",
        "tab_appearance": "外观",
        "tab_advanced": "高级",
        "tab_about": "关于",
        "lbl_voice": "语音模块",
        "lbl_key": "API密钥 (Gemini)",
        "chk_show": "显示密钥",
        "lbl_lang": "语言",
        "lbl_theme": "主题",
        "theme_dark": "深色",
        "theme_light": "浅色",
        "lbl_dev": "调试模式",
        "btn_save": "保存",
        "about_title": "Py mycroft 2.0",
        "about_desc": "基于Google Gemini的AI语音助手。\n实时语音交互。",
        "btn_support": "支持项目",
        "city_label": "默认城市",
        "city_placeholder": "北京",
        "city_placeholder": "北京",
    },
    "JA": {
        "win_settings": "設定",
        "tab_ai": "ニューラルネットワーク",
        "tab_appearance": "外観",
        "tab_advanced": "詳細",
        "tab_about": "について",
        "lbl_voice": "音声モジュール",
        "lbl_key": "APIキー (Gemini)",
        "chk_show": "キーを表示",
        "lbl_lang": "言語",
        "lbl_theme": "テーマ",
        "theme_dark": "ダーク",
        "theme_light": "ライト",
        "lbl_dev": "デバッグモード",
        "btn_save": "保存",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Google Gemini搭載のAI音声アシスタント。\nリアルタイム音声対話。",
        "btn_support": "プロジェクトを支援",
        "city_label": "デフォルト都市",
        "city_placeholder": "東京",
        "city_placeholder": "東京",
    },
    "KO": {
        "win_settings": "설정",
        "tab_ai": "신경망",
        "tab_appearance": "외관",
        "tab_advanced": "고급",
        "tab_about": "소개",
        "lbl_voice": "음성 모듈",
        "lbl_key": "API 키 (Gemini)",
        "chk_show": "키 표시",
        "lbl_lang": "언어",
        "lbl_theme": "테마",
        "theme_dark": "다크",
        "theme_light": "라이트",
        "lbl_dev": "디버그 모드",
        "btn_save": "저장",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Google Gemini 기반 AI 음성 어시스턴트.\n실시간 음성 상호작용.",
        "btn_support": "프로젝트 지원",
        "city_label": "기본 도시",
        "city_placeholder": "서울",
        "city_placeholder": "서울",
    },
    "PT": {
        "win_settings": "Configurações",
        "tab_ai": "Rede Neural",
        "tab_appearance": "Aparência",
        "tab_advanced": "Avançado",
        "tab_about": "Sobre",
        "lbl_voice": "Módulo de Voz",
        "lbl_key": "Chave API (Gemini)",
        "chk_show": "Mostrar chave",
        "lbl_lang": "Idioma",
        "lbl_theme": "Tema",
        "theme_dark": "Escuro",
        "theme_light": "Claro",
        "lbl_dev": "Modo depuração",
        "btn_save": "Salvar",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Assistente de voz IA com Google Gemini.\nInteração por voz em tempo real.",
        "btn_support": "Apoiar projeto",
        "city_label": "Cidade padrão",
        "city_placeholder": "Lisboa",
        "city_placeholder": "Lisboa",
    },
    "IT": {
        "win_settings": "Impostazioni",
        "tab_ai": "Rete Neurale",
        "tab_appearance": "Aspetto",
        "tab_advanced": "Avanzato",
        "tab_about": "Informazioni",
        "lbl_voice": "Modulo Vocale",
        "lbl_key": "Chiave API (Gemini)",
        "chk_show": "Mostra chiave",
        "lbl_lang": "Lingua",
        "lbl_theme": "Tema",
        "theme_dark": "Scuro",
        "theme_light": "Chiaro",
        "lbl_dev": "Modalità debug",
        "btn_save": "Salva",
        "about_title": "Py mycroft 2.0",
        "about_desc": "Assistente vocale IA con Google Gemini.\nInterazione vocale in tempo reale.",
        "btn_support": "Supporta il progetto",
        "city_label": "Città predefinita",
        "city_placeholder": "Roma",
    },
}


def get_output_device_index(p):
    try:
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                name = info.get("name", "").lower()
                if info["maxOutputChannels"] > 0:
                    if "pipewire" in name or "pulse" in name:
                        return i
            except:
                continue

        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info["maxOutputChannels"] > 0:
                    return i
            except:
                continue
        return None
    except:
        return None


def get_input_device_index(p):
    try:
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                name = info.get("name", "").lower()
                if info["maxInputChannels"] > 0:
                    if "pipewire" in name or "pulse" in name or "default" in name:
                        return i
            except:
                continue

        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    return i
            except:
                continue
        return None
    except:
        return None


def audio_process_worker(
    audio_to_ai_queue, audio_to_speaker_queue, ui_events_queue, audio_cmd_queue, use_wwd
):
    import queue
    import threading
    import time

    import numpy as np
    import pyaudio

    try:
        from main import get_input_device_index, get_output_device_index
    except ImportError:
        pass

    running = True
    ai_is_speaking = False
    is_active_mode = not use_wwd
    needs_oww_reset = False
    ignore_wwd_until = 0  # <--- ADDED COOLDOWN VARIABLE
    oww_model = None
    p = pyaudio.PyAudio()

    if use_wwd:
        ui_events_queue.put(("log", "🔄 Loading WWD model..."))
        try:
            import openwakeword
            from openwakeword.model import Model

            model_paths = [
                path
                for path in openwakeword.get_pretrained_model_paths()
                if "hey_mycroft" in path
            ]
            oww_model = Model(wakeword_model_paths=model_paths)
            ui_events_queue.put(("log", "✅ WWD model 'hey_mycroft' ready"))
        except Exception as e:
            ui_events_queue.put(("log", f"❌ WWD Error: {e}"))
            oww_model = None
            is_active_mode = True

    ui_events_queue.put(("ready", None))

    def mic_thread_fn():
        nonlocal is_active_mode, running, needs_oww_reset, ignore_wwd_until  # <--- PASSED HERE
        device_id = None
        try:
            from main import get_input_device_index

            device_id = get_input_device_index(p)
        except:
            pass

        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_id,
                frames_per_buffer=2048,
            )
            ui_events_queue.put(("log", f"🎤 MIC ACTIVE (Device: {device_id})"))
        except Exception as e:
            ui_events_queue.put(("log", f"❌ MIC ERROR: {e}"))
            return

        while running:
            # ❌ УДАЛИЛИ старый кусок, который делал continue и обрывал поток:
            # if ai_is_speaking:
            #     time.sleep(0.08)
            #     continue

            try:
                # Read microphone ALWAYS to prevent buffer overflow
                data = stream.read(2048, exception_on_overflow=False)

                # === ECHO AND DISCONNECT FIX ===
                if ai_is_speaking:
                    # Replace real sound with zeros (silence)
                    data = b"\x00" * len(data)
                    audio_np = np.zeros(1024, dtype=np.int16)
                else:
                    audio_np = np.frombuffer(data, dtype=np.int16)

                vol = np.abs(audio_np).mean()
                ui_events_queue.put(("amplitude", float(vol / 5000.0)))

                if needs_oww_reset:
                    if oww_model:
                        oww_model.reset()
                    needs_oww_reset = False
                    ignore_wwd_until = time.time() + 1.5

                if is_active_mode:
                    if vol > 150:
                        ui_events_queue.put(("status", "listening"))
                    # Now data (or silence) streams to Google continuously!
                    audio_to_ai_queue.put(data)
                elif oww_model:
                    prediction = oww_model.predict(audio_np)
                    if time.time() > ignore_wwd_until:
                        if any(v > 0.5 for v in prediction.values()):
                            is_active_mode = True
                            ui_events_queue.put(("log", "🟢 WAKE WORD DETECTED"))
                            ui_events_queue.put(("mode", "active"))
                            ui_events_queue.put(("status", "listening"))
                            audio_to_ai_queue.put(data)
            except Exception as e:
                pass
            time.sleep(0.01)

        if stream:
            stream.stop_stream()
            stream.close()

    def speaker_thread_fn():
        nonlocal ai_is_speaking, running
        stream = None
        try:
            from main import get_output_device_index

            device_id = get_output_device_index(p)
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=48000,
                output=True,
                output_device_index=device_id,
            )
            ui_events_queue.put(("log", "🔊 AUDIO OUTPUT ACTIVE"))
        except:
            pass

        if stream is None:
            try:
                stream = p.open(
                    format=pyaudio.paInt16, channels=1, rate=48000, output=True
                )
            except:
                pass

        if stream is None:
            try:
                stream = p.open(
                    format=pyaudio.paInt16, channels=1, rate=24000, output=True
                )
            except Exception as e:
                ui_events_queue.put(("log", f"❌ SPEAKER ERROR: {e}"))
                return

        while running:
            try:
                data = audio_to_speaker_queue.get(timeout=0.1)
                if data is None:
                    continue
                ai_is_speaking = True
                ui_events_queue.put(("status", "speaking"))
                audio_np = np.frombuffer(data, dtype=np.int16)
                vol = np.abs(audio_np).mean()
                ui_events_queue.put(("amplitude", float(vol / 5000.0)))
                resampled_np = np.repeat(audio_np, 2)
                if stream:
                    stream.write(resampled_np.tobytes())
            except queue.Empty:
                if ai_is_speaking:
                    ai_is_speaking = False
                    ui_events_queue.put(("status", "idle"))
            except Exception as e:
                pass

        if stream:
            stream.stop_stream()
            stream.close()

    mic_t = threading.Thread(target=mic_thread_fn, daemon=True)
    speaker_t = threading.Thread(target=speaker_thread_fn, daemon=True)
    mic_t.start()
    speaker_t.start()

    while running:
        try:
            cmd = audio_cmd_queue.get(timeout=0.2)
            if cmd == "STOP":
                running = False
            elif cmd == "STANDBY":
                if oww_model:
                    is_active_mode = False
                    needs_oww_reset = True
                    ui_events_queue.put(("mode", "standby"))
                    ui_events_queue.put(("log", "⚪ MODE: STANDBY"))
            elif cmd == "ACTIVE":
                is_active_mode = True
                ui_events_queue.put(("mode", "active"))
        except queue.Empty:
            pass

    mic_t.join(timeout=1.0)
    speaker_t.join(timeout=1.0)
    p.terminate()


def ai_process_worker(
    audio_to_ai_queue,
    audio_to_speaker_queue,
    ui_events_queue,
    ai_cmd_queue,
    audio_cmd_queue,
    voice_name,
    city,
    api_key,
):
    import asyncio
    import inspect
    import queue

    from google import genai
    from google.genai.types import FunctionResponse, Part

    try:
        from commands import (
            TOOLS_LIST,
            TOOLS_MAPPING,
            WAITING_PHRASES,
            get_city_time_info,
        )
    except ImportError:
        TOOLS_LIST = []
        TOOLS_MAPPING = {}

        def get_city_time_info(city):
            return {
                "hour": 12,
                "period": "day",
                "formatted_time": "12:00",
                "city": city,
            }

        WAITING_PHRASES = {"EN": ["One moment..."]}

    try:
        from main import load_dynamic_plugins

        dyn_tools, dyn_mapping = load_dynamic_plugins()
        TOOLS_LIST.extend(dyn_tools)
        TOOLS_MAPPING.update(dyn_mapping)
        if dyn_tools:
            ui_events_queue.put(("log", f"🧩 Plugins loaded: {len(dyn_tools)}"))
    except Exception as e:
        ui_events_queue.put(("log", f"❌ Plugin error: {e}"))

    try:
        from main import MemoryManager

        memory = MemoryManager()
        memory_context = memory.get_user_context()
        user_name = memory.get_fact("user", "name") or "User"
        memory.close()
    except Exception as e:
        memory_context = ""
        user_name = "User"

    async def run_ai():
        if not api_key:
            ui_events_queue.put(("log", "❌ ERROR: API KEY MISSING"))
            return

        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
        actual_city = city if city.strip() else "Ужгород"

        time_info = get_city_time_info(actual_city)
        current_hour = time_info["hour"]
        time_period = time_info["period"]

        tone_instruction = f"=== TONE ===\nIt's {time_period} for the user ({current_hour}:00). Speak naturally."
        waiting_examples = WAITING_PHRASES.get(
            "RU", WAITING_PHRASES.get("EN", ["One moment..."])
        )
        waiting_examples_str = ", ".join([f'"{p}"' for p in waiting_examples[:8]])

        sys_instruction = f"""IDENTITY: You are Py mycroft 2.0, a MALE AI voice assistant based on Arch Linux.
GENDER (CRITICAL): MALE (Мужской). When speaking Russian, you MUST ALWAYS refer to yourself in the masculine gender. Use masculine verbs and adjectives (e.g., say "я сделал", "я нашел", "я готов", NEVER "сделала", "нашла", or "готова").
LOCATION: {actual_city}
USER NAME: {user_name}
CURRENT TIME: approximately {current_hour}:00 ({time_period})

{memory_context}
{tone_instruction}

=== RULE 1: ACTIVATION AND STANDBY ===
You are in Voice Interaction mode.
CRITICAL: When the user says "диалог завершен" or "пока", you MUST IMMEDIATELY call the `standby_mode()` tool. Do NOT answer with audio, do NOT say goodbye. Just execute the tool!

=== RULE 2: VARIABLE WAITING PHRASES ===
Use phrases like {waiting_examples_str} before using tools. Pick a DIFFERENT one each time!

=== RULE 3: AUTONOMOUS MEMORY ===
Use `save_memory` for long-term facts. Check memory first!

=== RULE 4: TOOL USAGE ===
- Weather -> get_weather(city)
- Play music/track -> play_music(query)
- Play on Spotify -> play_on_spotify(query)
- Search -> internet_research(query)
- Screenshot -> capture_screen()
- Open app -> run_app(name)
- Time in city -> get_city_time_info(city)

=== RULE 5: LANGUAGE ===
You MUST reply in the EXACT same language the user is speaking right now. If the user speaks English, speak English. Ignore any Russian text in your instructions if the user speaks English.

=== RULE 6: VISION & SCREENSHOTS ===
When using `capture_screen`, the frames are pushed to your visual stream.
DO NOT GUESS! DO NOT INVENT! Look at the actual images. Describe strictly what you see (e.g., a YouTube video, a movie, a code editor). If you cannot see anything, honestly admit it.
"""

        config = {
            "response_modalities": ["AUDIO"],
            "tools": TOOLS_LIST,
            "system_instruction": sys_instruction,
            "speech_config": {
                "voice_config": {"prebuilt_voice_config": {"voice_name": voice_name}}
            },
        }

        async def check_for_stop():
            while True:
                try:
                    if ai_cmd_queue.get_nowait() == "STOP":
                        return True
                except queue.Empty:
                    await asyncio.sleep(0.1)

        # ==========================================
        # 🟢 OUTER RING (STANDBY Mode)
        # ==========================================
        while True:
            # FIX 1: Hard reset UI to idle state ("Система онлайн")
            ui_events_queue.put(("status", "idle"))

            # Clear queue of old noise
            while True:
                try:
                    audio_to_ai_queue.get_nowait()
                except queue.Empty:
                    break

            ui_events_queue.put(("log", "⚪ Waiting for wake-word..."))

            first_data = None
            stop_requested = False

            # Wait for microphone trigger or STOP button
            while True:
                try:
                    if ai_cmd_queue.get_nowait() == "STOP":
                        stop_requested = True
                        break
                except queue.Empty:
                    pass

                try:
                    first_data = audio_to_ai_queue.get_nowait()
                    if first_data is not None:
                        break
                except queue.Empty:
                    await asyncio.sleep(0.05)

            if stop_requested:
                break

            # ==========================================
            # 🔴 INNER RING (ACTIVE Mode - Dialog)
            # ==========================================
            while True:
                restart_session = False
                try:
                    ui_events_queue.put(("log", "🔗 Connecting to Gemini..."))
                    async with client.aio.live.connect(
                        model="gemini-2.5-flash-native-audio-preview-12-2025",
                        config=config,
                    ) as session:
                        ui_events_queue.put(
                            ("log", f"✅ SESSION ONLINE ({actual_city})")
                        )

                        if first_data:
                            await session.send_realtime_input(
                                media={"data": first_data, "mime_type": "audio/pcm"}
                            )
                            first_data = None

                        async def send_audio():
                            while True:
                                try:
                                    data = audio_to_ai_queue.get_nowait()
                                    if data is None:
                                        break
                                    await session.send_realtime_input(
                                        media={"data": data, "mime_type": "audio/pcm"}
                                    )
                                except queue.Empty:
                                    await asyncio.sleep(0.02)
                                except Exception:
                                    break

                        async def receive_cloud():
                            nonlocal restart_session
                            try:
                                async for response in session.receive():
                                    if response.tool_call:
                                        ui_events_queue.put(("status", "processing"))
                                        for fc in response.tool_call.function_calls:
                                            name = fc.name
                                            args = fc.args
                                            if name == "standby_mode":
                                                audio_cmd_queue.put("STANDBY")
                                                restart_session = True
                                                return
                                            else:
                                                audio_cmd_queue.put("ACTIVE")
                                                ui_events_queue.put(
                                                    ("log", f"🟢 TOOL: {name}")
                                                )

                                            if name in TOOLS_MAPPING:
                                                ui_events_queue.put(
                                                    ("log", f"⚙️ EXEC: {name}")
                                                )
                                                func = TOOLS_MAPPING[name]
                                                try:
                                                    if inspect.iscoroutinefunction(
                                                        func
                                                    ):
                                                        result = await func(**args)
                                                    else:
                                                        result = (
                                                            await asyncio.to_thread(
                                                                lambda: func(**args)
                                                            )
                                                        )
                                                except Exception as e:
                                                    result = f"Error: {e}"

                                                if isinstance(result, bytes):
                                                    ui_events_queue.put(
                                                        (
                                                            "log",
                                                            "📸 Packing screen as an object...",
                                                        )
                                                    )

                                                    try:
                                                        # 1. Close tool (otherwise API will block sending messages)
                                                        await session.send_tool_response(
                                                            function_responses=[
                                                                FunctionResponse(
                                                                    name=name,
                                                                    id=fc.id,
                                                                    response={
                                                                        "result": "Скриншот сделан. Я отправляю его следующим сообщением, посмотри на него."
                                                                    },
                                                                )
                                                            ]
                                                        )
                                                        await asyncio.sleep(0.5)

                                                        # 2. Send screenshot as a SOLID context piece (not video stream!)
                                                        image_part = Part.from_bytes(
                                                            data=result,
                                                            mime_type="image/jpeg",
                                                        )
                                                        await session.send(
                                                            input=image_part
                                                        )
                                                        ui_events_queue.put(
                                                            (
                                                                "log",
                                                                "✅ Screenshot in context!",
                                                            )
                                                        )

                                                    except Exception as e:
                                                        ui_events_queue.put(
                                                            (
                                                                "log",
                                                                f"❌ Error sending Part: {e}",
                                                            )
                                                        )
                                                    continue

                                                await session.send_tool_response(
                                                    function_responses=[
                                                        FunctionResponse(
                                                            name=name,
                                                            id=fc.id,
                                                            response={
                                                                "result": str(result)
                                                            },
                                                        )
                                                    ]
                                                )
                                    elif (
                                        response.server_content
                                        and response.server_content.model_turn
                                    ):
                                        for (
                                            part
                                        ) in response.server_content.model_turn.parts:
                                            if part.inline_data:
                                                audio_to_speaker_queue.put(
                                                    part.inline_data.data
                                                )
                            except Exception:
                                pass

                        t_send = asyncio.create_task(send_audio())
                        t_recv = asyncio.create_task(receive_cloud())
                        t_stop = asyncio.create_task(check_for_stop())

                        done, pending = await asyncio.wait(
                            [t_send, t_recv, t_stop],
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for t in pending:
                            t.cancel()

                        if t_stop in done and t_stop.result() == True:
                            stop_requested = True
                            break

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    ui_events_queue.put(("log", f"CONNECTION ERROR: {e}"))
                    await asyncio.sleep(1)

                if stop_requested:
                    break

                if restart_session:
                    ui_events_queue.put(("log", "⚪ Synchronizing streams..."))
                    await asyncio.sleep(0.5)
                    break

                ui_events_queue.put(("log", "🔄 Restoring stream..."))
                await asyncio.sleep(0.2)

            # FIX 2: If STOP is pressed during dialogue - hard exit, don't fall asleep!
            if stop_requested:
                break

        ui_events_queue.put(("finished", None))

    asyncio.run(run_ai())


# ========================================
# DEBUG LOG WINDOW
# ========================================
class LogWindow(QMainWindow):
    """Separate window for debug logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🐛 Mycrofet Debug Logs")
        self.resize(700, 400)
        self.setStyleSheet("background-color: #0a0a0a;")

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #00ff88;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: none;
                padding: 15px;
            }
        """)

        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #1a1a1a; padding: 8px;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        clear_btn = QPushButton("🗑 Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        clear_btn.clicked.connect(self.log_text.clear)

        toolbar_layout.addWidget(QLabel("📋 Debug Console"))
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(clear_btn)

        # Layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self.log_text)

    def append_log(self, msg):
        """Add log message."""
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


class TechVisualizer(QWidget):
    PI2 = math.pi * 2
    DEG_TO_RAD = math.pi / 180

    STATUS_TEXTS = {
        "listening": "◉ LISTENING",
        "processing": "◎ PROCESSING",
        "speaking": "◈ SPEAKING",
    }

    def __init__(self):
        super().__init__()
        self.setMinimumSize(220, 220)
        self.amp = 0.0
        self.target_amp = 0.0
        self.mode = "idle"
        self.visual_state = "standby"
        self.dev_mode = False

        self.angle_1 = 0.0
        self.angle_2 = 0.0
        self.angle_3 = 0.0
        self.wave_phase = 0.0

        self.particles = []
        for _ in range(10):
            self.particles.append(
                {
                    "angle": random.uniform(0, 360),
                    "radius": random.uniform(50, 90),
                    "speed": random.uniform(0.4, 1.2),
                    "size": random.uniform(2, 4),
                    "alpha": random.uniform(0.4, 0.7),
                    "cos": 0.0,
                    "sin": 0.0,
                }
            )

        self.cr, self.cg, self.cb = 80, 80, 80
        self.tr, self.tg, self.tb = 80, 80, 80

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(33)

        self.frame_count = 0

    def update_level(self, level):
        self.target_amp = min(level * 2.5, 2.0)

    def set_mode(self, mode):
        self.mode = mode
        if mode == "listening":
            self.tr, self.tg, self.tb = 0, 220, 255
        elif mode == "processing":
            self.tr, self.tg, self.tb = 255, 180, 0
        elif mode == "speaking":
            if self.dev_mode:
                self.tr, self.tg, self.tb = 0, 255, 100
            else:
                self.tr, self.tg, self.tb = 100, 150, 255
        else:
            self.tr, self.tg, self.tb = 80, 80, 80

    def set_visual_state(self, state):
        self.visual_state = state

    def set_dev_mode(self, enabled):
        self.dev_mode = enabled

    def animate(self):
        self.frame_count += 1

        self.amp += (self.target_amp - self.amp) * 0.18
        self.target_amp = max(0, self.target_amp - 0.04)

        self.cr += int((self.tr - self.cr) * 0.1)
        self.cg += int((self.tg - self.cg) * 0.1)
        self.cb += int((self.tb - self.cb) * 0.1)

        speed_mult = 1.0 + self.amp * 1.5
        self.angle_1 = (self.angle_1 + 0.5 * speed_mult) % 360
        self.angle_2 = (self.angle_2 - 1.0 * speed_mult) % 360
        self.angle_3 = (self.angle_3 + 2.0 * speed_mult) % 360
        self.wave_phase = (self.wave_phase + 0.1) % self.PI2

        for p in self.particles:
            p["angle"] = (p["angle"] + p["speed"] * speed_mult) % 360
            rad = p["angle"] * self.DEG_TO_RAD
            p["cos"] = math.cos(rad)
            p["sin"] = math.sin(rad)
            if self.amp > 0.1:
                p["radius"] = 50 + 30 * (
                    1 + math.sin(self.wave_phase + p["angle"] * 0.1) * self.amp * 0.5
                )

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() * 0.5, self.height() * 0.5
        cr, cg, cb = self.cr, self.cg, self.cb
        pulse = self.amp * 20

        # Background glow
        grad = QRadialGradient(cx, cy, 100 + pulse)
        grad.setColorAt(0, QColor(cr, cg, cb, 35))
        grad.setColorAt(0.6, QColor(cr, cg, cb, 15))
        grad.setColorAt(1, Qt.GlobalColor.transparent)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), 100 + pulse, 100 + pulse)

        # Particles
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self.particles:
            px = cx + pt["radius"] * pt["cos"]
            py = cy + pt["radius"] * pt["sin"]
            alpha = int(pt["alpha"] * 200 * (0.6 + self.amp * 0.4))
            p.setBrush(QColor(cr, cg, cb, alpha))
            p.drawEllipse(QPointF(px, py), pt["size"], pt["size"])

        # Wave rings (reduced - only 2 rings)
        if self.mode != "idle":
            p.setBrush(Qt.GlobalColor.transparent)
            sin_wave = math.sin(self.wave_phase) * 6 * self.amp
            for i in range(2):
                radius = 40 + i * 20 + sin_wave + pulse * 0.4
                p.setPen(QPen(QColor(cr, cg, cb, 120 - i * 40), 2))
                p.drawEllipse(QPointF(cx, cy), radius, radius)

        # Rotating arcs (inner)
        p.setBrush(Qt.GlobalColor.transparent)
        pen_inner = QPen(QColor(cr, cg, cb, 200), 4, cap=Qt.PenCapStyle.RoundCap)
        p.setPen(pen_inner)
        ri = 45 + pulse * 0.3
        rect_i = QRectF(cx - ri, cy - ri, ri * 2, ri * 2)
        a2_16 = self.angle_2 * 16
        for i in range(3):
            p.drawArc(rect_i, int(a2_16 + i * 1920), 1280)

        # Rotating arcs (outer)
        pen_outer = QPen(QColor(cr, cg, cb, 140), 2, cap=Qt.PenCapStyle.RoundCap)
        p.setPen(pen_outer)
        ro = 70 + pulse * 0.5
        rect_o = QRectF(cx - ro, cy - ro, ro * 2, ro * 2)
        a1_16 = self.angle_1 * 16
        for i in range(4):
            p.drawArc(rect_o, int(a1_16 + i * 1440), 480)

        # Dynamic outer ring
        if self.mode != "idle" or self.visual_state == "active":
            p.setPen(QPen(QColor(cr, cg, cb, 80), 1))
            rd = 85 + pulse
            rect_d = QRectF(cx - rd, cy - rd, rd * 2, rd * 2)
            a3_16 = int(self.angle_3 * 16)
            p.drawArc(rect_d, a3_16, 2240)
            p.drawArc(rect_d, a3_16 + 2880, 2240)

        # Core - increased size
        cs = 22 + self.amp * 10

        cg_grad = QRadialGradient(cx, cy, cs * 2)
        cg_grad.setColorAt(0, QColor(cr, cg, cb, 160))
        cg_grad.setColorAt(0.5, QColor(cr, cg, cb, 40))
        cg_grad.setColorAt(1, Qt.GlobalColor.transparent)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(cg_grad))
        p.drawEllipse(QPointF(cx, cy), cs * 2, cs * 2)

        cs_grad = QRadialGradient(cx - cs * 0.3, cy - cs * 0.3, cs)
        cs_grad.setColorAt(0, QColor(255, 255, 255, 180))
        cs_grad.setColorAt(0.35, QColor(cr, cg, cb))
        cs_grad.setColorAt(1, QColor(cr >> 1, cg >> 1, cb >> 1))
        p.setBrush(QBrush(cs_grad))
        p.setPen(QPen(QColor(255, 255, 255, 80), 2))
        p.drawEllipse(QPointF(cx, cy), cs, cs)

        # Status text removed - now shown only in header to avoid duplication


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_win = parent
        self.resize(450, 400)
        self.setWindowTitle("Settings")

        # Adaptive styles based on current theme
        if parent.current_theme == "light":
            self.setStyleSheet("""
                QDialog { background-color: #f0f4f8; color: #1a1a1a; }
                QPushButton.tab_btn {
                    background: transparent;
                    color: #666;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 20px;
                }
                QPushButton.tab_btn:hover {
                    background: #e0e4e8;
                    color: #333;
                }
                QPushButton.tab_btn[selected="true"] {
                    background: #3498db;
                    color: #fff;
                }
                QLabel { color: #555; font-size: 12px; }
                QLabel#section_title { color: #1a1a1a; font-size: 14px; font-weight: bold; margin-bottom: 10px; }
                QComboBox {
                    background: #ffffff;
                    border: 1px solid #cbd5e1;
                    color: #1a1a1a;
                    padding: 8px 12px;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QComboBox::drop-down { border: none; width: 30px; }
                QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #64748b; }
                QComboBox QAbstractItemView {
                    background: #ffffff;
                    color: #1a1a1a;
                    selection-background-color: #3498db;
                    selection-color: white;
                    border: 1px solid #cbd5e1;
                }
                QLineEdit {
                    background: #ffffff;
                    border: 1px solid #cbd5e1;
                    color: #0066cc;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QCheckBox { color: #555; spacing: 8px; }
                QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #94a3b8; background: #ffffff; }
                QCheckBox::indicator:checked { background: #3498db; border-color: #3498db; }
                QPushButton#save_btn {
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    font-weight: bold;
                    border-radius: 8px;
                    font-size: 13px;
                }
                QPushButton#save_btn:hover { background: #2980b9; }
                QPushButton#support_btn {
                    background: transparent;
                    color: #e74c3c;
                    border: 2px solid #e74c3c;
                    padding: 10px 20px;
                    font-weight: bold;
                    border-radius: 8px;
                }
                QPushButton#support_btn:hover { background: #e74c3c; color: white; }
            """)
        elif parent.current_theme == "gray":
            self.setStyleSheet("""
                QDialog { background-color: #4a4a4a; color: #e0e0e0; }
                QPushButton.tab_btn {
                    background: transparent;
                    color: #999;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 20px;
                }
                QPushButton.tab_btn:hover {
                    background: #555;
                    color: #ccc;
                }
                QPushButton.tab_btn[selected="true"] {
                    background: #3498db;
                    color: #fff;
                }
                QLabel { color: #bbb; font-size: 12px; }
                QLabel#section_title { color: #fff; font-size: 14px; font-weight: bold; margin-bottom: 10px; }
                QComboBox {
                    background: #3a3a3a;
                    border: 1px solid #666;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QComboBox::drop-down { border: none; width: 30px; }
                QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #aaa; }
                QComboBox QAbstractItemView {
                    background: #3a3a3a;
                    color: white;
                    selection-background-color: #3498db;
                    selection-color: white;
                    border: 1px solid #666;
                }
                QLineEdit {
                    background: #3a3a3a;
                    border: 1px solid #666;
                    color: #00ffcc;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QCheckBox { color: #bbb; spacing: 8px; }
                QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #777; background: #3a3a3a; }
                QCheckBox::indicator:checked { background: #3498db; border-color: #3498db; }
                QPushButton#save_btn {
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    font-weight: bold;
                    border-radius: 8px;
                    font-size: 13px;
                }
                QPushButton#save_btn:hover { background: #2980b9; }
                QPushButton#support_btn {
                    background: transparent;
                    color: #e74c3c;
                    border: 2px solid #e74c3c;
                    padding: 10px 20px;
                    font-weight: bold;
                    border-radius: 8px;
                }
                QPushButton#support_btn:hover { background: #e74c3c; color: white; }
            """)
        else:
            # Dark theme (default)
            self.setStyleSheet("""
                QDialog { background-color: #1a1a1a; color: #e0e0e0; }
                QPushButton.tab_btn {
                    background: transparent;
                    color: #666;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 20px;
                }
                QPushButton.tab_btn:hover {
                    background: #333;
                    color: #aaa;
                }
                QPushButton.tab_btn[selected="true"] {
                    background: #3498db;
                    color: #fff;
                }
                QLabel { color: #aaa; font-size: 12px; }
                QLabel#section_title { color: #fff; font-size: 14px; font-weight: bold; margin-bottom: 10px; }
                QComboBox {
                    background: #2a2a2a;
                    border: 1px solid #444;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QComboBox::drop-down { border: none; width: 30px; }
                QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #888; }
                QComboBox QAbstractItemView {
                    background: #2a2a2a;
                    color: white;
                    selection-background-color: #3498db;
                    selection-color: white;
                    border: 1px solid #444;
                }
                QLineEdit {
                    background: #2a2a2a;
                    border: 1px solid #444;
                    color: #00ffcc;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QCheckBox { color: #aaa; spacing: 8px; }
                QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #555; background: #2a2a2a; }
                QCheckBox::indicator:checked { background: #3498db; border-color: #3498db; }
                QPushButton#save_btn {
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    font-weight: bold;
                    border-radius: 8px;
                    font-size: 13px;
                }
                QPushButton#save_btn:hover { background: #2980b9; }
                QPushButton#support_btn {
                    background: transparent;
                    color: #e74c3c;
                    border: 2px solid #e74c3c;
                    padding: 10px 20px;
                    font-weight: bold;
                    border-radius: 8px;
                }
                QPushButton#support_btn:hover { background: #e74c3c; color: white; }
            """)

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Left sidebar with icon buttons
        sidebar = QVBoxLayout()
        sidebar.setSpacing(4)

        t = TRANSLATIONS[parent.current_lang]
        # Icons: brain/network, palette, gear, info
        tabs = [
            ("⚛", "tab_ai"),
            ("◐", "tab_appearance"),
            ("⚙", "tab_advanced"),
            ("ℹ", "tab_about"),
        ]
        self.tab_buttons = []

        for i, (icon, key) in enumerate(tabs):
            btn = QPushButton(icon)
            btn.setFixedSize(48, 48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(t.get(key, key))
            btn.setProperty("selected", "true" if i == 0 else "false")
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #666;
                    border: none;
                    border-radius: 8px;
                    font-size: 22px;
                }
                QPushButton:hover {
                    background: #333;
                    color: #aaa;
                }
                QPushButton[selected="true"] {
                    background: #3498db;
                    color: #fff;
                }
            """)
            btn.clicked.connect(lambda checked, idx=i: self.switch_tab(idx))
            sidebar.addWidget(btn)
            self.tab_buttons.append(btn)

        sidebar.addStretch()
        main_layout.addLayout(sidebar)

        # Content area
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        self.create_ai_page()
        self.create_appearance_page()
        self.create_advanced_page()
        self.create_about_page()

    def create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        t = TRANSLATIONS[self.parent_win.current_lang]

        title = QLabel(t.get("tab_ai", "Neural Network"))
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(QLabel(t.get("lbl_voice", "Voice Module")))
        self.cb_voice = QComboBox()
        self.cb_voice.addItems(["Puck", "Charon", "Kore", "Fenrir", "Aoede"])
        self.cb_voice.setCurrentText(getattr(self.parent_win, "selected_voice", "Puck"))
        layout.addWidget(self.cb_voice)

        layout.addWidget(QLabel(t.get("city_label", "Default City")))
        self.input_city = QLineEdit()
        self.input_city.setText(self.parent_win.default_city)
        self.input_city.setPlaceholderText(t.get("city_placeholder", "Los Angeles"))
        layout.addWidget(self.input_city)

        layout.addWidget(QLabel(t.get("lbl_key", "API Key")))
        self.input_key = QLineEdit()
        self.input_key.setText(CURRENT_API_KEY if CURRENT_API_KEY else "")
        self.input_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.input_key)

        self.chk_show = QCheckBox(t.get("chk_show", "Show Key"))
        self.chk_show.stateChanged.connect(
            lambda s: self.input_key.setEchoMode(
                QLineEdit.EchoMode.Normal if s == 2 else QLineEdit.EchoMode.Password
            )
        )
        layout.addWidget(self.chk_show)

        layout.addStretch()

        btn_save = QPushButton(t.get("btn_save", "Save"))
        btn_save.setObjectName("save_btn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

        self.stack.addWidget(page)

    def create_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        t = TRANSLATIONS[self.parent_win.current_lang]

        title = QLabel(t.get("tab_appearance", "Appearance"))
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(QLabel(t.get("lbl_lang", "Language")))
        self.cb_lang = QComboBox()
        self.cb_lang.addItems(list(TRANSLATIONS.keys()))
        self.cb_lang.setCurrentText(self.parent_win.current_lang)
        self.cb_lang.currentTextChanged.connect(self.update_ui_language)
        layout.addWidget(self.cb_lang)

        layout.addWidget(QLabel(t.get("lbl_theme", "Theme")))
        self.cb_theme = QComboBox()
        # Use translated theme names
        theme_translated = [
            t.get("theme_dark", "Dark"),
            t.get("theme_light", "Light"),
            t.get("theme_gray", "Gray"),
        ]
        self.cb_theme.addItems(theme_translated)
        # Map current theme to translated name
        theme_to_translated = {
            "dark": t.get("theme_dark", "Dark"),
            "light": t.get("theme_light", "Light"),
            "gray": t.get("theme_gray", "Gray"),
        }
        self.cb_theme.setCurrentText(
            theme_to_translated.get(
                self.parent_win.current_theme, t.get("theme_dark", "Dark")
            )
        )
        layout.addWidget(self.cb_theme)

        layout.addStretch()

        btn_save = QPushButton(t.get("btn_save", "Save"))
        btn_save.setObjectName("save_btn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

        self.stack.addWidget(page)

    def create_advanced_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        t = TRANSLATIONS[self.parent_win.current_lang]

        title = QLabel(t.get("tab_advanced", "Advanced"))
        title.setObjectName("section_title")
        layout.addWidget(title)

        self.chk_dev = QCheckBox(t.get("lbl_dev", "Debug Mode"))
        self.chk_dev.setChecked(self.parent_win.dev_mode)
        layout.addWidget(self.chk_dev)

        layout.addStretch()

        btn_save = QPushButton(t.get("btn_save", "Save"))
        btn_save.setObjectName("save_btn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

        self.stack.addWidget(page)

    def create_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        t = TRANSLATIONS[self.parent_win.current_lang]

        title = QLabel(t.get("about_title", "Py mycroft 2.0"))
        title.setObjectName("section_title")
        title.setStyleSheet("font-size: 20px;")
        layout.addWidget(title)

        desc = QLabel(t.get("about_desc", "AI Voice Assistant"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; line-height: 1.6;")
        layout.addWidget(desc)

        version = QLabel("Version 2.3.0")
        version.setStyleSheet("color: #555; margin-top: 10px;")
        layout.addWidget(version)

        layout.addStretch()

        btn_support = QPushButton(t.get("btn_support", "Support Project"))
        btn_support.setObjectName("support_btn")
        btn_support.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_support.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/sponsors"))
        )
        layout.addWidget(btn_support)

        self.stack.addWidget(page)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        # Update button selection states
        for i, btn in enumerate(self.tab_buttons):
            btn.setProperty("selected", "true" if i == index else "false")
            btn.setStyle(btn.style())  # Force style refresh

    def update_ui_language(self, lang):
        t = TRANSLATIONS.get(lang, TRANSLATIONS["EN"])
        keys = ["tab_ai", "tab_appearance", "tab_advanced", "tab_about"]
        for i, btn in enumerate(self.tab_buttons):
            btn.setToolTip(t.get(keys[i], keys[i]))

    def save_and_close(self):
        global CURRENT_API_KEY
        self.parent_win.selected_voice = self.cb_voice.currentText()
        self.parent_win.current_lang = self.cb_lang.currentText()
        self.parent_win.dev_mode = self.chk_dev.isChecked()
        self.parent_win.default_city = self.input_city.text().strip()
        # Save theme - map translated names back to theme codes
        t = TRANSLATIONS.get(self.parent_win.current_lang, TRANSLATIONS["EN"])
        translated_to_theme = {
            t.get("theme_dark", "Dark"): "dark",
            t.get("theme_light", "Light"): "light",
            t.get("theme_gray", "Gray"): "gray",
        }
        self.parent_win.current_theme = translated_to_theme.get(
            self.cb_theme.currentText(), "dark"
        )
        self.parent_win.viz.set_dev_mode(self.parent_win.dev_mode)

        new_key = self.input_key.text().strip()
        if new_key and new_key != CURRENT_API_KEY:
            try:
                with open(ENV_FILE, "w") as f:
                    f.write(f"GOOGLE_API_KEY={new_key}")
                CURRENT_API_KEY = new_key
            except Exception as e:
                print(f"Error saving .env: {e}")

        self.parent_win.save_settings()
        self.parent_win.apply_theme()
        self.parent_win.update_ui()
        self.close()


class MemoryManager:
    """SQLite-based long-term memory for the AI assistant."""

    def __init__(self, db_path=MEMORY_DB):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def save_fact(self, category: str, key: str, value: str):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO facts (category, key, value) VALUES (?, ?, ?)
        """,
            (category, key, value),
        )
        self.conn.commit()

    def get_fact(self, category: str, key: str) -> str:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT value FROM facts WHERE category = ? AND key = ?", (category, key)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_all_facts(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT category, key, value FROM facts ORDER BY category")
        return cursor.fetchall()

    def get_all_facts_with_id(self) -> list:
        """Returns all facts with their IDs for deletion."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, category, key, value FROM facts ORDER BY category, key"
        )
        return cursor.fetchall()

    def delete_fact(self, fact_id: int):
        """Deletes a fact by its ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self.conn.commit()

    def delete_facts_by_ids(self, ids: list):
        """Deletes multiple facts by their IDs."""
        cursor = self.conn.cursor()
        for fact_id in ids:
            cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self.conn.commit()

    def clear_all(self):
        """Clears all facts from memory."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM facts")
        self.conn.commit()

    def get_db_size_mb(self) -> float:
        """Returns the database file size in MB."""
        try:
            if os.path.exists(self.db_path):
                return os.path.getsize(self.db_path) / (1024 * 1024)
            return 0.0
        except:
            return 0.0

    def get_user_context(self) -> str:
        """Returns a formatted string of all known facts about the user."""
        facts = self.get_all_facts()
        if not facts:
            return ""
        lines = ["=== USER MEMORY ==="]
        for cat, key, val in facts:
            lines.append(f"[{cat}] {key}: {val}")
        return "\n".join(lines)

    def close(self):
        self.conn.close()


class MemoryCleanupDialog(QDialog):
    """Dialog for managing memory when database grows too large."""

    def __init__(self, memory: MemoryManager, current_size_mb: float, parent=None):
        super().__init__(parent)
        self.memory = memory
        self.current_size = current_size_mb
        self.checkboxes = {}
        self.action = None  # 'cleaned', 'ignore', 'remind_later'
        self.remind_size = 500

        self.setWindowTitle("🧠 Memory Management")
        self.setFixedSize(550, 500)
        self.setStyleSheet("""
            QDialog {
                background: #1a1a2e;
                color: white;
            }
            QLabel { color: white; }
            QLabel#title { font-size: 20px; font-weight: bold; color: #ff6b6b; }
            QLabel#subtitle { font-size: 13px; color: #aaa; }
            QScrollArea { background: transparent; border: none; }
            QWidget#scroll_content { background: transparent; }
            QCheckBox {
                color: white;
                padding: 8px;
                background: rgba(255,255,255,0.05);
                border-radius: 6px;
                margin: 2px 0;
            }
            QCheckBox:hover { background: rgba(255,255,255,0.1); }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:checked {
                background: #ff6b6b;
                border-radius: 4px;
            }
            QPushButton {
                background: rgba(255,255,255,0.1);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); }
            QPushButton#delete_btn { background: #ff6b6b; color: black; font-weight: bold; }
            QPushButton#delete_btn:hover { background: #ff8585; }
            QSpinBox {
                background: rgba(255,255,255,0.1);
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 6px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Title
        title = QLabel("⚠️ Memory Database is Large")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel(
            f"Your memory file is {current_size_mb:.1f} MB. Select items to delete:"
        )
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # Scrollable area with checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(250)

        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(4)

        facts = memory.get_all_facts_with_id()
        for fact_id, category, key, value in facts:
            display_text = (
                f"[{category}] {key}: {value[:50]}{'...' if len(value) > 50 else ''}"
            )
            cb = QCheckBox(display_text)
            cb.fact_id = fact_id
            self.checkboxes[fact_id] = cb
            scroll_layout.addWidget(cb)

        if not facts:
            scroll_layout.addWidget(QLabel("No memories stored yet."))

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Select all / Deselect all buttons
        select_layout = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self.select_all)
        btn_deselect = QPushButton("Deselect All")
        btn_deselect.clicked.connect(self.deselect_all)
        select_layout.addWidget(btn_select_all)
        select_layout.addWidget(btn_deselect)
        select_layout.addStretch()
        layout.addLayout(select_layout)

        # Delete selected button
        btn_delete = QPushButton("🗑️ Delete Selected")
        btn_delete.setObjectName("delete_btn")
        btn_delete.clicked.connect(self.delete_selected)
        layout.addWidget(btn_delete)

        # Separator
        layout.addSpacing(10)

        # Remind later option
        remind_layout = QHBoxLayout()
        remind_layout.addWidget(QLabel("Or remind me when file reaches:"))
        self.spin_remind = QSpinBox()
        self.spin_remind.setRange(100, 5000)
        self.spin_remind.setValue(1000)
        self.spin_remind.setSuffix(" MB")
        remind_layout.addWidget(self.spin_remind)
        btn_remind = QPushButton("Set & Close")
        btn_remind.clicked.connect(self.remind_later)
        remind_layout.addWidget(btn_remind)
        layout.addLayout(remind_layout)

        # Never show again button
        btn_ignore = QPushButton("Don't show this again")
        btn_ignore.clicked.connect(self.ignore_forever)
        layout.addWidget(btn_ignore)

    def select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def delete_selected(self):
        ids_to_delete = [
            fact_id for fact_id, cb in self.checkboxes.items() if cb.isChecked()
        ]
        if ids_to_delete:
            self.memory.delete_facts_by_ids(ids_to_delete)
            self.action = "cleaned"
            self.accept()
        else:
            QMessageBox.information(
                self, "No Selection", "Please select at least one item to delete."
            )

    def remind_later(self):
        self.action = "remind_later"
        self.remind_size = self.spin_remind.value()
        self.accept()

    def ignore_forever(self):
        self.action = "ignore"
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_lang = "EN"
        self.selected_voice = "Puck"
        self.dev_mode = False
        self.default_city = ""
        self.current_theme = "dark"
        self.is_running = False
        self.log_window = None  # Separate debug window

        self.load_settings()

        self.setWindowTitle("PY MYCROFT 2.0")
        self.resize(340, 620)
        self.setMinimumSize(300, 550)
        self.setStyleSheet("background-color: #1a1a1a;")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 16px;
                margin: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(16, 12, 16, 16)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #555; font-size: 18px;")
        header_layout.addWidget(self.status_indicator)

        self.status_label = QLabel("System Offline")
        self.status_label.setStyleSheet(
            "color: #888; font-size: 14px; font-weight: 500;"
        )
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(40, 40)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666;
                font-size: 22px;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background: #3d3d3d;
                color: #aaa;
            }
        """)
        self.btn_settings.clicked.connect(self.open_settings)
        header_layout.addWidget(self.btn_settings)

        card_layout.addLayout(header_layout)

        # Title
        self.title = QLabel("PY MYCROFT 2.0")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            font-family: 'Segoe UI', Arial, sans-serif;
            letter-spacing: 2px;
            padding: 6px 0;
        """)
        card_layout.addWidget(self.title)

        # Visualizer - fixed size 260x260
        self.viz = TechVisualizer()
        self.viz.setMinimumSize(260, 260)
        self.viz.setMaximumSize(260, 260)
        self.viz.set_dev_mode(self.dev_mode)
        card_layout.addWidget(self.viz, alignment=Qt.AlignmentFlag.AlignCenter)

        card_layout.addStretch()

        # Main button
        self.btn_main = QPushButton("INIT")
        self.btn_main.setFixedHeight(48)
        self.btn_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_main.clicked.connect(self.toggle)
        self.update_button_style()
        card_layout.addWidget(self.btn_main)

        # Debug console (GREEN color, bigger)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(140)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #00ff88;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: none;
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        self.console.setVisible(self.dev_mode)
        card_layout.addWidget(self.console)

        main_layout.addWidget(card)

        self.thread = None
        self.update_ui()
        self.check_api_key_on_startup()

    def check_api_key_on_startup(self):
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["EN"])
        if not CURRENT_API_KEY:
            self.update_status_display(False, t.get("no_api_key", "No API Key"))
        else:
            self.update_status_display(False, t.get("status_offline", "System Offline"))

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_lang = data.get("lang", "EN")
                    self.selected_voice = data.get("voice", "Puck")
                    self.dev_mode = data.get("dev_mode", False)
                    self.default_city = data.get("city", "")
                    self.current_theme = data.get("theme", "dark")
            except:
                pass

    def save_settings(self):
        data = {
            "lang": self.current_lang,
            "voice": self.selected_voice,
            "dev_mode": self.dev_mode,
            "city": self.default_city,
            "theme": self.current_theme,
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except:
            pass

    def apply_theme(self):
        if self.current_theme == "light":
            # Light theme - clean and readable
            self.setStyleSheet("background-color: #f0f4f8;")
            self.findChild(QFrame).setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border-radius: 16px;
                    margin: 12px;
                    border: 1px solid #d1d5db;
                }
            """)
            self.status_label.setStyleSheet(
                "color: #374151; font-size: 14px; font-weight: 600;"
            )
            self.title.setStyleSheet("""
                color: #111827;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                letter-spacing: 2px;
                padding: 6px 0;
            """)
            self.console.setStyleSheet("""
                QTextEdit {
                    background-color: #f9fafb;
                    color: #1d4ed8;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    border: 1px solid #d1d5db;
                    border-radius: 8px;
                    padding: 10px;
                    margin-top: 10px;
                }
            """)
        elif self.current_theme == "gray":
            # Gray theme
            self.setStyleSheet("background-color: #3a3a3a;")
            self.findChild(QFrame).setStyleSheet("""
                QFrame {
                    background-color: #4a4a4a;
                    border-radius: 16px;
                    margin: 12px;
                }
            """)
            self.status_label.setStyleSheet(
                "color: #aaa; font-size: 14px; font-weight: 500;"
            )
            self.title.setStyleSheet("""
                color: #e0e0e0;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                letter-spacing: 2px;
                padding: 6px 0;
            """)
            self.console.setStyleSheet("""
                QTextEdit {
                    background-color: #333;
                    color: #00cc88;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    margin-top: 10px;
                }
            """)
        else:
            # Dark theme (default)
            self.setStyleSheet("background-color: #1a1a1a;")
            self.findChild(QFrame).setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border-radius: 16px;
                    margin: 12px;
                }
            """)
            self.status_label.setStyleSheet(
                "color: #888; font-size: 14px; font-weight: 500;"
            )
            self.title.setStyleSheet("""
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                letter-spacing: 2px;
                padding: 6px 0;
            """)
            self.console.setStyleSheet("""
                QTextEdit {
                    background-color: #0a0a0a;
                    color: #00ff88;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    margin-top: 10px;
                }
            """)

    def update_button_style(self):
        if not CURRENT_API_KEY:
            self.btn_main.setText("NO API KEY")
            self.btn_main.setEnabled(False)
            self.btn_main.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #666;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 24px;
                    border: none;
                }
            """)
            return

        self.btn_main.setEnabled(True)
        if self.is_running:
            self.btn_main.setText("STOP")
            self.btn_main.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 24px;
                    border: none;
                }
                QPushButton:hover { background-color: #c0392b; }
                QPushButton:pressed { background-color: #a93226; }
            """)
        else:
            self.btn_main.setText("INIT")
            self.btn_main.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 24px;
                    border: none;
                }
                QPushButton:hover { background-color: #2980b9; }
                QPushButton:pressed { background-color: #1f6dad; }
            """)

    def update_status_display(self, online=False, text="System Offline"):
        if online:
            self.status_indicator.setStyleSheet("color: #2ecc71; font-size: 18px;")
            self.status_label.setStyleSheet(
                "color: #2ecc71; font-size: 14px; font-weight: 500;"
            )
        else:
            self.status_indicator.setStyleSheet("color: #555; font-size: 18px;")
            self.status_label.setStyleSheet(
                "color: #888; font-size: 14px; font-weight: 500;"
            )
        self.status_label.setText(text)

    def poll_ui_events(self):
        try:
            import queue

            while True:
                try:
                    event, data = self.ui_events_queue.get_nowait()
                    if event == "amplitude":
                        self.viz.update_level(data)
                    elif event == "status":
                        self.on_status_change(data)
                    elif event == "log":
                        self.log_msg(data)
                    elif event == "mode":
                        self.viz.set_visual_state(data)
                    elif event == "finished":
                        self.on_thread_finished()
                    elif event == "ready":
                        self.btn_main.setEnabled(True)
                        self.update_button_style()
                        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["EN"])
                        self.update_status_display(
                            True, t.get("status_online", "System Online")
                        )
                except queue.Empty:
                    break
        except Exception:
            pass

    def toggle(self):
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["EN"])
        if not CURRENT_API_KEY:
            QMessageBox.warning(self, "API Key", "Please add API key in Settings")
            return

        if self.is_running:
            self.log_msg("STOPPING...")
            if hasattr(self, "ai_cmd_queue"):
                self.ai_cmd_queue.put("STOP")
            if hasattr(self, "audio_cmd_queue"):
                self.audio_cmd_queue.put("STOP")
        else:
            self.console.clear()
            self.log_msg("INITIALIZING MULTIPROCESSING...")
            import multiprocessing

            self.ui_events_queue = multiprocessing.Queue()
            self.audio_to_ai_queue = multiprocessing.Queue()
            self.audio_to_speaker_queue = multiprocessing.Queue()
            self.ai_cmd_queue = multiprocessing.Queue()
            self.audio_cmd_queue = multiprocessing.Queue()

            use_wwd = True

            self.audio_process = multiprocessing.Process(
                target=audio_process_worker,
                args=(
                    self.audio_to_ai_queue,
                    self.audio_to_speaker_queue,
                    self.ui_events_queue,
                    self.audio_cmd_queue,
                    use_wwd,
                ),
            )
            self.ai_process = multiprocessing.Process(
                target=ai_process_worker,
                args=(
                    self.audio_to_ai_queue,
                    self.audio_to_speaker_queue,
                    self.ui_events_queue,
                    self.ai_cmd_queue,
                    self.audio_cmd_queue,
                    self.selected_voice,
                    self.default_city,
                    CURRENT_API_KEY,
                ),
            )
            self.audio_process.start()
            self.ai_process.start()

            self.ui_timer = QTimer()
            self.ui_timer.timeout.connect(self.poll_ui_events)
            self.ui_timer.start(30)

            self.is_running = True
            self.btn_main.setEnabled(False)
            self.btn_main.setText("LOADING...")
            self.btn_main.setStyleSheet("""
                QPushButton {
                    background-color: #f39c12;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 24px;
                    border: none;
                }
            """)
            self.update_status_display(True, "Loading Models...")

    def on_thread_finished(self):
        if hasattr(self, "ui_timer"):
            self.ui_timer.stop()
        self.is_running = False
        self.update_button_style()
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["EN"])
        self.update_status_display(False, t.get("status_offline", "System Offline"))
        self.viz.set_mode("idle")
        self.viz.set_visual_state("standby")
        self.log_msg("SYSTEM HALTED")

    def on_status_change(self, s):
        self.viz.set_mode(s)
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["EN"])

        if s == "listening":
            self.update_status_display(True, t.get("status_listening", "Listening..."))
        elif s == "processing":
            self.update_status_display(
                True, t.get("status_processing", "Processing...")
            )
        elif s == "speaking":
            self.update_status_display(True, t.get("status_speaking", "Speaking..."))
        else:
            if self.is_running:
                self.update_status_display(
                    True, t.get("status_online", "System Online")
                )

    def log_msg(self, msg):
        """Log message to console or separate window."""
        if self.dev_mode and self.log_window:
            # Log to separate window
            self.log_window.append_log(msg)
        else:
            # Log to inline console
            self.console.append(msg)
            self.console.verticalScrollBar().setValue(
                self.console.verticalScrollBar().maximum()
            )

    def closeEvent(self, event):
        """Close log window when main window closes."""
        if self.is_running:
            if hasattr(self, "ai_cmd_queue"):
                self.ai_cmd_queue.put("STOP")
            if hasattr(self, "audio_cmd_queue"):
                self.audio_cmd_queue.put("STOP")
            if hasattr(self, "audio_process") and self.audio_process.is_alive():
                self.audio_process.terminate()
            if hasattr(self, "ai_process") and self.ai_process.is_alive():
                self.ai_process.terminate()
        if self.log_window:
            self.log_window.close()
        super().closeEvent(event)

    def open_settings(self):
        SettingsDialog(self).exec()

    def update_ui(self):
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["EN"])

        # Manage separate debug window
        if self.dev_mode:
            if not self.log_window:
                self.log_window = LogWindow(self)
            self.log_window.show()
        else:
            if self.log_window:
                self.log_window.hide()

        # Always hide inline console (using separate window now)
        self.console.setVisible(False)

        self.viz.set_dev_mode(self.dev_mode)
        self.update_button_style()
        self.apply_theme()

        if not CURRENT_API_KEY:
            self.update_status_display(False, t.get("no_api_key", "No API Key"))
        elif not self.is_running:
            self.update_status_display(False, t.get("status_offline", "System Offline"))


if __name__ == "__main__":
    import multiprocessing

    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass
    app = QApplication(sys.argv)

    # Check memory size and show cleanup dialog if needed
    try:
        # Load settings to check memory warning preferences
        memory_warning_limit = 500  # Default 500 MB
        memory_warning_disabled = False

        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
                memory_warning_limit = settings_data.get("memory_warning_limit", 500)
                memory_warning_disabled = settings_data.get(
                    "memory_warning_disabled", False
                )

        if not memory_warning_disabled:
            memory = MemoryManager()
            size_mb = memory.get_db_size_mb()

            if size_mb >= memory_warning_limit:
                dialog = MemoryCleanupDialog(memory, size_mb)
                dialog.exec()

                # Save user's choice to settings
                if dialog.action:
                    try:
                        settings_data = {}
                        if os.path.exists(SETTINGS_FILE):
                            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                                settings_data = json.load(f)

                        if dialog.action == "ignore":
                            settings_data["memory_warning_disabled"] = True
                        elif dialog.action == "remind_later":
                            settings_data["memory_warning_limit"] = dialog.remind_size
                        # 'cleaned' doesn't change settings

                        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                            json.dump(settings_data, f, indent=4)
                    except:
                        pass

            memory.close()
    except Exception as e:
        print(f"Memory check error: {e}")

    window = MainWindow()

    # Apply theme based on settings
    if window.current_theme == "light":
        app.setStyleSheet(qdarktheme.load_stylesheet("light"))
    else:
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))

    window.show()
    sys.exit(app.exec())
