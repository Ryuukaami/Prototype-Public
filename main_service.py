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

class PowerStateMonitor:
    def __init__(self, tracker_process_ref):
        # Power state constants
        self.WM_POWERBROADCAST = 0x0218
        self.PBT_APMRESUMEAUTOMATIC = 0x0012
        self.PBT_APMSUSPEND = 0x0004
        self.tracker_process_ref = tracker_process_ref
        self.window_handle = None
        self.class_atom = None
        
    def create_window(self):
        """Create a hidden window to receive power broadcasts"""
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._window_proc
        wc.lpszClassName = "PowerMonitorWindow"
        wc.hInstance = win32api.GetModuleHandle(None)
        self.class_atom = win32gui.RegisterClass(wc)
        self.window_handle = win32gui.CreateWindow(
            self.class_atom,
            "PowerMonitor",
            0,
            0, 0, 0, 0,
            0,
            0,
            wc.hInstance,
            None
        )
        return self.window_handle

    def destroy_window(self):
        """Clean up window resources"""
        if self.window_handle:
            win32gui.DestroyWindow(self.window_handle)
            self.window_handle = None
        if self.class_atom:
            win32gui.UnregisterClass(self.class_atom, win32api.GetModuleHandle(None))
            self.class_atom = None

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
        stop_tracker(self.tracker_process_ref)

        # Update device state with sleep time
        current_state = load_device_state()
        if current_state:
            current_state["last_sleep"] = datetime.now().isoformat()
            save_device_state(current_state)

    def _on_resume(self):
        """Handle system resume event"""
        print("[Service] System resuming from sleep state")
        
        # Update device state with wake time
        current_state = load_device_state()
        if current_state:
            current_state["last_awake"] = datetime.now().isoformat()
            save_device_state(current_state)
            
        # Clear the handled_state.json to force authentication
        clear_handled_state()

def stop_tracker(tracker_process_ref):
    """Stop the file tracker process if it's running"""
    if tracker_process_ref.get('process') and tracker_process_ref['process'].is_alive():
        print("[Service] Stopping file tracker")
        tracker_process_ref['process'].terminate()
        tracker_process_ref['process'].join(timeout=3)
        if tracker_process_ref['process'].is_alive():
            tracker_process_ref['process'].kill()
        tracker_process_ref['process'] = None
        return True
    return False

def clear_handled_state():
    """Clear the handled state file to force authentication"""
    try:
        if os.path.exists("handled_state.json"):
            os.remove("handled_state.json")
            print("[Service] Cleared handled state")
    except OSError as e:
        print(f"[Service] Error clearing handled state: {e}")

def initialize_device_state():
    """Initialize the device state file with default values"""
    current_time = datetime.now().isoformat()
    initial_state = {
        "last_awake": current_time,
        "last_sleep": None
    }
    try:
        with open("device_state.json", "w") as state_file:
            json.dump(initial_state, state_file, indent=4)
        print("[Service] Initialized device state")
        return initial_state
    except IOError as e:
        print(f"[Service] Error initializing device state: {e}")
        return None

def load_device_state(set_awake=False):
    """Load the device state, initialize if not present"""
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
    """Save the device state"""
    try:
        with open("device_state.json", "w") as state_file:
            json.dump(state, state_file, indent=4)
    except IOError as e:
        print(f"[Service] Error saving device state: {e}")

def load_last_handled_awake():
    """Load the last handled wake-up timestamp from a file"""
    try:
        with open("handled_state.json", "r") as state_file:
            state = json.load(state_file)
            return datetime.fromisoformat(state.get("last_handled_awake"))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None

def save_last_handled_awake(timestamp):
    """Save the last handled wake-up timestamp to a file"""
    try:
        with open("handled_state.json", "w") as state_file:
            json.dump({"last_handled_awake": timestamp.isoformat()}, state_file)
        print(f"[Service] Updated handled wake time: {timestamp}")
    except IOError as e:
        print(f"[Service] Error saving handled state: {e}")

def start_file_tracker_process():
    """Function to start the file tracker."""
    print("[Service] Starting file tracker1...")
    os.system("python file_tracker.py")

def start_file_tracker(tracker_process_ref):
    """Start the file tracker in a separate process"""
    print("[Service] Starting file tracker2...")
    tracker_process_ref['process'] = multiprocessing.Process(target=start_file_tracker_process)
    tracker_process_ref['process'].start()

def launch_auth_app():
    """Run the authentication app and block until it exits"""
    print("[Service] Starting auth app...")
    process = Popen([sys.executable, "auth_app.py"])
    process.wait()
    print("[Service] Auth app exited.")

def cleanup_handler(tracker_process_ref, power_monitor):
    """Handle cleanup when service is shutting down"""
    print("[Service] Performing cleanup...")
    
    # Stop the file tracker if it's running
    stop_tracker(tracker_process_ref)

    # Update device state with sleep time
    current_state = load_device_state()
    if current_state:
        current_state["last_sleep"] = datetime.now().isoformat()
        save_device_state(current_state)
        print("[Service] Updated device state with sleep time")
    
    # Clean up window resources
    if power_monitor:
        power_monitor.destroy_window()

def monitor_device_state():
    """Main function to monitor device state and manage processes"""
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
        """Handle termination signals"""
        print(f"[Service] Received signal {signum}...")
        cleanup_handler(tracker_process_ref, power_monitor)
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            # Process any waiting window messages
            for _ in range(10):  # Process a limited number of messages per cycle
                if not win32gui.PumpWaitingMessages():
                    break
                
            current_state = load_device_state()

            if not current_state:
                print("[Service] Unable to load device state, retrying in 5 seconds...")
                time.sleep(5)
                continue

            current_awake = datetime.fromisoformat(current_state["last_awake"]) if current_state.get("last_awake") else None
            current_sleep = datetime.fromisoformat(current_state["last_sleep"]) if current_state.get("last_sleep") else None

            # Check if this is a new wake event that needs handling
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

                # Stop tracker if running
                stop_tracker(tracker_process_ref)

                # Run authentication
                launch_auth_app()

                # Start file tracker after authentication
                print("[Service] Starting file tracker after auth.")
                start_file_tracker(tracker_process_ref)

                # Reset sleep state
                current_state["last_sleep"] = None
                save_device_state(current_state)

            time.sleep(1)
    except Exception as e:
        print(f"[Service] Unexpected error: {e}")
        cleanup_handler(tracker_process_ref, power_monitor)
        raise
    finally:
        cleanup_handler(tracker_process_ref, power_monitor)

if __name__ == "__main__":
    print("[Service] Starting main service...")
    try:
        monitor_device_state()
    except KeyboardInterrupt:
        print("[Service] Stopping service...")