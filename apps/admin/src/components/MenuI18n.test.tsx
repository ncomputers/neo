import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MenuI18nImport } from './MenuI18nImport';
import { MenuI18nExport } from './MenuI18nExport';
import { toast } from '@neo/ui';

vi.mock('@neo/ui', async () => {
  const actual: any = await vi.importActual('@neo/ui');
  return {
    ...actual,
    toast: { success: vi.fn(), error: vi.fn() },
  };
});

const TENANT = 't1';

beforeEach(() => {
  (global as any).fetch = vi.fn();
  (global as any).URL.createObjectURL = vi.fn(() => 'blob:');
  (global as any).URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('Menu i18n CSV', () => {
  test('Import posts multipart and displays counts', async () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ updated_rows: 1, skipped: 2, errors: [] }),
    });
    render(<MenuI18nImport tenant={TENANT} />);
    await userEvent.click(screen.getByLabelText('EN'));
    await userEvent.click(screen.getByLabelText('HI'));
    const file = new File(['a'], 'm.csv', { type: 'text/csv' });
    const input = screen.getByTestId('i18n-import-file') as HTMLInputElement;
    await userEvent.upload(input, file);
    expect(fetch).toHaveBeenCalledWith(
      `/api/outlet/${TENANT}/menu/i18n/import?langs=en,hi`,
      expect.objectContaining({ method: 'POST', body: expect.any(FormData) })
    );
    expect(await screen.findByTestId('import-result')).toHaveTextContent('Updated: 1');
  });

  test('Export calls endpoint with langs and downloads a file', async () => {
    (fetch as any).mockResolvedValue({ ok: true, text: () => Promise.resolve('csv') });
    render(<MenuI18nExport tenant={TENANT} />);
    await userEvent.click(screen.getByLabelText('EN'));
    await userEvent.click(screen.getByLabelText('HI'));
    await userEvent.click(screen.getByText('Export CSV'));
    expect(fetch).toHaveBeenCalledWith(`/api/outlet/${TENANT}/menu/i18n/export?langs=en,hi`);
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  test('Missing lang handled gracefully', async () => {
    (fetch as any).mockResolvedValue({ ok: true, text: () => Promise.resolve('') });
    render(<MenuI18nExport tenant={TENANT} />);
    await userEvent.click(screen.getByText('Export CSV'));
    expect(fetch).not.toHaveBeenCalled();
    const t: any = toast;
    expect(t.error).toHaveBeenCalled();
  });
});
