import { apiFetch, idempotency } from './api';

export interface MenuItem {
  id: string;
  name: string;
  price: number;
}
export function getMenu() {
  return apiFetch<MenuItem[]>('/menu');
}

export interface PlaceOrderRequest {
  items: { id: string; qty: number }[];
}
export interface PlaceOrderResponse {
  id: string;
}
export function placeOrder(body: PlaceOrderRequest) {
  return apiFetch<PlaceOrderResponse>('/orders', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    idempotencyKey: idempotency()
  });
}

export interface OrderStreamEvent {
  id: string;
  status: string;
}
export const orderStream = () => '/orders/stream';

export interface KdsTicket {
  id: string;
  table: string;
  items: string[];
}
export const kdsTickets = () => '/kds/tickets';

export interface AdminBilling {
  total: number;
  gst: number;
}
export function adminBilling() {
  return apiFetch<AdminBilling>('/admin/billing');
}

export interface BillingPlan {
  plan_id: string;
  active_tables: number;
  table_cap: number;
  scheduled_change?: { to_plan_id: string; scheduled_for: string };
}
export function getBillingPlan() {
  return apiFetch<BillingPlan>('/admin/billing/plan');
}

export interface PlanPreview {
  delta: number;
  gst: number;
  table_cap: number;
  effective: string;
}
export function previewBillingPlan(to_plan_id: string) {
  return apiFetch<PlanPreview>(`/admin/billing/plan/preview?to_plan_id=${to_plan_id}`);
}

export interface PlanChangeRequest {
  to_plan_id: string;
  change_type: 'upgrade' | 'downgrade';
  when: 'now' | 'period_end';
}
export interface PlanChangeResponse {
  invoice_id?: string;
  scheduled_for?: string;
}
export function changeBillingPlan(body: PlanChangeRequest) {
  return apiFetch<PlanChangeResponse>('/admin/billing/plan/change', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  });
}

export interface Invoice {
  id: string;
  date: string;
  number: string;
  period: { from: string; to: string };
  amount: number;
  gst: number;
  status: 'PAID' | 'OPEN' | 'REFUNDED';
}

export function listInvoices(params: {
  from?: string;
  to?: string;
  status?: string;
}) {
  const qs = new URLSearchParams();
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  if (params.status) qs.set('status', params.status);
  const q = qs.toString();
  return apiFetch<Invoice[]>(
    `/admin/billing/invoices${q ? `?${q}` : ''}`
  );
}

export function downloadInvoice(id: string) {
  return apiFetch<void>(`/admin/billing/invoice/${id}.pdf`);
}

export interface Credits {
  balance: number;
  referrals: number;
  adjustments: number;
}

export function getCredits() {
  return apiFetch<Credits>('/admin/billing/credits');
}

export interface ReferralCredit {
  id: string;
  amount_inr: number;
  applied_invoice_id?: string;
  created_at: string;
}

export interface Referral {
  code: string;
  landing_url: string;
  clicks: number;
  signups: number;
  converted: number;
  max_credit_inr: number;
  credits: ReferralCredit[];
}

export function getReferral() {
  return apiFetch<Referral | null>('/admin/referrals');
}

export function createReferral() {
  return apiFetch<Referral>('/admin/referrals/new', { method: 'POST' });
}

export interface Subscription {
  plan_id: string;
  table_cap: number;
  active_tables: number;
  status: 'ACTIVE' | 'GRACE' | 'EXPIRED';
  current_period_end: string;
  grace_ends_at?: string;
  trial_ends_at?: string;
  scheduled_change?: { to_plan_id: string; scheduled_for: string };
}

export function getSubscription() {
  return apiFetch<Subscription>('/admin/billing/subscription');
}

export interface Category {
  id: string;
  name: string;
}

export interface CategoryRequest {
  name: string;
}

export function getCategories(tenant?: string) {
  return apiFetch<Category[]>('/menu/categories', { tenant });
}

export function createCategory(body: CategoryRequest, tenant?: string) {
  return apiFetch<Category>('/menu/categories', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    tenant,
    idempotencyKey: idempotency()
  });
}

export function deleteCategory(id: string, tenant?: string) {
  return apiFetch<void>(`/menu/categories/${id}`, {
    method: 'DELETE',
    tenant
  });
}

export interface Item {
  id: string;
  name: string;
  price: number;
  categoryId: string;
  imageUrl?: string;
}

export interface ItemRequest {
  name: string;
  price: number;
  categoryId: string;
}

export type ItemUpdate = Partial<ItemRequest>;

export function getItems(tenant?: string) {
  return apiFetch<Item[]>('/menu/items', { tenant });
}

export function createItem(body: ItemRequest, tenant?: string) {
  return apiFetch<Item>('/menu/items', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    tenant,
    idempotencyKey: idempotency()
  });
}

export function updateItem(id: string, body: ItemUpdate, tenant?: string) {
  return apiFetch<Item>(`/menu/items/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    tenant
  });
}

export function deleteItem(id: string, tenant?: string) {
  return apiFetch<void>(`/menu/items/${id}`, {
    method: 'DELETE',
    tenant
  });
}

export function uploadImage(itemId: string, file: File, tenant?: string) {
  const form = new FormData();
  form.append('file', file);
  return apiFetch(`/menu/items/${itemId}/image`, {
    method: 'POST',
    body: form,
    tenant
  });
}

export async function exportMenuI18n(langs: string[], tenant?: string) {
  const qs = langs.map((l) => `lang=${encodeURIComponent(l)}`).join('&');
  const headers: Record<string, string> = {};
  if (tenant) headers['X-Tenant'] = tenant;
  const res = await fetch(`/menu/i18n/export?${qs}`, { headers });
  if (!res.ok) throw new Error(res.statusText);
  return res.text();
}

export function importMenuI18n(file: File, tenant?: string) {
  const form = new FormData();
  form.append('file', file);
  return apiFetch(`/menu/i18n/import`, {
    method: 'POST',
    body: form,
    tenant
  });
}
