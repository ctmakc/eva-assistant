"""Weather integration for EVA using OpenWeatherMap API."""

import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("eva.weather")

# Weather condition translations
WEATHER_RU = {
    "clear sky": "ясно",
    "few clouds": "небольшая облачность",
    "scattered clouds": "переменная облачность",
    "broken clouds": "облачно с прояснениями",
    "overcast clouds": "пасмурно",
    "shower rain": "ливень",
    "rain": "дождь",
    "light rain": "небольшой дождь",
    "moderate rain": "умеренный дождь",
    "heavy rain": "сильный дождь",
    "thunderstorm": "гроза",
    "snow": "снег",
    "light snow": "небольшой снег",
    "heavy snow": "сильный снег",
    "mist": "туман",
    "fog": "туман",
    "haze": "дымка",
}


class WeatherService:
    """Weather service using OpenWeatherMap."""

    def __init__(self):
        self.api_key: Optional[str] = None
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.default_city = "Kyiv"  # Default city

    def configure(self, api_key: str, default_city: str = None):
        """Configure the weather service."""
        self.api_key = api_key
        if default_city:
            self.default_city = default_city
        logger.info(f"Weather service configured, default city: {self.default_city}")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_current(self, city: str = None) -> Dict[str, Any]:
        """Get current weather for a city."""
        if not self.api_key:
            return {"success": False, "error": "Weather API not configured"}

        city = city or self.default_city

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/weather"
                params = {
                    "q": city,
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "en"
                }

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        return {"success": False, "error": f"API error: {error}"}

                    data = await resp.json()

                    # Parse response
                    weather_desc = data["weather"][0]["description"]
                    weather_ru = WEATHER_RU.get(weather_desc, weather_desc)

                    return {
                        "success": True,
                        "city": data["name"],
                        "country": data["sys"]["country"],
                        "temp": round(data["main"]["temp"]),
                        "feels_like": round(data["main"]["feels_like"]),
                        "humidity": data["main"]["humidity"],
                        "pressure": data["main"]["pressure"],
                        "wind_speed": round(data["wind"]["speed"], 1),
                        "description": weather_desc,
                        "description_ru": weather_ru,
                        "icon": data["weather"][0]["icon"],
                    }

        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {"success": False, "error": str(e)}

    async def get_forecast(self, city: str = None, days: int = 3) -> Dict[str, Any]:
        """Get weather forecast for upcoming days."""
        if not self.api_key:
            return {"success": False, "error": "Weather API not configured"}

        city = city or self.default_city

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/forecast"
                params = {
                    "q": city,
                    "appid": self.api_key,
                    "units": "metric",
                    "cnt": days * 8  # 8 forecasts per day (every 3 hours)
                }

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return {"success": False, "error": "API error"}

                    data = await resp.json()

                    # Group by day
                    daily = {}
                    for item in data["list"]:
                        dt = datetime.fromtimestamp(item["dt"])
                        day_key = dt.strftime("%Y-%m-%d")

                        if day_key not in daily:
                            daily[day_key] = {
                                "date": day_key,
                                "day_name": dt.strftime("%A"),
                                "temps": [],
                                "descriptions": []
                            }

                        daily[day_key]["temps"].append(item["main"]["temp"])
                        daily[day_key]["descriptions"].append(item["weather"][0]["description"])

                    # Calculate daily summaries
                    forecast = []
                    for day_key, day_data in list(daily.items())[:days]:
                        temps = day_data["temps"]
                        desc = max(set(day_data["descriptions"]), key=day_data["descriptions"].count)

                        forecast.append({
                            "date": day_data["date"],
                            "day": day_data["day_name"],
                            "temp_min": round(min(temps)),
                            "temp_max": round(max(temps)),
                            "description": desc,
                            "description_ru": WEATHER_RU.get(desc, desc)
                        })

                    return {
                        "success": True,
                        "city": data["city"]["name"],
                        "forecast": forecast
                    }

        except Exception as e:
            logger.error(f"Weather forecast error: {e}")
            return {"success": False, "error": str(e)}

    def format_current(self, data: Dict[str, Any]) -> str:
        """Format current weather as human-readable text."""
        if not data.get("success"):
            return f"Не удалось получить погоду: {data.get('error', 'unknown')}"

        temp = data["temp"]
        feels = data["feels_like"]
        desc = data["description_ru"]
        city = data["city"]
        humidity = data["humidity"]
        wind = data["wind_speed"]

        # Temperature feeling
        if temp <= -15:
            temp_feel = "очень холодно"
        elif temp <= -5:
            temp_feel = "холодно"
        elif temp <= 5:
            temp_feel = "прохладно"
        elif temp <= 15:
            temp_feel = "умеренно"
        elif temp <= 25:
            temp_feel = "тепло"
        else:
            temp_feel = "жарко"

        text = f"В городе {city} сейчас {desc}, {temp}°C"

        if abs(temp - feels) >= 3:
            text += f" (ощущается как {feels}°C)"

        text += f". {temp_feel.capitalize()}."

        if wind > 10:
            text += f" Ветер {wind} м/с."

        if humidity > 80:
            text += " Высокая влажность."

        return text

    def format_forecast(self, data: Dict[str, Any]) -> str:
        """Format forecast as human-readable text."""
        if not data.get("success"):
            return f"Не удалось получить прогноз: {data.get('error', 'unknown')}"

        city = data["city"]
        lines = [f"Прогноз погоды для {city}:"]

        day_names_ru = {
            "Monday": "Понедельник",
            "Tuesday": "Вторник",
            "Wednesday": "Среда",
            "Thursday": "Четверг",
            "Friday": "Пятница",
            "Saturday": "Суббота",
            "Sunday": "Воскресенье"
        }

        for day in data["forecast"]:
            day_ru = day_names_ru.get(day["day"], day["day"])
            lines.append(f"• {day_ru}: {day['temp_min']}..{day['temp_max']}°C, {day['description_ru']}")

        return "\n".join(lines)


# Singleton
_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()

        # Try to load from vault
        try:
            from integrations.vault import get_vault
            vault = get_vault()
            creds = vault.get("weather")
            if creds:
                _weather_service.configure(
                    api_key=creds.get("api_key"),
                    default_city=creds.get("default_city")
                )
        except Exception:
            pass

    return _weather_service
