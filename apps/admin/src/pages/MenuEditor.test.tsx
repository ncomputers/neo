import { describe, test, expect, afterEach, vi } from 'vitest';
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
  exportMenuI18n: vi.fn().mockResolvedValue('id,en_name'),
  importMenuI18n: vi.fn(),
  uploadImage: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('MenuEditor', () => {
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

  test('Editing hi tab updates name_i18n["hi"] and saves', async () => {
    render(<MenuEditor />);
    await userEvent.click(screen.getByText('Add Item'));
    const row = screen.getAllByRole('row')[1];
    const nameCell = within(row).getAllByRole('cell')[1];
    await userEvent.click(nameCell);
    await userEvent.click(screen.getByRole('button', { name: 'HI' }));
    const nameInput = screen.getByPlaceholderText('Name') as HTMLInputElement;
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Namaste');
    await new Promise((r) => setTimeout(r, 600));
    await userEvent.click(screen.getByRole('button', { name: 'EN' }));
    await userEvent.click(screen.getByRole('button', { name: 'HI' }));
    expect(screen.getByPlaceholderText('Name')).toHaveValue('Namaste');
    expect(api.updateItem).toHaveBeenCalledWith(expect.any(String), { name_i18n: { hi: 'Namaste' } });
  });

  test('Export button calls exportMenuI18n with selected languages', async () => {
    (global as any).URL.createObjectURL = vi.fn(() => 'blob:fake');
    (global as any).URL.revokeObjectURL = vi.fn();
    render(<MenuEditor />);
    await userEvent.click(screen.getByLabelText('EN'));
    await userEvent.click(screen.getByLabelText('HI'));
    await userEvent.click(screen.getByText('Export'));
    expect(api.exportMenuI18n).toHaveBeenCalledWith(['en', 'hi']);
  });

  test('Reordering items persists after save', async () => {
    render(<MenuEditor />);
    await userEvent.click(screen.getByText('Add Item'));
    await userEvent.click(screen.getByText('Add Item'));
    let rows = screen.getAllByRole('row');
    let firstRow = rows[1];
    let secondRow = rows[2];
    await userEvent.click(within(firstRow).getAllByRole('cell')[1]);
    await userEvent.type(screen.getByPlaceholderText('Name'), 'One');
    await userEvent.click(within(firstRow).getAllByRole('cell')[1]);
    await userEvent.click(within(secondRow).getAllByRole('cell')[1]);
    await userEvent.type(screen.getByPlaceholderText('Name'), 'Two');
    await userEvent.click(within(secondRow).getAllByRole('cell')[1]);
    rows = screen.getAllByRole('row');
    secondRow = rows[2];
    await userEvent.click(within(secondRow).getByRole('button', { name: 'Move Up' }));
    await userEvent.click(screen.getByText('Save'));
    rows = screen.getAllByRole('row');
    const names = rows.slice(1,3).map((r) => within(r).getAllByRole('cell')[1].textContent);
    expect(names).toEqual(['Two', 'One']);
  });
});
