import atexit
import os
import socket
import subprocess
import sys
import tempfile
import time
import webbrowser

import streamlit  # noqa: F401  (kept so PyInstaller detects and bundles Streamlit)

APP_TITLE = "Blend 0.1"


# ------------------------------------------------------------------ helpers
def setup_logging():
    """Write logs right next to the executable for easy debugging."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_path = os.path.join(exe_dir, "blend.log")
    log = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log
    sys.stderr = log


def base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS           # folder where PyInstaller put app.py
    return os.path.dirname(os.path.abspath(__file__))


def skip_email_prompt():
    cred = os.path.join(os.path.expanduser("~"), ".streamlit", "credentials.toml")
    if not os.path.exists(cred):
        os.makedirs(os.path.dirname(cred), exist_ok=True)
        with open(cred, "w", encoding="utf-8") as f:
            f.write('[general]\nemail = ""\n')


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(port, proc, timeout=300):
    """True once the server accepts connections; False if it died or timed out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ------------------------------------------------------------------ server mode
def run_server(port):
    skip_email_prompt()
    sys.argv = [
        "streamlit",
        "run",
        os.path.join(base_dir(), "app.py"),
        "--global.developmentMode=false",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.headless=true",              # our own window opens the page
        "--browser.gatherUsageStats=false",
    ]
    from streamlit.web import cli as stcli

    sys.exit(stcli.main())


# ------------------------------------------------------------------ window modes
LOADING_HTML = (
    "<html><body style='font-family:Segoe UI,sans-serif;background:#0e1117;color:#eee;"
    "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
    "<div style='text-align:center'><h2>Starting Blend...</h2>"
    "<p>The first start can take a minute while the model loads.</p></div></body></html>"
)
ERROR_HTML = (
    "<html><body style='font-family:Segoe UI,sans-serif;padding:2em'>"
    "<h3>Blend could not start.</h3>"
    "<p>See the log file (blend.log) next to the application executable.</p></body></html>"
)


def open_native_window(webview, url, port, proc):
    window = webview.create_window(APP_TITLE, html=LOADING_HTML, width=1100, height=820)

    def go():
        if wait_for_server(port, proc):
            window.load_url(url)
        else:
            window.load_html(ERROR_HTML)

    webview.start(go)           # blocks until the window is closed


def find_edge():
    for var in ("ProgramFiles(x86)", "ProgramFiles"):
        root = os.environ.get(var)
        if root:
            path = os.path.join(root, "Microsoft", "Edge", "Application", "msedge.exe")
            if os.path.exists(path):
                return path
    return None


def open_edge_app(url, port, proc):
    if not wait_for_server(port, proc):
        return
    edge = find_edge()
    if edge:
        profile = tempfile.mkdtemp(prefix="blend_edge_")       # separate instance, so wait() works
        subprocess.Popen([edge, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run"]).wait()
    else:
        webbrowser.open(url)
        proc.wait()


# ------------------------------------------------------------------ main
def main():
    setup_logging()

    if "--server" in sys.argv:
        port = int(next(a.split("=", 1)[1] for a in sys.argv if a.startswith("--port=")))
        run_server(port)
        return

    port = free_port()
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--server", f"--port={port}"]
    else:
        cmd = [sys.executable, os.path.abspath(__file__), "--server", f"--port={port}"]

    proc = subprocess.Popen(cmd)
    atexit.register(stop, proc)
    url = f"http://127.0.0.1:{port}"

    try:
        import webview
    except ImportError:
        webview = None

    if webview is not None:
        open_native_window(webview, url, port, proc)
    else:
        open_edge_app(url, port, proc)

    stop(proc)


if __name__ == "__main__":
    main()