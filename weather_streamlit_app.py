"""
Weather App - Streamlit Version
Gets current temperature for any location using Open-Meteo API (free, no API key required)
Supports multiple weather models: ECMWF, GFS, ICON
"""

import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(
    page_title="Weather App",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Dark Mode
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    .weather-card {
        background: rgba(30, 30, 45, 0.95);
        border-radius: 30px;
        padding: 40px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        animation: slideIn 0.5s ease-out;
        border: 1px solid rgba(100, 100, 150, 0.2);
    }
    .weather-icon {
        text-align: center;
        font-size: 100px;
        animation: float 3s ease-in-out infinite;
        filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.3));
        margin: 10px 0;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-15px); }
    }
    .temperature {
        text-align: center;
        font-size: 64px;
        font-weight: bold;
        color: #00d4ff;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        margin: 5px 0;
    }
    .detail-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 12px 16px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    }
    .coordinates {
        text-align: center;
        color: #aaa;
        font-size: 12px;
        padding-top: 20px;
        border-top: 2px solid #444;
    }
    h1, h2, h3 {
        color: #e0e0e0;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 12px 30px;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.5);
        transform: translateY(-2px);
    }
    /* Sidebar Dark Mode */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p {
        color: #e0e0e0 !important;
    }
    /* Input fields dark mode */
    .stTextInput input {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .stTextInput input::placeholder {
        color: rgba(255, 255, 255, 0.5);
    }
    /* Radio buttons dark mode */
    .stRadio > div {
        color: white;
    }
    /* Info boxes dark mode */
    .stAlert {
        background-color: rgba(30, 30, 45, 0.8);
        color: #e0e0e0;
        border: 1px solid rgba(100, 100, 150, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'unit_temp' not in st.session_state:
    st.session_state.unit_temp = 'F'
if 'unit_wind' not in st.session_state:
    st.session_state.unit_wind = 'mph'
if 'last_location' not in st.session_state:
    st.session_state.last_location = None
if 'weather_data' not in st.session_state:
    st.session_state.weather_data = None

def get_location_by_name(location_name):
    """Get coordinates for a location name using geocoding API."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            'name': location_name,
            'count': 5,
            'language': 'en',
            'format': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'results' in data and len(data['results']) > 0:
            results = data['results']
            return results
        else:
            # Try just the city name if full search fails
            if ',' in location_name:
                city_only = location_name.split(',')[0].strip()
                params['name'] = city_only
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    return data['results']
            return None
    except Exception as e:
        st.error(f"Error searching for location: {e}")
        return None

def get_current_location():
    """Get approximate location based on IP address."""
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        data = response.json()
        
        if data.get('latitude') and data.get('longitude'):
            return {
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'city': data.get('city', 'Unknown'),
                'region': data.get('region', 'Unknown'),
                'country': data.get('country_name', 'Unknown')
            }
        return None
    except Exception as e:
        st.error(f"Error getting location: {e}")
        return None

def get_weather(latitude, longitude, model='best_match'):
    """Get current weather data from Open-Meteo API with hourly forecast.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        model: Weather model to use. Options:
            - 'best_match' (default): Automatically selects best model for region
              Open-Meteo intelligently picks from: ICON (Europe), GFS (N.America), 
              ECMWF (global), or best regional model available
            - 'ecmwf_ifs025': ECMWF IFS 0.25° (European model, global coverage)
            - 'gfs_global': GFS Global (NOAA model, best for North America)
            - 'icon_global': ICON Global (German Weather Service, high resolution)
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'current': 'temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code',
            'hourly': 'temperature_2m,precipitation_probability,precipitation,weather_code,rain,showers,snowfall',
            'temperature_unit': 'fahrenheit',
            'wind_speed_unit': 'mph',
            'forecast_days': 1,
            'timezone': 'auto'
        }
        
        # Add model parameter if not using best_match
        if model != 'best_match':
            params['models'] = model
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Add model info to response for display
        data['model_used'] = model
        
        return data
    except Exception as e:
        st.error(f"Error getting weather: {e}")
        return None

def check_precipitation_soon(weather_data):
    """Check if precipitation is expected soon and return details including type."""
    try:
        if not weather_data or 'hourly' not in weather_data:
            return None
        
        hourly = weather_data['hourly']
        times = hourly.get('time', [])
        precip_prob = hourly.get('precipitation_probability', [])
        precipitation = hourly.get('precipitation', [])
        rain = hourly.get('rain', [])
        showers = hourly.get('showers', [])
        snowfall = hourly.get('snowfall', [])
        weather_codes = hourly.get('weather_code', [])
        
        current_time = datetime.now()
        
        # Check next 12 hours for precipitation
        for i, time_str in enumerate(times[:12]):
            if i >= len(precip_prob):
                continue
                
            prob = precip_prob[i] if i < len(precip_prob) else 0
            precip = precipitation[i] if i < len(precipitation) else 0
            rain_amt = rain[i] if i < len(rain) else 0
            shower_amt = showers[i] if i < len(showers) else 0
            snow_amt = snowfall[i] if i < len(snowfall) else 0
            w_code = weather_codes[i] if i < len(weather_codes) else 0
            
            # If moderate to high probability (>30%) or actual precipitation expected
            if (prob and prob > 30) or precip > 0.1:
                # Calculate minutes until this time
                try:
                    # Handle different time formats
                    if 'T' in time_str:
                        forecast_time = datetime.fromisoformat(time_str.replace('Z', ''))
                    else:
                        forecast_time = datetime.fromisoformat(time_str)
                    
                    # Calculate time difference
                    current_time = datetime.now()
                    time_diff = (forecast_time - current_time).total_seconds()
                    minutes = int(time_diff / 60)
                    
                    if minutes > 0 and minutes <= 720:  # Within next 12 hours
                        # Determine precipitation type
                        precip_type = 'Rain'
                        emoji = '🌧️'
                        color_start = '#ff6b6b'
                        color_end = '#ee5a6f'
                        
                        # Check for snow
                        if snow_amt > 0 or w_code in [71, 73, 75, 77, 85, 86]:
                            precip_type = 'Snow'
                            emoji = '❄️'
                            color_start = '#64b5f6'
                            color_end = '#42a5f5'
                        # Check for freezing rain/sleet
                        elif w_code in [56, 57, 66, 67]:
                            precip_type = 'Freezing Rain'
                            emoji = '🧊'
                            color_start = '#9575cd'
                            color_end = '#7e57c2'
                        # Check for thunderstorm
                        elif w_code in [95, 96, 99]:
                            precip_type = 'Thunderstorm'
                            emoji = '⛈️'
                            color_start = '#ffa726'
                            color_end = '#ff9800'
                        # Check for showers vs rain
                        elif shower_amt > rain_amt:
                            precip_type = 'Showers'
                            emoji = '🌦️'
                        
                        return {
                            'minutes': minutes,
                            'probability': prob,
                            'amount': precip if precip else 0,
                            'type': precip_type,
                            'emoji': emoji,
                            'color_start': color_start,
                            'color_end': color_end
                        }
                except Exception as time_err:
                    continue  # Skip this time slot if parsing fails
        
        return None
    except Exception as e:
        st.error(f"Error checking precipitation: {e}")
        return None

def get_weather_description(weather_code):
    """Convert weather code to description."""
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(weather_code, "Unknown")

def get_weather_emoji(conditions):
    """Get emoji based on weather conditions."""
    weather_emoji = {
        "Clear sky": "☀️",
        "Mainly clear": "🌤️",
        "Partly cloudy": "⛅",
        "Overcast": "☁️",
        "Foggy": "🌫️",
        "Depositing rime fog": "🌫️",
        "Light drizzle": "🌦️",
        "Moderate drizzle": "🌧️",
        "Dense drizzle": "🌧️",
        "Slight rain": "🌧️",
        "Moderate rain": "🌧️",
        "Heavy rain": "⛈️",
        "Slight snow": "🌨️",
        "Moderate snow": "❄️",
        "Heavy snow": "❄️",
        "Snow grains": "❄️",
        "Slight rain showers": "🌦️",
        "Moderate rain showers": "🌧️",
        "Violent rain showers": "⛈️",
        "Slight snow showers": "🌨️",
        "Heavy snow showers": "❄️",
        "Thunderstorm": "⛈️",
        "Thunderstorm with slight hail": "⛈️",
        "Thunderstorm with heavy hail": "⛈️"
    }
    return weather_emoji.get(conditions, "🌤️")

def convert_temp(temp_f, to_celsius=False):
    """Convert temperature between F and C."""
    if to_celsius:
        return (temp_f - 32) * 5/9
    return temp_f

def convert_wind(wind_mph, to_kmh=False):
    """Convert wind speed between mph and km/h."""
    if to_kmh:
        return wind_mph * 1.60934
    return wind_mph

def display_radar(location):
    """Display animated weather radar using RainViewer and OpenStreetMap."""
    st.markdown("### 🌧️ Local Weather Radar")
    st.markdown("<p style='color: #aaa; font-size: 0.9em;'>Animated radar: 2 hours past + 30 min forecast</p>", unsafe_allow_html=True)
    
    lat = location['latitude']
    lon = location['longitude']
    
    # Create radar map HTML with animation using RainViewer and Leaflet
    radar_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; background: #1e1e2d; }}
            #map {{ 
                height: 500px; 
                width: 100%; 
                border-radius: 15px;
                border: 2px solid rgba(100, 100, 150, 0.3);
            }}
            .leaflet-container {{
                background: #0f0c29;
            }}
            .leaflet-layer {{
                transition: opacity 0.3s ease-in-out;
            }}
            .radar-controls {{
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: rgba(30, 30, 45, 0.95);
                padding: 12px;
                border-radius: 10px;
                color: white;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                min-width: 180px;
            }}
            .radar-controls button {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                cursor: pointer;
                margin: 2px;
                font-size: 12px;
                width: 100%;
            }}
            .radar-controls button:hover {{
                background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            }}
            .radar-controls button:disabled {{
                background: #555;
                cursor: not-allowed;
                opacity: 0.5;
            }}
            .timestamp {{
                font-size: 11px;
                color: #aaa;
                margin-top: 8px;
                text-align: center;
            }}
            .control-group {{
                margin: 5px 0;
            }}
            .play-btn {{
                background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%) !important;
            }}
            .play-btn:hover {{
                background: linear-gradient(135deg, #0099cc 0%, #00d4ff 100%) !important;
            }}
        </style>
    </head>
    <body>
        <div class="radar-controls">
            <div style="margin-bottom: 8px;"><strong>🌧️ Radar Animation</strong></div>
            <div class="control-group">
                <button id="playBtn" class="play-btn" onclick="toggleAnimation()">▶️ Play</button>
            </div>
            <div class="control-group">
                <button onclick="map.setView([{lat}, {lon}], map.getZoom())">📍 Center</button>
            </div>
            <div class="control-group">
                <button onclick="toggleRadarVisibility()">👁️ Toggle Radar</button>
            </div>
            <div class="timestamp" id="timestamp">Loading frames...</div>
        </div>
        <div id="map"></div>
        <script>
            // Clean up any existing map instance
            if (window.radarMap) {{
                window.radarMap.remove();
                window.radarMap = null;
            }}
            
            // Clear any existing animation intervals
            if (window.radarAnimationInterval) {{
                clearInterval(window.radarAnimationInterval);
                window.radarAnimationInterval = null;
            }}
            
            // Initialize map with zoom limits
            const map = L.map('map', {{
                maxZoom: 13,  // Limit to radar data availability
                zoomControl: true
            }}).setView([{lat}, {lon}], 8);
            window.radarMap = map;  // Store globally for cleanup
            
            // Add dark tile layer
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                maxZoom: 19  // Base map supports higher zoom even if radar doesn't
            }}).addTo(map);
            
            // Add zoom warning
            map.on('zoomend', function() {{
                const zoom = map.getZoom();
                const timestamp = document.getElementById('timestamp');
                if (zoom > 13 && radarVisible) {{
                    if (!timestamp.textContent.includes('⚠️')) {{
                        timestamp.textContent = '⚠️ Radar data limited at this zoom level';
                    }}
                }} else if (radarFrames.length > 0 && !timestamp.textContent.includes('⚠️')) {{
                    updateTimestamp();
                }}
            }});
            
            // Add location marker
            const marker = L.marker([{lat}, {lon}]).addTo(map);
            marker.bindPopup('<b>{location['city']}</b><br>{location['region']}, {location['country']}').openPopup();
            
            // Animation variables
            let radarFrames = [];
            let radarLayers = [];
            let animationInterval = null;
            let currentFrameIndex = 0;
            let isPlaying = false;
            let radarVisible = true;
            let framesLoaded = 0;
            let pastFramesCount = 0;  // Track where past ends and future begins
            
            // Load all radar frames with preloading for smooth animation
            function loadRadarFrames() {{
                fetch('https://api.rainviewer.com/public/weather-maps.json')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.radar) {{
                            // Combine past and future (nowcast) frames
                            let allFrames = [];
                            
                            // Add past frames (2 hours)
                            if (data.radar.past && data.radar.past.length > 0) {{
                                allFrames = allFrames.concat(data.radar.past);
                            }}
                            
                            // Add nowcast frames (30 min future) if available
                            if (data.radar.nowcast && data.radar.nowcast.length > 0) {{
                                allFrames = allFrames.concat(data.radar.nowcast);
                            }}
                            
                            if (allFrames.length === 0) return;
                            
                            radarFrames = allFrames;
                            framesLoaded = 0;
                            
                            pastFramesCount = data.radar.past ? data.radar.past.length : 0;
                            
                            // Create and preload layers for all frames
                            radarFrames.forEach((frame, index) => {{
                                // Color scheme 4 = The Weather Channel style
                                // RainViewer tiles work best up to zoom level 12-13
                                const radarUrl = `https://tilecache.rainviewer.com${{frame.path}}/256/{{z}}/{{x}}/{{y}}/4/1_1.png`;
                                
                                const layer = L.tileLayer(radarUrl, {{
                                    opacity: 0,
                                    zIndex: 10 + index,
                                    className: 'radar-layer',
                                    maxZoom: 13,  // Radar data available up to zoom 13
                                    minZoom: 0
                                }});
                                
                                // Add to map immediately but invisible (for preloading)
                                layer.addTo(map);
                                
                                // Listen for tile loading
                                layer.on('load', function() {{
                                    framesLoaded++;
                                    if (framesLoaded === radarFrames.length) {{
                                        const hasNowcast = data.radar.nowcast && data.radar.nowcast.length > 0;
                                        const msg = hasNowcast ? 
                                            `Ready - ${{pastFramesCount}} past + ${{radarFrames.length - pastFramesCount}} future` :
                                            `Ready - ${{radarFrames.length}} frames loaded`;
                                        document.getElementById('timestamp').textContent = msg;
                                        // Show last past frame (present moment) once all loaded
                                        showFrame(pastFramesCount - 1);
                                    }} else {{
                                        document.getElementById('timestamp').textContent = 
                                            `Loading... ${{framesLoaded}}/${{radarFrames.length}}`;
                                    }}
                                }});
                                
                                radarLayers.push(layer);
                            }});
                            
                            currentFrameIndex = pastFramesCount - 1;  // Start at current time
                        }}
                    }})
                    .catch(error => {{
                        console.error('Error loading radar:', error);
                        document.getElementById('timestamp').textContent = 'Radar unavailable';
                    }});
            }}
            
            function updateTimestamp() {{
                if (radarFrames.length > 0) {{
                    const frame = radarFrames[currentFrameIndex];
                    const date = new Date(frame.time * 1000);
                    const timeStr = date.toLocaleTimeString();
                    
                    // Determine if frame is past or future
                    const label = currentFrameIndex < pastFramesCount ? '📊 PAST' : '🔮 FUTURE';
                    const now = currentFrameIndex === pastFramesCount - 1 ? ' (NOW)' : '';
                    
                    document.getElementById('timestamp').textContent = 
                        `${{label}}${{now}} - ${{timeStr}}`;
                }}
            }}
            
            function showFrame(index) {{
                // Smoothly fade out current frame
                if (radarLayers[currentFrameIndex]) {{
                    radarLayers[currentFrameIndex].setOpacity(0);
                }}
                
                // Update index
                currentFrameIndex = index;
                
                // Smoothly fade in new frame
                if (radarVisible && radarLayers[currentFrameIndex]) {{
                    radarLayers[currentFrameIndex].setOpacity(0.7);
                }}
                
                updateTimestamp();
            }}
            
            function toggleAnimation() {{
                const playBtn = document.getElementById('playBtn');
                
                if (isPlaying) {{
                    // Stop animation
                    clearInterval(animationInterval);
                    window.radarAnimationInterval = null;
                    isPlaying = false;
                    playBtn.textContent = '▶️ Play';
                }} else {{
                    // Start animation
                    isPlaying = true;
                    playBtn.textContent = '⏸️ Pause';
                    
                    animationInterval = setInterval(() => {{
                        let nextFrame = currentFrameIndex + 1;
                        if (nextFrame >= radarFrames.length) {{
                            nextFrame = 0;  // Loop back to start
                        }}
                        showFrame(nextFrame);
                    }}, 500);  // 500ms per frame (2 frames/second)
                    window.radarAnimationInterval = animationInterval;  // Store globally for cleanup
                }}
            }}
            
            function toggleRadarVisibility() {{
                radarVisible = !radarVisible;
                
                if (radarVisible) {{
                    // Fade in current frame
                    if (radarLayers[currentFrameIndex]) {{
                        radarLayers[currentFrameIndex].setOpacity(0.7);
                    }}
                }} else {{
                    // Fade out all frames
                    radarLayers.forEach(layer => {{
                        layer.setOpacity(0);
                    }});
                }}
            }}
            
            // Load radar on startup
            loadRadarFrames();
            
            // Refresh radar data every 5 minutes
            setInterval(function() {{
                // Stop animation if playing
                if (isPlaying) {{
                    toggleAnimation();
                }}
                
                // Clear existing layers
                radarLayers.forEach(layer => map.removeLayer(layer));
                radarLayers = [];
                radarFrames = [];
                currentFrameIndex = 0;
                
                // Reload
                loadRadarFrames();
            }}, 300000);
        </script>
    </body>
    </html>
    """
    
    # Display the radar map
    components.html(radar_html, height=520)
    
    st.markdown("""
    <div style='text-align: center; margin-top: 10px; color: #888; font-size: 0.85em;'>
        🔄 Radar updates every 5 minutes | 
        <span style='color: #667eea;'>Blue/Green</span> = Light Rain | 
        <span style='color: #e6b800;'>Yellow</span> = Moderate | 
        <span style='color: #ff4444;'>Red</span> = Heavy
    </div>
    """, unsafe_allow_html=True)

def display_weather(location, weather_data, model_key='default'):
    """Display weather information.
    
    Args:
        location: Location dictionary
        weather_data: Weather data from API
        model_key: Unique key for this model instance (prevents widget ID conflicts in tabs)
    """
    current = weather_data.get('current', {})
    temperature = current.get('temperature_2m')
    humidity = current.get('relative_humidity_2m')
    wind_speed = current.get('wind_speed_10m')
    weather_code = current.get('weather_code')
    conditions = get_weather_description(weather_code)
    emoji = get_weather_emoji(conditions)
    
    # Location header
    st.markdown(f"<h1 style='text-align: center; color: #e0e0e0; margin-bottom: 5px; margin-top: 0px;'>{location['city']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #aaa; margin-top: 0px; margin-bottom: 10px;'>{location['region']}, {location['country']}</p>", unsafe_allow_html=True)
    
    # Weather icon
    st.markdown(f"<div class='weather-icon'>{emoji}</div>", unsafe_allow_html=True)
    
    # Temperature display
    if st.session_state.unit_temp == 'F':
        temp_display = f"{temperature:.1f}°F"
    else:
        temp_c = convert_temp(temperature, to_celsius=True)
        temp_display = f"{temp_c:.1f}°C"
    
    st.markdown(f"<div class='temperature'>{temp_display}</div>", unsafe_allow_html=True)
    
    # Conditions
    st.markdown(f"<h3 style='text-align: center; color: #bbb; margin-top: 10px; margin-bottom: 20px;'>{conditions}</h3>", unsafe_allow_html=True)
    
    # Check for upcoming precipitation
    precip_alert = check_precipitation_soon(weather_data)
    
    # Debug: Show precipitation forecast data (you can remove this later)
    if weather_data.get('hourly'):
        with st.expander("🔍 Debug: Precipitation Forecast (next 12 hours)", expanded=False):
            hourly = weather_data['hourly']
            if 'precipitation_probability' in hourly:
                # Find current hour index using UTC time comparison
                all_times = hourly.get('time', [])
                start_idx = 0
                
                if all_times:
                    try:
                        # Get current UTC time
                        now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                        
                        for i, time_str in enumerate(all_times):
                            # Parse the time string from API
                            dt = datetime.fromisoformat(time_str)
                            # Make timezone-aware if not already
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            
                            if dt >= now_utc:
                                start_idx = i
                                break
                    except:
                        start_idx = 0
                
                # Get next 12 hours starting from current hour
                probs = hourly['precipitation_probability'][start_idx:start_idx+12]
                times = all_times[start_idx:start_idx+12]
                
                st.write("**Precipitation Probabilities:**")
                for i, (time_str, prob) in enumerate(zip(times, probs)):
                    # Show all hours, even if probability is 0 or None
                    try:
                        dt = datetime.fromisoformat(time_str)
                        time_only = dt.strftime("%I:%M %p")  # Format as 12-hour time
                    except:
                        time_only = time_str.split('T')[1] if 'T' in time_str else time_str
                    
                    # Display probability, defaulting to 0% if None
                    prob_display = f"{prob}%" if prob is not None else "0%"
                    st.write(f"- {time_only}: {prob_display}")


    
    if precip_alert:
        minutes = precip_alert['minutes']
        prob = precip_alert['probability']
        precip_type = precip_alert['type']
        precip_emoji = precip_alert['emoji']
        color_start = precip_alert['color_start']
        color_end = precip_alert['color_end']
        
        if minutes < 60:
            time_str = f"{minutes} minutes"
        else:
            hours = minutes // 60
            time_str = f"{hours} hour{'s' if hours > 1 else ''}"
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {color_start} 0%, {color_end} 100%); 
                    padding: 15px; border-radius: 15px; text-align: center; 
                    margin: 20px auto; max-width: 500px; 
                    box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
                    animation: pulse 2s ease-in-out infinite;'>
            <div style='font-size: 32px; margin-bottom: 5px;'>{precip_emoji}</div>
            <div style='font-size: 18px; font-weight: bold; color: white;'>
                {precip_type} Expected in {time_str}
            </div>
            <div style='font-size: 14px; color: rgba(255,255,255,0.9); margin-top: 5px;'>
                {prob}% probability
            </div>
        </div>
        <style>
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.02); }}
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # Details cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class='detail-card'>
            <div style='font-size: 28px; margin-bottom: 5px;'>💧</div>
            <div style='font-size: 12px; opacity: 0.9; margin-bottom: 3px;'>Humidity</div>
            <div style='font-size: 22px; font-weight: bold;'>{humidity}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.session_state.unit_wind == 'mph':
            wind_display = f"{wind_speed:.1f} mph"
        else:
            wind_kmh = convert_wind(wind_speed, to_kmh=True)
            wind_display = f"{wind_kmh:.1f} km/h"
        
        st.markdown(f"""
        <div class='detail-card'>
            <div style='font-size: 28px; margin-bottom: 5px;'>💨</div>
            <div style='font-size: 12px; opacity: 0.9; margin-bottom: 3px;'>Wind Speed</div>
            <div style='font-size: 22px; font-weight: bold;'>{wind_display}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Hourly Forecast Section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📅 Hourly Forecast")
    
    if weather_data.get('hourly'):
        hourly = weather_data['hourly']
        all_times = hourly.get('time', [])
        all_temps = hourly.get('temperature_2m', [])
        all_weather_codes = hourly.get('weather_code', [])
        all_precip_probs = hourly.get('precipitation_probability', [])
        
        
        # Find current hour index by comparing against UTC time
        # The API returns times in ISO format with timezone info
        start_idx = 0
        if all_times:
            try:
                # Get current UTC time
                now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                
                # Find the current or next hour in the hourly data
                for i, time_str in enumerate(all_times):
                    # Parse the time string from API (handles timezone automatically)
                    dt = datetime.fromisoformat(time_str)
                    # Make timezone-aware if not already
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    
                    # Check if this time is current or future
                    if dt >= now_utc:
                        start_idx = i
                        break
            except Exception as e:
                # Fallback to first hour if parsing fails
                start_idx = 0
        
        # Get 24 hours starting from current hour
        times = all_times[start_idx:start_idx+24]
        temps = all_temps[start_idx:start_idx+24] if all_temps else []
        weather_codes = all_weather_codes[start_idx:start_idx+24] if all_weather_codes else []
        precip_probs = all_precip_probs[start_idx:start_idx+24] if all_precip_probs else []
        
        # Create scrollable horizontal forecast
        hourly_cards = []
        for idx in range(len(times)):
            try:
                # Parse time (handles timezone from API response)
                dt = datetime.fromisoformat(times[idx])
                
                # Show "Now" for first hour, otherwise time
                if idx == 0:
                    time_str = "Now"
                else:
                    time_str = dt.strftime("%I%p").lstrip('0')  # "2PM" format
                
                # Get temperature
                if idx < len(temps):
                    temp = temps[idx]
                    if st.session_state.unit_temp == 'C':
                        temp = convert_temp(temp, to_celsius=True)
                        temp_str = f"{temp:.0f}°"
                    else:
                        temp_str = f"{temp:.0f}°"
                else:
                    temp_str = "N/A"
                
                # Get weather emoji
                weather_emoji = "🌤️"
                if idx < len(weather_codes):
                    w_desc = get_weather_description(weather_codes[idx])
                    weather_emoji = get_weather_emoji(w_desc)
                
                # Get precipitation probability - always show it
                precip_str = ""
                if idx < len(precip_probs):
                    prob_value = precip_probs[idx] if precip_probs[idx] is not None else 0
                    precip_str = f"<div style='font-size: 11px; color: #64b5f6; margin-top: 3px;'>💧 {prob_value:.0f}%</div>"
                else:
                    precip_str = "<div style='font-size: 11px; color: #64b5f6; margin-top: 3px;'>💧 0%</div>"
                
                hourly_cards.append(f"""
                    <div style='background: rgba(30, 30, 45, 0.6); 
                                padding: 15px 12px; 
                                border-radius: 12px; 
                                text-align: center;
                                border: 1px solid rgba(100, 100, 150, 0.2);
                                min-width: 85px;
                                flex-shrink: 0;
                                margin-right: 10px;'>
                        <div style='font-size: 12px; color: #aaa; margin-bottom: 5px; font-weight: {"bold" if idx == 0 else "normal"};'>{time_str}</div>
                        <div style='font-size: 36px; margin: 8px 0;'>{weather_emoji}</div>
                        <div style='font-size: 20px; font-weight: bold; color: #e0e0e0;'>{temp_str}</div>
                        {precip_str}
                    </div>
                """)
            except Exception as e:
                continue
        
        # Display scrollable container using components.html for proper rendering
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ 
                    margin: 0; 
                    padding: 0; 
                    background: transparent;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }}
                .hourly-container {{
                    overflow-x: auto; 
                    display: flex; 
                    padding: 10px 0;
                    scrollbar-width: thin;
                    scrollbar-color: rgba(100, 100, 150, 0.5) rgba(30, 30, 45, 0.3);
                }}
                .hourly-container::-webkit-scrollbar {{
                    height: 8px;
                }}
                .hourly-container::-webkit-scrollbar-track {{
                    background: rgba(30, 30, 45, 0.3);
                    border-radius: 10px;
                }}
                .hourly-container::-webkit-scrollbar-thumb {{
                    background: rgba(100, 100, 150, 0.5);
                    border-radius: 10px;
                }}
                .hourly-container::-webkit-scrollbar-thumb:hover {{
                    background: rgba(100, 100, 150, 0.7);
                }}
            </style>
        </head>
        <body>
            <div class='hourly-container'>
                {"".join(hourly_cards)}
            </div>
        </body>
        </html>
        """
        
        components.html(html_content, height=150, scrolling=False)
    
    # Coordinates
    st.markdown(f"""
    <div class='coordinates' style='margin-top: 30px;'>
        📍 {location['latitude']:.4f}°, {location['longitude']:.4f}°
    </div>
    """, unsafe_allow_html=True)
    
    # Timestamp
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    st.markdown(f"<p style='text-align: center; color: #888; font-size: 12px; margin-top: 15px; font-style: italic;'>Updated: {timestamp}</p>", unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("°F ⇄ °C", key=f"temp_toggle_{model_key}"):
            st.session_state.unit_temp = 'C' if st.session_state.unit_temp == 'F' else 'F'
            st.rerun()
    
    with col2:
        if st.button("mph ⇄ km/h", key=f"wind_toggle_{model_key}"):
            st.session_state.unit_wind = 'kmh' if st.session_state.unit_wind == 'mph' else 'mph'
            st.rerun()
    
    with col3:
        if st.button("🔄 Refresh", key=f"refresh_{model_key}"):
            st.rerun()

def main():
    # Sidebar
    with st.sidebar:
        st.header("🔍 Location Search")
        
        search_option = st.radio(
            "Choose search method:",
            ["📍 Use Current Location", "🌍 Search by Name"],
            index=1
        )
        
        location = None
        
        if search_option == "📍 Use Current Location":
            if st.button("Detect Location", use_container_width=True):
                with st.spinner("Detecting your location..."):
                    location = get_current_location()
                    if location:
                        st.session_state.last_location = location
                        weather_data = get_weather(location['latitude'], location['longitude'])
                        st.session_state.weather_data = (location, weather_data)
                    else:
                        st.error("Could not detect your location. Please try searching by name.")
        
        else:
            location_name = st.text_input(
                "Enter location:",
                placeholder="e.g., London, Boston, Paris",
                help="Enter city name, or 'City, Country' for more specific results"
            )
            
            # Search button
            if st.button("Search", use_container_width=True):
                if location_name:
                    with st.spinner(f"Searching for {location_name}..."):
                        results = get_location_by_name(location_name)
                        
                        if results:
                            st.session_state.search_results = results
                            st.session_state.search_query = location_name
                        else:
                            st.session_state.search_results = None
                            st.error(f"Location '{location_name}' not found. Try a different search.")
                else:
                    st.warning("Please enter a location name")
            
            # Display search results if available
            if 'search_results' in st.session_state and st.session_state.search_results:
                results = st.session_state.search_results
                
                if len(results) > 1:
                    st.info(f"Found {len(results)} locations:")
                    
                    # Create selection options
                    location_options = [
                        f"{r.get('name')}, {r.get('admin1', '')}, {r.get('country')}"
                        for r in results
                    ]
                    
                    selected = st.selectbox(
                        "Choose location:", 
                        location_options,
                        key="location_selector"
                    )
                    
                    if st.button("Get Weather", use_container_width=True, type="primary"):
                        selected_idx = location_options.index(selected)
                        result = results[selected_idx]
                        
                        location = {
                            'latitude': result.get('latitude'),
                            'longitude': result.get('longitude'),
                            'city': result.get('name'),
                            'region': result.get('admin1', ''),
                            'country': result.get('country')
                        }
                        
                        st.session_state.last_location = location
                        
                        with st.spinner("Fetching weather data..."):
                            weather_data = get_weather(location['latitude'], location['longitude'])
                            st.session_state.weather_data = (location, weather_data)
                        
                        # Clear search results after selection
                        st.session_state.search_results = None
                        st.rerun()
                else:
                    # Only one result, use it directly
                    result = results[0]
                    st.success(f"Found: {result.get('name')}, {result.get('admin1', '')}, {result.get('country')}")
                    
                    if st.button("Get Weather", use_container_width=True, type="primary"):
                        location = {
                            'latitude': result.get('latitude'),
                            'longitude': result.get('longitude'),
                            'city': result.get('name'),
                            'region': result.get('admin1', ''),
                            'country': result.get('country')
                        }
                        
                        st.session_state.last_location = location
                        
                        with st.spinner("Fetching weather data..."):
                            weather_data = get_weather(location['latitude'], location['longitude'])
                            st.session_state.weather_data = (location, weather_data)
                        
                        # Clear search results after selection
                        st.session_state.search_results = None
                        st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("<div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);'>This app uses the free Open-Meteo API to fetch real-time weather data. No API key required!</div>", unsafe_allow_html=True)
        
        st.markdown("### 💡 Tips")
        st.markdown("""
        <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);'>
        • Search by city name (e.g., "London")<br>
        • Use "City, Country" for specific results<br>
        • Toggle between °F/°C and mph/km/h<br>
        • Click refresh for latest data
        </div>
        """, unsafe_allow_html=True)
    
    # Main content
    if st.session_state.weather_data:
        location, weather_data = st.session_state.weather_data
        
        if weather_data:
            # Add weather model comparison tabs
            st.markdown("### 🌐 Weather Model Comparison")
            st.markdown("<p style='color: #aaa; font-size: 0.9em; margin-bottom: 20px;'>Compare forecasts from different global weather models</p>", unsafe_allow_html=True)
            
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Best Match (Auto)", 
                "🇪🇺 ECMWF (European)", 
                "🇺🇸 GFS (NOAA)", 
                "🇩🇪 ICON (German)"
            ])
            
            with tab1:
                display_weather(location, weather_data, model_key='best_match')
            
            with tab2:
                st.markdown("<p style='color: #888; font-size: 0.85em; font-style: italic;'>ECMWF IFS 0.25° - European Centre for Medium-Range Weather Forecasts (High accuracy, global coverage)</p>", unsafe_allow_html=True)
                with st.spinner("Loading ECMWF model data..."):
                    ecmwf_data = get_weather(location['latitude'], location['longitude'], model='ecmwf_ifs025')
                    if ecmwf_data:
                        display_weather(location, ecmwf_data, model_key='ecmwf')
                    else:
                        st.error("Unable to load ECMWF model data")
            
            with tab3:
                st.markdown("<p style='color: #888; font-size: 0.85em; font-style: italic;'>GFS - NOAA Global Forecast System (Best for North America, 4x daily updates)</p>", unsafe_allow_html=True)
                with st.spinner("Loading GFS model data..."):
                    gfs_data = get_weather(location['latitude'], location['longitude'], model='gfs_global')
                    if gfs_data:
                        display_weather(location, gfs_data, model_key='gfs')
                    else:
                        st.error("Unable to load GFS model data")
            
            with tab4:
                st.markdown("<p style='color: #888; font-size: 0.85em; font-style: italic;'>ICON - German Weather Service (High resolution, updated 4x daily)</p>", unsafe_allow_html=True)
                with st.spinner("Loading ICON model data..."):
                    icon_data = get_weather(location['latitude'], location['longitude'], model='icon_global')
                    if icon_data:
                        display_weather(location, icon_data, model_key='icon')
                    else:
                        st.error("Unable to load ICON model data")
            
            # Add spacing
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Display radar below weather card (full width)
            display_radar(location)
        else:
            st.error("Could not fetch weather data. Please try again.")
    else:
        # Welcome message
        st.markdown("""
        <div style='text-align: center; padding: 50px; background: rgba(30, 30, 45, 0.9); border-radius: 20px; margin: 50px auto; max-width: 600px; border: 1px solid rgba(100, 100, 150, 0.3);'>
            <h2 style='color: #00d4ff; text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);'>🌤️</h2>
            <p style='color: #bbb; font-size: 18px; margin-top: 20px;'>
                Get started by searching for a location in the sidebar or use your current location.
            </p>
            <p style='color: #888; font-size: 14px; margin-top: 30px;'>
                ☀️ Real-time weather data<br>
                🌍 Search any location worldwide<br>
                🔄 Multiple unit conversions<br>
                📱 Responsive design
            </p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
