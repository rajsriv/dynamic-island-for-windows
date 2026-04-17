![Dynamic Island for Windows Banner](src/Dynamic%20Island%200.jpg)

# Dynamic Island for Windows

A sleek, fluid, and highly customizable Dynamic Island for Windows built with Python and PyQt6.

# Scroll on the Panels !

## Features

- **Fluid Animations**: Smooth transitions between states (Idle, Hover, Music, Notifications).
- **System Monitoring**: Real-time CPU and RAM usage tracking.
- **Media Controls**: Integrated media playback controls with album art accent color detection.
- **Event Notifications**: Visual feedback for Caps Lock/Num Lock changes and system notifications.
- **Customizable Appearance**: Choose between different animation styles (Glow Sweep, Fluid Blobs, Neon Border) and island styles (Default, Liquid Glass).
- **Auto-start**: Option to start with Windows.

## Previews

### Default View & Smart Theming
The island displays the current day and time by default. Its intelligent engine auto-detects your wallpaper's accent color to ensure the UI feels like a native part of your desktop.

![Default State](src/Dynamic%20Island%201.jpg)

### Smart Notifications & Keyboard Status
Stay informed with instant notification detection. The island also provides sleek visual cues when Caps Lock or Num Lock is toggled.

![Notifications](src/Dynamic%20Island%202.jpg)

### Interactive Information Panels
Access a variety of rich widgets including real-time Weather, a detailed Calendar with progress tracking, comprehensive System Monitoring (CPU, RAM, Storage, Network), and your Daily Tasks.

![Information Panels](src/Dynamic%20Island%203.jpg)

### Fluid Media Player
Control your music with ease. The media player's background and animations dynamically adapt their color palette to match the album art of the currently playing track.

![Music Player](src/Dynamic%20Island%205.jpg)

### Basics Control Hub
A dedicated panel for essential system tools. Quickly access Power, Sleep, and Restart controls through a fluid, scrollable interface.

![Basics Panel](src/Dynamic%20Island%207.jpg)

### Deep Customization
Tailor the experience to your liking. Right-click the island to access settings for animation styles, island designs, and location preferences.

![Context Menu](src/Dynamic%20Island%204.jpg)
![Settings](src/Dynamic%20Island%206.jpg)

### Notch Nook Style
For those who prefer a more integrated look, the "Notch Nook" style replaces the floating island with a sleek, top-centered notch that anchors directly to the screen edge.

![Notch Nook](src/Notch_Nook.png)

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
