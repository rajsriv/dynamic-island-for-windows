# app_styles.py

def get_stylesheet(accent_color: str = "#0078D7") -> str:
    """
    Returns the QSS stylesheet for the Dynamic Island.
    The accent color is used for highlights/graphs.
    """
    return f"""
    QWidget#IslandWidget {{
        background-color: #000000;
        border: 1.2px solid rgba(255, 255, 255, 40);
    }}
    
    QLabel {{
        color: white;
        font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    }}
    
    QLabel#TitleLabel {{
        font-size: 13px;
        font-weight: 600;
    }}
    
    QLabel#SubtitleLabel {{
        font-size: 11px;
        color: #A0A0A0;
    }}
    
    QLabel#IconLabel {{
        background-color: transparent;
        font-size: 16px;
    }}
    
    QPushButton#MediaButton {{
        background-color: transparent;
        color: white;
        border-radius: 14px;
        border: none;
        width: 28px;
        height: 28px;
        padding: 2px;
    }}
    
    QPushButton#MediaButton:hover {{
        background-color: rgba(255, 255, 255, 30);
    }}
    
    QPushButton#MediaButton:pressed {{
        background-color: rgba(255, 255, 255, 50);
    }}
    
    
    QLabel#PerfLabel {{
        font-size: 11px;
        color: #CCCCCC;
        font-weight: 600;
    }}

    QPushButton#ActionButton {{
        background-color: rgba(255, 255, 255, 15);
        color: white;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 10);
    }}
    
    QPushButton#ActionButton:hover {{
        background-color: rgba(255, 255, 255, 35);
        border: 1px solid rgba(255, 255, 255, 40);
    }}

    QPushButton#ActionButton:pressed {{
        background-color: rgba(255, 255, 255, 50);
    }}
    """
