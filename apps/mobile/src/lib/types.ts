export type Company = {
  id: string;
  business_name: string;
  trade: string;
  callback_window_minutes: number;
  appointment_window: string;
  business_phone: string;
  twilio_number: string | null;
  subscription_status: string;
};

export type User = {
  id: string;
  email: string;
  company: Company;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Template = {
  id: string;
  trade: string;
  body: string;
  variables: string[];
};

export type CallLog = {
  id: string;
  call_sid: string;
  caller_number: string;
  called_number: string;
  status: string;
  missed: boolean;
  created_at: string;
};

export type Message = {
  id: string;
  direction: string;
  from_number: string;
  to_number: string;
  body: string;
  status: string;
  created_at: string;
};

export type Customer = {
  id: string;
  name: string | null;
  phone: string;
  email: string | null;
  address: string | null;
};

export type Job = {
  id: string;
  customer_id: string | null;
  source_call_log_id: string | null;
  title: string;
  description: string | null;
  status: string;
  scheduled_window: string | null;
  created_at: string;
};

export type Invoice = {
  id: string;
  number: string;
  amount_minor: number;
  currency: string;
  status: string;
  sumup_checkout_url: string | null;
  created_at: string;
};

export type StockItem = {
  id: string;
  name: string;
  sku: string;
  quantity: number;
  reorder_level: number;
  unit_cost_minor: number;
};

export type VoiceSession = {
  id: string;
  call_id: string;
  caller_number: string | null;
  called_number: string | null;
  status: string;
  transcript_summary: string | null;
  created_at: string;
};

