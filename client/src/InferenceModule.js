import React, { useState } from 'react';
import './InferenceModule.css';

const InferenceModule = () => {
  const [symptoms, setSymptoms] = useState('');
  const [results, setResults] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch('/api/infer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symptoms })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Inference error:', error);
    }
  };

  return (
    <div className="inference-container">
      <h1>Marine Envenomation Expert System</h1>
      <form onSubmit={handleSubmit}>
        <textarea
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
          placeholder="Enter symptoms here..."
          rows="4"
        />
        <button type="submit">Submit</button>
      </form>

      <div className="results">
        {results.map((res, i) => (
          <div className="species-card" key={i}>
            <h2>{res.common_name}</h2>
            {res.image && <img src={res.image} alt={res.common_name} className="species-image" />}
            <p><strong>Match Score:</strong> {res.match_score.toFixed(2)}%</p>
            <p><strong>Symptom:</strong> {res.symptom}</p>
            <p><strong>Onset Time:</strong> {res.onset_time}</p>
            <p><strong>Duration:</strong> {res.duration}</p>
            {res.doi_url ? (
              <p><strong>Reference:</strong> <a href={res.doi_url} target="_blank" rel="noreferrer">[Ref]</a></p>
            ) : (
              <p><strong>Reference:</strong> No reference available</p>
            )}
            {res.first_aid && (
              <div className="treatment">
                <h3>Recommended Treatment</h3>
                <p><strong>First Aid:</strong> {res.first_aid}</p>
                <p><strong>Hospital Treatment:</strong> {res.hospital_treatment}</p>
                <p><strong>Prognosis:</strong> {res.prognosis}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default InferenceModule;