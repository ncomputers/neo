import { handleSwMessage } from '../sw-client';

test('ORDER_SYNCED redirects to track page', () => {
  const original = window.location;
  // @ts-ignore
  delete window.location;
  // @ts-ignore
  window.location = { href: '' };
  handleSwMessage(new MessageEvent('message', { data: { type: 'ORDER_SYNCED', orderId: '7' } }));
  expect(window.location.href).toBe('/track/7');
  window.location = original;
});
