#!/usr/bin/env python3
"""
Development server with file watching for Citation Needed
"""

import os
import subprocess
import sys
import time


def watch_and_reload():
    """Watch for file changes and restart the app"""

    # Files to watch
    watch_files = ["app.py", "models/", "ui/", "search/"]

    # Get initial modification times
    def get_mtimes():
        mtimes = {}
        for item in watch_files:
            if os.path.isfile(item):
                mtimes[item] = os.path.getmtime(item)
            elif os.path.isdir(item):
                for root, _dirs, files in os.walk(item):
                    for file in files:
                        if file.endswith(".py") or file.endswith(".css"):
                            path = os.path.join(root, file)
                            mtimes[path] = os.path.getmtime(path)
        return mtimes

    print("🔥 Citation Needed Development Server")
    print("Watching for file changes...")
    print("Press Ctrl+C to stop")

    process = None
    last_mtimes = get_mtimes()

    def start_app():
        nonlocal process
        if process:
            process.terminate()
            process.wait()

        print(f"\n{'=' * 50}")
        print("🚀 Starting app...")
        process = subprocess.Popen([sys.executable, "app.py"])
        return process

    # Start initial app
    process = start_app()

    try:
        while True:
            time.sleep(1)  # Check every second

            current_mtimes = get_mtimes()

            # Check if any files changed
            changed_files = []
            for file, mtime in current_mtimes.items():
                if file not in last_mtimes or mtime != last_mtimes[file]:
                    changed_files.append(file)

            if changed_files:
                print(f"\n📝 Files changed: {', '.join(changed_files)}")
                print("🔄 Reloading...")
                last_mtimes = current_mtimes
                process = start_app()

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping development server...")
        if process:
            process.terminate()
            process.wait()
        print("👋 Goodbye!")


if __name__ == "__main__":
    watch_and_reload()
