// Erzeugt von tools/extract_icon_rules.py — nicht von Hand ändern.
//
// Die Symbolableitung des Backends (`get_icon_ha` in icons.py) für Einträge ohne eigenes
// `icon`. Die Vorschau bildet sie nach, damit dort dasselbe Symbol steht wie am Gerät —
// gerade bei Domänen, für die Home Assistant selbst kein Symbolattribut führt.
export const ICON_RULES = {
 "simple_type_mapping": {
  "button": "gesture-tap-button",
  "navigate": "gesture-tap-button",
  "input_button": "gesture-tap-button",
  "input_select": "gesture-tap-button",
  "scene": "palette",
  "script": "script-text",
  "switch": "light-switch",
  "automation": "robot",
  "number": "ray-vertex",
  "input_number": "ray-vertex",
  "light": "lightbulb",
  "fan": "fan",
  "person": "account",
  "vacuum": "robot-vacuum",
  "timer": "timer-outline"
 },
 "weather_mapping": {
  "clear-night": "weather-night",
  "cloudy": "weather-cloudy",
  "exceptional": "alert-circle-outline",
  "fog": "weather-fog",
  "hail": "weather-hail",
  "lightning": "weather-lightning",
  "lightning-rainy": "weather-lightning-rainy",
  "partlycloudy": "weather-partly-cloudy",
  "pouring": "weather-pouring",
  "rainy": "weather-rainy",
  "snowy": "weather-snowy",
  "snowy-rainy": "weather-snowy-rainy",
  "sunny": "weather-sunny",
  "windy": "weather-windy",
  "windy-variant": "weather-windy-variant"
 },
 "climate_mapping": {
  "auto": "fan-auto",
  "heat_cool": "sun-snowflake-variant",
  "heat": "fire",
  "off": "power",
  "cool": "snowflake",
  "dry": "water-percent",
  "fan_only": "fan"
 },
 "alarm_control_panel_mapping": {
  "disarmed": "shield-off",
  "armed_home": "shield-home",
  "armed_away": "shield-lock",
  "armed_night": "weather-night",
  "armed_vacation": "shield-airplane",
  "arming": "shield",
  "pending": "shield",
  "triggered": "bell-ring"
 },
 "sensor_mapping": {
  "apparent_power": "flash",
  "aqi": "smog",
  "battery": "battery",
  "carbon_dioxide": "smog",
  "carbon_monoxide": "smog",
  "current": "flash",
  "date": "calendar",
  "duration": "timer",
  "energy": "flash",
  "frequency": "chart-bell-curve",
  "gas": "gas-cylinder",
  "humidity": "air-humidifier",
  "illuminance": "light",
  "monetary": "cash",
  "nitrogen_dioxide": "smog",
  "nitrogen_monoxide": "smog",
  "nitrous_oxide": "smog",
  "ozone": "smog",
  "pm1": "smog",
  "pm10": "smog",
  "pm25": "smog",
  "power_factor": "flash",
  "power": "flash",
  "pressure": "gauge",
  "reactive_power": "flash",
  "signal_strength": "signal",
  "sulphur_dioxide": "smog",
  "temperature": "thermometer",
  "timestamp": "calendar-clock",
  "volatile_organic_compounds": "smog",
  "voltage": "flash"
 },
 "sensor_mapping_on": {
  "battery": "battery-outline",
  "battery_charging": "battery-charging",
  "carbon_monoxide": "smoke-detector-alert",
  "cold": "snowflake",
  "connectivity": "check-network-outline",
  "door": "door-open",
  "garage_door": "garage-open",
  "power": "power-plug",
  "gas": "alert-circle",
  "problem": "alert-circle",
  "safety": "alert-circle",
  "tamper": "alert-circle",
  "smoke": "smoke-detector-variant-alert",
  "heat": "fire",
  "light": "brightness-7",
  "lock": "lock-open",
  "moisture": "water",
  "motion": "motion-sensor",
  "occupancy": "home",
  "opening": "square-outline",
  "plug": "power-plug",
  "presence": "home",
  "running": "play",
  "sound": "music-note",
  "update": "package-up",
  "vibration": "vibrate",
  "window": "window-open"
 },
 "sensor_mapping_off": {
  "battery": "battery",
  "battery_charging": "battery",
  "carbon_monoxide": "smoke-detector",
  "cold": "thermometer",
  "connectivity": "close-network-outline",
  "door": "door-closed",
  "garage_door": "garage",
  "power": "power-plug-off",
  "gas": "checkbox-marked-circle",
  "problem": "checkbox-marked-circle",
  "safety": "checkbox-marked-circle",
  "tamper": "check-circle",
  "smoke": "smoke-detector-variant",
  "heat": "thermometer",
  "light": "brightness-5",
  "lock": "lock",
  "moisture": "water-off",
  "motion": "motion-sensor-off",
  "occupancy": "home-outline",
  "opening": "square",
  "plug": "power-plug-off",
  "presence": "home-outline",
  "running": "stop",
  "sound": "music-note-off",
  "update": "package",
  "vibration": "crop-portrait",
  "window": "window-closed"
 },
 "media_content_type_mapping": {
  "music": "music",
  "tvshow": "movie",
  "video": "video",
  "episode": "alert-circle-outline",
  "channel": "alert-circle-outline",
  "playlist": "alert-circle-outline"
 },
 "cover_mapping": {
  "awning": {
   "offen": "window-open",
   "geschlossen": "window-closed"
  },
  "blind": {
   "offen": "blinds-open",
   "geschlossen": "blinds"
  },
  "curtain": {
   "offen": "curtains",
   "geschlossen": "curtains-closed"
  },
  "damper": {
   "offen": "checkbox-blank-circle",
   "geschlossen": "circle-slice-8"
  },
  "door": {
   "offen": "door-open",
   "geschlossen": "door-closed"
  },
  "garage": {
   "offen": "garage-open",
   "geschlossen": "garage"
  },
  "gate": {
   "offen": "gate-open",
   "geschlossen": "gate"
  },
  "shade": {
   "offen": "blinds-open",
   "geschlossen": "blinds"
  },
  "shutter": {
   "offen": "window-shutter-open",
   "geschlossen": "window-shutter"
  },
  "window": {
   "offen": "window-open",
   "geschlossen": "window-closed"
  }
 },
 "feste_zweige": {
  "input_boolean": {
   "on": "check-circle-outline",
   "sonst": "close-circle-outline"
  },
  "lock": {
   "unlocked": "lock-open",
   "sonst": "lock"
  },
  "sun": {
   "above_horizon": "weather-sunset-up",
   "sonst": "weather-sunset-down"
  },
  "binary_sensor": {
   "on": "checkbox-marked-circle",
   "sonst": "radiobox-blank"
  },
  "media_player": {
   "sonst": "speaker-off"
  }
 },
 "ersatz": "alert-circle-outline",
 "wetter_sonderfaelle": [
  "sensor.weather_forecast_daily",
  "sensor.weather_forecast_hourly"
 ]
};
