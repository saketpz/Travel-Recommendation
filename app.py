from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import json

# Load environment variables
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
EVENTBRITE_API_KEY = os.getenv("EVENTBRITE_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

##############################################
# 1. Convert City to Coordinates (Geocoding)
##############################################
def get_coordinates_from_city(city_name, api_key):
    """Converts a city name to 'lat,lon' using Google Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": city_name, "key": api_key}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return f"{loc['lat']},{loc['lng']}"
        else:
            return None
    except Exception as e:
        print("Error fetching coordinates:", e)
        return None

###################################################
# 2. Fetch General Places Using Google Places API
###################################################
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
        print("Error fetching places:", e)
        return [{"name": "Error fetching places"}]

#############################################################
# 3. Fetch Trekking Spots Using OpenStreetMap (OSM) API
#############################################################
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
        print("Error fetching trekking spots:", e)
        return [{"name": "Error fetching treks"}]

##########################################################################
# 4. (Optional) Fetch Additional Trek Details from Google Places API
##########################################################################
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
        if "candidates" in data and data["candidates"]:
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
        print("Error fetching trek details:", e)
        return {"rating": "Unknown", "reviews": 0, "address": "Unknown"}

####################################################################
# 5. Merge Duplicate Places to Remove Very Close Duplicates
####################################################################
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

###########################################################
# 6. Fetch Weather Data Using OpenWeather API
###########################################################
def get_weather_info(location, api_key):
    """Fetches current weather for a given 'lat,lon' using OpenWeather API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": location.split(",")[0],
        "lon": location.split(",")[1],
        "appid": api_key,
        "units": "metric"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "weather" in data and "main" in data:
            weather_desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            return f"{weather_desc}, {temp}°C"
        else:
            return "Weather data not available"
    except Exception as e:
        print("Error fetching weather:", e)
        return "Weather data not available"

###############################################################
# 7. Fetch Upcoming Events Using Eventbrite API
###############################################################
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
        if "events" in data and data["events"]:
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
        print("Error fetching events:", e)
        return [{"name": "Error fetching events"}]

###########################################################
# 8. Fetch Real-time Travel Time Using Google API
###########################################################
def get_travel_time(origin, destination, api_key, mode="driving"):
    """
    Fetches real-time travel time using Google Distance Matrix API.
    
    Parameters:
      - origin: "lat,lon" for starting location.
      - destination: "lat,lon" for destination.
      - mode: Travel mode ("driving", "walking", "transit").
      
    Returns:
      - Travel time as a string in minutes (e.g., "15 mins") or "Unknown".
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
        if "rows" in data and data["rows"]:
            element = data["rows"][0]["elements"][0]
            if element.get("status") == "OK":
                travel_time_seconds = element["duration"]["value"]
                return f"{travel_time_seconds // 60} mins"
            else:
                return "Unknown"
        else:
            return "Unknown"
    except Exception as e:
        print("Error fetching travel time:", e)
        return "Unknown"

###############################################################
# 9. Best Season to Visit Based on Category (Static Mapping)
###############################################################
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

###########################################################
# 10. Fetch Description from Wikipedia (Free, Optional)
###########################################################
def get_wikipedia_description(place_name):
    """
    Fetches a short summary of the place from Wikipedia's REST API.
    Returns an empty string if not available.
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
        print("Error fetching Wikipedia description:", e)
        return "No description available."

###########################################################
# 11. Calculate Score and Rank Destinations (Recommendation Logic)
###########################################################
def calculate_score(place):
    """
    Calculates a score for a place based on rating, travel time, and number of reviews.
    Higher score means a better recommendation.
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

    # Example scoring formula: Increase score for higher rating & reviews; subtract penalty for longer travel time.
    score = (rating * 10) + (reviews * 0.01) - (travel_val * 0.5)
    return score

def rank_destinations(destinations):
    """Ranks destinations using calculated scores and returns them sorted in descending order."""
    for place in destinations:
        place["score"] = calculate_score(place)
    return sorted(destinations, key=lambda x: x["score"], reverse=True)


def fetch_image_for_place(place_name, city_name=None):
    """
    Fetches a single image URL from Unsplash based on the place name.
    Optionally include city_name in the query for better context.
    Returns None if no image found.
    """
    if not UNSPLASH_ACCESS_KEY:
        return None  # Avoid errors if key is missing

    base_url = "https://api.unsplash.com/search/photos"
    query = place_name if not city_name else f"{place_name} {city_name}"
    params = {
        "query": query,
        "per_page": 1,          # Get only 1 image
        "orientation": "landscape",  # Or "portrait" if you prefer
        "client_id": UNSPLASH_ACCESS_KEY
    }
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        results = data.get("results", [])
        if len(results) > 0:
            # 'small' is good for quick loading; you can use 'regular' or 'thumb'
            return results[0]["urls"]["small"]
        else:
            return None
    except Exception as e:
        print("Error fetching Unsplash image:", e)
        return None
    
    
###############################################################
# 12. Main Flask API Endpoint for Travel Recommendations
###############################################################
@app.route('/recommend', methods=['POST'])
def recommend():
    """Fetches recommendations based on city name and preferences, then applies ranking and adds additional details."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user_city = data.get("city")
    preferences = data.get("preferences")  # e.g., "temple, food, trekking, shopping"
    travel_mode = data.get("travel_mode", "driving")

    if not user_city or not preferences:
        return jsonify({"error": "Provide 'city' and 'preferences'."}), 400

    # Convert city to coordinates
    user_location = get_coordinates_from_city(user_city, GOOGLE_MAPS_API_KEY)
    if not user_location:
        return jsonify({"error": "Invalid city name or location not found."}), 400

    all_destinations = []
    # Process each preference
    for preference in preferences.split(","):
        pref = preference.strip().lower()
        if pref == "trekking":
            lat, lon = map(float, user_location.split(","))
            treks = get_trekking_spots_osm(lat, lon)
            for trek in treks:
                details = get_trek_details_google(trek["name"], GOOGLE_MAPS_API_KEY)
                trek.update(details)
                trek["category"] = "trekking"
                trek["best_season"] = get_best_season_for_category("trekking")
                trek["description"] = get_wikipedia_description(trek["name"])
            all_destinations.extend(treks)
        else:
            places = get_nearby_places(user_location, pref, GOOGLE_MAPS_API_KEY)
            for place in places:
                tt = get_travel_time(user_location, f"{place['lat']},{place['lng']}", GOOGLE_MAPS_API_KEY, travel_mode)
                place["travel_time"] = tt if tt is not None else "Unknown"
                place["best_season"] = get_best_season_for_category(pref)
                place["description"] = get_wikipedia_description(place["name"])
            all_destinations.extend(places)

    # Merge duplicate places
    all_destinations = merge_duplicate_places(all_destinations)
    # Rank destinations using our scoring function
    ranked_destinations = rank_destinations(all_destinations)

    weather_info = get_weather_info(user_location, OPENWEATHER_API_KEY)
    events = get_upcoming_events(user_city, EVENTBRITE_API_KEY)

    return jsonify({
        "weather": weather_info,
        "destinations": ranked_destinations,
        "events": events
    })

##############################################
# Run Flask App
##############################################
if __name__ == '__main__':
    app.run(debug=True)
