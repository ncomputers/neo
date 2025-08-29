import { describe, test, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, cleanup, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MenuEditor } from './MenuEditor';
import * as api from '@neo/api';

vi.mock('react-router-dom', async () => {
  const actual: any = await vi.importActual('react-router-dom');
  return {
    ...actual,
    unstable_useBlocker: () => ({ state: 'unblocked', proceed: vi.fn(), reset: vi.fn() })
  };
});

vi.mock('@neo/api', () => ({
  getCategories: vi.fn(),
  createCategory: vi.fn(),
  getItems: vi.fn(),
  updateItem: vi.fn(),
  exportMenuI18n: vi.fn(),
  useLicenseStatus: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('MenuEditor', () => {
  beforeEach(() => {
    (api.useLicenseStatus as any).mockReturnValue({ data: { status: 'ACTIVE' } });
  });

  test('Creating a category renders it in the category list', async () => {
    render(<MenuEditor />);
    await userEvent.click(screen.getByText('Add Category'));
    expect(screen.getByDisplayValue('New Category')).toBeInTheDocument();
  });

  test("Updating an item's price persists after save", async () => {
    render(<MenuEditor />);
    await userEvent.click(screen.getByText('Add Item'));
    const priceInput = screen.getByDisplayValue('0') as HTMLInputElement;
    await userEvent.clear(priceInput);
    await userEvent.type(priceInput, '99');
    await userEvent.click(screen.getByText('Save'));
    expect(priceInput).toHaveValue(99);
    expect(screen.getByText('Save')).toBeDisabled();
  });

  test('disables save when license expired', async () => {
    (api.useLicenseStatus as any).mockReturnValue({ data: { status: 'EXPIRED' } });
    render(<MenuEditor />);
    await userEvent.click(screen.getByText('Add Item'));
    expect(screen.getByText('Save')).toBeDisabled();
  });

  test('Editing hi tab updates name_i18n["hi"]', async () => {
    render(<MenuEditor />);
    await userEvent.click(screen.getByText('Add Item'));
    const row = screen.getAllByRole('row')[1];
    const nameCell = within(row).getAllByRole('cell')[1];
    await userEvent.click(nameCell);
    await userEvent.click(screen.getByRole('button', { name: 'HI' }));
    const nameInput = screen.getByPlaceholderText('Name') as HTMLInputElement;
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Namaste');
    await userEvent.click(screen.getByRole('button', { name: 'EN' }));
    await userEvent.click(screen.getByRole('button', { name: 'HI' }));
    expect(screen.getByPlaceholderText('Name')).toHaveValue('Namaste');
  });

  test('Export button calls exportMenuI18n with selected languages', async () => {
    render(<MenuEditor />);
    await userEvent.click(screen.getByLabelText('EN'));
    await userEvent.click(screen.getByLabelText('HI'));
    await userEvent.click(screen.getByText('Export'));
    expect(api.exportMenuI18n).toHaveBeenCalledWith(['en', 'hi']);
  });
});
