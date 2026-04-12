import requests
from PyQt6.QtCore import QThread, pyqtSignal
import time
import datetime

class WeatherMonitor(QThread):
    weather_updated = pyqtSignal(dict)
    
    def __init__(self, city="Varanasi, India", lat=25.3333, lon=83.0):
        super().__init__()
        self.city = city
        self.lat = lat
        self.lon = lon
        self.running = True
        self.force_update = False
        self.update_interval = 1800  # 30 minutes
        
    def set_location(self, city):
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
            res = requests.get(geo_url, timeout=10).json()
            if "results" in res:
                result = res["results"][0]
                self.city = f"{result['name']}, {result.get('country', '')}"
                self.lat = result["latitude"]
                self.lon = result["longitude"]
                self.refresh()
                return True, self.city
            return False, "City not found"
        except Exception as e:
            return False, str(e)

    def refresh(self):
        self.force_update = True

    def get_weather_icon(self, code):
        mapping = {
            0: "mdi.weather-sunny",
            1: "mdi.weather-partly-cloudy", 2: "mdi.weather-partly-cloudy", 3: "mdi.weather-cloudy",
            45: "mdi.weather-fog", 48: "mdi.weather-fog",
            51: "mdi.weather-rainy", 53: "mdi.weather-rainy", 55: "mdi.weather-rainy",
            61: "mdi.weather-pouring", 63: "mdi.weather-pouring", 65: "mdi.weather-pouring",
            71: "mdi.weather-snowy", 73: "mdi.weather-snowy", 75: "mdi.weather-snowy",
            80: "mdi.weather-rainy", 81: "mdi.weather-rainy", 82: "mdi.weather-rainy",
            95: "mdi.weather-lightning", 96: "mdi.weather-lightning", 99: "mdi.weather-lightning"
        }
        return mapping.get(code, "mdi.weather-cloudy")

    def get_weather_desc(self, code):
        mapping = {
            0: "Clear Sky",
            1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing Rime Fog",
            51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
            61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            71: "Slight Snow", 73: "Moderate Snow", 75: "Heavy Snow",
            80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
            95: "Thunderstorm", 96: "Thunderstorm with Slight Hail", 99: "Thunderstorm with Heavy Hail"
        }
        return mapping.get(code, "Unknown")

    def run(self):
        time_since_last = self.update_interval # Fetch immediately on start
        while self.running:
            if time_since_last >= self.update_interval or self.force_update:
                try:
                    url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current_weather=true&hourly=temperature_2m,weathercode"
                    res = requests.get(url, timeout=10).json()
                    
                    if "current_weather" in res:
                        current = res["current_weather"]
                        hourly = res["hourly"]
                        
                        # Prepare hourly data (next 5 hours)
                        hourly_data = []
                        current_time_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:00")
                        try:
                            start_idx = hourly["time"].index(current_time_str)
                        except ValueError:
                            start_idx = 0
                            
                        for i in range(1, 6):
                            idx = start_idx + i
                            if idx < len(hourly["time"]):
                                t_str = hourly["time"][idx]
                                t_dt = datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M")
                                hourly_data.append({
                                    "time": t_dt.strftime("%I%p").lstrip("0"),
                                    "temp": f"{int(hourly['temperature_2m'][idx])}°",
                                    "icon": self.get_weather_icon(hourly["weathercode"][idx])
                                })
                        
                        data = {
                            "city": self.city,
                            "temp": f"{int(current['temperature'])}°",
                            "desc": self.get_weather_desc(current["weathercode"]),
                            "icon": self.get_weather_icon(current["weathercode"]),
                            "hourly": hourly_data
                        }
                        self.weather_updated.emit(data)
                        self.force_update = False
                        time_since_last = 0
                except Exception as e:
                    print(f"Weather update error: {e}")
            
            time.sleep(1) # Check every second for force_update
            time_since_last += 1

    def stop(self):
        self.running = False
        self.wait()
