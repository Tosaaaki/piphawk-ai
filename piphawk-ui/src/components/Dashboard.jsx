import React from 'react';
import styled from 'styled-components';
import { colors, shadows } from '../theme';

const Container = styled.div`
  padding: 2rem;
  color: ${colors.text};
  background: ${colors.background};
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  @media (min-width: 768px) {
    grid-template-columns: 1fr 1fr;
  }
`;

const Header = styled.h1`
  margin-bottom: 1.5rem;
  color: ${colors.accentGreen};
  text-shadow: 0 0 6px ${colors.accentGreen};
  grid-column: 1 / -1;
`;

const Card = styled.div`
  background: ${colors.cardBackground};
  box-shadow: ${shadows.card};
  border: 1px solid ${colors.accentCyan};
  border-radius: 8px;
  padding: 1rem;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  th, td {
    padding: 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
  }
  th {
    text-align: left;
    color: ${colors.accentCyan};
  }
`;

const ChartPlaceholder = styled.div`
  height: 300px;
  background: ${colors.background};
  border: 1px dashed ${colors.accentCyan};
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${colors.accentCyan};
`;

const Dashboard = ({ trades = [], wins = 0, losses = 0 }) => {
  const winRate = wins + losses ? ((wins / (wins + losses)) * 100).toFixed(2) : '0';
  return (
    <Container>
      <Header>PipHawk Dashboard</Header>
      <Card>
        <Table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Close Time</th>
              <th>Instrument</th>
              <th>Price</th>
              <th>P/L</th>
            </tr>
          </thead>
          <tbody>
            {trades.map(t => (
              <tr key={t.id}>
                <td>{t.id}</td>
                <td>{t.closeTime}</td>
                <td>{t.instrument}</td>
                <td>{t.price}</td>
                <td>{t.profit}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <Card>
        Wins: {wins}, Losses: {losses}, Win Rate: {winRate}%
      </Card>
      <Card>
        <ChartPlaceholder>Line Chart Placeholder</ChartPlaceholder>
      </Card>
    </Container>
  );
};

export default Dashboard;
