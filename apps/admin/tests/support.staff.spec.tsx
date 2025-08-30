import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { SupportStaff } from '../src/pages/SupportStaff';

vi.mock('../src/diagnostics', () => ({ collectDiagnostics: () => ({}) }));

describe('Support staff UI', () => {
  beforeEach(() => {
    (global.fetch as any) = vi.fn(async (url: any, opts: any) => {
      if (typeof url === 'string' && url.startsWith('/staff/support?')) {
        return {
          ok: true,
          json: async () => ({ data: [{ id: '1', subject: 'Bug', tenant: 'demo', status: 'open', updated_at: 'now' }] }),
        } as any;
      }
      if (url === '/staff/support/1') {
        return {
          ok: true,
          json: async () => ({ data: { id: '1', subject: 'Bug', tenant: 'demo', status: 'open', messages: [] } }),
        } as any;
      }
      if (url === '/staff/support/1/reply') {
        return { ok: true, json: async () => ({}) } as any;
      }
      if (url === '/staff/support/1/close') {
        return { ok: true, json: async () => ({}) } as any;
      }
      return { ok: true, json: async () => ({ data: [] }) } as any;
    });
  });

  test('filter, open, reply, close and canned reply', async () => {
    render(
      <MemoryRouter>
        <SupportStaff />
      </MemoryRouter>
    );
    await screen.findByText('Bug');
    await userEvent.selectOptions(screen.getByRole('combobox'), 'open');
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledWith('/staff/support?status=open'));
    await userEvent.click(screen.getByText('1'));
    await screen.findByText('Close');
    await screen.findByText('Getting Started');
    await userEvent.click(screen.getByText('Getting Started'));
    const boxes = screen.getAllByRole('textbox');
    const box = boxes[boxes.length - 1];
    await userEvent.type(box, ' hi');
    await userEvent.click(screen.getByText('Send'));
    const call = (fetch as any).mock.calls.find((c: any[]) => c[0] === '/staff/support/1/reply');
    expect(JSON.parse(call[1].body).message).toContain('Getting Started');
    await userEvent.click(screen.getByText('Close'));
    expect(fetch).toHaveBeenCalledWith('/staff/support/1/close', expect.anything());
  });
});
