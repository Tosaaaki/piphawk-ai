import React, { useEffect, useState } from 'react';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Modal, Box } from '@mui/material';
import { colors } from '../theme';

const API_URL = process.env.REACT_APP_API_URL;

const modalStyle = {
  position: 'absolute' as const,
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  backgroundColor: colors.cardBackground,
  border: `1px solid ${colors.accentCyan}`,
  padding: '1rem',
  color: colors.text,
  maxHeight: '80vh',
  overflow: 'auto',
};

interface TradeRow {
  trade_id: number;
  instrument: string;
  open_time: string;
  close_time: string;
  open_price: number;
  close_price: number;
  units: number;
  realized_pl: number;
  state: string;
  tp_price?: number;
  sl_price?: number;
}

const columns: GridColDef[] = [
  { field: 'trade_id', headerName: 'ID', width: 80 },
  { field: 'close_time', headerName: 'Close Time', width: 170 },
  { field: 'instrument', headerName: 'Instrument', width: 130 },
  { field: 'close_price', headerName: 'Price', width: 90 },
  { field: 'realized_pl', headerName: 'P/L', width: 90 },
];

const TradesTable = () => {
  const [rows, setRows] = useState<TradeRow[]>([]);
  const [selected, setSelected] = useState<TradeRow | null>(null);

  const fetchTrades = () => {
    fetch(`${API_URL}/trades/recent?limit=100`)
      .then(res => res.json())
      .then(data => setRows(data.trades || []))
      .catch(console.error);
  };

  useEffect(() => {
    fetchTrades();
    const id = setInterval(fetchTrades, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      <div style={{ height: 400, width: '100%' }}>
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={row => row.trade_id}
          pageSizeOptions={[5, 10, 25]}
          onRowClick={params => setSelected(params.row as TradeRow)}
        />
      </div>
      <Modal open={!!selected} onClose={() => setSelected(null)}>
        <Box sx={modalStyle}>
          <pre style={{ margin: 0 }}>
            {selected && JSON.stringify(selected, null, 2)}
          </pre>
        </Box>
      </Modal>
    </>
  );
};

export default TradesTable;
