import React from 'react';
import { ThemeProvider } from 'styled-components';
import Dashboard from './components/Dashboard';
import { colors, shadows } from './theme';

function App() {
  return (
    <ThemeProvider theme={{ colors, shadows }}>
      <div className="App">
        <Dashboard />
      </div>
    </ThemeProvider>
  );
}

export default App;