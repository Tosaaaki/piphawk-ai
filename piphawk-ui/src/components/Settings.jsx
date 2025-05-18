import React, { useState } from 'react';
import styled from 'styled-components';
import { colors, shadows } from '../theme';

const Container = styled.div`
  padding: 2rem;
  color: ${colors.text};
  background: ${colors.background};
  min-height: 100vh;
`;

const Header = styled.h2`
  margin-bottom: 1rem;
  color: ${colors.accentCyan};
`;

const Section = styled.div`
  margin-bottom: 2rem;
`;

const Card = styled.div`
  background: ${colors.cardBackground};
  box-shadow: ${shadows.card};
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Label = styled.label`
  margin-right: 1rem;
`;

const Slider = styled.input`
  flex: 1;
  margin-right: 1rem;
`;

const Toggle = styled.input``;

const Select = styled.select`
  width: 100%;
  padding: 0.5rem;
  background: ${colors.cardBackground};
  color: ${colors.text};
  border: none;
  box-shadow: ${shadows.card};
`;

const Button = styled.button`
  padding: 0.75rem 1.5rem;
  background: ${colors.accentCyan};
  border: none;
  color: ${colors.background};
  border-radius: 8px;
  cursor: pointer;
  &:hover {
    background: ${colors.accentGreen};
  }
`;

const Settings = ({
  numericParams = [],
  boolParams = [],
  models = { value: "", options: [], onChange: () => {} },
  onReset = () => {},
}) => {
  const [locked, setLocked] = useState({});

  const toggleLock = key => {
    setLocked(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <Container>
      <Header>Settings</Header>

      <Section>
        <h3>Parameters</h3>
        {(numericParams ?? []).map(param => (
          <Card key={param.key}>
            <Label>{param.label}</Label>
            <Slider
              type="range"
              min={param.min}
              max={param.max}
              value={param.value}
              onChange={e => param.onChange?.(Number(e.target.value))}
              disabled={locked[param.key]}
            />
            <Toggle
              type="checkbox"
              checked={!locked[param.key]}
              onChange={() => toggleLock(param.key)}
            />
          </Card>
        ))}
      </Section>

      <Section>
        <h3>Features</h3>
        {(boolParams ?? []).map(param => (
          <Card key={param.key}>
            <Label>{param.label}</Label>
            <Toggle
              type="checkbox"
              checked={param.value}
              onChange={e => param.onChange?.(e.target.checked)}
            />
          </Card>
        ))}
      </Section>

      <Section>
        <h3>Model</h3>
        <Select onChange={e => models.onChange?.(e.target.value)} value={models.value ?? ""}>
          {(models.options ?? []).map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </Select>
      </Section>

      <Button onClick={onReset}>Reset to Defaults</Button>
    </Container>
  );
};

export default Settings;
