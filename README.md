# py-mycroft-2.0
🚀 Py Mycroft 2.0 — An autonomous AI voice assistant powered by Google Gemini. Features a self-expanding dynamic plugin ecosystem: tell it what you need, and it finds, reviews, and installs its own skills from GitHub.


# 🎙️ Py Mycroft 2.0

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Py Mycroft 2.0 is an advanced, voice-controlled AI assistant designed for Linux (optimized for Arch/KDE). It doesn't just answer questions — it executes local commands, remembers context, and **dynamically expands its own capabilities**.

## 🔥 The Killer Feature: AI Package Manager
Unlike static assistants, Mycroft 2.0 can upgrade itself. Need a weather tracker or a crypto parser? Just say:
> *"Mycroft, find and install a crypto tracker plugin."*

The AI will:
1. Search GitHub for repositories tagged with `pymycroft-plugin`.
2. Extract the raw Python code.
3. **Silently review the code for security** (preventing malicious commands).
4. Save it to the local `plugins/` directory and activate it instantly.

## 🛠️ Built-in Capabilities
* **System Control:** Launch apps, control media, adjust volume.
* **Computer Vision:** Can take screenshots (`spectacle`) and analyze your screen context.
* **Long-Term Memory:** Uses a local SQLite database to remember important facts about you.
* **Internet Research:** Real-time web search and summarization.

## 🚀 Quick Start
1. Clone the repo:
   ```bash
   git clone https://github.com/archpulse/py-mycroft-2.0.git
   cd py-mycroft-2.0
Install dependencies (Requires portaudio for mic access):

Bash
pip install -r requirements.txt
Set your Google Gemini API Key in the UI settings or create a .env file:


GOOGLE_API_KEY=your_api_key_here

Run the core:



python main.py

🧩 How to Write a Plugin
Creating a skill for Mycroft is incredibly simple. Just write a standalone .py file with your functions and a register_plugin() entry point.
Add the pymycroft-plugin topic to your GitHub repo, and the assistant will find it automatically!


(Check the plugins/ folder for examples).
