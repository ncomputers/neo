import { useEffect, useState, Fragment } from 'react';
import { Button, Toaster, toast } from '@neo/ui';
import {
  getCategories,
  createCategory,
  getItems,
  updateItem,
  exportMenuI18n,
  Category,
  Item
} from '@neo/api';

const LANGS = ['en', 'hi'];

export function MenuEditor() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [selectedCat, setSelectedCat] = useState<string>('');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [exportLangs, setExportLangs] = useState<string[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    getCategories().then((c) => {
      setCategories(c);
      if (c.length) setSelectedCat(c[0].id);
    });
    getItems().then(setItems);
  }, []);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const catItems = items.filter((i) => i.categoryId === selectedCat);

  function addCategory() {
    createCategory({ name: 'New Category' }).then((cat) => {
      setCategories((prev) => [...prev, cat]);
      setSelectedCat(cat.id);
      toast('Category created');
    });
  }

  function changePrice(id: string, price: number) {
    const p = isNaN(price) ? 0 : price;
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, price: p } : it)));
    setDirty(true);
    Promise.resolve(updateItem(id, { price: p })).catch((e) => toast(e.message));
  }

  function changeName(id: string, lang: string, value: string) {
    setItems((prev) =>
      prev.map((it) =>
        it.id === id ? { ...it, name_i18n: { ...(it.name_i18n || {}), [lang]: value } } : it
      )
    );
    setDirty(true);
  }

  function saveItem(it: Item) {
    Promise.resolve(updateItem(it.id, { name_i18n: it.name_i18n })).then(() => {
      toast('Item saved');
      setDirty(false);
    });
  }

  function exportCsv() {
    exportMenuI18n(exportLangs).then(() => toast('Export started'));
  }

  return (
    <div className="flex gap-4">
      <Toaster />
      <div>
        <h2>Categories</h2>
        <ul>
          {categories.map((c) => (
            <li key={c.id}>
              <button onClick={() => setSelectedCat(c.id)}>{c.name}</button>
            </li>
          ))}
        </ul>
        <Button onClick={addCategory}>Add Category</Button>
      </div>
      <div className="flex-1">
        <h2>Items</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Price</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {catItems.map((it) => (
              <Fragment key={it.id}>
                <tr>
                  <td>{it.name_i18n?.en || it.name}</td>
                  <td>
                    <input
                      aria-label={`price-${it.id}`}
                      type="number"
                      value={it.price}
                      onChange={(e) => changePrice(it.id, parseFloat(e.target.value))}
                    />
                  </td>
                  <td>
                    <Button onClick={() => setExpanded(expanded === it.id ? null : it.id)}>
                      Edit
                    </Button>
                  </td>
                </tr>
                {expanded === it.id && (
                  <tr>
                    <td colSpan={3}>
                      <ItemForm
                        item={it}
                        onChange={(lang, val) => changeName(it.id, lang, val)}
                        onSave={() => saveItem(it)}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
        <div className="mt-4">
          {LANGS.map((l) => (
            <label key={l} className="mr-2">
              <input
                type="checkbox"
                value={l}
                aria-label={`lang-${l}`}
                checked={exportLangs.includes(l)}
                onChange={(e) =>
                  setExportLangs((s) =>
                    e.target.checked ? [...s, l] : s.filter((x) => x !== l)
                  )
                }
              />
              {l}
            </label>
          ))}
          <Button onClick={exportCsv}>Export CSV</Button>
        </div>
      </div>
    </div>
  );
}

interface ItemFormProps {
  item: Item;
  onChange: (lang: string, value: string) => void;
  onSave: () => void;
}

function ItemForm({ item, onChange, onSave }: ItemFormProps) {
  const [lang, setLang] = useState<string>('en');
  return (
    <div>
      <div className="mb-2">
        {LANGS.map((l) => (
          <Button
            key={l}
            onClick={() => setLang(l)}
            className={lang === l ? 'bg-blue-600 text-white' : ''}
          >
            {l.toUpperCase()}
          </Button>
        ))}
      </div>
      <input
        aria-label={`name-${lang}`}
        className="border p-1"
        value={item.name_i18n?.[lang] || ''}
        onChange={(e) => onChange(lang, e.target.value)}
      />
      <Button onClick={onSave} className="ml-2">
        Save
      </Button>
    </div>
  );
}

export default MenuEditor;
