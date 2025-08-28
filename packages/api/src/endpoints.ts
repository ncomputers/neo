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

// Menu editor endpoints
export interface Category {
  id: string;
  name: string;
  sort_order: number;
}

export interface Item {
  id: string;
  category_id: string;
  name: string;
  price: number;
  active: boolean;
  sort_order: number;
  name_i18n?: Record<string, string>;
  desc_i18n?: Record<string, string>;
  image?: string;
}

export function getCategories() {
  return apiFetch<Category[]>('/menu/categories');
}

export function createCategory(body: Partial<Category>) {
  return apiFetch<Category>('/menu/categories', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  });
}

export function updateCategory(id: string, body: Partial<Category>) {
  return apiFetch<Category>(`/menu/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  });
}

export function deleteCategory(id: string) {
  return apiFetch<void>(`/menu/categories/${id}`, { method: 'DELETE' });
}

export function getItems(categoryId: string) {
  return apiFetch<Item[]>(`/menu/categories/${categoryId}/items`);
}

export function createItem(categoryId: string, body: Partial<Item>) {
  return apiFetch<Item>(`/menu/categories/${categoryId}/items`, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  });
}

export function updateItem(id: string, body: Partial<Item>) {
  return apiFetch<Item>(`/menu/items/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  });
}

export function deleteItem(id: string) {
  return apiFetch<void>(`/menu/items/${id}`, { method: 'DELETE' });
}

export function uploadImage(file: File) {
  const form = new FormData();
  form.append('file', file);
  return apiFetch<{ url: string }>('/upload', {
    method: 'POST',
    body: form
  });
}

export function exportI18nCSV(langs: string[]) {
  return apiFetch<Blob>('/menu/i18n/export', {
    method: 'POST',
    body: JSON.stringify({ langs }),
    headers: { 'Content-Type': 'application/json' }
  });
}

export function importI18nCSV(file: File) {
  const form = new FormData();
  form.append('file', file);
  return apiFetch<void>('/menu/i18n/import', {
    method: 'POST',
    body: form
  });
}
