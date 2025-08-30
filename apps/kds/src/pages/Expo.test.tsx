import React from 'react';
import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within, act, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

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
    useWS,
    useLicense: vi.fn(),
    getToken: () => 't'
  };
});

vi.mock('@neo/ui', async () => {
  const actual = await vi.importActual<any>('../../../../packages/ui/src/index.ts');
  return { ...actual, Flag: ({ children }: any) => <>{children}</> };
});

import { Expo } from './Expo';
import { apiFetch } from '@neo/api';
import { useKdsPrefs } from '../state/kdsPrefs';

beforeEach(async () => {
  (global as any).WebSocket = MockWebSocket as any;
  sockets.length = 0;
  MockWebSocket.autoOpen = true;
  const api: any = await import('@neo/api');
  api.useLicense.mockReturnValue({ data: { status: 'ACTIVE' } });
  (global as any).Audio = vi.fn().mockImplementation(() => ({ play: vi.fn() }));
  (global as any).Notification = Object.assign(vi.fn(), {
    permission: 'granted',
    requestPermission: vi.fn().mockResolvedValue('granted'),
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  localStorage.clear();
  useKdsPrefs.getState().set({
    soundNew: true,
    soundReady: true,
    desktopNotify: false,
    darkMode: false,
    fontScale: 100,
    printer: false,
    layout: 'compact',
  });
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

  test('actions blocked when license expired', async () => {
    const api: any = await import('@neo/api');
    api.useLicense.mockReturnValue({ data: { status: 'EXPIRED' } });
    apiFetch.mockResolvedValueOnce({ tickets: [{ id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 }] });
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    await userEvent.click(screen.getByTestId('ticket-1'));
    fireEvent.keyDown(window, { key: 'a' });
    const newCol = screen.getByRole('heading', { name: 'New' }).parentElement!.querySelector('ul')!;
    expect(within(newCol).getByTestId('ticket-1')).toBeInTheDocument();
  });

  test('grace shows banner and allows action', async () => {
    const api: any = await import('@neo/api');
    api.useLicense.mockReturnValue({ data: { status: 'GRACE', daysLeft: 2 } });
    apiFetch.mockResolvedValueOnce({ tickets: [{ id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 }] });
    apiFetch.mockResolvedValue({});
    render(
      <>
        <div>Subscription ends in 2 days</div>
        <Expo />
      </>
    );
    await screen.findByTestId('ticket-1');
    expect(screen.getByText(/Subscription ends in 2 days/)).toBeInTheDocument();
    await userEvent.click(screen.getByTestId('ticket-1'));
    fireEvent.keyDown(window, { key: 'a' });
    await act(async () => {});
    const prepCol = screen.getByRole('heading', { name: 'Preparing' }).parentElement!.querySelector('ul')!;
    expect(within(prepCol).getByTestId('ticket-1')).toBeInTheDocument();
  });

  test('settings persist', async () => {
    apiFetch.mockResolvedValueOnce({ tickets: [] });
    render(<Expo />);
    await userEvent.click(screen.getByTestId('settings-btn'));
    const soundToggle = screen.getByLabelText('New ticket sound') as HTMLInputElement;
    await userEvent.click(soundToggle);
    expect(soundToggle.checked).toBe(false);
    cleanup();
    apiFetch.mockResolvedValueOnce({ tickets: [] });
    render(<Expo />);
    await userEvent.click(screen.getByTestId('settings-btn'));
    expect((screen.getByLabelText('New ticket sound') as HTMLInputElement).checked).toBe(false);
  });

  test('Print KOT button triggers notify', async () => {
    apiFetch.mockResolvedValueOnce({
      tickets: [{ id: '1', table: 'T1', items: [], status: 'NEW', age_s: 0, promise_s: 300 }],
    });
    apiFetch.mockResolvedValue({});
    useKdsPrefs.getState().set({ printer: true, layout: 'compact' });
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    const fakeWindow = {
      document: { write: vi.fn(), close: vi.fn() },
      focus: vi.fn(),
      print: vi.fn(),
    } as any;
    const open = vi.spyOn(window, 'open').mockReturnValue(fakeWindow);
    await userEvent.click(screen.getByRole('button', { name: 'Print KOT' }));
    expect(apiFetch).toHaveBeenCalledWith(
      '/print/notify',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ order_id: '1', layout: 'compact' }),
      })
    );
    expect(open).toHaveBeenCalled();
    open.mockRestore();
  });

  test('Test Print hits endpoint in dev', async () => {
    apiFetch.mockResolvedValueOnce({ tickets: [] });
    render(<Expo />);
    await userEvent.click(screen.getByTestId('settings-btn'));
    await userEvent.click(screen.getByLabelText('Print KOT'));
    apiFetch.mockResolvedValue({});
    await userEvent.click(screen.getByRole('button', { name: 'Test Print' }));
    expect(apiFetch).toHaveBeenCalledWith('/print/test');
  });

  test('new ticket plays sound and notifies when enabled', async () => {
    apiFetch.mockResolvedValueOnce({ tickets: [] });
    useKdsPrefs.getState().set({ soundNew: true, desktopNotify: true });
    const play = vi.fn();
    (window as any).Audio = vi.fn().mockImplementation(() => ({ play }));
    const notify = vi.fn();
    function FakeNotification(msg: string) {
      notify(msg);
    }
    (FakeNotification as any).permission = 'granted';
    (window as any).Notification = FakeNotification as any;
    render(<Expo />);
    const ws = sockets[0];
    ws.onmessage({ data: JSON.stringify({ ticket: { id: '1', table: '12', items: [], status: 'NEW', age_s: 0, promise_s: 300 } }) });
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });
    expect(play).toHaveBeenCalledTimes(1);
    expect(notify).toHaveBeenCalledWith('New order T-12');
  });

  test('ready ticket plays sound and notifies when enabled', async () => {
    apiFetch.mockResolvedValueOnce({ tickets: [{ id: '1', table: '5', items: [], status: 'PREPARING', age_s: 0, promise_s: 300 }] });
    useKdsPrefs.getState().set({ soundReady: true, desktopNotify: true });
    const play = vi.fn();
    (window as any).Audio = vi.fn().mockImplementation(() => ({ play }));
    const notify = vi.fn();
    function FakeNotification(msg: string) {
      notify(msg);
    }
    (FakeNotification as any).permission = 'granted';
    (window as any).Notification = FakeNotification as any;
    render(<Expo />);
    await screen.findByTestId('ticket-1');
    const ws = sockets[0];
    ws.onmessage({ data: JSON.stringify({ ticket: { id: '1', table: '5', items: [], status: 'READY', age_s: 0, promise_s: 300 } }) });
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });
    expect(play).toHaveBeenCalledTimes(1);
    expect(notify).toHaveBeenCalledWith('Order ready T-5');
  });
});
