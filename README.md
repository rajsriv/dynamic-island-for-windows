# Dynamic Island for Windows

A sleek, fluid, and highly customizable Dynamic Island for Windows built with Python and PyQt6.

## Features

- **Fluid Animations**: Smooth transitions between states (Idle, Hover, Music, Notifications).
- **System Monitoring**: Real-time CPU and RAM usage tracking.
- **Media Controls**: Integrated media playback controls with album art accent color detection.
- **Event Notifications**: Visual feedback for Caps Lock/Num Lock changes and system notifications.
- **Customizable Appearance**: Choose between different animation styles (Glow Sweep, Fluid Blobs, Neon Border) and island styles (Default, Liquid Glass).
- **Auto-start**: Option to start with Windows.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rajsriv/dynamic-island-for-windows.git
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Dependencies

- PyQt6
- QtAwesome
- psutil
- winsdk (for media and notification monitoring)

## License

[MIT License](LICENSE)
