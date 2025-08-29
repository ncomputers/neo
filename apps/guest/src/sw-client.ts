export function handleSwMessage(event: MessageEvent) {
  if (event.data?.type === 'ORDER_SYNCED') {
    window.location.href = `/track/${event.data.orderId}`;
  }
}
