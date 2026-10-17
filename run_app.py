import os
import sys

import streamlit  # noqa: F401  (kept so PyInstaller detects and bundles Streamlit)


def skip_email_prompt():
    """Streamlit asks for an email on first run unless a credentials file exists.
    Writing an empty one lets the packaged app start without any prompt."""
    cred = os.path.join(os.path.expanduser("~"), ".streamlit", "credentials.toml")
    if not os.path.exists(cred):
        os.makedirs(os.path.dirname(cred), exist_ok=True)
        with open(cred, "w", encoding="utf-8") as f:
            f.write('[general]\nemail = ""\n')


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS          # folder where PyInstaller put app.py
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    skip_email_prompt()

    app_path = os.path.join(base_dir, "app.py")

    # Same as typing:  streamlit run app.py ...
    # Not headless, so Streamlit opens your browser automatically.
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]

    from streamlit.web import cli as stcli

    sys.exit(stcli.main())