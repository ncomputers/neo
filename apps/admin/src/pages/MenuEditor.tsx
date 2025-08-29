import { useState, useEffect, useRef } from 'react';
import { Toaster, toast, Button } from '@neo/ui';
import { updateItem as updateItemApi, uploadImage, useLicense } from '@neo/api';
import { unstable_useBlocker as useBlocker } from 'react-router-dom';
import { MenuI18nImport } from '../components/MenuI18nImport';
import { MenuI18nExport } from '../components/MenuI18nExport';
import { TENANT_ID } from '../env';

interface Category {
  id: string;
  name: string;
}

interface Item {
  id: string;
  name_i18n: Record<string, string>;
  desc_i18n: Record<string, string>;
  price: number;
  active: boolean;
  sort_order: number;
  image?: File | null;
  dietary?: string;
  allergens?: string;
  tags?: string;
}

const LANGS = ['en', 'hi'];

function useNavigationGuard(when: boolean) {
  const blocker = useBlocker(when);
  useEffect(() => {
    if (blocker.state === 'blocked') {
      const proceed = window.confirm('You have unsaved changes. Leave anyway?');
      if (proceed) blocker.proceed();
      else blocker.reset();
    }
  }, [blocker]);
}

export function MenuEditor() {
  const [categories, setCategories] = useState<Category[]>([
    { id: 'cat-1', name: 'Category 1' }
  ]);
  const [selectedCat, setSelectedCat] = useState('cat-1');
  const [catDrag, setCatDrag] = useState<number | null>(null);
  const [itemsMap, setItemsMap] = useState<Record<string, Item[]>>({
    'cat-1': []
  });
  const [itemDrag, setItemDrag] = useState<number | null>(null);
  const [selectedItems, setSelectedItems] = useState<Record<string, boolean>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [dirty, setDirty] = useState(false);
  const { data: license } = useLicense();
  const expired = license?.status === 'EXPIRED';
  const saveTimers = useRef<Record<string, number>>({});

  const items = itemsMap[selectedCat] || [];
  useNavigationGuard(dirty);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const addCategory = () => {
    const id = `cat-${Date.now()}`;
    setCategories([...categories, { id, name: 'New Category' }]);
    setItemsMap({ ...itemsMap, [id]: [] });
    setSelectedCat(id);
    setDirty(true);
  };

  const removeCategory = (id: string) => {
    const updated = categories.filter((c) => c.id !== id);
    setCategories(updated);
    const {[id]: _, ...rest} = itemsMap;
    setItemsMap(rest);
    if (selectedCat === id && updated.length) setSelectedCat(updated[0].id);
    setDirty(true);
  };

  const moveCategory = (from: number, to: number) => {
    const next = [...categories];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    setCategories(next);
    setDirty(true);
  };

  const addItem = () => {
    const id = `item-${Date.now()}`;
    const newItem: Item = {
      id,
      name_i18n: {},
      desc_i18n: {},
      price: 0,
      active: true,
      sort_order: items.length,
      image: null
    };
    setItemsMap({ ...itemsMap, [selectedCat]: [...items, newItem] });
    setDirty(true);
  };

  const updateItem = (id: string, data: Partial<Item>) => {
    const next = items.map((it) => (it.id === id ? { ...it, ...data } : it));
    setItemsMap({ ...itemsMap, [selectedCat]: next });
    setDirty(true);
    if (saveTimers.current[id]) window.clearTimeout(saveTimers.current[id]);
    saveTimers.current[id] = window.setTimeout(() => {
      updateItemApi(id, data);
    }, 500);
  };

  const deleteItem = (id: string) => {
    const item = items.find((i) => i.id === id);
    const next = items.filter((i) => i.id !== id);
    setItemsMap({ ...itemsMap, [selectedCat]: next });
    setDirty(true);
    toast('Item deleted', {
      action: {
        label: 'Undo',
        onClick: () => {
          setItemsMap({ ...itemsMap, [selectedCat]: [...next, item!].sort((a, b) => a.sort_order - b.sort_order) });
        }
      }
    });
  };

  const moveItem = (from: number, to: number) => {
    const next = [...items];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    next.forEach((it, idx) => (it.sort_order = idx));
    setItemsMap({ ...itemsMap, [selectedCat]: next });
    setDirty(true);
  };

  const toggleSelect = (id: string) => {
    setSelectedItems({ ...selectedItems, [id]: !selectedItems[id] });
  };

  const bulkActivate = (active: boolean) => {
    const next = items.map((it) =>
      selectedItems[it.id] ? { ...it, active } : it
    );
    setItemsMap({ ...itemsMap, [selectedCat]: next });
    setSelectedItems({});
    setDirty(true);
    toast.success('Items updated');
  };

  const save = () => {
    setDirty(false);
    toast.success('Changes saved');
  };

  return (
    <div className="flex h-full">
      <Toaster />
      <div className="w-1/3 p-4 border-r">
        <h2 className="mb-2 font-bold">Categories</h2>
        <ul>
          {categories.map((cat, idx) => (
            <li
              key={cat.id}
              draggable
              onDragStart={() => setCatDrag(idx)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => catDrag !== null && moveCategory(catDrag, idx)}
              className={`p-2 border mb-1 cursor-move ${selectedCat === cat.id ? 'bg-gray-100' : ''}`}
              onClick={() => setSelectedCat(cat.id)}
            >
              <div className="flex justify-between items-center">
                <input
                  value={cat.name}
                  onChange={(e) => {
                    const next = categories.map((c) =>
                      c.id === cat.id ? { ...c, name: e.target.value } : c
                    );
                    setCategories(next);
                    setDirty(true);
                  }}
                  className="flex-1 mr-2 border p-1"
                />
                <div className="space-x-1">
                  <Button
                    aria-label="Move Up"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (idx > 0) moveCategory(idx, idx - 1);
                    }}
                  >↑</Button>
                  <Button
                    aria-label="Move Down"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (idx < categories.length - 1) moveCategory(idx, idx + 1);
                    }}
                  >↓</Button>
                  <Button onClick={(e) => { e.stopPropagation(); removeCategory(cat.id); }}>×</Button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        <Button onClick={addCategory}>Add Category</Button>
      </div>
      <div className="flex-1 p-4">
        <div className="flex justify-between mb-2">
          <div className="space-x-2">
            <Button onClick={() => bulkActivate(true)}>Activate</Button>
            <Button onClick={() => bulkActivate(false)}>Deactivate</Button>
          </div>
          <Button onClick={addItem}>Add Item</Button>
        </div>
        <table className="w-full border">
          <thead>
            <tr className="border-b">
              <th className="p-1"><input type="checkbox" onChange={(e) => {
                const checked = e.target.checked;
                const sel: Record<string, boolean> = {};
                items.forEach((it) => (sel[it.id] = checked));
                setSelectedItems(sel);
              }} /></th>
              <th className="p-1">Name</th>
              <th className="p-1">Price</th>
              <th className="p-1">Active</th>
              <th className="p-1">Order</th>
              <th className="p-1">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, idx) => (
              <>
                <tr
                  key={it.id}
                  draggable
                  onDragStart={() => setItemDrag(idx)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => itemDrag !== null && moveItem(itemDrag, idx)}
                  className="border-b cursor-move"
                >
                  <td className="p-1 text-center">
                    <input
                      type="checkbox"
                      checked={!!selectedItems[it.id]}
                      onChange={() => toggleSelect(it.id)}
                    />
                  </td>
                  <td className="p-1" onClick={() => setExpanded({ ...expanded, [it.id]: !expanded[it.id] })}>{it.name_i18n.en || ''}</td>
                  <td className="p-1">
                    <input
                      type="number"
                      value={it.price}
                      onChange={(e) => updateItem(it.id, { price: parseFloat(e.target.value) })}
                      className="w-20 border p-1"
                    />
                  </td>
                  <td className="p-1 text-center">
                    <input
                      type="checkbox"
                      checked={it.active}
                      onChange={(e) => updateItem(it.id, { active: e.target.checked })}
                    />
                  </td>
                  <td className="p-1 text-center">{it.sort_order}</td>
                  <td className="p-1 text-center">
                    <div className="space-x-1">
                      <Button aria-label="Move Up" onClick={() => idx > 0 && moveItem(idx, idx - 1)}>↑</Button>
                      <Button aria-label="Move Down" onClick={() => idx < items.length - 1 && moveItem(idx, idx + 1)}>↓</Button>
                      <Button onClick={() => deleteItem(it.id)}>Delete</Button>
                    </div>
                  </td>
                </tr>
                {expanded[it.id] && (
                  <tr key={it.id + '-form'} className="border-b">
                    <td colSpan={6} className="p-2 bg-gray-50">
                      <ItemForm item={it} onChange={(data) => updateItem(it.id, data)} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
        <div className="mt-4 flex items-center space-x-4">
          <Button onClick={save} disabled={!dirty || expired} title={expired ? 'License expired' : undefined}>Save</Button>
          <div className="flex items-center space-x-4">
            <MenuI18nImport tenant={TENANT_ID || ''} />
            <MenuI18nExport tenant={TENANT_ID || ''} />
          </div>
        </div>
      </div>
    </div>
  );
}

interface ItemFormProps {
  item: Item;
  onChange: (data: Partial<Item>) => void;
}

function ItemForm({ item, onChange }: ItemFormProps) {
  const [lang, setLang] = useState<string>('en');
  const [preview, setPreview] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    onChange({ image: file });
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result as string);
    reader.readAsDataURL(file);
    setProgress(0);
    try {
      await uploadImage(item.id, file);
      setProgress(100);
    } catch {
      toast.error('Upload failed');
    }
  };

  return (
    <div>
      <div className="mb-2 space-x-2">
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
      <div className="mb-2">
        <input
          className="border p-1 w-full"
          placeholder="Name"
          value={item.name_i18n[lang] || ''}
          onChange={(e) => onChange({ name_i18n: { ...item.name_i18n, [lang]: e.target.value } })}
        />
      </div>
      <div className="mb-2">
        <textarea
          className="border p-1 w-full"
          placeholder="Description"
          value={item.desc_i18n[lang] || ''}
          onChange={(e) => onChange({ desc_i18n: { ...item.desc_i18n, [lang]: e.target.value } })}
        />
      </div>
      <div className="mb-2">
        {preview && <img src={preview} alt="preview" className="h-20 mb-2" />}
        {progress > 0 && progress < 100 && (
          <div className="w-full bg-gray-200 h-2 mb-2">
            <div className="bg-blue-600 h-2" style={{ width: `${progress}%` }} />
          </div>
        )}
        <input type="file" onChange={handleImage} />
      </div>
      <div className="mb-2">
        <input
          className="border p-1 w-full"
          placeholder="Dietary"
          value={item.dietary || ''}
          onChange={(e) => onChange({ dietary: e.target.value })}
        />
      </div>
      <div className="mb-2">
        <input
          className="border p-1 w-full"
          placeholder="Allergens"
          value={item.allergens || ''}
          onChange={(e) => onChange({ allergens: e.target.value })}
        />
      </div>
      <div>
        <input
          className="border p-1 w-full"
          placeholder="Tags"
          value={item.tags || ''}
          onChange={(e) => onChange({ tags: e.target.value })}
        />
      </div>
    </div>
  );
}

export default MenuEditor;

