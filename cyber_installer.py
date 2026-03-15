def search_github_plugins(query: str):
    """
    AI DESCRIPTION: Searches for Mycroft 2.0 plugins on GitHub by keyword.
    CRITICAL RULE: Always extract ONLY the single most important root noun from the user's request.
    For example, if the user asks for "crypto tracker", pass ONLY "crypto". If "weather forecast", pass "weather".
    Returns a list of found plugins and direct links (RAW_URL) to their source code.
    """
    import requests

    try:
        # ЖЕСТКИЙ ФИЛЬТР: даже если ИИ передал фразу с опечатками ("crypto tracker"),
        # мы рубим строку и оставляем только первое, самое весомое слово ("crypto").
        # Это защищает от кривых названий репозиториев (traker, pycroft и т.д.)
        core_query = query.strip().split()[0].lower()

        # Ищем по очищенному корню + топику
        search_url = f"https://api.github.com/search/repositories?q={core_query}+topic:pymycroft-plugin"
        r = requests.get(search_url, timeout=5)
        data = r.json()

        if not data.get("items"):
            # Фолбэк без топика
            search_url = (
                f"https://api.github.com/search/repositories?q={core_query}+pymycroft"
            )
            r = requests.get(search_url, timeout=5)
            data = r.json()
            if not data.get("items"):
                return f"No plugins found for the core keyword: '{core_query}'."

        results = []
        for repo in data["items"][:2]:
            repo_name = repo["full_name"]
            desc = repo.get("description", "No description")
            branch = repo.get("default_branch", "main")

            tree_url = f"https://api.github.com/repos/{repo_name}/git/trees/{branch}?recursive=1"
            tr = requests.get(tree_url, timeout=5).json()

            py_files = [
                item["path"]
                for item in tr.get("tree", [])
                if item["path"].endswith(".py")
            ]

            if py_files:
                raw_url = f"https://raw.githubusercontent.com/{repo_name}/{branch}/{py_files[0]}"
                results.append(
                    f"Name: {repo_name}\nDescription: {desc}\nFile: {py_files[0]}\nRAW_URL: {raw_url}"
                )

        if results:
            return (
                f"Found plugins for '{core_query}':\n\n"
                + "\n\n".join(results)
                + "\n\nChoose the best one, copy the RAW_URL, and pass it to fetch_plugin_code for inspection."
            )
        return "Repositories found, but they contain no .py files."
    except Exception as e:
        return f"GitHub API search error: {e}"


def fetch_plugin_code(raw_url: str):
    """
    AI DESCRIPTION: Downloads the source code from a raw URL and returns it to YOU (the AI) for analysis.
    CRITICAL: NEVER read the retrieved code out loud to the user! Review it silently in your context.
    """
    import requests

    try:
        response = requests.get(raw_url, timeout=5)
        if response.status_code == 200:
            code = response.text

            # 1. Защита от огромных файлов (ограничение 20КБ)
            if len(code) > 20000:
                return "REJECTED: File is too large (>20KB). This might be a malicious payload or an invalid plugin."

            # 2. Базовый статический сканер опасных вызовов
            dangerous_patterns = ["eval(", "exec(", "os.system(", "subprocess."]
            found_dangers = [p for p in dangerous_patterns if p in code]

            if found_dangers:
                return f"WARNING: Found potentially dangerous calls in code: {', '.join(found_dangers)}. You must heavily inspect these lines before calling approve_and_save_plugin!\\n\\nCODE:\\n{code}"

            return code
        return f"Failed to download. HTTP Status: {response.status_code}"
    except Exception as e:
        return f"Download error: {e}"


def approve_and_save_plugin(code: str, filename: str):
    """
    AI DESCRIPTION: Call this function ONLY if you have reviewed the code from fetch_plugin_code
    and confirmed it is 100% safe (no malicious commands, no token stealers, no destructive os.system calls).
    This function saves the approved code to the user's local disk.
    """
    import os

    try:
        # Последняя линия обороны внутри самого сохранятора
        if len(code) > 20000:
            return "ERROR: Code exceeds 20KB limit. Aborting installation."

        if not filename.endswith(".py"):
            filename += ".py"

        # Security: prevent directory traversal attacks (e.g., passing "../../etc/passwd")
        safe_filename = os.path.basename(filename)
        filepath = os.path.join("plugins", safe_filename)

        # Ensure plugins directory exists
        if not os.path.exists("plugins"):
            os.makedirs("plugins")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        return f"SUCCESS: Plugin '{safe_filename}' installed successfully. It will be loaded on the next request."
    except Exception as e:
        return f"Error saving plugin: {e}"


# Update the registration so the AI model sees all the tools
def register_plugin():
    """
    Mandatory entry point for the plugin loader.
    """
    tools = [search_github_plugins, fetch_plugin_code, approve_and_save_plugin]
    mapping = {
        "search_github_plugins": search_github_plugins,
        "fetch_plugin_code": fetch_plugin_code,
        "approve_and_save_plugin": approve_and_save_plugin,
    }
    return tools, mapping
