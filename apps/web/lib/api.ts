export type RelationshipType =
  | "romantic"
  | "ex"
  | "friend"
  | "family"
  | "manager_colleague"
  | "customer"
  | "unknown";

export type UserGoal =
  | "calm_conflict"
  | "set_boundary"
  | "improve_relationship"
  | "professional_reply"
  | "make_them_accountable"
  | "avoid_needy"
  | "end_conversation"
  | "understand_only";

export type FreeDecodeResponse = {
  decode_id: string;
  safety_label: string;
  prompt_version: string;
  model_version: string;
  free_output?: {
    dominant_lens: { fa: string; en: string; key: string };
    dominant_lens_explanation: string;
    why_this_lens: string;
    secondary_lenses: { fa: string; en: string; key: string }[];
    lens_mix?: { dopamine: number; oxytocin: number; serotonin: number };
    tone_stress?: { label: string; intensity: number };
    likely_underlying_need: string;
    conversation_risk: string;
    recommended_direction: string;
    confidence: string;
    alternative_read: string;
    privacy_warning?: string | null;
    cta: string;
  } | null;
  safety_output?: {
    warning_title: string;
    priority: string;
    suggested_reply: string;
    recommendation: string;
  } | null;
};

export type PaidDecodeResponse = {
  decode_id: string;
  credit_balance: number;
  paid_output: {
    deep_read: string;
    reply_options: { label: string; text: string; why_it_works: string; reaction_prediction?: string | null }[];
    words_to_avoid: string[];
    safe_opening_line: string;
    copy_ready_reply: string;
    attribution_reply?: string | null;
    follow_up_question: string;
  };
};

export type DecodeHistoryItem = {
  id: string;
  created_at: string;
  relationship_type: string;
  user_goal: string;
  safety_label: string;
  dominant_lens: string;
  confidence_level: string;
  has_paid_output: boolean;
  message_preview?: string | null;
  free_output: NonNullable<FreeDecodeResponse["free_output"]>;
  paid_output?: PaidDecodeResponse["paid_output"] | null;
};

export type Contact = {
  id: string;
  name: string;
  relationship_type: RelationshipType;
  default_goal?: UserGoal | null;
  profile_summary?: string | null;
  interaction_count: number;
  created_at: string;
};

export type ContactIn = {
  name: string;
  relationship_type: RelationshipType;
  default_goal?: UserGoal | null;
  profile_summary?: string | null;
};

export type RelationshipThermometer = {
  contact_id: string;
  interaction_count: number;
  defensive_trend: number;
  warmth_score: number;
  label: string;
  summary: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? (
  typeof window !== "undefined"
    ? (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "")
    : "http://127.0.0.1:8000"
);

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    let errorMessage = "ارتباط برقرار نشد. چند لحظه دیگر دوباره تلاش کنید.";
    if (body.detail) {
      if (typeof body.detail === "string") {
        errorMessage = body.detail;
      } else if (Array.isArray(body.detail)) {
        errorMessage = body.detail.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
      } else {
        errorMessage = JSON.stringify(body.detail);
      }
    }
    throw new Error(errorMessage);
  }
  return res.json() as Promise<T>;
}

export function freeDecode(input: {
  message_text: string;
  relationship_type: RelationshipType;
  user_goal: UserGoal;
  optional_context?: string;
  privacy_consent: "none" | "history" | "anonymized";
  contact_id?: string | null;
  ghost_mode?: boolean;
}, token?: string | null) {
  return request<FreeDecodeResponse>("/decode/free", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: JSON.stringify(input)
  });
}

export function requestOtp(phone: string) {
  return request<{ ok: boolean; dev_otp_code?: string }>("/auth/request-otp", {
    method: "POST",
    body: JSON.stringify({ phone })
  });
}

export function verifyOtp(phone: string, code: string) {
  return request<{ token: string; user_id: string; credit_balance: number }>("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ phone, code })
  });
}

export function createPayment(token: string, package_id: "credits_5" | "credits_20" | "credits_50") {
  return request<{ payment_id: string; payment_url: string; amount: number; credits: number; authority?: string | null }>("/payment/create", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ package_id })
  });
}

export function verifyPayment(
  token: string,
  payment_id: string,
  options: { authority?: string | null; status?: string | null } = {}
) {
  return request<{ payment_id: string; status: string; credit_balance: number; ref_id?: string | null }>("/payment/verify", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      payment_id,
      authority: options.authority ?? undefined,
      status: options.status ?? "sandbox_success"
    })
  });
}

export function paidDecode(token: string, decode_id: string) {
  return request<PaidDecodeResponse>("/decode/paid", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ decode_id })
  });
}

export function getDecodeHistory(token: string) {
  return request<{ items: DecodeHistoryItem[] }>("/decode/history", {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function deleteDecode(token: string, decode_id: string) {
  return request<{ ok: boolean }>(`/decode/${decode_id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function deleteStoredData(token: string) {
  return request<{ ok: boolean; deleted_decodes: number; deleted_messages: number; deleted_contacts: number }>("/user/stored-data", {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function copyEvent(decode_id: string, reply_label: string, reply_text_id?: string) {
  return request<{ ok: boolean }>("/copy-event", {
    method: "POST",
    body: JSON.stringify({ decode_id, reply_label, reply_text_id })
  });
}

export function sendFeedback(input: {
  decode_id: string;
  user_rating?: string;
  favorite_reply_label?: string;
  copied_response?: boolean;
  sent_response?: string;
  outcome?: string;
  regret_score?: number;
  user_comment?: string;
}) {
  return request<{ ok: boolean }>("/feedback", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function sendSelectedReplyFeedback(input: {
  decode_id: string;
  selected_reply_label: string;
  copied_response?: boolean;
  outcome?: string;
  contact_id?: string | null;
}, token?: string | null) {
  return request<{ ok: boolean }>("/feedback/selected-reply", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: JSON.stringify(input)
  });
}

export function adminMetrics(token: string) {
  return request<{
    users: number;
    free_decodes: number;
    paid_decodes: number;
    revenue: number;
    conversion: number;
    copy_rate: number;
    by_lens: { dominant_lens: string; count: number }[];
    safety: { safety_label: string; count: number }[];
  }>("/admin/metrics", {
    headers: { "X-Admin-Token": token }
  });
}

export type AdminDecodeItem = {
  id: string;
  created_at: string;
  paid_at?: string | null;
  relationship_type: string;
  user_goal: string;
  privacy_consent: string;
  safety_label: string;
  dominant_lens: string;
  secondary_lenses: string[];
  confidence_level: string;
  prompt_version: string;
  model_version: string;
  free_model_version?: string | null;
  paid_model_version?: string | null;
  rule_engine_version?: string | null;
  output_schema_version?: string | null;
  has_paid_output: boolean;
  anonymized_preview?: string | null;
  feedback_count: number;
  copy_count: number;
};

export function adminDecodeList(
  token: string,
  filters: {
    relationship_type?: string;
    dominant_lens?: string;
    safety_label?: string;
    prompt_version?: string;
    limit?: number;
    offset?: number;
  } = {}
) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return request<{ items: AdminDecodeItem[]; total: number; limit: number; offset: number }>(
    `/admin/decodes${query ? `?${query}` : ""}`,
    { headers: { "X-Admin-Token": token } }
  );
}

// ─── Contacts CRUD ────────────────────────────────────────────────────────────

export function getContacts(token: string) {
  return request<Contact[]>("/contacts", {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function createContact(token: string, payload: ContactIn) {
  return request<Contact>("/contacts", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload)
  });
}

export function updateContact(token: string, id: string, payload: ContactIn) {
  return request<Contact>(`/contacts/${id}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload)
  });
}

export function deleteContact(token: string, id: string) {
  return request<{ ok: boolean }>(`/contacts/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function getRelationshipThermometer(token: string, id: string) {
  return request<RelationshipThermometer>(`/contacts/${id}/thermometer`, {
    headers: { Authorization: `Bearer ${token}` }
  });
}
