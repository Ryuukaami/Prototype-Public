import sys
import json
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from win32gui import GetForegroundWindow
from win32process import GetWindowThreadProcessId
import win32con
import win32api
import win32security
import ntsecuritycon
import pythoncom
import pyWinhook as pyhook
import os

def load_files_during_sleep():
    """Load files accessed during the last session."""
    try:
        with open("file_activity.json", "r") as activity_file:
            tracked_files = json.load(activity_file)

        # Return files from the previous session
        return list(tracked_files.get("previous_session", {}).keys())
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"Error loading files during sleep: {e}")
        return []

def get_incorrect_files():
    """Get a pool of realistic and believable incorrect file names for an enterprise environment."""
    return [
        "project_plan_v2.docx",           # Project documentation
        "api_integration_guide.pdf",      # API documentation
        "style_guide_v1.css",             # Company style guide
        "deployment_config.yaml",         # Deployment configuration file
        "test_suite_results.json",        # Test results
        "user_auth_handler.py",           # Authentication handler script
        "error_tracking_service.js",      # Error tracking service script
        "database_migration.sql",         # Database migration script
        "dashboard_component.jsx",        # Frontend dashboard component
        "employee_directory.xlsx",        # Employee directory spreadsheet
        "meeting_notes_2024-12-15.md",    # Meeting notes markdown file
        "module_registry.xml",            # Module registry file
        "team_collaboration_roadmap.pptx",# Team collaboration roadmap
        "performance_report_2024.pdf",    # Performance report
        "client_project_overview.html",   # Client project overview webpage
        "feature_toggle_flags.json",      # Feature toggle configuration
        "staging_environment.log",        # Staging environment log file
        "qa_checklist_latest.xlsx",       # QA checklist
        "access_logs_2024-12-20.txt",     # Access logs
        "legacy_codebase_review.docx"     # Review document for legacy code
    ]

class AuthenticationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.hm = pyhook.HookManager()
        self.block_input_timer = None
        self.auth_successful = False
        self.secure_desktop = None
        self.original_desktop = None
        self.initUI()
        self.makeSecure()
        self.setupSecureDesktop()

    def setupSecureDesktop(self):
        try:
            self.original_desktop = win32api.GetThreadDesktop(win32api.GetCurrentThreadId())

            self.secure_desktop = win32api.CreateDesktop(
                "SecureAuthDesktop",
                0,  
                win32con.GENERIC_ALL,  
                win32security.SECURITY_ATTRIBUTES()
            )

            self.secure_desktop.SetThreadDesktop()

            sd = win32security.SECURITY_DESCRIPTOR()
            sd.Initialize()
            
            restricted_sid = win32security.CreateWellKnownSid(
                win32security.WinRestrictedCodeSid
            )
            
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                win32con.GENERIC_READ | win32con.GENERIC_EXECUTE,
                restricted_sid
            )
            
            sd.SetDacl(1, dacl, 0)
            self.secure_desktop.SetSecurityDescriptor(sd)

        except Exception as e:
            print(f"Error setting up secure desktop: {e}")
            self.setupFallbackProtection()

    def setupFallbackProtection(self):
        """Fallback protection if secure desktop creation fails"""
        try:
            # Disable task manager access
            key = win32api.RegOpenKeyEx(
                win32con.HKEY_CURRENT_USER,
                "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
                0,
                win32con.KEY_SET_VALUE
            )
            win32api.RegSetValueEx(
                key,
                "DisableTaskMgr",
                0,
                win32con.REG_DWORD,
                1
            )
            win32api.RegCloseKey(key)

            # Set up a watchdog timer to detect desktop switches
            self.watchdog = QTimer(self)
            self.watchdog.timeout.connect(self.checkDesktopState)
            self.watchdog.start(100)

        except Exception as e:
            print(f"Error setting up fallback protection: {e}")

    def checkDesktopState(self):
        """Monitor for desktop switching attempts"""
        try:
            current_desktop = win32api.GetThreadDesktop(win32api.GetCurrentThreadId())
            if current_desktop != self.original_desktop:
                # Force back to our window
                self.activateWindow()
                self.raise_(
        except Exception:
            pass

    def initUI(self):

        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint
        )
        

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.setWindowTitle("Task-Based Authentication")
        
       
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(50, 50, 50, 50)  
        
        content_widget = QWidget()
        content_widget.setFixedWidth(600)  
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)  
        
        self.label = QLabel("Select the 3 files you worked on recently:")
        self.label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        content_layout.addWidget(self.label)

        self.recent_files = load_files_during_sleep()
        if not self.recent_files:  
            self.recent_files = ["document1.txt", "document2.txt", "document3.txt"]
        self.correct_files = self.get_random_correct_files()
        self.challenge_files = self.generate_challenge_files()

        self.checkboxes = []
        for file in self.challenge_files:
            checkbox = QCheckBox(file)
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: white;
                    padding: 5px;
                    font-size: 12px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            self.checkboxes.append(checkbox)
            content_layout.addWidget(checkbox)

        self.submit_btn = QPushButton("Submit")
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                min-width: 120px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.submit_btn.clicked.connect(self.verify)
        content_layout.addWidget(self.submit_btn, alignment=Qt.AlignCenter)
        main_layout.addWidget(content_widget, alignment=Qt.AlignCenter)
        self.setLayout(main_layout)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        content_widget.setStyleSheet("background-color: rgba(40, 40, 40, 200); padding: 30px; border-radius: 10px;")

    def makeSecure(self):
        self.block_input_timer = QTimer(self)
        self.block_input_timer.timeout.connect(self.enforce_focus)
        self.block_input_timer.start(100)  # Check every 100ms
        self.hm.KeyDown = self.on_keyboard_event
        self.hm.HookKeyboard()

    def on_keyboard_event(self, event):
        # Block Alt+F4, Alt+Tab, Win key, Ctrl+Esc, Ctrl+Alt+Del
        if (
            (event.Alt and event.Key == 'F4') or
            (event.Alt and event.Key == 'Tab') or
            (event.Key == 'Lwin') or
            (event.Key == 'Rwin') or
            (event.Control and event.Key == 'Escape') or
            (event.Control and event.Alt and event.Key == 'Delete')
        ):
            return False
        return True

    def enforce_focus(self):
        current_window = GetForegroundWindow()
        current_pid = GetWindowThreadProcessId(current_window)[1]
        if current_pid != os.getpid():
            self.activateWindow()
            self.raise_()

    def cleanup(self):

        try:
            if self.original_desktop:
                win32api.SetThreadDesktop(self.original_desktop)
            
            if self.secure_desktop:
                self.secure_desktop.CloseDesktop()

            # Re-enable task manager if it was disabled
            key = win32api.RegOpenKeyEx(
                win32con.HKEY_CURRENT_USER,
                "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
                0,
                win32con.KEY_SET_VALUE
            )
            win32api.RegSetValueEx(
                key,
                "DisableTaskMgr",
                0,
                win32con.REG_DWORD,
                0
            )
            win32api.RegCloseKey(key)

        except Exception as e:
            print(f"Error during cleanup: {e}")

    def closeEvent(self, event):
        """Prevent window from being closed unless authentication was successful"""
        if not self.auth_successful:
            event.ignore()
        else:
            self.cleanup()
            event.accept()

    def get_random_correct_files(self):
        """Randomly select 3 correct files from recently worked-on files."""
        if len(self.recent_files) < 3:
            return self.recent_files
        return random.sample(self.recent_files, 3)

    def generate_challenge_files(self):
        """Combine correct and incorrect files, then shuffle them."""
        incorrect_files = get_incorrect_files()
        selected_incorrect_files = random.sample(incorrect_files, 3) 
        combined_files = self.correct_files + selected_incorrect_files
        random.shuffle(combined_files)
        return combined_files

    def exit_application(self):

        try:
            self.hm.UnhookKeyboard()
            
            if self.block_input_timer:
                self.block_input_timer.stop()
        
            self.auth_successful = True
            self.setWindowFlags(Qt.Window)
            self.show()
            self.cleanup()
            self.close()
            QApplication.quit()
            
        except Exception as e:
            print(f"Error during exit: {e}")

    def verify(self):
        """Check if the user selected all 3 correct files."""
        selected_files = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        
        # Check if exactly 3 files are selected
        if len(selected_files) != 3:
            QMessageBox.warning(self, "Access Denied", "Please select exactly 3 files.\nTry again.")
            return

        if set(selected_files) == set(self.correct_files):
            self.setWindowFlags(Qt.Window)
            self.show()
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Access Granted")
            msg_box.setText("You have successfully logged in!")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setWindowFlags(Qt.WindowStaysOnTopHint)
            screen = QApplication.primaryScreen().geometry()
            msg_box.move(
                screen.center().x() - msg_box.width() // 2,
                screen.center().y() - msg_box.height() // 2
            )
            
            msg_box.finished.connect(self.exit_application)
            msg_box.exec_()
        else:
            QMessageBox.warning(self, "Access Denied", "Incorrect challenge response.\nPlease try again.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    auth_app = AuthenticationApp()
    auth_app.show()
    message_timer = QTimer()
    message_timer.timeout.connect(lambda: None)
    message_timer.start(50)
    sys.exit(app.exec_())