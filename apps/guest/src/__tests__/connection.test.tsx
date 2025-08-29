import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n';
import { PoorConnectionBanner } from '../components/PoorConnectionBanner';

describe('PoorConnectionBanner', () => {
  test('shows when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
    render(
      <I18nextProvider i18n={i18n}>
        <PoorConnectionBanner />
      </I18nextProvider>
    );
    expect(screen.getByText(/Poor connection/i)).toBeInTheDocument();
  });

  test('shows on high latency', async () => {
    jest.useFakeTimers();
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    (global.fetch as any) = jest.fn(
      () => new Promise((resolve) => setTimeout(() => resolve({}), 2100))
    );
    render(
      <I18nextProvider i18n={i18n}>
        <PoorConnectionBanner />
      </I18nextProvider>
    );
    await act(async () => {
      jest.advanceTimersByTime(2100);
    });
    expect(screen.getByText(/Poor connection/i)).toBeInTheDocument();
    jest.useRealTimers();
  });
});
