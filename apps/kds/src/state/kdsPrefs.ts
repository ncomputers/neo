import { create } from 'zustand';

export interface KdsPrefs {
  soundNew: boolean;
  soundReady: boolean;
  desktopNotify: boolean;
  darkMode: boolean;
  fontScale: number; // percent
  set: (prefs: Partial<KdsPrefs>) => void;
}

const LS_KEY = 'kdsPrefs';

const load = (): Partial<KdsPrefs> => {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const prefersDark =
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-color-scheme: dark)').matches;

export const useKdsPrefs = create<KdsPrefs>((set) => {
  const stored = load();
  return {
    soundNew: stored.soundNew ?? true,
    soundReady: stored.soundReady ?? true,
    desktopNotify: stored.desktopNotify ?? false,
    darkMode: stored.darkMode ?? prefersDark,
    fontScale: stored.fontScale ?? 100,
    set: (prefs) =>
      set((state) => {
        const next = { ...state, ...prefs } as KdsPrefs;
        localStorage.setItem(
          LS_KEY,
          JSON.stringify({
            soundNew: next.soundNew,
            soundReady: next.soundReady,
            desktopNotify: next.desktopNotify,
            darkMode: next.darkMode,
            fontScale: next.fontScale,
          })
        );
        return next;
      }),
  };
});
