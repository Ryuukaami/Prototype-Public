# Task-Based Authentication System Prototype

### Overview
This project is a multi-component service that tracks file activity, authenticates users based on recent file access, and responds to system power events like sleep and resume.

---

### Quick Start Guide

#### Prerequisites

1. Install Python 3.8 or later.
2. Install the required Python packages:
   ```bash
   pip install PyQt5 watchdog pyWinhook pywin32
   ```
3. Use a Windows operating system for full functionality.

---

#### Running the Application

1. Start the main service:
   ```bash
   python main_service.py
   ```
   - This initializes power state monitoring and launches the file tracker and authentication app when needed.

2. (Optional) Run the file tracker independently:
   ```bash
   python file_tracker.py
   ```

3. (Optional) Test the authentication app:
   ```bash
   python auth_app.py
   ```

---

### Configuration

- Update monitored directories and excluded paths in `file_tracker.py`.
- Customize authentication challenges in `auth_app.py`.

---

### License

This project is licensed under the MIT License. See the LICENSE file for details.

---

### Contributions

Contributions, issues, and feature requests are welcome! Feel free to open an issue or submit a pull request.

