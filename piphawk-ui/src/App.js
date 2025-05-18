import React, { useState, useEffect } from 'react';
import { ThemeProvider } from 'styled-components';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import { colors, shadows } from './theme';

// --- runtime settings state -------------------------
const API_URL = process.env.REACT_APP_API_URL;

function App() {
  // ── front‑end state that mirrors backend /settings/runtime ──────────
  const [numericParams, setNumericParams] = useState([]);
  const [boolParams,    setBoolParams]    = useState([]);
  const [modelSelect,   setModelSelect]   = useState({ value: '', options: [] });

  // Fetch settings once on mount
  useEffect(() => {
    fetch(`${API_URL}/settings/runtime`)
      .then(res => res.json())
      .then(cfg => {
        // ----- map backend keys → UI spec --------------------
        setNumericParams([
          {
            key: 'ai_cooldown_open',
            label: 'AI Cool‑down (Open)',
            min: 10, max: 300,
            value: cfg.ai_cooldown_open ?? 30,
            onChange: v => patchSetting({ ai_cooldown_open: v })
          },
          {
            key: 'ai_cooldown_flat',
            label: 'AI Cool‑down (Flat)',
            min: 10, max: 600,
            value: cfg.ai_cooldown_flat ?? 60,
            onChange: v => patchSetting({ ai_cooldown_flat: v })
          },
          {
            key: 'review_sec',
            label: 'Review Interval (sec)',
            min: 10, max: 600,
            value: cfg.review_sec ?? 60,
            onChange: v => patchSetting({ review_sec: v })
          }
        ]);
        setBoolParams([]);
        setModelSelect({ value: '', options: [] });
      })
      .catch(console.error);
  }, []);

  // PATCH helper
  const patchSetting = patch =>
    fetch(`${API_URL}/settings/runtime`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    });

  return (
    <ThemeProvider theme={{ colors, shadows }}>
      <BrowserRouter>
        {/* very simple navigation */}
        <nav style={{ padding: '12px' }}>
          <Link to="/" style={{ marginRight: 12 }}>Dashboard</Link>
          <Link to="/settings">Settings</Link>
        </nav>

        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route
            path="/settings"
            element={
              <Settings
                numericParams={numericParams}
                boolParams={boolParams}
                models={modelSelect}
                onReset={() => window.location.reload()}
              />
            }
          />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
