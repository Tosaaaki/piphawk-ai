import React, { useState } from 'react';
import Button from '@mui/material/Button';

const API_URL = process.env.REACT_APP_API_URL;

const PanicButton = () => {
  const [loading, setLoading] = useState(false);

  const handleClick = () => {
    setLoading(true);
    fetch(`${API_URL}/control/panic_stop`, { method: 'POST' })
      .finally(() => setLoading(false));
  };

  return (
    <Button
      variant="contained"
      color="error"
      onClick={handleClick}
      disabled={loading}
    >
      {loading ? 'Stopping...' : 'Emergency Stop'}
    </Button>
  );
};

export default PanicButton;
