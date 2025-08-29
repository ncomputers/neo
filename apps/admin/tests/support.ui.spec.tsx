import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../src/diagnostics', () => ({ collectDiagnostics: () => ({}) }));
import { Support } from '../src/pages/Support';

describe('Support UI', () => {
  beforeEach(() => {
    (global.fetch as any) = vi.fn(async (url: any, opts: any) => {
      if (url === '/support/tickets' && opts?.method === 'POST') {
        return { ok: true, json: async () => ({ data: { id: '1' } }) } as any;
      }
      if (url === '/support/tickets') {
        return { ok: true, json: async () => ({ data: [{ id: '1', subject: 'Bug' }] }) } as any;
      }
      if (url === '/support/tickets/1') {
        return { ok: true, json: async () => ({ data: { id: '1', subject: 'Bug', messages: [{ id: 'm1', author: 'owner', body: 'Issue' }] } }) } as any;
      }
      if (url === '/support/tickets/1/reply') {
        return { ok: true, json: async () => ({ data: { status: 'sent' } }) } as any;
      }
      if (url === '/support/feedback') {
        return { ok: true, json: async () => ({}) } as any;
      }
      return { ok: true, json: async () => ({}) } as any;
    });
  });

  test('create ticket, reply thread, render FAQ', async () => {
    render(
      <MemoryRouter>
        <Support />
      </MemoryRouter>
    );
    await screen.findAllByText('Getting Started');
    await userEvent.click(screen.getByText('CONTACT'));
    await userEvent.type(screen.getByPlaceholderText('Subject'), 'Bug');
    await userEvent.type(screen.getByPlaceholderText('Message'), 'Issue');
    await userEvent.click(screen.getByText('Submit'));
    await screen.findByText('Bug');
    await userEvent.click(screen.getByText('Bug'));
    await screen.findByText('Issue');
    await userEvent.type(screen.getByPlaceholderText('Reply'), 'Thanks');
    await userEvent.click(screen.getByText('Send'));
    expect(fetch).toHaveBeenCalledWith('/support/tickets/1/reply', expect.anything());
  });
});
