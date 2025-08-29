import { apiFetch, idempotency } from './api';

export interface LoginPinRequest {
  phone: string;
  pin: string;
}
export interface LoginPinResponse {
  token: string;
}
export function loginPin(body: LoginPinRequest) {
  return apiFetch<LoginPinResponse>('/login/pin', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    idempotencyKey: idempotency()
  });
}

export interface LicenseStatus {
  status: 'ACTIVE' | 'GRACE' | 'EXPIRED';
  days_left?: number;
  renew_url?: string;
}

export function getLicenseStatus() {
  return apiFetch<LicenseStatus>('/license');
}

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

export function exportMenuI18n(langs: string[], tenant?: string) {
  return apiFetch(`/menu/i18n/export`, {
    method: 'POST',
    body: JSON.stringify({ langs }),
    headers: { 'Content-Type': 'application/json' },
    tenant
  });
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
