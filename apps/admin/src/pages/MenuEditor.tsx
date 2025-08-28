import { useEffect, useState } from 'react';
import {
  getCategories,
  createCategory,
  getItems,
  updateItem,
  exportI18nCSV,
  Category,
  Item
} from '@neo/api';

const LANGS = ['en', 'hi'];

export function MenuEditor() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [currentCat, setCurrentCat] = useState<string | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [editing, setEditing] = useState<Item | null>(null);
  const [lang, setLang] = useState<string>('en');
  const [exportLangs, setExportLangs] = useState<string[]>(['en']);

  useEffect(() => {
    getCategories().then((c) => {
      setCategories(c);
      if (c.length && !currentCat) {
        setCurrentCat(c[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (currentCat) {
      getItems(currentCat).then(setItems);
    }
  }, [currentCat]);

  const addCategory = async () => {
    const name = window.prompt('Category name?');
    if (!name) return;
    const cat = await createCategory({ name });
    setCategories((c) => [...c, cat]);
  };

  const saveItem = async () => {
    if (!editing) return;
    const updated = await updateItem(editing.id, editing);
    setItems((list) => list.map((i) => (i.id === updated.id ? updated : i)));
    setEditing(null);
  };

  const toggleExportLang = (l: string, on: boolean) => {
    setExportLangs((cur) =>
      on ? [...cur, l] : cur.filter((x) => x !== l)
    );
  };

  return (
    <div className="flex gap-4">
      <div className="w-1/4">
        <button onClick={addCategory}>Add Category</button>
        <ul data-testid="cat-list">
          {categories.map((c) => (
            <li key={c.id}>
              <button onClick={() => setCurrentCat(c.id)}>{c.name}</button>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex-1">
        <div className="mb-2">
          {LANGS.map((l) => (
            <label key={l} className="mr-2">
              <input
                type="checkbox"
                checked={exportLangs.includes(l)}
                onChange={(e) => toggleExportLang(l, e.target.checked)}
              />
              <span>{l}</span>
            </label>
          ))}
          <button onClick={() => exportI18nCSV(exportLangs)}>Export CSV</button>
        </div>
        <table className="w-full text-left">
          <thead>
            <tr>
              <th>Name</th>
              <th>Price</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} data-testid={`item-${it.id}`}>
                <td>{it.name_i18n?.[lang] || it.name}</td>
                <td>
                  {editing?.id === it.id ? (
                    <input
                      value={editing.price}
                      onChange={(e) =>
                        setEditing({ ...editing, price: Number(e.target.value) })
                      }
                    />
                  ) : (
                    it.price
                  )}
                </td>
                <td>
                  <button onClick={() => { setEditing({ ...it }); setLang('en'); }}>Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {editing && (
          <div className="mt-4" data-testid="edit-form">
            <div className="mb-2">
              {LANGS.map((l) => (
                <button
                  key={l}
                  onClick={() => setLang(l)}
                  data-testid={`lang-${l}`}
                  className={
                    lang === l ? 'font-bold mr-2' : 'mr-2'
                  }
                >
                  {l}
                </button>
              ))}
            </div>
            <input
              placeholder="Name"
              value={editing.name_i18n?.[lang] || ''}
              onChange={(e) =>
                setEditing({
                  ...editing,
                  name_i18n: { ...editing.name_i18n, [lang]: e.target.value }
                })
              }
            />
            <button onClick={saveItem}>Save</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default MenuEditor;

