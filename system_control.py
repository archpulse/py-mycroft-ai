def lock_workstation():
    """Locks the system screen (KDE Plasma)."""
    import os

    # Native systemd command, which KDE intercepts to gracefully lock the screen
    result = os.system("loginctl lock-session")

    if result == 0:
        return "Screen locked successfully."
    else:
        return "Error: failed to lock KDE screen."


# Mandatory interface function for the dynamic plugin loader
def register_plugin():
    mapping = {"lock_workstation": lock_workstation}
    tools = [
        lock_workstation
    ]  # Google extracts the name and description from the docstring automatically
    return tools, mapping