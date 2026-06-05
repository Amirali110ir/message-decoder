from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Hard caps for the episode context, so a long paste can never blow up the
# token budget sent to the model (see roadmap section 10 / T10.1).
MAX_RECENT_MESSAGES = 5
MAX_RECENT_MESSAGE_LEN = 500


RelationshipType = Literal[
    "romantic",
    "ex",
    "friend",
    "family",
    "manager_colleague",
    "customer",
    "unknown",
]
UserGoal = Literal[
    "calm_conflict",
    "set_boundary",
    "improve_relationship",
    "professional_reply",
    "make_them_accountable",
    "avoid_needy",
    "end_conversation",
    "understand_only",
]
PrivacyConsent = Literal["none", "history", "anonymized"]


class RequestOtpIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class RequestOtpOut(BaseModel):
    ok: bool
    dev_otp_code: str | None = None
    telegram_payload: dict | None = None


class TelegramOtpPayloadIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class TelegramOtpPayloadOut(BaseModel):
    ok: bool
    chat_id: str | None = None
    text: str | None = None


class TelegramLinkIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    telegram_id: str = Field(min_length=1, max_length=64)


class VerifyOtpIn(BaseModel):
    phone: str
    code: str
    referral_code: str | None = Field(default=None, max_length=32)


class VerifyOtpOut(BaseModel):
    token: str
    user_id: str
    credit_balance: int


class LensLabel(BaseModel):
    fa: str
    en: str
    key: str


class LensMix(BaseModel):
    dopamine: int = 0
    oxytocin: int = 0
    serotonin: int = 0


class ToneStress(BaseModel):
    label: str = "مبهم"
    intensity: int = Field(default=35, ge=0, le=100)


class FreeDecodeOutput(BaseModel):
    dominant_lens: LensLabel
    dominant_lens_explanation: str
    why_this_lens: str
    message_focus: str | None = None
    personalization_note: str | None = None
    secondary_lenses: list[LensLabel] = []
    lens_mix: LensMix = Field(default_factory=LensMix)
    tone_stress: ToneStress = Field(default_factory=ToneStress)
    likely_underlying_need: str
    conversation_risk: str
    recommended_direction: str
    confidence: Literal["پایین", "متوسط", "بالا"]
    alternative_read: str
    # One specific, human "I see what's really going on" line (T3.2). Concrete,
    # not generic — e.g. «این پیام عصبانی نیست، ترسیده».
    insight_line: str | None = None
    # Short structured narrative of the situation arc when episode context is
    # given (T3.4) — where trust wavered / dignity was hit / threat fired. Not a
    # single-message label, and no biological claims.
    situation_arc: str | None = None
    privacy_warning: str | None = None
    cta: str


class ReactionForecast(BaseModel):
    likely_reaction: str            # واکنشِ محتمل (آرام می‌شود / تدافعی می‌شود / سرد می‌شود...)
    reason: str                     # دلیلِ کوتاه (چرا این واکنش)
    risk_level: Literal["کم", "متوسط", "زیاد"]


class ReplyOption(BaseModel):
    label: str
    text: str
    why_it_works: str
    reaction_prediction: str | None = None      # legacy free-text (kept for back-compat)
    reaction_forecast: ReactionForecast | None = None  # structured prediction (T3.1)


class PaidDecodeOutput(BaseModel):
    deep_read: str
    dominant_lens: LensLabel
    secondary_lenses: list[LensLabel] = []
    personalization_note: str | None = None
    reply_options: list[ReplyOption]
    words_to_avoid: list[str]
    safe_opening_line: str
    copy_ready_reply: str
    attribution_reply: str | None = None
    follow_up_question: str


ToneTarget = Literal["softer", "firmer", "shorter", "warmer", "formal"]


class ToneEditIn(BaseModel):
    reply_text: str = Field(min_length=1, max_length=4000)
    target_tone: ToneTarget
    relationship_type: RelationshipType = "unknown"
    user_goal: UserGoal = "understand_only"
    original_message: str | None = Field(default=None, max_length=4000)


class ToneEditOut(BaseModel):
    tone: ToneTarget
    tone_label: str
    text: str


class BeforeSendIn(BaseModel):
    draft_text: str = Field(min_length=1, max_length=4000)
    relationship_type: RelationshipType = "unknown"
    user_goal: UserGoal = "understand_only"
    original_message: str | None = Field(default=None, max_length=4000)


class BeforeSendOut(BaseModel):
    risk_level: Literal["کم", "متوسط", "زیاد"]
    risk_score: int = Field(ge=0, le=100)
    summary: str
    flags: list[str] = []
    suggestions: list[str] = []
    improved_text: str | None = None


class SafetyOutput(BaseModel):
    warning_title: str
    priority: str
    suggested_reply: str
    recommendation: str


class FreeDecodeIn(BaseModel):
    # Focal message is the only required text; everything else is optional so
    # the entry never becomes a big mandatory form (T1.7 day-0 warning).
    message_text: str = Field(min_length=1, max_length=4000)
    relationship_type: RelationshipType = "unknown"
    user_goal: UserGoal = "understand_only"
    optional_context: str | None = Field(default=None, max_length=2000)
    # --- Episode fields: the unit of analysis is the situation, not one message ---
    episode_background: str | None = Field(default=None, max_length=1000)  # قبلش چه شد / رابطه چطور بود
    their_behavior: str | None = Field(default=None, max_length=1000)      # طرف چطور رفتار/واکنش نشان داد
    recent_messages: list[str] | None = Field(default=None)               # چند پیامِ آخر (سقف‌دار)
    privacy_consent: PrivacyConsent = "none"
    contact_id: str | None = None
    contact_name: str | None = Field(default=None, max_length=100)
    ghost_mode: bool = False

    @field_validator("recent_messages")
    @classmethod
    def _cap_recent_messages(cls, value: list[str] | None) -> list[str] | None:
        if not value:
            return None
        capped = [m.strip()[:MAX_RECENT_MESSAGE_LEN] for m in value if isinstance(m, str) and m.strip()]
        return capped[:MAX_RECENT_MESSAGES] or None

    def episode_context(self) -> str | None:
        """Compact, structured rendering of the episode for prompts/storage.

        Returns None when no episode field was supplied, so the single-message
        path stays byte-for-byte identical to before.
        """
        parts: list[str] = []
        if self.episode_background:
            parts.append(f"پیشینه/رابطه: {self.episode_background.strip()}")
        if self.their_behavior:
            parts.append(f"رفتار طرف مقابل: {self.their_behavior.strip()}")
        if self.recent_messages:
            joined = " | ".join(self.recent_messages)
            parts.append(f"چند پیامِ آخر: {joined}")
        return "\n".join(parts) if parts else None


class FreeDecodeResponse(BaseModel):
    decode_id: str
    safety_label: str
    free_output: FreeDecodeOutput | None = None
    safety_output: SafetyOutput | None = None
    contact_id: str | None = None
    contact_profile_summary: str | None = None
    # One targeted question when the message is too ambiguous to analyse well and
    # no episode context was given (T2.4). None otherwise.
    clarifying_question: str | None = None
    prompt_version: str
    model_version: str


class PaidDecodeIn(BaseModel):
    decode_id: str


class GhostPaidDecodeIn(BaseModel):
    decode_id: str
    free_output: FreeDecodeOutput
    message_text: str = Field(min_length=1, max_length=4000)
    relationship_type: RelationshipType = "unknown"
    user_goal: UserGoal = "understand_only"
    optional_context: str | None = Field(default=None, max_length=2000)


class PaidDecodeResponse(BaseModel):
    decode_id: str
    paid_output: PaidDecodeOutput
    credit_balance: int


class DecodeHistoryItem(BaseModel):
    id: str
    created_at: str
    relationship_type: str
    user_goal: str
    safety_label: str
    dominant_lens: str
    confidence_level: str
    has_paid_output: bool
    message_preview: str | None = None
    free_output: dict
    paid_output: dict | None = None


class DecodeHistoryOut(BaseModel):
    items: list[DecodeHistoryItem]


class RelationshipThermometerOut(BaseModel):
    contact_id: str
    interaction_count: int
    defensive_trend: int = Field(ge=-100, le=100)
    warmth_score: int = Field(ge=0, le=100)
    label: str
    summary: str


class CreditsOut(BaseModel):
    credit_balance: int


class ReferralOut(BaseModel):
    referral_code: str
    referral_url: str
    reward_credits: int = 5


class AdminLoginIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class AdminLoginOut(BaseModel):
    token: str


class AdminUserItem(BaseModel):
    id: str
    phone: str | None = None
    telegram_id: str | None = None
    created_at: str
    credit_balance: int
    source_channel: str
    referral_code: str | None = None
    referred_by_user_id: str | None = None
    referral_count: int = 0
    decodes_count: int = 0
    paid_decodes_count: int = 0
    contacts_count: int = 0


class AdminUserListOut(BaseModel):
    items: list[AdminUserItem]
    total: int
    limit: int
    offset: int


class AdminActivityItem(BaseModel):
    id: str
    user_id: str | None = None
    phone: str | None = None
    event_type: str
    title: str
    detail: str | None = None
    status: str | None = None
    created_at: str


class AdminActivityListOut(BaseModel):
    items: list[AdminActivityItem]
    total: int
    limit: int
    offset: int


class AdminGrantCreditsIn(BaseModel):
    user_id: str | None = None
    phone: str | None = None
    credits: int = Field(ge=-1000, le=1000)


class AdminGrantCreditsOut(BaseModel):
    user_id: str
    credit_balance: int


class AdminBulkGrantCreditsIn(BaseModel):
    credits: int = Field(ge=-1000, le=1000)


class AdminBulkGrantCreditsOut(BaseModel):
    updated_users: int


class PaymentCreateIn(BaseModel):
    package_id: Literal["credits_5", "credits_20", "credits_50"]


class PaymentCreateOut(BaseModel):
    payment_id: str
    payment_url: str
    amount: int
    credits: int
    authority: str | None = None


class PaymentVerifyIn(BaseModel):
    payment_id: str
    authority: str | None = None
    status: str


class PaymentVerifyOut(BaseModel):
    payment_id: str
    status: str
    credit_balance: int
    ref_id: str | None = None


class FeedbackIn(BaseModel):
    decode_id: str
    user_rating: str | None = None
    favorite_reply_label: str | None = None
    copied_response: bool | None = None
    sent_response: str | None = None
    outcome: str | None = None
    regret_score: int | None = Field(default=None, ge=1, le=5)
    user_comment: str | None = None


class SelectedReplyFeedbackIn(BaseModel):
    decode_id: str
    selected_reply_label: str
    copied_response: bool | None = None
    outcome: str | None = None
    contact_id: str | None = None


class CopyEventIn(BaseModel):
    decode_id: str
    reply_label: str
    reply_text_id: str | None = None


class OkOut(BaseModel):
    ok: bool


class DeletedStoredDataOut(BaseModel):
    ok: bool
    deleted_decodes: int
    deleted_messages: int
    deleted_contacts: int


class AdminDecodeItem(BaseModel):
    id: str
    created_at: str
    paid_at: str | None = None
    relationship_type: str
    user_goal: str
    privacy_consent: str
    safety_label: str
    dominant_lens: str
    secondary_lenses: list[str] = []
    confidence_level: str
    prompt_version: str
    model_version: str
    free_model_version: str | None = None
    paid_model_version: str | None = None
    rule_engine_version: str | None = None
    output_schema_version: str | None = None
    has_paid_output: bool
    anonymized_preview: str | None = None
    feedback_count: int = 0
    copy_count: int = 0


class AdminDecodeListOut(BaseModel):
    items: list[AdminDecodeItem]
    total: int
    limit: int
    offset: int


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    relationship_type: RelationshipType
    default_goal: UserGoal | None = None
    profile_summary: str | None = Field(default=None, max_length=2000)


class ContactOut(BaseModel):
    id: str
    name: str
    relationship_type: RelationshipType
    default_goal: UserGoal | None = None
    profile_summary: str | None = None
    memory_summary: str | None = None
    interaction_count: int
    created_at: str
