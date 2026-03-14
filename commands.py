import datetime
import io
import os
import random
import re
import subprocess
import webbrowser
from pathlib import Path

import psutil
import pyautogui
import requests
from duckduckgo_search import DDGS

# Cached HTTP session for performance
_http_session = requests.Session()
_http_session.headers.update(
    {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
)

# ----------------------------
# BASIC UTILITIES
# ----------------------------


def open_website(url: str):
    """Opens the specified URL or website in the browser."""
    webbrowser.open(url)
    return f"Opening link: {url}"


def run_app(app_name: str):
    """Launches an application by name (e.g., firefox, nautilus, code)."""

    # Dictionary of web versions of popular applications
    web_alternatives = {
        "spotify": "https://open.spotify.com",
        "discord": "https://discord.com/app",
        "telegram": "https://web.telegram.org",
        "whatsapp": "https://web.whatsapp.com",
        "slack": "https://app.slack.com",
        "notion": "https://www.notion.so",
        "figma": "https://www.figma.com",
        "youtube": "https://www.youtube.com",
        "netflix": "https://www.netflix.com",
        "twitch": "https://www.twitch.tv",
        "twitter": "https://twitter.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "gmail": "https://mail.google.com",
        "outlook": "https://outlook.live.com",
        "drive": "https://drive.google.com",
        "docs": "https://docs.google.com",
        "sheets": "https://sheets.google.com",
    }

    app_lower = app_name.lower().strip()

    # Check if the application is installed
    try:
        result = subprocess.run(["which", app_lower], capture_output=True, text=True)
        app_exists = result.returncode == 0
    except:
        app_exists = False

    if app_exists:
        # Application found - launch it
        try:
            subprocess.Popen(
                [app_lower],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Application {app_name} launched."
        except Exception as e:
            return f"Error launching {app_name}: {e}"
    else:
        # Application not found - look for a web alternative
        if app_lower in web_alternatives:
            url = web_alternatives[app_lower]
            webbrowser.open(url)
            return f"Application {app_name} is not installed locally. Opening web version in browser: {url}. What would you like to do next?"
        else:
            return f"Application {app_name} not found locally and no web version is available."


# ----------------------------
# INTERNET
# ----------------------------


def internet_research(query: str):
    """Performs an internet search and returns a brief answer."""
    # Attempt 1: DuckDuckGo
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3, timeout=10))
        if results:
            return "\n".join(
                f"{i}. {r['title']}: {r['body']}" for i, r in enumerate(results, 1)
            )
    except Exception as e:
        print(f"DuckDuckGo error: {e}")

    # Attempt 2: Wikipedia API
    try:
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        r = _http_session.get(wiki_url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if "extract" in data:
                return f"{data.get('title', query)}: {data['extract']}"
    except Exception as e:
        print(f"Wikipedia error: {e}")

    # Attempt 3: HTML search via DuckDuckGo
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        r = _http_session.get(search_url, timeout=8)
        if r.status_code == 200:
            snippets = re.findall(r'class="result__snippet"[^>]*>([^<]+)<', r.text)
            if snippets:
                return f"Result: {snippets[0]}"
    except Exception as e:
        print(f"HTML search error: {e}")

    return f"Unfortunately, search is temporarily unavailable. Please try again later or rephrase your query: {query}"


def get_news(city: str):
    """Searches for the latest news for a specific city."""
    return internet_research(f"новости {city} сегодня")


def get_weather(city: str):
    """Retrieves current weather via wttr.in service."""
    try:
        r = _http_session.get(f"https://wttr.in/{city}?format=3", timeout=5)
        if r.status_code == 200:
            return r.text.strip()
        else:
            return f"Weather service returned an error (code {r.status_code})"
    except requests.exceptions.Timeout:
        return "Weather server response timeout exceeded"
    except requests.exceptions.ConnectionError:
        return "No internet connection. Please check your network."
    except Exception as e:
        return f"Error fetching weather: {e}"


# ----------------------------
# SYSTEM
# ----------------------------


def get_system_stats():
    """Returns current CPU and RAM usage."""
    cpu = psutil.cpu_percent(interval=0.1)  # Reduced interval for speed
    mem = psutil.virtual_memory().percent
    return f"System status: CPU: {cpu}%, RAM: {mem}%"


# ----------------------------
# MEDIA (Windows)
# ----------------------------


def media_play_pause():
    """Toggles playback (pause/start)."""
    pyautogui.press("playpause")
    return "Media: Play/Pause"


def media_next():
    """Switches to the next track."""
    pyautogui.press("nexttrack")
    return "Media: Next track"


def media_prev():
    """Switches to the previous track."""
    pyautogui.press("prevtrack")
    return "Media: Previous track"


def set_volume(action: str):
    """Changes system volume (up - louder, down - quieter)."""
    if action == "up":
        pyautogui.press("volumeup", presses=5)
    else:
        pyautogui.press("volumedown", presses=5)
    return f"Volume changed: {action}"


# ----------------------------
# TIME OF DAY BY CITY
# ----------------------------

# Timezone cache to avoid requesting every time
_timezone_cache = {}


def get_city_time_info(city: str):
    """Determines the current time and time of day for the specified city.
    Returns a dictionary with hour, period (morning/day/evening/night), formatted_time."""
    try:
        # Mapping popular cities to timezones (fast path)
        CITY_TZ_MAP = {
            # Ukraine
            "ужгород": "Europe/Uzhgorod",
            "киев": "Europe/Kiev",
            "київ": "Europe/Kiev",
            "львов": "Europe/Kiev",
            "львів": "Europe/Kiev",
            "одесса": "Europe/Kiev",
            "одеса": "Europe/Kiev",
            "харьков": "Europe/Kiev",
            "харків": "Europe/Kiev",
            "днепр": "Europe/Kiev",
            "дніпро": "Europe/Kiev",
            # Russia
            "москва": "Europe/Moscow",
            "санкт-петербург": "Europe/Moscow",
            "петербург": "Europe/Moscow",
            "новосибирск": "Asia/Novosibirsk",
            "екатеринбург": "Asia/Yekaterinburg",
            "казань": "Europe/Moscow",
            # Europe
            "berlin": "Europe/Berlin",
            "london": "Europe/London",
            "paris": "Europe/Paris",
            "madrid": "Europe/Madrid",
            "rome": "Europe/Rome",
            "roma": "Europe/Rome",
            "warsaw": "Europe/Warsaw",
            "варшава": "Europe/Warsaw",
            "prague": "Europe/Prague",
            "прага": "Europe/Prague",
            "budapest": "Europe/Budapest",
            "будапешт": "Europe/Budapest",
            "vienna": "Europe/Vienna",
            "вена": "Europe/Vienna",
            # America
            "new york": "America/New_York",
            "нью-йорк": "America/New_York",
            "los angeles": "America/Los_Angeles",
            "лос-анджелес": "America/Los_Angeles",
            "chicago": "America/Chicago",
            "чикаго": "America/Chicago",
            # Asia
            "tokyo": "Asia/Tokyo",
            "токио": "Asia/Tokyo",
            "beijing": "Asia/Shanghai",
            "пекин": "Asia/Shanghai",
            "seoul": "Asia/Seoul",
            "сеул": "Asia/Seoul",
            "istanbul": "Europe/Istanbul",
            "стамбул": "Europe/Istanbul",
            "dubai": "Asia/Dubai",
            "дубай": "Asia/Dubai",
        }

        city_lower = city.lower().strip()
        tz_name = CITY_TZ_MAP.get(city_lower)

        if tz_name:
            # Use TimeAPI for accurate time
            try:
                r = _http_session.get(
                    f"https://timeapi.io/api/time/current/zone?timeZone={tz_name}",
                    timeout=5,
                )
                if r.status_code == 200:
                    data = r.json()
                    hour = data.get("hour", 12)
                else:
                    # Fallback: use offset calculation
                    hour = datetime.datetime.now().hour  # approximately
            except:
                hour = datetime.datetime.now().hour
        else:
            # Try via geocoding for unknown cities
            try:
                r = _http_session.get(
                    f"https://timeapi.io/api/timezone/zone?timeZone=Europe/Kiev",
                    timeout=5,
                )
                hour = datetime.datetime.now().hour  # fallback
            except:
                hour = datetime.datetime.now().hour

        # Determine the period of the day
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "day"
        elif 17 <= hour < 22:
            period = "evening"
        else:
            period = "night"

        return {
            "hour": hour,
            "period": period,
            "formatted_time": f"{hour:02d}:00",
            "city": city,
        }
    except Exception as e:
        return {"hour": 12, "period": "day", "formatted_time": "12:00", "city": city}


# ----------------------------
# WAITING PHRASES (VARIABILITY)
# ----------------------------

WAITING_PHRASES = {
    "RU": [
        "Секунду...",
        "Сейчас посмотрю...",
        "Одну минутку...",
        "Подождите, пожалуйста...",
        "Секундочку...",
        "Сейчас узнаю...",
        "Дайте мне секунду...",
        "Момент...",
        "Сейчас проверю...",
        "Уже ищу...",
        "Подождите немного...",
        "Сейчас сейчас...",
        "Один момент...",
        "Сию секунду...",
    ],
    "UA": [
        "Секундочку...",
        "Зараз подивлюсь...",
        "Одну хвилинку...",
        "Зачекайте, будь ласка...",
        "Зараз дізнаюсь...",
        "Дайте мені секунду...",
        "Момент...",
        "Зараз перевірю...",
        "Вже шукаю...",
        "Зачекайте трохи...",
    ],
    "EN": [
        "One moment...",
        "Let me check...",
        "Just a second...",
        "Hold on...",
        "Give me a moment...",
        "Looking into it...",
        "Let me look that up...",
        "One sec...",
        "Bear with me...",
        "Checking now...",
    ],
    "DE": [
        "Einen Moment...",
        "Sekunde...",
        "Einen Augenblick...",
        "Moment bitte...",
        "Ich schaue mal...",
    ],
    "ES": [
        "Un momento...",
        "Un segundo...",
        "Déjame ver...",
        "Espera un momento...",
        "Ya lo busco...",
    ],
    "FR": [
        "Un instant...",
        "Une seconde...",
        "Laissez-moi vérifier...",
        "Un moment s'il vous plaît...",
        "Je regarde...",
    ],
}


def get_random_waiting_phrase(lang: str = "RU") -> str:
    """Returns a random waiting phrase in the specified language."""
    phrases = WAITING_PHRASES.get(lang, WAITING_PHRASES.get("EN", ["One moment..."]))
    return random.choice(phrases)


# ----------------------------
# SCREENSHOT
# ----------------------------


def capture_screen():
    """Captures the screen and sends it to your visual stream."""
    import io
    import os
    import subprocess

    from PIL import Image

    tmp_file = "/tmp/v.jpg"
    debug_file = os.path.expanduser("~/debug_screen.jpg")

    try:
        # Silent screenshot
        subprocess.run(
            ["spectacle", "-b", "-n", "-o", tmp_file],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            check=True,
        )

        with Image.open(tmp_file) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")

            # AGGRESSIVE COMPRESSION: turn screenshot into a lightweight video frame
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG", quality=60)
            data = img_byte_arr.getvalue()

            # Save a copy for verification
            img.save(debug_file, format="JPEG", quality=60)

        os.remove(tmp_file)
        return data
    except Exception as e:
        return f"Error capturing screen: {e}"


# ----------------------------
# ENTERTAINMENT
# ----------------------------


def roll_dice():
    """Rolls a die."""
    return f"Dice roll result: 🎲 {random.randint(1, 6)}"


def coin_flip():
    """Flips a coin."""
    return "🪙 Result: Heads" if random.random() > 0.5 else "🪙 Result: Tails"


def play_music(query: str):
    """Searches for and plays music/track on YouTube."""
    try:
        # Keywords for abstract queries
        ABSTRACT_KW = {
            "самый",
            "лучший",
            "популярный",
            "топ",
            "best",
            "top",
            "popular",
            "most",
        }
        query_lower = query.lower()

        actual_track = query
        if any(kw in query_lower for kw in ABSTRACT_KW):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(f"{query} 2024", max_results=1))
                if results:
                    text = f"{results[0].get('body', '')} {results[0].get('title', '')}"
                    # Look for "Artist - Song" pattern
                    match = re.search(
                        r"([A-Za-zА-Яа-яЁё0-9\s\-]+)\s*[-–—]\s*([A-Za-zА-Яа-яЁё0-9\s\-]+)",
                        text,
                    )
                    actual_track = (
                        f"{match.group(1).strip()} - {match.group(2).strip()}"
                        if match
                        else " ".join(text.split()[:5])
                    )
            except:
                pass

        webbrowser.open(
            f"https://www.youtube.com/results?search_query={actual_track.replace(' ', '+')}+official"
        )
        return f"Opening: {actual_track}"
    except Exception as e:
        return f"Error: {e}"


def play_on_spotify(query: str):
    """Opens track search in Spotify Web."""
    try:
        ABSTRACT_KW = {"самый", "лучший", "популярный", "топ", "best", "top", "popular"}
        query_lower = query.lower()

        actual_track = query
        if any(kw in query_lower for kw in ABSTRACT_KW):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(f"{query} 2024 spotify", max_results=1))
                if results:
                    text = results[0].get("title", "")
                    match = re.search(
                        r"([A-Za-zА-Яа-яЁё0-9\s]+)\s*[-–]\s*([A-Za-zА-Яа-яЁё0-9\s]+)",
                        text,
                    )
                    if match:
                        actual_track = (
                            f"{match.group(1).strip()} {match.group(2).strip()}"
                        )
            except:
                pass

        webbrowser.open(
            f"https://open.spotify.com/search/{actual_track.replace(' ', '%20')}"
        )
        return f"Opening Spotify: {actual_track}"
    except Exception as e:
        return f"Error: {e}"


# ----------------------------
# MEMORY
# ----------------------------


def save_memory(category: str, key: str, value: str):
    """Saves information to long-term memory. Use to remember important facts about the user.
    Examples: save_memory('user', 'favorite_color', 'blue'), save_memory('user', 'pet_name', 'Барсик')"""
    import sqlite3

    try:
        conn = sqlite3.connect("memory.db")
        cursor = conn.cursor()
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
        cursor.execute(
            "INSERT OR REPLACE INTO facts (category, key, value) VALUES (?, ?, ?)",
            (category, key, value),
        )
        conn.commit()
        conn.close()
        return f"✅ Remembered: {key} = {value}"
    except Exception as e:
        return f"Error saving memory: {e}"


def get_memory(category: str, key: str):
    """Retrieves information from long-term memory."""
    import sqlite3

    try:
        conn = sqlite3.connect("memory.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM facts WHERE category = ? AND key = ?", (category, key)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return f"{key}: {row[0]}"
        return f"I do not remember information about {key}"
    except Exception as e:
        return f"Error reading memory: {e}"


def standby_mode():
    """CRITICAL: Call this function IMMEDIATELY if the user says 'dialog finished', 'bye', 'hang up', or wants to end the conversation. This is the only way to go to sleep."""
    return "System switched to standby mode."


# ----------------------------
# TOOL REGISTRATION (NO LAMBDA)
# ----------------------------

TOOLS_MAPPING = {
    "run_app": run_app,
    "open_website": open_website,
    "internet_research": internet_research,
    "get_news": get_news,
    "get_weather": get_weather,
    "get_system_stats": get_system_stats,
    "media_play_pause": media_play_pause,
    "media_next": media_next,
    "media_prev": media_prev,
    "set_volume": set_volume,
    "roll_dice": roll_dice,
    "coin_flip": coin_flip,
    "capture_screen": capture_screen,
    "play_music": play_music,
    "play_on_spotify": play_on_spotify,
    "save_memory": save_memory,
    "get_memory": get_memory,
    "get_city_time_info": get_city_time_info,
    "standby_mode": standby_mode,
}

TOOLS_LIST = list(TOOLS_MAPPING.values())
