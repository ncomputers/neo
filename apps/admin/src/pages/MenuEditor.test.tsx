import { describe, test, beforeEach, vi, expect } from 'vitest';
import { render, screen, within, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MenuEditor } from './MenuEditor';

const cats = [{ id: 'c1', name: 'Drinks', sort_order: 0 }];
const items = [
  {
    id: 'i1',
    category_id: 'c1',
    name: 'Tea',
    price: 10,
    active: true,
    sort_order: 0,
    name_i18n: {},
    desc_i18n: {}
  }
];

vi.mock('@neo/api', () => ({
  getCategories: vi.fn(() => Promise.resolve([...cats])),
  createCategory: vi.fn(async ({ name }: any) => {
    const cat = { id: `c${cats.length + 1}`, name, sort_order: cats.length };
    cats.push(cat);
    return cat;
  }),
  getItems: vi.fn(async (catId: string) =>
    Promise.resolve(items.filter((i) => i.category_id === catId))
  ),
  updateItem: vi.fn(async (id: string, body: any) => {
    const idx = items.findIndex((i) => i.id === id);
    items[idx] = { ...items[idx], ...body };
    return items[idx];
  }),
  exportI18nCSV: vi.fn(async () => {})
}));

beforeEach(() => {
  cats.length = 1;
  cats[0] = { id: 'c1', name: 'Drinks', sort_order: 0 };
  items.length = 1;
  items[0] = {
    id: 'i1',
    category_id: 'c1',
    name: 'Tea',
    price: 10,
    active: true,
    sort_order: 0,
    name_i18n: {},
    desc_i18n: {}
  };
  vi.clearAllMocks();
  cleanup();
});

describe('MenuEditor', () => {
  test('Create category appears in list', async () => {
    render(<MenuEditor />);
    await screen.findByText('Drinks');
    vi.spyOn(window, 'prompt').mockReturnValue('Snacks');
    await userEvent.click(screen.getByText('Add Category'));
    await screen.findByText('Snacks');
  });

  test('Update item price persists', async () => {
    render(<MenuEditor />);
    await screen.findByText('Drinks');
    const itemRow = await screen.findByTestId('item-i1');
    await userEvent.click(within(itemRow).getByText('Edit'));
    const priceInput = screen.getByDisplayValue('10');
    await userEvent.clear(priceInput);
    await userEvent.type(priceInput, '12');
    await userEvent.click(screen.getByText('Save'));
    await screen.findByText('12');
  });

  test("i18n tab save updates name_i18n['hi']", async () => {
    render(<MenuEditor />);
    await screen.findByText('Drinks');
    const itemRow = await screen.findByTestId('item-i1');
    await userEvent.click(within(itemRow).getByText('Edit'));
    await userEvent.click(screen.getByTestId('lang-hi'));
    const nameInput = screen.getByPlaceholderText('Name');
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Chai');
    await userEvent.click(screen.getByText('Save'));
    const api = await import('@neo/api');
    expect(api.updateItem).toHaveBeenCalledWith(
      'i1',
      expect.objectContaining({ name_i18n: { hi: 'Chai' } })
    );
  });

  test('CSV export called with selected langs', async () => {
    const api = await import('@neo/api');
    render(<MenuEditor />);
    await screen.findByText('Drinks');
    const hiCb = screen.getByLabelText('hi');
    await userEvent.click(hiCb);
    await userEvent.click(screen.getByText('Export CSV'));
    expect(api.exportI18nCSV).toHaveBeenCalledWith(['en', 'hi']);
  });
});

