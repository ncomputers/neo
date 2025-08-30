import { apiFetch } from '@neo/api';
import { Flag } from '@neo/ui';
import { useKdsPrefs } from '../state/kdsPrefs';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function SettingsDrawer({ open, onClose }: Props) {
  const {
    soundNew,
    soundReady,
    desktopNotify,
    darkMode,
    fontScale,
    printer,
    layout,
    set,
  } = useKdsPrefs();

  if (!open) return null;

  const onDesktopToggle = async (checked: boolean) => {
    if (checked) {
      if (typeof Notification !== 'undefined') {
        const perm = await Notification.requestPermission();
        if (perm === 'granted') set({ desktopNotify: true });
      }
    } else {
      set({ desktopNotify: false });
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex justify-end" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-700 p-4 space-y-2 w-64"
        onClick={(e) => e.stopPropagation()}
      >
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={soundNew}
            onChange={(e) => set({ soundNew: e.target.checked })}
          />
          <span>New ticket sound</span>
        </label>
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={soundReady}
            onChange={(e) => set({ soundReady: e.target.checked })}
          />
          <span>Ready sound</span>
        </label>
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={desktopNotify}
            onChange={(e) => onDesktopToggle(e.target.checked)}
          />
          <span>Desktop notifications</span>
        </label>
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={darkMode}
            onChange={(e) => set({ darkMode: e.target.checked })}
          />
          <span>Dark mode</span>
        </label>
        <label className="flex items-center space-x-2">
          <span>Font</span>
          <input
            type="range"
            min={90}
            max={130}
            value={fontScale}
            onChange={(e) => set({ fontScale: parseInt(e.target.value) })}
          />
          <span>{fontScale}%</span>
        </label>
        <Flag name="kds_print">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={printer}
              onChange={(e) => set({ printer: e.target.checked })}
            />
            <span>Print KOT</span>
          </label>
          {printer && (
            <div className="flex items-center space-x-2">
              <span>Layout</span>
              <select
                value={layout}
                onChange={(e) => set({ layout: e.target.value as 'compact' | 'full' })}
                className="border p-1 rounded"
              >
                <option value="compact">Compact</option>
                <option value="full">Full</option>
              </select>
            </div>
          )}
          {printer && import.meta.env.MODE !== 'production' && (
            <button
              onClick={() =>
                apiFetch('/print/test').catch(() => {
                  /* ignore */
                })
              }
              className="border px-2 py-1 rounded"
            >
              Test Print
            </button>
          )}
        </Flag>
      </div>
    </div>
  );
}
