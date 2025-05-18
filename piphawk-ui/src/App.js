import React, { useState, useEffect } from 'react';
import { ThemeProvider } from 'styled-components';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import { colors, shadows } from './theme';

// --- runtime settings state -------------------------
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function App() {
  // ── front‑end state that mirrors backend /settings ──────────
  const [numericParams, setNumericParams] = useState([]);
  const [boolParams,    setBoolParams]    = useState([]);
  const [modelSelect,   setModelSelect]   = useState({ value: '', options: [] });

  // Fetch settings once on mount
  useEffect(() => {
    fetch(`${API_URL}/settings`)
      .then(res => res.json())
      .then(cfg => {
        // ----- map backend keys → UI spec --------------------
        setNumericParams([
          {
            key: 'AI_COOLDOWN_SEC_OPEN',
            label: 'AI Cool‑down (Open)',
            min: 10, max: 300,
            value: cfg.AI_COOLDOWN_SEC_OPEN ?? 60,
            onChange: v => patchSetting({ AI_COOLDOWN_SEC_OPEN: v })
          },
          {
            key: 'POSITION_REVIEW_SEC',
            label: 'Review Interval (sec)',
            min: 10, max: 600,
            value: cfg.POSITION_REVIEW_SEC ?? 60,
            onChange: v => patchSetting({ POSITION_REVIEW_SEC: v })
          }
        ]);

        setBoolParams([
          {
            key: 'TRAIL_ENABLED',
            label: 'Trailing Stop',
            value: cfg.TRAIL_ENABLED ?? false,
            onChange: v => patchSetting({ TRAIL_ENABLED: v })
          },
          {
            key: 'HIGHER_TF_ENABLED',
            label: 'Higher‑TF Levels',
            value: cfg.HIGHER_TF_ENABLED ?? true,
            onChange: v => patchSetting({ HIGHER_TF_ENABLED: v })
          }
        ]);

        setModelSelect({
          value: cfg.AI_EXIT_MODEL ?? '',
          options: ['gpt-4o-mini', 'gpt-4o', 'gpt-4'],
          onChange: v => patchSetting({ AI_EXIT_MODEL: v })
        });
      })
      .catch(console.error);
  }, []);

  // PATCH helper
  const patchSetting = patch =>
    fetch(`${API_URL}/settings`, {
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