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
