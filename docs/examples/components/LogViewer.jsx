import React, { useState } from 'react';
import styled from 'styled-components';
import { colors, shadows } from '../theme';

const Container = styled.div`
  color: ${colors.text};
`;

const Tabs = styled.div`
  display: flex;
  margin-bottom: 1rem;
`;

const Tab = styled.button`
  flex: 1;
  padding: 0.5rem;
  background: ${props => (props.active ? colors.accentCyan : colors.cardBackground)};
  border: none;
  color: ${colors.text};
  cursor: pointer;
  &:not(:last-child) {
    margin-right: 0.5rem;
  }
`;

const LogCard = styled.pre`
  background: ${colors.logBackground};
  box-shadow: ${shadows.card};
  border-radius: 8px;
  padding: 1rem;
  max-height: 300px;
  overflow-y: auto;
  font-family: monospace;
`;

const LogViewer = ({ errors = [], trades = [] }) => {
  const [tab, setTab] = useState('errors');
  const lines = tab === 'errors' ? errors.slice(-50) : trades.slice(-50);
  return (
    <Container>
      <Tabs>
        <Tab active={tab === 'errors'} onClick={() => setTab('errors')}>Errors</Tab>
        <Tab active={tab === 'trades'} onClick={() => setTab('trades')}>Recent Trades</Tab>
      </Tabs>
      <LogCard>
        {lines.map((line, idx) => (
          <div key={idx}>{line}</div>
        ))}
      </LogCard>
    </Container>
  );
};

export default LogViewer;

