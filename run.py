import os
import sys
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:8000/')

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    threading.Thread(target=open_browser, daemon=True).start()
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line([sys.argv[0], 'runserver', '127.0.0.1:8000'])
