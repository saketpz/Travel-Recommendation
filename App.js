import React, { useState } from "react";
import "./App.css";

function App() {
  const [city, setCity] = useState("");
  const [preferences, setPreferences] = useState("");
  const [travelMode, setTravelMode] = useState("driving");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const payload = {
      city: city,
      preferences: preferences,
      travel_mode: travelMode,
    };

    try {
      const response = await fetch("http://127.0.0.1:5000/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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
          <label htmlFor="preferences">Preferences:</label>
          <input
            id="preferences"
            type="text"
            value={preferences}
            onChange={(e) => setPreferences(e.target.value)}
            placeholder="e.g., temple, food, trekking, shopping"
            required
          />
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
        <button type="submit">Get Recommendations</button>
      </form>

      {loading && <p className="loading">Loading recommendations...</p>}
      {error && <p className="error">{error}</p>}

      {/* If we have results, display them */}
      {result && (
        <div className="results">
          <section className="weather-section">
            <h2>Weather</h2>
            <p>{result.weather}</p>
          </section>
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
                  {dest.description && (
                    <p>
                      <strong>Description:</strong>{" "}
                      {dest.description.length > 150
                        ? dest.description.substring(0, 150) + "..."
                        : dest.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
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
