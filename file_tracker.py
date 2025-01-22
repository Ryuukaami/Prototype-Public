import time
import json
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, tracked_files, reset_threshold=3):
        super().__init__()
        self.tracked_files = tracked_files
        self.allowed_extensions = ['.py', '.docx', '.xlsx', '.txt', '.html', '.css', '.js']
        self.excluded_dirs = ['C:\\Windows', 'C:\\Program Files', 'C:\\ProgramData']
        self.reset_threshold = reset_threshold

    def on_modified(self, event):
        if not event.is_directory:
            self.handle_file_event(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self.handle_file_event(event.src_path)

    def handle_file_event(self, file_path):
        if any(excluded in file_path for excluded in self.excluded_dirs):
            return

        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[-1].lower()

        if file_extension not in self.allowed_extensions:
            return

        # Exclude junk file patterns (e.g., browser cache, temporary files)
        junk_patterns = [
            ".br[1].js",  # Browser cache files
            "[1].js",     # Temporary JavaScript files
        # add more pattern later
        ]
        if any(pattern in file_name for pattern in junk_patterns):
            return

        # Log relevant file
        current_time = time.strftime("%Y-%m-%dT%H:%M:%S")
        if "current_session" not in self.tracked_files:
            self.tracked_files["current_session"] = {}

        if file_name not in self.tracked_files["current_session"]:
            self.tracked_files["current_session"][file_name] = current_time
            print(f"File Detected: {file_name}")

            self.save_tracked_files()


    def save_tracked_files(self):
        try:
            with open("file_activity.json", "w") as file:
                json.dump(self.tracked_files, file, indent=4)
        except IOError as e:
            print(f"Error saving file activity: {e}")

def update_device_state(state_type):
    try:
        with open("device_state.json", "r") as state_file:
            device_state = json.load(state_file)
    except (FileNotFoundError, json.JSONDecodeError):
        device_state = {"last_awake": None, "last_sleep": None}

    current_time = datetime.now().isoformat()
    
    if state_type == "awake":
        # Only update wake time if we were previously sleeping
        if device_state.get("last_sleep"):
            device_state["last_awake"] = current_time
    elif state_type == "sleep":
        device_state["last_sleep"] = current_time
        # Transfer current session data to previous session when going to sleep
        transfer_session_data(tracked_files)

    with open("device_state.json", "w") as state_file:
        json.dump(device_state, state_file, indent=4)

def transfer_session_data(tracked_files):
    if "current_session" not in tracked_files:
        tracked_files["current_session"] = {}
    if "previous_session" not in tracked_files:
        tracked_files["previous_session"] = {}

    current_session_files = tracked_files["current_session"]

    if len(current_session_files) >= 3:
        print("Transferring current session data to previous session (replacing previous session)...")
        tracked_files["previous_session"] = current_session_files
    else:
        print("Merging current session data into previous session...")
        tracked_files["previous_session"].update(current_session_files)

    tracked_files["current_session"] = {}

    try:
        with open("file_activity.json", "w") as file:
            json.dump(tracked_files, file, indent=4)
        print("Session data successfully updated.")
    except IOError as e:
        print(f"Error transferring session data: {e}")

def monitor_system():
    folder_to_watch = "C:\\"
    print(f"Monitoring system-wide: {folder_to_watch}")

    tracked_files = {"previous_session": {}, "current_session": {}}

    try:
        with open("file_activity.json", "r") as file:
            tracked_files = json.load(file)
            if not isinstance(tracked_files, dict):
                tracked_files = {"previous_session": {}, "current_session": {}}
    except (FileNotFoundError, json.JSONDecodeError):
        print("Initializing file_activity.json...")
        with open("file_activity.json", "w") as file:
            json.dump(tracked_files, file, indent=4)

    event_handler = FileMonitorHandler(tracked_files)
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
        print("Monitoring stopped.")
        transfer_session_data(tracked_files)

    observer.join()

if __name__ == "__main__":
    update_device_state("awake")
    monitor_system()