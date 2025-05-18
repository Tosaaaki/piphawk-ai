import React from 'react';
import styled, { keyframes } from 'styled-components';
import { colors, shadows } from '../theme';

const Container = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
`;

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

const Button = styled.button`
  flex: 1;
  padding: 0.75rem 1rem;
  color: ${colors.background};
  border: none;
  border-radius: 8px;
  box-shadow: ${shadows.card};
  cursor: pointer;
  position: relative;
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const Spinner = styled.div`
  width: 16px;
  height: 16px;
  border: 2px solid ${colors.background};
  border-top-color: transparent;
  border-radius: 50%;
  animation: ${spin} 1s linear infinite;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
`;

const ContainerControls = ({ status, onStart, onStop, onRestart }) => (
  <Container>
    <Button
      style={{ background: colors.accentGreen }}
      onClick={onStart}
      disabled={status === 'starting'}
    >
      {status === 'starting' && <Spinner />}Start
    </Button>
    <Button
      style={{ background: '#E74C3C' }}
      onClick={onStop}
      disabled={status === 'stopping'}
    >
      {status === 'stopping' && <Spinner />}Stop
    </Button>
    <Button
      style={{ background: '#E67E22' }}
      onClick={onRestart}
      disabled={status === 'restarting'}
    >
      {status === 'restarting' && <Spinner />}Restart
    </Button>
  </Container>
);

export default ContainerControls;

