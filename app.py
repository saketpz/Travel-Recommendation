import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import json
import math
import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
EVENTBRITE_API_KEY = os.getenv("EVENTBRITE_API_KEY")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ------------------------------------------------------------------------
#  (A) ITINERARY BUILDER (Minimal Example)
# ------------------------------------------------------------------------
# In a real app, you'd use a database & user auth. Here, we store in memory.
user_itineraries = {}  # e.g. { "user123": [ { placeName, lat, lng, day, order }, ... ] }

@app.route('/itinerary', methods=['POST'])
def itinerary():
    """
    Minimal example of an itinerary builder endpoint.
    Expects JSON like:
    {
      "user_id": "someUser",
      "places": [
        { "name": "Place A", "lat": 1.23, "lng": 4.56, "day": 1 },
        { "name": "Place B", "lat": 7.89, "lng": 0.12, "day": 2 }
      ]
    }
    Stores in a global dictionary user_itineraries for demonstration only.
    """
    data = request.get_json()
    user_id = data.get("user_id")
    places = data.get("places", [])

    if not user_id or not places:
        return jsonify({"error": "Missing user_id or places"}), 400

    user_itineraries[user_id] = places
    return jsonify({"message": "Itinerary saved", "itinerary": places}), 200

# ------------------------------------------------------------------------
#  (B) HELPER FUNCTIONS
# ------------------------------------------------------------------------

def get_coordinates_from_city(city_name, api_key):
    """Converts a city name to 'lat,lon' using Google Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": city_name, "key": api_key}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return f"{loc['lat']},{loc['lng']}"
        else:
            return None
    except Exception as e:
        logger.error("Error fetching coordinates: %s", e)
        return None


def get_nearby_places(location, preference, api_key):
    """
    Fetches nearby places for a given category using Google Places API.
    Returns only places with rating >= 4.0.
    """
    place_types = {
        "temple": "hindu_temple",
        "mosque": "mosque",
        "church": "church",
        "historical": "museum, landmark, heritage_site",
        "nature": "park, zoo, botanical_garden, national_park",
        "adventure": "amusement_park, hiking_area, theme_park",
        "food": "restaurant, cafe, bakery, bar",
        "shopping": "shopping_mall, flea_market, supermarket",
        "beach": "beach, waterfront",
        "nightlife": "night_club, casino, bar",
        "wellness": "spa, wellness_center, yoga_studio",
        "family": "aquarium, amusement_park, playground, kids_activity"
    }
    place_type = place_types.get(preference.lower(), "tourist_attraction")
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": location,
        "radius": 7000,
        "type": place_type,
        "keyword": f"{preference}, best {place_type} in the city",
        "rankby": "prominence",
        "key": api_key
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        places = []
        for place in data.get("results", []):
            rating = place.get("rating", 0)
            if rating >= 4.0:
                places.append({
                    "name": place["name"],
                    "category": preference,
                    "lat": place["geometry"]["location"]["lat"],
                    "lng": place["geometry"]["location"]["lng"],
                    "rating": rating,
                    "user_ratings": place.get("user_ratings_total", 0)
                })
        return places if places else [{"name": "No places found"}]
    except Exception as e:
        logger.error("Error fetching places: %s", e)
        return [{"name": "Error fetching places"}]


def get_trekking_spots_osm(lat, lon, radius_km=50):
    """
    Fetch trekking spots from OSM Overpass API.
    Only nodes with a 'name' are returned.
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
        node["tourism"="attraction"]["hiking"="yes"]["name"~"."](around:{radius_km * 1000}, {lat}, {lon});
        node["natural"="peak"]["name"~"."](around:{radius_km * 1000}, {lat}, {lon});
    );
    out center;
    """
    try:
        response = requests.get(overpass_url, params={"data": query})
        data = response.json()
        treks = []
        for place in data.get("elements", []):
            name = place.get("tags", {}).get("name", "Unnamed Trek")
            treks.append({
                "name": name,
                "lat": place["lat"],
                "lng": place["lon"]
            })
        return treks if treks else [{"name": "No trekking places found"}]
    except Exception as e:
        logger.error("Error fetching trekking spots: %s", e)
        return [{"name": "Error fetching treks"}]


def get_trek_details_google(name, api_key):
    """
    Fetches trek details (rating, reviews, address) using Google Places API.
    """
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": name,
        "inputtype": "textquery",
        "fields": "name,rating,user_ratings_total,formatted_address",
        "key": api_key
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("candidates"):
            place = data["candidates"][0]
            return {
                "name": place.get("name", name),
                "rating": place.get("rating", "Unknown"),
                "reviews": place.get("user_ratings_total", 0),
                "address": place.get("formatted_address", "Unknown")
            }
        else:
            return {"rating": "Unknown", "reviews": 0, "address": "Unknown"}
    except Exception as e:
        logger.error("Error fetching trek details: %s", e)
        return {"rating": "Unknown", "reviews": 0, "address": "Unknown"}


def merge_duplicate_places(places, precision=4):
    """Merge duplicate places based on rounded latitude and longitude."""
    unique = {}
    for place in places:
        key = (round(place.get("lat", 0), precision), round(place.get("lng", 0), precision))
        if key in unique:
            if isinstance(place.get("rating"), (int, float)) and place.get("rating") > unique[key].get("rating", 0):
                unique[key] = place
        else:
            unique[key] = place
    return list(unique.values())


def get_weather_info(location, api_key):
    """
    Fetches current weather for a given 'lat,lon' using OpenWeather API.
    Returns a dictionary with description, temperature, and an icon URL.
    """
    url = "https://api.openweathermap.org/data/2.5/weather"
    lat, lon = location.split(",")
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "weather" in data and "main" in data:
            weather = data["weather"][0]
            icon_code = weather.get("icon")
            icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else ""
            return {
                "description": weather.get("description", "N/A"),
                "temp": data["main"].get("temp", "N/A"),
                "icon_url": icon_url
            }
        else:
            return {"description": "Weather data not available", "temp": "N/A", "icon_url": ""}
    except Exception as e:
        logger.error("Error fetching weather: %s", e)
        return {"description": "Weather data not available", "temp": "N/A", "icon_url": ""}


def get_upcoming_events(city, api_key):
    """Fetches upcoming events in a city using Eventbrite API."""
    url = "https://www.eventbriteapi.com/v3/events/search/"
    params = {
        "location.address": city,
        "location.within": "100km",
        "sort_by": "date",
        "categories": "music, arts, culture, sports, food, business",
        "token": api_key
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("events"):
            events = []
            for event in data["events"][:5]:
                events.append({
                    "name": event["name"]["text"],
                    "date": event["start"]["local"],
                    "url": event["url"]
                })
            return events
        else:
            return [{"name": "No major events found"}]
    except Exception as e:
        logger.error("Error fetching events: %s", e)
        return [{"name": "Error fetching events"}]


def get_travel_time(origin, destination, api_key, mode="driving"):
    """
    Fetches real-time travel time using Google Distance Matrix API.
    Returns travel time in minutes or "Unknown".
    """
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "mode": mode,
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": api_key
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("rows"):
            element = data["rows"][0]["elements"][0]
            if element.get("status") == "OK":
                travel_time_seconds = element["duration"]["value"]
                return f"{travel_time_seconds // 60} mins"
            else:
                return "Unknown"
        else:
            return "Unknown"
    except Exception as e:
        logger.error("Error fetching travel time: %s", e)
        return "Unknown"


def get_best_season_for_category(category):
    """
    Returns a recommended best season or months for visiting based on the place category.
    """
    best_season_map = {
        "trekking": "October to March",
        "temple": "All year round",
        "historical": "October to March",
        "nature": "Monsoon & Winter (June to February)",
        "adventure": "October to March",
        "food": "All year round",
        "shopping": "All year round",
        "beach": "November to February",
        "nightlife": "All year round",
        "wellness": "All year round",
        "family": "All year round"
    }
    return best_season_map.get(category.lower(), "All year round")


def get_wikipedia_description(place_name):
    """
    Fetches a short summary of the place from Wikipedia's REST API.
    Returns a description string.
    """
    title = place_name.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("extract", "No description available.")
        else:
            return "No description available."
    except Exception as e:
        logger.error("Error fetching Wikipedia description: %s", e)
        return "No description available."


# ------------------------------------------------------------------------
#  (C) REFINED RECOMMENDATION LOGIC
# ------------------------------------------------------------------------
def calculate_score(place, user_preferences=None):
    """
    Calculates a score for a place based on rating, travel time, reviews,
    and a small bonus if the place's category is in the user's preferences.
    """
    # Convert rating to float; default to 4.0 if not valid
    try:
        rating = float(place.get("rating", 4.0))
    except (ValueError, TypeError):
        rating = 4.0

    # Convert reviews to float; default to 0 if not valid
    try:
        reviews = float(place.get("user_ratings", place.get("reviews", 0)))
    except (ValueError, TypeError):
        reviews = 0

    # Convert travel time string (e.g., "15 mins") to an integer (in minutes)
    travel_str = place.get("travel_time", "30 mins")
    try:
        travel_val = int(travel_str.split()[0])
    except (ValueError, IndexError):
        travel_val = 30

    # Base scoring formula
    score = (rating * 10) + (reviews * 0.01) - (travel_val * 0.5)

    # Small bonus if the place's category is in the user's preferences
    if user_preferences and place.get("category") in user_preferences:
        score += 1.0  # or any other weighting you prefer

    return score


def rank_destinations(destinations, user_preferences=None):
    """Ranks destinations using the refined scoring function."""
    for place in destinations:
        place["score"] = calculate_score(place, user_preferences)
    return sorted(destinations, key=lambda x: x["score"], reverse=True)


# ------------------------------------------------------------------------
#  (D) ADVANCED WEATHER: MULTI-DAY FORECAST + SEASONAL INSIGHTS
# ------------------------------------------------------------------------
def get_weather_forecast(location, api_key, days=3):
    """
    Fetches a multi-day forecast using OpenWeather's 5-day/3-hour forecast API.
    Returns a simplified list of daily summaries.
    """
    url = "https://api.openweathermap.org/data/2.5/forecast"
    lat, lon = location.split(",")
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "list" not in data:
            return []

        # We'll group forecasts by day
        daily_data = {}
        for entry in data["list"]:
            dt_txt = entry["dt_txt"]  # e.g. "2023-05-10 15:00:00"
            date_str = dt_txt.split(" ")[0]
            temp = entry["main"]["temp"]
            desc = entry["weather"][0]["description"]
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "temps": [],
                    "descs": []
                }
            daily_data[date_str]["temps"].append(temp)
            daily_data[date_str]["descs"].append(desc)

        # Build a simple summary for each day
        forecast_summaries = []
        sorted_days = sorted(daily_data.keys())
        for day_index, day in enumerate(sorted_days):
            if day_index >= days:
                break
            temps = daily_data[day]["temps"]
            descs = daily_data[day]["descs"]
            avg_temp = sum(temps) / len(temps)
            # A simple approach to choose the most common description
            most_common_desc = max(set(descs), key=descs.count)
            forecast_summaries.append({
                "date": day,
                "avg_temp": round(avg_temp, 1),
                "description": most_common_desc
            })

        return forecast_summaries

    except Exception as e:
        logger.error("Error fetching weather forecast: %s", e)
        return []


def add_seasonal_disclaimer(destinations):
    """
    Adds a 'seasonal_warning' field if the current month is outside the recommended best season range.
    This is a simplistic example; real logic might parse the months more accurately.
    """
    current_month = datetime.datetime.now().month  # 1=Jan, 12=Dec
    # We'll do a simple mapping from best season text to month ranges
    season_map = {
        "october to march": range(10, 13)  # plus 1,2,3
    }
    # We'll expand logic if needed, but this is a minimal example
    for dest in destinations:
        best_season = dest.get("best_season", "").lower()
        if "october to march" in best_season:
            # If not in 10,11,12,1,2,3 => add warning
            # We'll treat months 10,11,12,1,2,3 as "peak"
            if current_month not in [10, 11, 12, 1, 2, 3]:
                dest["seasonal_warning"] = "Note: Best visited between October and March."
        # You can expand for "monsoon & winter", "november to february", etc.
    return destinations


# ------------------------------------------------------------------------
#  (E) FILTER / SORT ENHANCEMENTS: DISTANCE FILTER
# ------------------------------------------------------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Returns the great-circle distance between two points on Earth (in km).
    """
    R = 6371  # Earth radius in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (
        math.sin(dLat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def filter_by_distance(destinations, user_location, max_distance_km):
    """
    Filters out places that are more than 'max_distance_km' from 'user_location'.
    We'll do a direct lat/lon 'as-the-crow-flies' distance using haversine.
    """
    lat1, lon1 = map(float, user_location.split(","))
    filtered = []
    for dest in destinations:
        lat2 = dest.get("lat")
        lon2 = dest.get("lng")
        if lat2 is None or lon2 is None:
            continue
        dist_km = haversine_distance(lat1, lon1, lat2, lon2)
        dest["distance_km"] = round(dist_km, 2)  # optional: store it
        if dist_km <= max_distance_km:
            filtered.append(dest)
    return filtered


# ------------------------------------------------------------------------
#  (F) MAIN RECOMMEND ENDPOINT
# ------------------------------------------------------------------------
@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Fetches recommendations based on city name and preferences, then applies ranking,
    filtering, advanced weather, and optional distance filter. 
    Returns:
      - weather: current weather
      - weather_forecast: multi-day forecast
      - destinations: recommended places
      - events: upcoming events
    JSON Body options:
      - city (str)
      - preferences (str or list)
      - travel_mode (default 'driving')
      - sort_by ('score' or 'rating')
      - min_rating (float, default 0)
      - max_distance (float, optional) => filters places beyond that distance (km)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user_city = data.get("city")
    preferences = data.get("preferences")
    travel_mode = data.get("travel_mode", "driving")
    sort_by = data.get("sort_by", "score")
    max_distance = data.get("max_distance", None)  # optional distance filter
    try:
        max_distance = float(max_distance) if max_distance else None
    except ValueError:
        max_distance = None

    if not user_city or not preferences:
        return jsonify({"error": "Provide 'city' and 'preferences'."}), 400

    # Support both comma-separated string and list for preferences
    if isinstance(preferences, list):
        pref_list = [str(p).strip().lower() for p in preferences if p]
    else:
        pref_list = [p.strip().lower() for p in preferences.split(",") if p.strip()]

    # Convert city to coordinates
    user_location = get_coordinates_from_city(user_city, GOOGLE_MAPS_API_KEY)
    if not user_location:
        return jsonify({"error": "Invalid city name or location not found."}), 400

    # Fetch places based on preferences
    all_destinations = []
    for pref in pref_list:
        if pref == "trekking":
            lat, lon = map(float, user_location.split(","))
            treks = get_trekking_spots_osm(lat, lon)
            for trek in treks:
                details = get_trek_details_google(trek["name"], GOOGLE_MAPS_API_KEY)
                trek.update(details)
                trek["category"] = "trekking"
                trek["best_season"] = get_best_season_for_category("trekking")
                trek["description"] = get_wikipedia_description(trek["name"])
                trek["travel_time"] = "N/A"
                all_destinations.append(trek)
        else:
            places = get_nearby_places(user_location, pref, GOOGLE_MAPS_API_KEY)
            for place in places:
                # Check for the presence of latitude and longitude keys
                if "lat" not in place or "lng" not in place:
                    continue
                tt = get_travel_time(
                    user_location,
                    f"{place['lat']},{place['lng']}",
                    GOOGLE_MAPS_API_KEY,
                    travel_mode
                )
                place["travel_time"] = tt if tt is not None else "Unknown"
                place["best_season"] = get_best_season_for_category(pref)
                place["description"] = get_wikipedia_description(place["name"])
                all_destinations.append(place)

    # Merge duplicates
    all_destinations = merge_duplicate_places(all_destinations)

    # (F1) OPTIONAL: Distance Filter
    if max_distance:
        all_destinations = filter_by_distance(all_destinations, user_location, max_distance)

    # (F2) Sorting Options: sort by 'score' or by 'rating'
    if sort_by == "rating":
        ranked_destinations = sorted(
            all_destinations,
            key=lambda x: float(x.get("rating") if isinstance(x.get("rating"), (int, float)) else 0),
            reverse=True
        )
    else:
        # Use the refined rank_destinations with user preferences
        ranked_destinations = rank_destinations(all_destinations, user_preferences=pref_list)

    # (F3) Optional min_rating filter
    try:
        min_rating = float(data.get("min_rating", 0))
    except Exception:
        min_rating = 0

    filtered_destinations = []
    for dest in ranked_destinations:
        try:
            dest_rating = float(dest.get("rating", 0))
        except (ValueError, TypeError):
            dest_rating = 0
        if dest_rating >= min_rating:
            filtered_destinations.append(dest)

    # (F4) Add seasonal disclaimers
    filtered_destinations = add_seasonal_disclaimer(filtered_destinations)

    # (F5) Weather + Forecast + Events
    weather_info = get_weather_info(user_location, OPENWEATHER_API_KEY)
    weather_forecast = get_weather_forecast(user_location, OPENWEATHER_API_KEY, days=3)
    events = get_upcoming_events(user_city, EVENTBRITE_API_KEY)

    return jsonify({
        "weather": weather_info,           # current weather
        "weather_forecast": weather_forecast,  # next few days
        "destinations": filtered_destinations,
        "events": events
    })


if __name__ == '__main__':
    app.run(debug=True)
