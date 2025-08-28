import { render } from '@testing-library/react';
import { describe, expect, test, afterEach } from 'vitest';
import React from 'react';
import { ThemeProvider } from './theme';

describe('ThemeProvider', () => {
  afterEach(() => {
    document.documentElement.style.removeProperty('--color-primary');
  });

  test('updates css vars on change', () => {
    const { rerender } = render(
      <ThemeProvider theme={{ primary: '#111111', accent: '#222222' }}>
        <div />
      </ThemeProvider>
    );
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe(
      '#111111'
    );
    rerender(
      <ThemeProvider theme={{ primary: '#333333', accent: '#222222' }}>
        <div />
      </ThemeProvider>
    );
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe(
      '#333333'
    );
  });
});
