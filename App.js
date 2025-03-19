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

    // Prepare the POST request payload
    const payload = {
      city: city,
      preferences: preferences,
      travel_mode: travelMode,
    };

    try {
      const response = await fetch("http://127.0.0.1:5000/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
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
      <h1>Travel Recommendation System</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>
            City:{" "}
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="e.g., Pune"
              required
            />
          </label>
        </div>
        <div>
          <label>
            Preferences:{" "}
            <input
              type="text"
              value={preferences}
              onChange={(e) => setPreferences(e.target.value)}
              placeholder="e.g., temple, food, trekking, shopping"
              required
            />
          </label>
        </div>
        <div>
          <label>
            Travel Mode:{" "}
            <select
              value={travelMode}
              onChange={(e) => setTravelMode(e.target.value)}
            >
              <option value="driving">Driving</option>
              <option value="walking">Walking</option>
              <option value="transit">Transit</option>
            </select>
          </label>
        </div>
        <button type="submit">Get Recommendations</button>
      </form>

      {loading && <p>Loading recommendations...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {result && (
        <div className="results">
          <h2>Weather:</h2>
          <p>{result.weather}</p>
          <h2>Destinations:</h2>
          <ul>
            {result.destinations.map((dest, index) => (
              <li key={index}>
                <strong>{dest.name}</strong> ({dest.category}) -{" "}
                {dest.travel_time || "N/A"} | Rating: {dest.rating || "N/A"}
              </li>
            ))}
          </ul>
          <h2>Events:</h2>
          <ul>
            {result.events.map((event, index) => (
              <li key={index}>
                {event.name} - {event.date || "N/A"}{" "}
                {event.url && (
                  <a href={event.url} target="_blank" rel="noopener noreferrer">
                    Details
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
