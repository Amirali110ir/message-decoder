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
  contact_id?: string | null;
  contact_profile_summary?: string | null;
  clarifying_question?: string | null;
  prompt_version: string;
  model_version: string;
  free_output?: {
    dominant_lens: { fa: string; en: string; key: string };
    dominant_lens_explanation: string;
    why_this_lens: string;
    message_focus?: string | null;
    personalization_note?: string | null;
    secondary_lenses: { fa: string; en: string; key: string }[];
    lens_mix?: { dopamine: number; oxytocin: number; serotonin: number };
    tone_stress?: { label: string; intensity: number };
    likely_underlying_need: string;
    conversation_risk: string;
    recommended_direction: string;
    confidence: string;
    alternative_read: string;
    insight_line?: string | null;
    situation_arc?: string | null;
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
    personalization_note?: string | null;
    reply_options: {
      label: string;
      text: string;
      why_it_works: string;
      reaction_prediction?: string | null;
      reaction_forecast?: { likely_reaction: string; reason: string; risk_level: "کم" | "متوسط" | "زیاد" } | null;
    }[];
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
  memory_summary?: string | null;
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
        : "https://message-decoder-py.liara.run")
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
  episode_background?: string;
  their_behavior?: string;
  recent_messages?: string[];
  privacy_consent: "none" | "history" | "anonymized";
  contact_id?: string | null;
  contact_name?: string | null;
  ghost_mode?: boolean;
}, token?: string | null) {
  return request<FreeDecodeResponse>("/decode/free", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: JSON.stringify(input)
  });
}

export function requestOtp(phone: string) {
  return request<{ ok: boolean; dev_otp_code?: string; telegram_payload?: any }>("/auth/request-otp", {
    method: "POST",
    body: JSON.stringify({ phone })
  });
}

function resolveTelegramRelayUrl(): string | null {
  const explicit = process.env.NEXT_PUBLIC_TELEGRAM_OTP_RELAY_URL;
  if (explicit) return explicit;
  if (typeof window === "undefined") return null;
  return `${window.location.origin}/api/telegram/send-otp`;
}

export async function notifyTelegramOtp(payload: any) {
  if (!payload || typeof window === "undefined" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return;
  }
  const url = resolveTelegramRelayUrl();
  if (!url) return;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload })
    });
  } catch {
    // Telegram delivery is best-effort; SMS/mock OTP flow should not fail because of it.
  }
}

export function verifyOtp(phone: string, code: string) {
  return request<{ token: string; user_id: string; credit_balance: number }>("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ phone, code })
  });
}

export function verifyOtpWithReferral(phone: string, code: string, referral_code?: string) {
  return request<{ token: string; user_id: string; credit_balance: number }>("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ phone, code, referral_code: referral_code || undefined })
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

export function paidDecodeGhost(
  token: string,
  input: {
    decode_id: string;
    free_output: NonNullable<FreeDecodeResponse["free_output"]>;
    message_text: string;
    relationship_type: RelationshipType;
    user_goal: UserGoal;
    optional_context?: string;
  }
) {
  return request<PaidDecodeResponse>("/decode/paid/ghost", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(input)
  });
}

export type ToneTarget = "softer" | "firmer" | "shorter" | "warmer" | "formal";

export type ToneEditResponse = {
  tone: ToneTarget;
  tone_label: string;
  text: string;
};

export type BeforeSendResponse = {
  risk_level: "کم" | "متوسط" | "زیاد";
  risk_score: number;
  summary: string;
  flags: string[];
  suggestions: string[];
  improved_text?: string | null;
};

export function toneEdit(
  token: string,
  input: {
    reply_text: string;
    target_tone: ToneTarget;
    relationship_type: RelationshipType;
    user_goal: UserGoal;
    original_message?: string | null;
  }
) {
  return request<ToneEditResponse>("/decode/tone-edit", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(input)
  });
}

export function beforeSendCheck(
  token: string,
  input: {
    draft_text: string;
    relationship_type: RelationshipType;
    user_goal: UserGoal;
    original_message?: string | null;
  }
) {
  return request<BeforeSendResponse>("/decode/before-send", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(input)
  });
}

export function getDecodeHistory(token: string) {
  return request<{ items: DecodeHistoryItem[] }>("/decode/history", {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function getReferral(token: string) {
  return request<{ referral_code: string; referral_url: string; reward_credits: number }>("/user/referral", {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export function getCredits(token: string) {
  return request<{ credit_balance: number }>("/user/credits", {
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
    verified_payments?: number;
    sms_sent?: number;
    sms_failed?: number;
    contacts?: number;
    referrals?: number;
    total_credits?: number;
    conversion: number;
    copy_rate: number;
    by_lens: { dominant_lens: string; count: number }[];
    safety: { safety_label: string; count: number }[];
    retention?: {
      d7_retention: { cohort: number; retained: number; rate: number };
      weekly_return: { cohort: number; returned: number; rate: number };
    };
    frequency?: {
      active_users: number;
      avg_actions_per_user: number;
      multi_action_rate: number;
      before_send_checks: number;
    };
  }>("/admin/metrics", {
    headers: { "X-Admin-Token": token }
  });
}

export function adminLogin(phone: string, password: string) {
  return request<{ token: string }>("/admin/login", {
    method: "POST",
    body: JSON.stringify({ phone, password })
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

export type AdminUserItem = {
  id: string;
  phone?: string | null;
  telegram_id?: string | null;
  created_at: string;
  credit_balance: number;
  source_channel: string;
  referral_code?: string | null;
  referred_by_user_id?: string | null;
  referral_count: number;
  decodes_count: number;
  paid_decodes_count: number;
  contacts_count: number;
};

export type AdminActivityItem = {
  id: string;
  user_id?: string | null;
  phone?: string | null;
  event_type: string;
  title: string;
  detail?: string | null;
  status?: string | null;
  created_at: string;
};

export function adminUserList(token: string, filters: { q?: string; limit?: number; offset?: number } = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return request<{ items: AdminUserItem[]; total: number; limit: number; offset: number }>(
    `/admin/users${query ? `?${query}` : ""}`,
    { headers: { "X-Admin-Token": token } }
  );
}

export function adminActivityList(token: string, filters: { q?: string; user_id?: string; limit?: number; offset?: number } = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return request<{ items: AdminActivityItem[]; total: number; limit: number; offset: number }>(
    `/admin/activity${query ? `?${query}` : ""}`,
    { headers: { "X-Admin-Token": token } }
  );
}

export function adminGrantCredits(token: string, input: { user_id?: string; phone?: string; credits: number }) {
  return request<{ user_id: string; credit_balance: number }>("/admin/credits/grant", {
    method: "POST",
    headers: { "X-Admin-Token": token },
    body: JSON.stringify(input)
  });
}

export function adminGrantAllCredits(token: string, credits: number) {
  return request<{ updated_users: number }>("/admin/credits/grant-all", {
    method: "POST",
    headers: { "X-Admin-Token": token },
    body: JSON.stringify({ credits })
  });
}

const TELEGRAM_WORKER_URL = process.env.NEXT_PUBLIC_TELEGRAM_WORKER_URL || "https://message-decoder-telegram.shabestani-am.workers.dev";

async function workerRequest<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${TELEGRAM_WORKER_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": token,
      ...(options.headers ?? {})
    }
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || body.detail || "درخواست ادمین تلگرام انجام نشد.");
  }
  return res.json() as Promise<T>;
}

export type TelegramAdminUser = {
  id: string;
  phone?: string | null;
  telegram_id: string;
  credit_balance: number;
  referral_code?: string | null;
  referred_by_user_id?: string | null;
  referral_count?: number;
  decodes_count?: number;
  paid_decodes_count?: number;
  created_at: string;
  last_decode_at?: string | null;
};

export type TelegramActivityItem = {
  id: string;
  user_id?: string | null;
  phone?: string | null;
  telegram_id?: string | null;
  event_type: string;
  title: string;
  detail?: string | null;
  status?: string | null;
  created_at: string;
};

export type TelegramBroadcastResult = {
  user_id: string;
  phone?: string | null;
  telegram_id: string;
  referral_code?: string | null;
  status: "sent" | "failed";
  error?: string | null;
};

export function telegramAdminMetrics(token: string) {
  return workerRequest<{
    users: number;
    free_decodes: number;
    paid_decodes: number;
    referrals: number;
    total_credits: number;
    broadcastable_users: number;
    payments: number;
    contacts: number;
  }>("/admin/metrics", token);
}

export function telegramAdminUsers(token: string, q = "") {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  return workerRequest<{ items: TelegramAdminUser[] }>(`/admin/users${params.toString() ? `?${params}` : ""}`, token);
}

export function telegramAdminActivity(token: string, q = "") {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  params.set("limit", "80");
  return workerRequest<{ items: TelegramActivityItem[]; total: number; limit: number }>(`/admin/activity?${params}`, token);
}

export function telegramGrantCredits(token: string, input: { user_id?: string; phone?: string; credits: number }) {
  return workerRequest<{ ok: boolean; user_id: string; credit_balance: number }>("/admin/credits/grant", token, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function telegramGrantAllCredits(token: string, credits: number) {
  return workerRequest<{ ok: boolean; updated_users: number }>("/admin/credits/grant-all", token, {
    method: "POST",
    body: JSON.stringify({ credits })
  });
}

export function telegramBroadcast(token: string, text: string) {
  return workerRequest<{ ok: boolean; sent: number; failed: number; results: TelegramBroadcastResult[] }>("/admin/broadcast", token, {
    method: "POST",
    body: JSON.stringify({ text })
  });
}

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

// ─── Admin: learning & rule-engine ────────────────────────────────────────────

export type LearningReport = {
  metrics: {
    report_date: string;
    window_start: string;
    window_end: string;
    total_decodes: number;
    paid_decodes: number;
    copied_paid_decodes: number;
    copy_rate: number;
    feedback_count: number;
    positive_feedback_rate: number;
    negative_feedback_rate: number;
    average_regret_score: number | null;
    lens_mix: { dominant_lens: string; count: number }[];
    safety_mix: { safety_label: string; count: number }[];
    model_mix: {
      free_model_version: string;
      paid_model_version: string;
      prompt_version: string;
      rule_engine_version: string;
      count: number;
    }[];
  };
  recommendations: string[];
};

export function adminLearningDaily(token: string, reportDate = "", persist = false) {
  const params = new URLSearchParams();
  if (reportDate) params.set("report_date", reportDate);
  if (persist) params.set("persist", "true");
  const query = params.toString();
  return request<LearningReport>(`/admin/learning/daily${query ? `?${query}` : ""}`, {
    headers: { "X-Admin-Token": token }
  });
}

export type RuleEvalResult = {
  id: string;
  lens_ok: boolean;
  safety_ok: boolean;
  expected_lens: string;
  actual_lens: string;
  expected_safety_label: string;
  actual_safety_label: string;
  expected_tones: string[];
  actual_tones: string[];
  missing_tones: string[];
  lens_scores: Record<string, number>;
  evidence_terms: string[];
  playbook_must_include: string[];
};

export type RuleEngineEval = {
  rule_engine_version: string;
  metrics: {
    case_count: number;
    lens_accuracy: number;
    safety_accuracy: number;
    tone_recall: number;
    lens_confusion: Record<string, number>;
  };
  misses: RuleEvalResult[];
  recommendations: string[];
  results: RuleEvalResult[];
};

export function adminRuleEngineEval(token: string) {
  return request<RuleEngineEval>("/admin/rule-engine/eval", {
    headers: { "X-Admin-Token": token }
  });
}

export type RuleCandidateCase = {
  feedback_id: string;
  decode_id: string;
  created_at: string;
  message_preview: string | null;
  relationship_type: string;
  user_goal: string;
  feedback_signals: {
    user_rating: string | null;
    outcome: string | null;
    regret_score: number | null;
    user_comment: string | null;
  };
  current_classification: {
    dominant_lens: string;
    safety_label: string;
    tones: string[];
    lens_scores: Record<string, number>;
    evidence_terms: string[];
  };
  suggested_eval_case: Record<string, unknown>;
};

export type RuleCandidateResponse = {
  rule_engine_version: string;
  candidate_count: number;
  candidate_cases: RuleCandidateCase[];
  selection_rule: string;
};

export function adminRuleEngineCandidates(token: string, limit = 50) {
  return request<RuleCandidateResponse>(`/admin/rule-engine/candidate-cases?limit=${limit}`, {
    headers: { "X-Admin-Token": token }
  });
}

export type RuleExplainResponse = {
  analysis: Record<string, unknown> & {
    dominant_lens?: string;
    safety_label?: string;
    tones?: string[];
    lens_scores?: Record<string, number>;
    evidence_terms?: string[];
    confidence_level?: string;
  };
  paid_reply_playbook: Record<string, unknown> & {
    must_include?: string[];
  };
};

export function adminRuleEngineExplain(
  token: string,
  input: {
    message_text: string;
    relationship_type: string;
    user_goal: string;
    optional_context?: string;
    privacy_consent?: "none" | "history" | "anonymized";
  }
) {
  return request<RuleExplainResponse>("/admin/rule-engine/explain", {
    method: "POST",
    headers: { "X-Admin-Token": token },
    body: JSON.stringify({ privacy_consent: "none", ...input })
  });
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
