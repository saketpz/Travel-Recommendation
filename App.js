import React, { useState } from "react";
import "./App.css";

function App() {
  // Basic input states
  const [city, setCity] = useState("");
  const [travelMode, setTravelMode] = useState("driving");
  
  // New form options
  const [selectedPreferences, setSelectedPreferences] = useState([]);
  const [sortBy, setSortBy] = useState("score");
  const [minRating, setMinRating] = useState("");
  const [maxDistance, setMaxDistance] = useState(""); // new field for distance filter

  // API result state
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Itinerary state
  const [itinerary, setItinerary] = useState([]);

  // Available preferences for checkboxes
  const availablePreferences = [
    "temple",
    "food",
    "trekking",
    "shopping",
    "historical",
    "nature",
    "adventure",
    "beach",
    "nightlife",
    "wellness",
    "family"
  ];

  const handlePreferenceChange = (e) => {
    const { value, checked } = e.target;
    if (checked) {
      setSelectedPreferences((prev) => [...prev, value]);
    } else {
      setSelectedPreferences((prev) => prev.filter((pref) => pref !== value));
    }
  };

  const addToItinerary = (dest) => {
    // Avoid duplicate entries (optional)
    if (!itinerary.find(item => item.name === dest.name)) {
      setItinerary((prev) => [...prev, dest]);
    }
  };

  const removeFromItinerary = (name) => {
    setItinerary((prev) => prev.filter((item) => item.name !== name));
  };

  const clearItinerary = () => {
    setItinerary([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const payload = {
      city: city,
      preferences: selectedPreferences, // array of preferences
      travel_mode: travelMode,
      sort_by: sortBy,
      min_rating: minRating,
      max_distance: maxDistance
    };

    try {
      const response = await fetch("http://127.0.0.1:5000/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error("API request failed");
      }
      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      setError("Error fetching recommendations.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Travel Recommendation System</h1>
      </header>

      <form onSubmit={handleSubmit} className="recommendation-form">
        <div className="form-group">
          <label htmlFor="city">City:</label>
          <input
            id="city"
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="e.g., Pune"
            required
          />
        </div>

        <div className="form-group">
          <label>Preferences:</label>
          <div className="checkbox-group">
            {availablePreferences.map((pref) => (
              <label key={pref} className="checkbox-label">
                <input
                  type="checkbox"
                  value={pref}
                  checked={selectedPreferences.includes(pref)}
                  onChange={handlePreferenceChange}
                />
                {pref.charAt(0).toUpperCase() + pref.slice(1)}
              </label>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="travelMode">Travel Mode:</label>
          <select
            id="travelMode"
            value={travelMode}
            onChange={(e) => setTravelMode(e.target.value)}
          >
            <option value="driving">Driving</option>
            <option value="walking">Walking</option>
            <option value="transit">Transit</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="sortBy">Sort By:</label>
          <select
            id="sortBy"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="score">Score</option>
            <option value="rating">Rating</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="minRating">Minimum Rating:</label>
          <input
            id="minRating"
            type="number"
            step="0.1"
            value={minRating}
            onChange={(e) => setMinRating(e.target.value)}
            placeholder="e.g., 4.0"
          />
        </div>

        <div className="form-group">
          <label htmlFor="maxDistance">Max Distance (km):</label>
          <input
            id="maxDistance"
            type="number"
            step="0.1"
            value={maxDistance}
            onChange={(e) => setMaxDistance(e.target.value)}
            placeholder="Optional"
          />
        </div>

        <button type="submit">Get Recommendations</button>
      </form>

      {loading && <p className="loading">Loading recommendations...</p>}
      {error && <p className="error">{error}</p>}

      {result && (
        <div className="results">
          {/* Weather Section */}
          <section className="weather-section">
            <h2>Current Weather</h2>
            {result.weather && result.weather.icon_url && (
              <img
                src={result.weather.icon_url}
                alt="Weather Icon"
                className="weather-icon"
              />
            )}
            {result.weather && (
              <p>
                {result.weather.description} | {result.weather.temp}°C
              </p>
            )}
          </section>

          {/* Forecast Section */}
          {result.weather_forecast && result.weather_forecast.length > 0 && (
            <section className="weather-forecast-section">
              <h2>Weather Forecast</h2>
              <div className="cards-container">
                {result.weather_forecast.map((fc, index) => (
                  <div className="card forecast-card" key={index}>
                    <h3>{fc.date}</h3>
                    <p>
                      <strong>Avg Temp:</strong> {fc.avg_temp}°C
                    </p>
                    <p>
                      <strong>Description:</strong> {fc.description}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Destinations Section */}
          <section className="destinations-section">
            <h2>Destinations</h2>
            <div className="cards-container">
              {result.destinations.map((dest, index) => (
                <div className="card destination-card" key={index}>
                  <h3>{dest.name}</h3>
                  <p>
                    <strong>Category:</strong> {dest.category}
                  </p>
                  <p>
                    <strong>Travel Time:</strong>{" "}
                    {dest.travel_time ? dest.travel_time : "N/A"}
                  </p>
                  <p>
                    <strong>Rating:</strong> {dest.rating ? dest.rating : "N/A"}
                  </p>
                  {dest.best_season && (
                    <p>
                      <strong>Best Season:</strong> {dest.best_season}
                    </p>
                  )}
                  {dest.seasonal_warning && (
                    <p className="warning">{dest.seasonal_warning}</p>
                  )}
                  {dest.description && (
                    <p>
                      <strong>Description:</strong>{" "}
                      {dest.description.length > 150
                        ? dest.description.substring(0, 150) + "..."
                        : dest.description}
                    </p>
                  )}
                  <button onClick={() => addToItinerary(dest)}>
                    Add to Itinerary
                  </button>
                </div>
              ))}
            </div>
          </section>

          {/* Itinerary Section */}
          {itinerary.length > 0 && (
            <section className="itinerary-section">
              <h2>My Itinerary</h2>
              <button onClick={clearItinerary}>Clear Itinerary</button>
              <ul>
                {itinerary.map((item, index) => (
                  <li key={index}>
                    {item.name}{" "}
                    <button onClick={() => removeFromItinerary(item.name)}>
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Events Section */}
          <section className="events-section">
            <h2>Events</h2>
            <div className="cards-container">
              {result.events.map((event, index) => (
                <div className="card event-card" key={index}>
                  <h3>{event.name}</h3>
                  <p>
                    <strong>Date:</strong> {event.date ? event.date : "N/A"}
                  </p>
                  {event.url && (
                    <a
                      href={event.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="event-link"
                    >
                      More Details
                    </a>
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default App;
