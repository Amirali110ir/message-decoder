from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class VerifyOtpIn(BaseModel):
    phone: str
    code: str


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
    secondary_lenses: list[LensLabel] = []
    lens_mix: LensMix = Field(default_factory=LensMix)
    tone_stress: ToneStress = Field(default_factory=ToneStress)
    likely_underlying_need: str
    conversation_risk: str
    recommended_direction: str
    confidence: Literal["پایین", "متوسط", "بالا"]
    alternative_read: str
    privacy_warning: str | None = None
    cta: str


class ReplyOption(BaseModel):
    label: str
    text: str
    why_it_works: str
    reaction_prediction: str | None = None


class PaidDecodeOutput(BaseModel):
    deep_read: str
    dominant_lens: LensLabel
    secondary_lenses: list[LensLabel] = []
    reply_options: list[ReplyOption]
    words_to_avoid: list[str]
    safe_opening_line: str
    copy_ready_reply: str
    attribution_reply: str | None = None
    follow_up_question: str


class SafetyOutput(BaseModel):
    warning_title: str
    priority: str
    suggested_reply: str
    recommendation: str


class FreeDecodeIn(BaseModel):
    message_text: str = Field(min_length=1, max_length=4000)
    relationship_type: RelationshipType = "unknown"
    user_goal: UserGoal = "understand_only"
    optional_context: str | None = Field(default=None, max_length=2000)
    privacy_consent: PrivacyConsent = "none"
    contact_id: str | None = None
    ghost_mode: bool = False


class FreeDecodeResponse(BaseModel):
    decode_id: str
    safety_label: str
    free_output: FreeDecodeOutput | None = None
    safety_output: SafetyOutput | None = None
    prompt_version: str
    model_version: str


class PaidDecodeIn(BaseModel):
    decode_id: str


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
    interaction_count: int
    created_at: str
