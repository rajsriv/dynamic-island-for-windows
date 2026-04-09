# app_styles.py

def get_stylesheet(accent_color: str = "#0078D7") -> str:
    """
    Returns the QSS stylesheet for the Dynamic Island.
    The accent color is used for highlights/graphs.
    """
    return f"""
    QWidget#IslandWidget {{
        background-color: rgb(15, 15, 15);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 30);
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
    
    QProgressBar {{
        border: none;
        background-color: rgba(255, 255, 255, 20);
        border-radius: 4px;
        text-align: right;
    }}
    
    QProgressBar::chunk {{
        background-color: {accent_color};
        border-radius: 4px;
    }}
    
    QLabel#PerfLabel {{
        font-size: 10px;
        color: #CCCCCC;
        font-weight: 600;
    }}
    """
