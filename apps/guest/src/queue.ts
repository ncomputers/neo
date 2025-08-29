export interface QueuedOrder {
  items: { id: string; qty: number; name: string }[];
  tip: number;
}

export function addQueuedOrder(order: QueuedOrder) {
  const existing: QueuedOrder[] = JSON.parse(localStorage.getItem('queuedOrders') || '[]');
  existing.push(order);
  localStorage.setItem('queuedOrders', JSON.stringify(existing));
}

export async function retryQueuedOrders(onSuccess?: (id: string) => void) {
  const existing: QueuedOrder[] = JSON.parse(localStorage.getItem('queuedOrders') || '[]');
  if (!existing.length) return;
  const remaining: QueuedOrder[] = [];
  for (const q of existing) {
    try {
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(q),
      });
      if (res.ok) {
        const data = await res.json();
        onSuccess?.(data.id);
      } else {
        remaining.push(q);
      }
    } catch {
      remaining.push(q);
    }
  }
  if (remaining.length) {
    localStorage.setItem('queuedOrders', JSON.stringify(remaining));
  } else {
    localStorage.removeItem('queuedOrders');
  }
}
