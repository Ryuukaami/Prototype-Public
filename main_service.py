import multiprocessing
import time
import os
import sys
import json
import signal
from subprocess import Popen
from datetime import datetime
import win32api
import win32con
import win32gui
import win32ts

class PowerStateMonitor:
    def __init__(self, tracker_process_ref):
        self.WM_POWERBROADCAST = 0x0218
        self.PBT_APMRESUMEAUTOMATIC = 0x0012
        self.PBT_APMSUSPEND = 0x0004
        self.tracker_process_ref = tracker_process_ref
        
    def create_window(self):
        """Create a hidden window to receive power broadcasts"""
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._window_proc
        wc.lpszClassName = "PowerMonitorWindow"
        wc.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        return win32gui.CreateWindow(
            class_atom,
            "PowerMonitor",
            0,
            0, 0, 0, 0,
            0,
            0,
            wc.hInstance,
            None
        )

    def _window_proc(self, hwnd, msg, wparam, lparam):
        """Window procedure to handle power broadcast messages"""
        if msg == self.WM_POWERBROADCAST:
            if wparam == self.PBT_APMRESUMEAUTOMATIC:
                self._on_resume()
            elif wparam == self.PBT_APMSUSPEND:
                self._on_suspend()
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _on_suspend(self):
        """Handle system suspend event"""
        print("[Service] System entering sleep state")
        # Stop file tracker if running
        if self.tracker_process_ref.get('process') and self.tracker_process_ref['process'].is_alive():
            print("[Service] Stopping file tracker before sleep")
            self.tracker_process_ref['process'].terminate()
            self.tracker_process_ref['process'].join()
            self.tracker_process_ref['process'] = None

        current_state = load_device_state()
        if current_state:
            current_state["last_sleep"] = datetime.now().isoformat()
            save_device_state(current_state)

    def _on_resume(self):
        """Handle system resume event"""
        print("[Service] System resuming from sleep state")
        current_state = load_device_state()
        if current_state:
            current_state["last_awake"] = datetime.now().isoformat()
            save_device_state(current_state)
            
        # Clear the handled_state.json to force authentication
        try:
            os.remove("handled_state.json")
        except FileNotFoundError:
            pass

def initialize_device_state():
    """Initialize the device state file with default values."""
    current_time = datetime.now().isoformat()
    initial_state = {
        "last_awake": current_time,
        "last_sleep": None
    }
    try:
        with open("device_state.json", "w") as state_file:
            json.dump(initial_state, state_file, indent=4)
        return initial_state
    except IOError as e:
        print(f"[Service] Error initializing device state: {e}")
        return None

def load_device_state(set_awake=False):
    """Load the device state, initialize if not present."""
    try:
        with open("device_state.json", "r") as state_file:
            state = json.load(state_file)
            if "last_awake" not in state or "last_sleep" not in state:
                return initialize_device_state()
            
            if set_awake:
                state["last_awake"] = datetime.now().isoformat()
                save_device_state(state)
            
            return state
    except (FileNotFoundError, json.JSONDecodeError):
        return initialize_device_state()

def save_device_state(state):
    """Save the device state."""
    try:
        with open("device_state.json", "w") as state_file:
            json.dump(state, state_file, indent=4)
    except IOError as e:
        print(f"[Service] Error saving device state: {e}")

def load_last_handled_awake():
    """Load the last handled wake-up timestamp from a file."""
    try:
        with open("handled_state.json", "r") as state_file:
            state = json.load(state_file)
            return datetime.fromisoformat(state.get("last_handled_awake"))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None

def save_last_handled_awake(timestamp):
    """Save the last handled wake-up timestamp to a file."""
    try:
        with open("handled_state.json", "w") as state_file:
            json.dump({"last_handled_awake": timestamp.isoformat()}, state_file)
    except IOError as e:
        print(f"[Service] Error saving handled state: {e}")

def run_file_tracker():
    """Run the file tracker."""
    print("[Service] Starting file tracker...")
    os.system("python file_tracker.py")

def launch_auth_app():
    """Run the authentication app and block until it exits."""
    print("[Service] Starting auth app...")
    process = Popen([sys.executable, "auth_app.py"])
    process.wait()
    print("[Service] Auth app exited.")

def cleanup_handler(tracker_process_ref=None):
    """Handle cleanup when service is shutting down."""
    print("[Service] Performing cleanup...")
    
    # Stop the file tracker if it's running
    if tracker_process_ref and tracker_process_ref.get('process') and tracker_process_ref['process'].is_alive():
        print("[Service] Stopping file tracker...")
        tracker_process_ref['process'].terminate()
        tracker_process_ref['process'].join()

    # Update device state with sleep time
    current_state = load_device_state()
    if current_state:
        current_state["last_sleep"] = datetime.now().isoformat()
        save_device_state(current_state)
        print("[Service] Updated device state with sleep time")

def monitor_device_state():
    print("[Service] Initializing device state monitoring...")
    handled_awake = load_last_handled_awake()
    tracker_process_ref = {'process': None}  # Using a dict to store the process reference
    power_monitor = PowerStateMonitor(tracker_process_ref)
    monitor_window = power_monitor.create_window()
    
    print("[Service] Loaded last handled awake:", handled_awake)

    # Set new wake time on startup
    current_state = load_device_state(set_awake=True)
    print("[Service] Set new wake time on startup")

    def signal_handler(signum, frame):
        print("[Service] Received shutdown signal...")
        cleanup_handler(tracker_process_ref)
        win32gui.DestroyWindow(monitor_window)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        try:
            win32gui.PumpWaitingMessages()
            current_state = load_device_state()

            if not current_state:
                print("[Service] Unable to load device state, retrying in 5 seconds...")
                time.sleep(5)
                continue

            current_awake = datetime.fromisoformat(current_state["last_awake"]) if current_state.get("last_awake") else None
            current_sleep = datetime.fromisoformat(current_state["last_sleep"]) if current_state.get("last_sleep") else None

            is_new_wake = (
                current_awake and 
                (
                    (not current_sleep) or
                    (current_awake > current_sleep)
                ) and
                (not handled_awake or current_awake > handled_awake)
            )

            if is_new_wake:
                print(f"[Service] Device wake detected at {current_awake}")
                handled_awake = current_awake
                save_last_handled_awake(handled_awake)

                if tracker_process_ref.get('process') and tracker_process_ref['process'].is_alive():
                    print("[Service] Stopping file tracker before auth.")
                    tracker_process_ref['process'].terminate()
                    tracker_process_ref['process'].join()

                launch_auth_app()

                print("[Service] Starting file tracker after auth.")
                tracker_process_ref['process'] = multiprocessing.Process(target=run_file_tracker)
                tracker_process_ref['process'].start()

                current_state["last_sleep"] = None
                save_device_state(current_state)

        except Exception as e:
            print(f"[Service] Error in monitor loop: {e}")
            time.sleep(5)
            continue

        time.sleep(1)

if __name__ == "__main__":
    print("[Service] Starting main service...")
    try:
        monitor_device_state()
    except KeyboardInterrupt:
        print("[Service] Stopping service...")
        cleanup_handler()