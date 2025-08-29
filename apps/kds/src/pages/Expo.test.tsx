import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within, act, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Expo } from './Expo';
import { apiFetch } from '@neo/api';

const sockets: any[] = [];
class MockWebSocket {
  static autoOpen = true;
  onopen: ((ev: any) => void) | null = null;
  onmessage: ((ev: any) => void) | null = null;
  onclose: ((ev: any) => void) | null = null;
  constructor(public url: string) {
    sockets.push(this);
    if (MockWebSocket.autoOpen) {
      setTimeout(() => this.onopen?.({}), 0);
    }
  }
  send() {}
  close() {
    this.onclose?.({});
  }
}

vi.mock('@neo/api', async () => {
  const { useWS } = await vi.importActual<any>('../../../../packages/api/src/hooks/ws.ts');
  return {
    apiFetch: vi.fn(),
    useWS
  };
});

beforeEach(() => {
  (global as any).WebSocket = MockWebSocket as any;
  sockets.length = 0;
  MockWebSocket.autoOpen = true;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('Expo', () => {
  test('WS message updates a ticket', async () => {
    apiFetch.mockResolvedValueOnce({ tickets: [{ id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 }] });
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    // initially in New column
    const newCol = screen.getByRole('heading', { name: 'New' }).parentElement!.querySelector('ul')!;
    expect(within(newCol).getByTestId('ticket-1')).toBeInTheDocument();
    const ws = sockets[0];
    ws.onmessage({ data: JSON.stringify({ ticket: { id: '1', table: 'T1', items: [], status: 'READY', age_s: 0, promise_s: 300 } }) });
    await act(async () => {});
    const readyCol = screen.getByRole('heading', { name: 'Ready' }).parentElement!.querySelector('ul')!;
    expect(within(readyCol).getByTestId('ticket-1')).toBeInTheDocument();
  });

  test('Keyboard Accept moves ticket to next column', async () => {
    apiFetch.mockResolvedValueOnce({ tickets: [{ id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 }] });
    apiFetch.mockResolvedValue({});
    sessionStorage.setItem('token', 't');
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    const ticket = screen.getByTestId('ticket-1');
    await userEvent.click(ticket);
    fireEvent.keyDown(window, { key: 'a' });
    await act(async () => {});
    const prepCol = screen.getByRole('heading', { name: 'Preparing' }).parentElement!.querySelector('ul')!;
    expect(within(prepCol).getByTestId('ticket-1')).toBeInTheDocument();
  });

  test('Offline banner appears when WS closed', async () => {
    apiFetch.mockResolvedValueOnce({ tickets: [] });
    apiFetch.mockResolvedValue({ tickets: [] });
    render(<Expo offlineMs={0} />);
    await act(async () => {});
    MockWebSocket.autoOpen = false;
    const ws = sockets[0];
    await act(async () => {
      ws.close();
    });
    await screen.findByTestId('offline');
  });

  test('Status filter shows only selected tickets', async () => {
    apiFetch.mockResolvedValueOnce({
      tickets: [
        { id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 },
        { id: '2', table: 'T2', items: [], status: 'READY', age_s: 0, promise_s: 300 }
      ]
    });
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    await screen.findByTestId('ticket-2');
    await userEvent.click(screen.getByRole('button', { name: 'Ready' }));
    expect(screen.queryByTestId('ticket-1')).not.toBeInTheDocument();
    expect(screen.getByTestId('ticket-2')).toBeInTheDocument();
  });

  test('Zone filter narrows tickets', async () => {
    apiFetch.mockResolvedValueOnce({
      tickets: [
        { id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300, zone: 'A' },
        { id: '2', table: 'T2', items: [], status: 'NEW', age_s: 0, promise_s: 300, zone: 'B' }
      ]
    });
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    await screen.findByTestId('ticket-2');
    await userEvent.selectOptions(screen.getByRole('combobox'), 'A');
    expect(screen.getByTestId('ticket-1')).toBeInTheDocument();
    expect(screen.queryByTestId('ticket-2')).not.toBeInTheDocument();
  });

  test('Search query filters tickets', async () => {
    apiFetch.mockResolvedValueOnce({
      tickets: [
        { id: '1', table: 'T1', items: [{ qty: 1, name: 'Burger' }], status: 'NEW', age_s: 0, promise_s: 300 },
        { id: '2', table: 'T2', items: [{ qty: 1, name: 'Fries' }], status: 'NEW', age_s: 0, promise_s: 300 }
      ]
    });
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    await screen.findByTestId('ticket-2');
    await userEvent.type(screen.getByPlaceholderText('Search'), 'Fries');
    expect(screen.queryByTestId('ticket-1')).not.toBeInTheDocument();
    expect(screen.getByTestId('ticket-2')).toBeInTheDocument();
  });

  test('Arrow keys move focus between tickets', async () => {
    apiFetch.mockResolvedValueOnce({
      tickets: [
        { id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 },
        { id: '2', table: 'T2', items: [], status: 'NEW', age_s: 0, promise_s: 300 },
        { id: '3', table: 'T3', items: [], status: 'PREPARING', age_s: 0, promise_s: 300 },
        { id: '4', table: 'T4', items: [], status: 'PREPARING', age_s: 0, promise_s: 300 }
      ]
    });
    render(<Expo />);
    await screen.findByTestId('ticket-4');
    const t1 = screen.getByTestId('ticket-1');
    await userEvent.click(t1);
    await act(async () => {
      fireEvent.keyDown(window, { key: 'ArrowDown' });
    });
    expect(screen.getByTestId('ticket-2')).toHaveClass('ring-2');
    await act(async () => {
      fireEvent.keyDown(window, { key: 'ArrowRight' });
    });
    expect(screen.getByTestId('ticket-4')).toHaveClass('ring-2');
    await act(async () => {
      fireEvent.keyDown(window, { key: 'ArrowUp' });
    });
    expect(screen.getByTestId('ticket-3')).toHaveClass('ring-2');
    await act(async () => {
      fireEvent.keyDown(window, { key: 'ArrowLeft' });
    });
    expect(screen.getByTestId('ticket-1')).toHaveClass('ring-2');
  });

  test('Enter key opens ticket detail', async () => {
    apiFetch.mockResolvedValueOnce({
      tickets: [{ id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 }]
    });
    const original = window.location;
    const assign = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { ...original, assign },
      writable: true,
    });
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    await userEvent.click(screen.getByTestId('ticket-1'));
    fireEvent.keyDown(window, { key: 'Enter' });
    expect(assign).toHaveBeenCalledWith('/kds/tickets/1');
    Object.defineProperty(window, 'location', { value: original });
  });
});
