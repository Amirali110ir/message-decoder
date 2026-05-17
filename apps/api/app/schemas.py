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


class FreeDecodeOutput(BaseModel):
    dominant_lens: LensLabel
    dominant_lens_explanation: str
    why_this_lens: str
    secondary_lenses: list[LensLabel] = []
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


class CreditsOut(BaseModel):
    credit_balance: int


class PaymentCreateIn(BaseModel):
    package_id: Literal["credits_5", "credits_20", "credits_50"]


class PaymentCreateOut(BaseModel):
    payment_id: str
    payment_url: str
    amount: int
    credits: int


class PaymentVerifyIn(BaseModel):
    payment_id: str
    authority: str | None = None
    status: str


class PaymentVerifyOut(BaseModel):
    payment_id: str
    status: str
    credit_balance: int


class FeedbackIn(BaseModel):
    decode_id: str
    user_rating: str | None = None
    favorite_reply_label: str | None = None
    copied_response: bool | None = None
    sent_response: str | None = None
    outcome: str | None = None
    regret_score: int | None = Field(default=None, ge=1, le=5)
    user_comment: str | None = None


class CopyEventIn(BaseModel):
    decode_id: str
    reply_label: str
    reply_text_id: str | None = None


class OkOut(BaseModel):
    ok: bool

