import React from 'react';
import styled from 'styled-components';
import { colors, shadows } from '../theme';
import TradesTable from './TradesTable';
import PanicButton from './PanicButton';

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

const ChartPlaceholder = styled.div`
  height: 300px;
  background: ${colors.background};
  border: 1px dashed ${colors.accentCyan};
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${colors.accentCyan};
`;

const Dashboard = () => {
  return (
    <Container>
      <Header>
        PipHawk Dashboard
        <div style={{ float: 'right' }}><PanicButton /></div>
      </Header>
      <Card>
        <TradesTable />
      </Card>
      <Card>
        <ChartPlaceholder>Line Chart Placeholder</ChartPlaceholder>
      </Card>
    </Container>
  );
};

export default Dashboard;
