export function formatDate(d: Date) {
  return new Intl.DateTimeFormat('en-IN').format(d);
}

export function formatCurrencyINR(v: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(v);
}

export function formatGST(gst: number) {
  return `${gst.toFixed(2)}%`;
}

export function moneyToWords(amount: number) {
  return `${amount} rupees`;
}
