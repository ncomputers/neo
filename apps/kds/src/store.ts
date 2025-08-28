import { create } from 'zustand';

interface CounterState {
  count: number;
  inc: () => void;
}

export const useCounterStore = create<CounterState>((set) => ({
  count: 0,
  inc: () => set((s) => ({ count: s.count + 1 })),
}));
