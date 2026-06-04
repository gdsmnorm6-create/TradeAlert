import type {
  AuthResponse,
  CallLog,
  Company,
  Customer,
  Invoice,
  Job,
  Message,
  StockItem,
  Template,
  User,
  VoiceSession,
} from './types';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

type RequestOptions = RequestInit & {
  token?: string | null;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (payload: {
    email: string;
    password: string;
    business_name: string;
    trade: string;
    callback_window_minutes: number;
    appointment_window: string;
    business_phone: string;
  }) => request<AuthResponse>('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),

  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),

  me: (token: string) => request<User>('/api/me', { token }),
  company: (token: string) => request<Company>('/api/company', { token }),
  template: (token: string) => request<Template>('/api/company/template', { token }),
  updateTemplate: (token: string, body: string) =>
    request<Template>('/api/company/template', {
      token,
      method: 'PATCH',
      body: JSON.stringify({ body }),
    }),
  calls: (token: string) => request<CallLog[]>('/api/calls', { token }),
  messages: (token: string) => request<Message[]>('/api/messages', { token }),
  sendMessage: (token: string, payload: { to_number: string; body: string }) =>
    request<Message>('/api/messages/send', { token, method: 'POST', body: JSON.stringify(payload) }),
  customers: (token: string) => request<Customer[]>('/api/customers', { token }),
  createCustomer: (token: string, payload: { name: string; phone: string; address?: string }) =>
    request<Customer>('/api/customers', { token, method: 'POST', body: JSON.stringify(payload) }),
  jobs: (token: string) => request<Job[]>('/api/jobs', { token }),
  createJob: (token: string, payload: { customer_id?: string; title: string; description?: string }) =>
    request<Job>('/api/jobs', { token, method: 'POST', body: JSON.stringify(payload) }),
  invoices: (token: string) => request<Invoice[]>('/api/invoices', { token }),
  createInvoice: (token: string, payload: { customer_id?: string; job_id?: string; amount_minor: number }) =>
    request<Invoice>('/api/invoices', { token, method: 'POST', body: JSON.stringify(payload) }),
  stock: (token: string) => request<StockItem[]>('/api/stock', { token }),
  createStock: (token: string, payload: { name: string; sku: string; quantity: number; reorder_level: number }) =>
    request<StockItem>('/api/stock', { token, method: 'POST', body: JSON.stringify(payload) }),
  createReceipt: (token: string, payload: { filename: string; job_id?: string; raw_text: string; amount_minor?: number }) =>
    request<{ receipt_upload_id: string; ocr_extraction_id: string; status: string }>('/api/ocr/receipts', {
      token,
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  voiceSessions: (token: string) => request<VoiceSession[]>('/api/voice-sessions', { token }),
};

