import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('@neo/api', () => ({
  getCategories: vi.fn(),
  createCategory: vi.fn(),
  getItems: vi.fn(),
  updateItem: vi.fn(),
  exportMenuI18n: vi.fn()
}));

import { MenuEditor } from './MenuEditor';
import {
  getCategories as mockGetCategories,
  createCategory as mockCreateCategory,
  getItems as mockGetItems,
  updateItem as mockUpdateItem,
  exportMenuI18n as mockExportMenuI18n
} from '@neo/api';

describe('MenuEditor', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  test('Create category → appears in list', async () => {
    mockGetCategories.mockResolvedValueOnce([]);
    mockGetItems.mockResolvedValueOnce([]);
    mockCreateCategory.mockResolvedValueOnce({ id: '1', name: 'New Category' });
    render(<MenuEditor />);
    await userEvent.click(await screen.findByText('Add Category'));
    expect(await screen.findByText('New Category')).toBeInTheDocument();
  });

  test('Update item price persists', async () => {
    mockGetCategories.mockResolvedValueOnce([{ id: 'c1', name: 'Cat' }]);
    mockGetItems.mockResolvedValueOnce([
      { id: 'i1', name: 'Tea', price: 10, categoryId: 'c1', name_i18n: { en: 'Tea' } }
    ]);
    mockUpdateItem.mockResolvedValue({});
    render(<MenuEditor />);
    const input = await screen.findByLabelText('price-i1');
    fireEvent.change(input, { target: { value: '15' } });
    expect(mockUpdateItem).toHaveBeenLastCalledWith('i1', { price: 15 });
    expect((input as HTMLInputElement).value).toBe('15');
  });

  test("i18n tab save updates name_i18n['hi']", async () => {
    mockGetCategories.mockResolvedValueOnce([{ id: 'c1', name: 'Cat' }]);
    mockGetItems.mockResolvedValueOnce([
      { id: 'i1', name: 'Tea', price: 10, categoryId: 'c1', name_i18n: { en: 'Tea' } }
    ]);
    mockUpdateItem.mockResolvedValue({});
    render(<MenuEditor />);
    await userEvent.click(await screen.findByText('Edit'));
    await userEvent.click(screen.getByText('HI'));
    const nameInput = screen.getByLabelText('name-hi');
    await userEvent.type(nameInput, 'चाय');
    await userEvent.click(screen.getByText('Save'));
    expect(mockUpdateItem).toHaveBeenCalledWith('i1', {
      name_i18n: { en: 'Tea', hi: 'चाय' }
    });
  });

  test('CSV export called with selected langs', async () => {
    mockGetCategories.mockResolvedValueOnce([]);
    mockGetItems.mockResolvedValueOnce([]);
    mockExportMenuI18n.mockResolvedValue({});
    render(<MenuEditor />);
    const [en] = screen.getAllByLabelText('lang-en');
    const [hi] = screen.getAllByLabelText('lang-hi');
    await userEvent.click(en);
    await userEvent.click(hi);
    const button = screen.getAllByText('Export CSV')[0];
    await userEvent.click(button);
    expect(mockExportMenuI18n).toHaveBeenCalledWith(['en', 'hi']);
  });
});
