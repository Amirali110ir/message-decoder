const RELATIONSHIPS = [
  ["romantic", "عاطفی"],
  ["ex", "اکس"],
  ["manager_colleague", "همکار/مدیر"],
  ["customer", "مشتری"],
  ["family", "خانواده"],
  ["friend", "دوست"],
];

const GOALS = [
  ["avoid_needy", "نیازمند به نظر نرسم"],
  ["set_boundary", "مرزبندی محترمانه"],
  ["calm_conflict", "آرام کردن تنش"],
  ["professional_reply", "پاسخ حرفه‌ای"],
  ["understand_only", "فقط بفهمم"],
];

const AI_SYSTEM_PROMPT = `
تو Message Decoder by NeuroLens هستی؛ یک ابزار فارسی‌زبان برای تحلیل پیام‌های مبهم، سرد، کنایه‌آمیز، احساسی یا حرفه‌ای قبل از پاسخ دادن.

مهم:
- از روی یک پیام درباره نیت، شخصیت یا اختلال روانی طرف مقابل حکم قطعی نده.
- از عبارت‌هایی مثل «احتمالاً»، «ممکن است»، «برداشت محتاطانه» استفاده کن.
- سه لنز Dopamine/Oxytocin/Serotonin فقط لنز رفتاری‌اند، نه تشخیص واقعی هورمونی.
- پاسخ‌ها باید فارسی طبیعی، مشخص، متناسب با متن کاربر، غیرکلیشه‌ای و قابل ارسال باشند.
- هیچ پاسخ manipulative، guilt-trip، تحقیرآمیز یا تحریک‌کننده تولید نکن.

لنزها:
1. Dopamine: نتیجه، کنترل، زمان‌بندی، فشار برای اقدام.
2. Oxytocin: امنیت، اعتماد، نزدیکی، ترس از بی‌اهمیت شدن.
3. Serotonin: شأن، احترام، جایگاه، دیده‌شدن.
`.trim();

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true });
    }
    if (request.method === "POST" && url.pathname.startsWith("/bot")) {
      return handleTelegramRelay(request, env, url);
    }
    if (request.method === "POST" && url.pathname === "/webhook") {
      if (env.TELEGRAM_WEBHOOK_SECRET) {
        const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
        if (secret !== env.TELEGRAM_WEBHOOK_SECRET) return json({ ok: false }, 401);
      }
      const update = await request.json();
      if (update.message) await handleMessage(update.message, env);
      if (update.callback_query) await handleCallback(update.callback_query, env);
      return json({ ok: true });
    }
    if (url.pathname.startsWith("/admin/")) {
      return handleAdmin(request, env, url);
    }
    return json({ ok: false, error: "not_found" }, 404);
  },
};

async function handleTelegramRelay(request, env, url) {
  const match = url.pathname.match(/^\/bot([^/]+)\/([A-Za-z0-9_]+)$/);
  if (!match) return json({ ok: false, error: "bad_relay_path" }, 404);
  const [, token, method] = match;
  if (token !== env.TELEGRAM_BOT_TOKEN) return json({ ok: false, error: "invalid_bot_token" }, 401);
  const payload = await request.json();
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return new Response(await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}

async function handleMessage(message, env) {
  const chatId = String(message.chat?.id || "");
  const telegramId = String(message.from?.id || "");
  if (!chatId || !telegramId) return;
  const session = await getOrCreateSession(env, telegramId, chatId);
  const text = (message.text || "").trim();

  if (text.startsWith("/start")) {
    const referralCode = parseStartReferral(text);
    if (referralCode) {
      await updateSession(env, telegramId, { pending_referral_code: referralCode });
    }
    if (session.user_id) {
      await sendMessage(env, chatId, "پیامت را بفرست تا سریع تحلیلش کنم.");
    } else {
      await sendMessage(env, chatId, referralCode
        ? "به Message Decoder خوش آمدی. کد معرفی ثبت شد؛ برای فعال شدن هدیه معرف، شماره موبایلت را با دکمه زیر تایید کن."
        : "به Message Decoder خوش آمدی. برای شروع، شماره موبایلت را با دکمه زیر تایید کن.", contactKeyboard());
    }
    return;
  }

  if (text.startsWith("/referral")) {
    if (!session.user_id) {
      await sendMessage(env, chatId, "اول با /start شماره‌ات را وصل کن تا کد معرفی اختصاصی بگیری.", contactKeyboard());
      return;
    }
    const referral = await getReferral(env, session.user_id);
    await sendMessage(env, chatId, `کد معرفی تو:\n<b>${referral.code}</b>\n\nلینک دعوت:\n${referral.url}\n\nهر شماره جدیدی که با این کد ثبت‌نام کند، ۵ اعتبار برای تو فعال می‌شود.`);
    return;
  }

  if (text.startsWith("/cancel")) {
    await updateSession(env, telegramId, {
      state: "awaiting_message",
      message_text: null,
      relationship_type: null,
      user_goal: null,
      last_free_json: null,
      ghost_mode: 0,
    });
    await sendMessage(env, chatId, "لغو شد. پیام بعدی را بفرست.");
    return;
  }

  if (text.startsWith("/ghost")) {
    await updateSession(env, telegramId, { state: "awaiting_message", ghost_mode: 1 });
    await sendMessage(env, chatId, "Ghost Mode برای پیام بعدی روشن شد. تحلیل ذخیره نمی‌شود و پاسخ پولی روی آن فعال نیست.");
    return;
  }

  if (message.contact) {
    const contactUserId = String(message.contact.user_id || "");
    if (contactUserId && contactUserId !== telegramId) {
      await sendMessage(env, chatId, "برای امنیت، فقط شماره خودت را می‌توانی وصل کنی.");
      return;
    }
    const phone = normalizePhone(String(message.contact.phone_number || ""));
    if (!phone) {
      await sendMessage(env, chatId, "شماره دریافت نشد. دوباره از دکمه اشتراک‌گذاری شماره استفاده کن.");
      return;
    }
    const latestSession = await getOrCreateSession(env, telegramId, chatId);
    const linked = await linkUser(env, telegramId, chatId, phone, latestSession.pending_referral_code);
    await syncLiaraTelegramLink(env, phone, telegramId);
    const bonus = linked.created && linked.balance > 0 ? " اعتبار هدیه فعال شد." : "";
    await sendMessage(env, chatId, `حساب تلگرام وصل شد.${bonus}\nحالا پیام را بفرست.`);
    return;
  }

  if (!session.user_id) {
    await sendMessage(env, chatId, "برای تحلیل پیام در تلگرام، اول شماره موبایلت را تایید کن.", contactKeyboard());
    return;
  }

  if (!text) {
    await sendMessage(env, chatId, "فعلاً فقط متن پیام را می‌توانم تحلیل کنم.");
    return;
  }

  await updateSession(env, telegramId, {
    state: "awaiting_relationship",
    message_text: text,
    relationship_type: null,
    user_goal: null,
    last_free_json: null,
  });
  await sendMessage(env, chatId, "این پیام مربوط به کدام رابطه است؟", relationshipKeyboard());
}

async function handleCallback(callback, env) {
  const chatId = String(callback.message?.chat?.id || "");
  const telegramId = String(callback.from?.id || "");
  const data = String(callback.data || "");
  if (!chatId || !telegramId) return;
  await answerCallback(env, callback.id);
  const session = await getOrCreateSession(env, telegramId, chatId);

  if (!session.user_id) {
    await sendMessage(env, chatId, "اول شماره موبایل را تایید کن.", contactKeyboard());
    return;
  }

  if (data.startsWith("rel:")) {
    await updateSession(env, telegramId, {
      relationship_type: data.slice(4),
      state: "awaiting_goal",
    });
    await sendMessage(env, chatId, "هدفت از پاسخ دادن چیست؟", goalKeyboard());
    return;
  }

  if (data.startsWith("goal:")) {
    await runFreeDecode(env, chatId, telegramId, session, data.slice(5));
    return;
  }

  if (data.startsWith("paid:")) {
    await runPaidDecode(env, chatId, session, data.slice(5));
    return;
  }

  if (data === "buy") {
    await sendMessage(env, chatId, "فعلاً پرداخت داخل نسخه Worker وصل نیست. برای تست، همان اعتبار هدیه اول را استفاده کن.");
  }
}

async function runFreeDecode(env, chatId, telegramId, oldSession, goal) {
  const session = await getOrCreateSession(env, telegramId, chatId);
  if (!session.message_text) {
    await sendMessage(env, chatId, "پیامی برای تحلیل پیدا نکردم. لطفاً متن را دوباره بفرست.");
    return;
  }
  const free = await freeDecode(env, session.message_text, session.relationship_type || "unknown", goal);
  const isGhost = Number(session.ghost_mode || 0) === 1;
  let decodeId = null;
  if (!isGhost) {
    decodeId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO decodes (id, user_id, message_text, relationship_type, user_goal, free_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
      .bind(decodeId, session.user_id, session.message_text, session.relationship_type || "unknown", goal, JSON.stringify(free), now())
      .run();
  }
  await updateSession(env, telegramId, {
    state: "awaiting_message",
    user_goal: goal,
    last_free_json: JSON.stringify(free),
    ghost_mode: 0,
  });

  const text =
    `📊 <b>تحلیل سریع</b>\n` +
    `لنز غالب: ${free.dominant_lens}\n` +
    `سهم لنزها: Dopamine ${free.lens_mix.dopamine}% | Oxytocin ${free.lens_mix.oxytocin}% | Serotonin ${free.lens_mix.serotonin}%\n` +
    `شدت لحن: ${free.tone_stress.label} (${free.tone_stress.intensity}/100)\n\n` +
    `⚠️ ریسک مکالمه: ${free.conversation_risk}\n` +
    `💡 برداشت احتمالی: ${free.likely_underlying_need}\n` +
    `🔎 چرا این برداشت: ${free.why_this_lens || "از ترکیب لحن و کلمات پیام."}\n` +
    `🧭 مسیر پیشنهادی: ${free.recommended_direction}`;

  if (isGhost) {
    await sendMessage(env, chatId, `${text}\n\nGhost Mode روشن بود؛ این تحلیل ذخیره نشد.`);
    return;
  }
  await sendMessage(env, chatId, text, paidKeyboard(decodeId));
}

async function runPaidDecode(env, chatId, session, decodeId) {
  const user = await env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(session.user_id).first();
  if (!user) {
    await sendMessage(env, chatId, "حساب پیدا نشد. /start را بزن.");
    return;
  }
  const decode = await env.DB.prepare("SELECT * FROM decodes WHERE id = ? AND user_id = ?").bind(decodeId, user.id).first();
  if (!decode) {
    await sendMessage(env, chatId, "تحلیل پیدا نشد. پیام را دوباره بفرست.");
    return;
  }
  let paid = decode.paid_json ? JSON.parse(decode.paid_json) : null;
  const shouldRegenerate = !paid || paid.ai_generated !== true;
  if (shouldRegenerate) {
    if (!decode.paid_json && Number(user.credit_balance || 0) < 1) {
      await sendMessage(env, chatId, "اعتبارت تمام شده. پرداخت در نسخه سبک هنوز وصل نیست.", buyKeyboard());
      return;
    }
    paid = await paidDecodeWithAi(env, JSON.parse(decode.free_json), decode.relationship_type, decode.user_goal, decode.message_text);
    if (!paid) {
      await sendMessage(env, chatId, "هوش مصنوعی برای ساخت پاسخ کامل در دسترس نیست. اعتبارت کم نشد؛ چند دقیقه دیگر دوباره بزن.");
      return;
    }
    const alreadyCharged = Boolean(decode.paid_json);
    await env.DB.batch([
      env.DB.prepare("UPDATE decodes SET paid_json = ?, paid_at = ? WHERE id = ?").bind(JSON.stringify(paid), now(), decodeId),
      ...(alreadyCharged ? [] : [env.DB.prepare("UPDATE users SET credit_balance = credit_balance - 1 WHERE id = ?").bind(user.id)]),
    ]);
  }
  const balance = await env.DB.prepare("SELECT credit_balance FROM users WHERE id = ?").bind(user.id).first();
  const replies = paid.reply_options
    .map((reply) => `<b>${escapeHtml(reply.label)}</b>\n${escapeHtml(reply.text)}\nواکنش محتمل: ${escapeHtml(reply.reaction_prediction)}`)
    .join("\n\n");
  const avoid = paid.words_to_avoid?.length ? `\n\nکلمات پرریسک: ${paid.words_to_avoid.map(escapeHtml).join("، ")}` : "";
  await sendMessage(env, chatId, `🔓 <b>پاسخ‌های قابل ارسال</b>\n\n${replies}${avoid}\n\nاعتبار باقی‌مانده: ${balance.credit_balance}`);
}

async function freeDecode(env, text, relationship, goal) {
  const ai = await freeDecodeWithAi(env, text, relationship, goal);
  if (ai) return ai;
  return freeDecodeFallback(text, relationship, goal);
}

function freeDecodeFallback(text, relationship, goal) {
  const lower = text.toLowerCase();
  const professional = relationship === "manager_colleague" || relationship === "customer" || goal === "professional_reply";
  const respectWords = ["احترام", "ارزش", "مهم نیست", "دیده", "زحمت", "انتظار"];
  const safetyWords = ["نگران", "می‌ترسم", "سکوت", "کجایی", "دوست", "بی‌اهمیت"];
  const controlWords = ["چرا", "باید", "قرار بود", "پیگیری", "انجام", "نتیجه"];
  const score = (words) => words.reduce((sum, word) => sum + (lower.includes(word) ? 1 : 0), 0);
  const serotonin = score(respectWords) + (lower.includes("هر جور راحتی") ? 2 : 0);
  const oxytocin = score(safetyWords) + (relationship === "romantic" ? 1 : 0);
  const dopamine = score(controlWords) + (professional ? 2 : 0);
  const dominant = dopamine >= oxytocin && dopamine >= serotonin ? "نتیجه و کنترل" : oxytocin >= serotonin ? "امنیت و اعتماد" : "شأن و احترام";
  const total = Math.max(1, dopamine + oxytocin + serotonin);
  const mix = {
    dopamine: Math.round((dopamine / total) * 100),
    oxytocin: Math.round((oxytocin / total) * 100),
    serotonin: 0,
  };
  mix.serotonin = 100 - mix.dopamine - mix.oxytocin;
  const intensity = Math.min(90, 35 + (text.includes("!") ? 15 : 0) + (text.length > 120 ? 15 : 0) + Math.max(dopamine, oxytocin, serotonin) * 8);
  return {
    dominant_lens: dominant,
    lens_mix: mix,
    tone_stress: { label: intensity > 65 ? "پرتنش" : intensity > 45 ? "متوسط" : "ملایم/مبهم", intensity },
    conversation_risk: intensity > 65 ? "بالا؛ پاسخ دفاعی می‌تواند تنش را بیشتر کند." : "متوسط؛ بهتر است قبل از توضیح دادن، نیاز پشت پیام دیده شود.",
    likely_underlying_need: dominant === "شأن و احترام" ? "احتمالاً طرف مقابل می‌خواهد سهم، احترام یا زحمتش دیده شود." : dominant === "امنیت و اعتماد" ? "احتمالاً نیاز به اطمینان یا کم شدن ابهام وجود دارد." : "احتمالاً مسئله اصلی نتیجه، زمان‌بندی یا کنترل موقعیت است.",
    recommended_direction: professional ? "کوتاه، روشن، مسئولیت‌پذیر و بدون دفاع اضافه جواب بده." : "اول حس طرف مقابل را کوتاه ببین، بعد مرز یا خواسته‌ات را آرام بگو.",
  };
}

async function paidDecode(env, free, relationship, goal, originalMessage) {
  const ai = await paidDecodeWithAi(env, free, relationship, goal, originalMessage);
  if (ai) return ai;
  return paidDecodeFallback(free, relationship, goal);
}

function paidDecodeFallback(free, relationship, goal) {
  const professional = relationship === "manager_colleague" || relationship === "customer" || goal === "professional_reply";
  const boundary = goal === "set_boundary";
  const calm = goal === "calm_conflict" || goal === "avoid_needy";
  const base = professional
    ? "حق با شماست که پیگیری می‌کنید. من موضوع را بررسی می‌کنم و تا زمان مشخص نتیجه را شفاف اطلاع می‌دهم."
    : boundary
      ? "می‌فهمم این موضوع برات مهمه. در عین حال می‌خوام گفتگو محترمانه بمونه تا بتونیم درست حلش کنیم."
      : "می‌فهمم چرا ممکنه این برداشت رو کرده باشی. قصدم بی‌اهمیت کردن تو نبود؛ دوست دارم روشن‌تر درباره‌اش حرف بزنیم.";
  return {
    reply_options: [
      {
        label: professional ? "حرفه‌ای" : "ملایم",
        text: base,
        reaction_prediction: "احتمالاً تنش را کم می‌کند و مسیر گفتگو را روشن‌تر می‌کند.",
      },
      {
        label: "کوتاه",
        text: professional ? "درست می‌گید. پیگیری می‌کنم و نتیجه را شفاف اطلاع می‌دهم." : "می‌فهمم چی می‌گی. قصدم این نبود؛ بگذار بهتر توضیح بدهم.",
        reaction_prediction: "برای وقتی خوب است که نمی‌خواهی گفتگو طولانی شود.",
      },
      {
        label: calm ? "آرام‌کننده" : "قاطع",
        text: calm ? "برام مهمه که این گفتگو بدتر نشه. حرفت رو شنیدم و می‌خوام بدون دفاع جواب بدم." : "می‌خوام موضوع را حل کنیم، اما با کنایه یا فشار ادامه دادن برای من سازنده نیست.",
        reaction_prediction: "مرز را روشن می‌کند، اما هنوز در را برای گفتگو باز می‌گذارد.",
      },
    ],
    note: free.recommended_direction,
  };
}

async function freeDecodeWithAi(env, messageText, relationship, goal) {
  const payload = {
    task: "free_decode",
    message_text: messageText,
    relationship_type: relationship,
    user_goal: goal,
    output_shape: {
      dominant_lens: "هدف و کنترل | امنیت و اعتماد | شأن و احترام",
      lens_mix: { dopamine: 20, oxytocin: 60, serotonin: 20 },
      tone_stress: { label: "کنایه‌آمیز", intensity: 58 },
      conversation_risk: "string",
      likely_underlying_need: "string",
      recommended_direction: "string",
      why_this_lens: "string",
      alternative_read: "string",
    },
    requirements: [
      "خروجی فقط JSON معتبر باشد.",
      "تحلیل باید مشخصاً به کلمات و لحن همین پیام اشاره کند؛ متن آماده و عمومی ننویس.",
      "پاسخ قابل ارسال کامل در free نده.",
      "lens_mix جمعاً 100 باشد و intensity بین 0 تا 100 باشد.",
    ],
  };
  const data = await chatJson(env, payload, env.AI_FREE_MODEL);
  if (!data) return null;
  const fallback = freeDecodeFallback(messageText, relationship, goal);
  const lens = normalizeLens(data.dominant_lens) || fallback.dominant_lens;
  return {
    dominant_lens: lens,
    lens_mix: normalizeLensMix(data.lens_mix) || fallback.lens_mix,
    tone_stress: normalizeToneStress(data.tone_stress) || fallback.tone_stress,
    conversation_risk: cleanText(data.conversation_risk) || fallback.conversation_risk,
    likely_underlying_need: cleanText(data.likely_underlying_need) || fallback.likely_underlying_need,
    recommended_direction: cleanText(data.recommended_direction) || fallback.recommended_direction,
    why_this_lens: cleanText(data.why_this_lens) || fallback.why_this_lens,
    alternative_read: cleanText(data.alternative_read) || "ممکن است پیام از خستگی، عجله یا سبک بیان غیرمستقیم آمده باشد.",
    ai_generated: true,
  };
}

async function paidDecodeWithAi(env, free, relationship, goal, originalMessage) {
  const payload = {
    task: "paid_decode",
    original_message: originalMessage,
    free_output: free,
    relationship_type: relationship,
    user_goal: goal,
    output_shape: {
      reply_options: [
        { label: "نرم", text: "string", reaction_prediction: "string", why_it_works: "string" },
        { label: "قاطع", text: "string", reaction_prediction: "string", why_it_works: "string" },
        { label: "کوتاه", text: "string", reaction_prediction: "string", why_it_works: "string" },
      ],
      words_to_avoid: ["string"],
      copy_ready_reply: "string",
      deep_read: "string",
    },
    requirements: [
      "خروجی فقط JSON معتبر باشد.",
      "حداقل 3 و حداکثر 5 پاسخ آماده بده.",
      "هر پاسخ باید دقیقاً مناسب همین پیام باشد، نه متن عمومی.",
      "پاسخ‌ها از نظر کاربرد فرق داشته باشند: نرم، قاطع/مرزی، کوتاه، و اگر کاری بود حرفه‌ای.",
      "فارسی طبیعی و قابل کپی بنویس.",
    ],
  };
  const data = await chatJson(env, payload, env.AI_PAID_MODEL);
  if (!data || !Array.isArray(data.reply_options)) return null;
  const replies = data.reply_options
    .map((reply) => ({
      label: cleanText(reply.label) || "پاسخ پیشنهادی",
      text: cleanText(reply.text),
      reaction_prediction: cleanText(reply.reaction_prediction) || "احتمالاً واکنش طرف مقابل به لحن و وضوح پاسخ وابسته است.",
      why_it_works: cleanText(reply.why_it_works) || "این پاسخ هم پیام را می‌بیند و هم تنش را بی‌دلیل بالا نمی‌برد.",
    }))
    .filter((reply) => reply.text)
    .slice(0, 5);
  if (replies.length < 3) return null;
  return {
    reply_options: replies,
    words_to_avoid: Array.isArray(data.words_to_avoid) ? data.words_to_avoid.map(cleanText).filter(Boolean).slice(0, 8) : [],
    copy_ready_reply: cleanText(data.copy_ready_reply) || replies[0].text,
    deep_read: cleanText(data.deep_read) || free.likely_underlying_need,
    note: free.recommended_direction,
    ai_generated: true,
  };
}

async function chatJson(env, userPayload, model) {
  if (env.AI) {
    const data = await chatJsonWithWorkersAi(env, userPayload);
    if (data) return data;
  }
  if (!env.AI_API_KEY || !env.AI_API_BASE_URL) return null;
  const endpoint = `${env.AI_API_BASE_URL.replace(/\/$/, "")}/chat/completions`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.AI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: AI_SYSTEM_PROMPT },
          { role: "user", content: JSON.stringify(userPayload) },
        ],
        temperature: userPayload.task === "paid_decode" ? 0.75 : 0.35,
        response_format: { type: "json_object" },
      }),
    });
    if (!response.ok) {
      console.log(`AI request failed: ${response.status}`);
      return null;
    }
    const body = await response.json();
    const content = body?.choices?.[0]?.message?.content;
    return parseJsonObject(content);
  } catch (error) {
    console.log(`AI request error: ${error?.message || error}`);
    return null;
  }
}

async function chatJsonWithWorkersAi(env, userPayload) {
  try {
    const result = await env.AI.run(env.CF_AI_MODEL || "@cf/meta/llama-3.1-8b-instruct", {
      messages: [
        { role: "system", content: AI_SYSTEM_PROMPT },
        { role: "user", content: `${JSON.stringify(userPayload)}\n\nفقط یک JSON معتبر برگردان. هیچ توضیحی بیرون JSON ننویس.` },
      ],
      temperature: userPayload.task === "paid_decode" ? 0.65 : 0.25,
      max_tokens: userPayload.task === "paid_decode" ? 1800 : 1000,
    });
    return parseJsonObject(result?.response || result?.result || result?.text);
  } catch (error) {
    console.log(`Workers AI request error: ${error?.message || error}`);
    return null;
  }
}

function parseJsonObject(content) {
  if (!content) return null;
  try {
    const parsed = JSON.parse(content);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    const match = String(content).match(/\{[\s\S]*\}/);
    if (!match) return null;
    try {
      const parsed = JSON.parse(match[0]);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch {
      return null;
    }
  }
}

function normalizeLens(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("dopamine") || text.includes("کنترل") || text.includes("هدف")) return "هدف و کنترل";
  if (text.includes("oxytocin") || text.includes("اعتماد") || text.includes("امنیت")) return "امنیت و اعتماد";
  if (text.includes("serotonin") || text.includes("احترام") || text.includes("شأن")) return "شأن و احترام";
  return null;
}

function normalizeLensMix(value) {
  if (!value || typeof value !== "object") return null;
  const dopamine = clampInt(value.dopamine, 0, 100);
  const oxytocin = clampInt(value.oxytocin, 0, 100);
  let serotonin = clampInt(value.serotonin, 0, 100);
  const sum = dopamine + oxytocin + serotonin;
  if (sum <= 0) return null;
  if (sum !== 100) serotonin = Math.max(0, 100 - dopamine - oxytocin);
  return { dopamine, oxytocin, serotonin };
}

function normalizeToneStress(value) {
  if (!value || typeof value !== "object") return null;
  return {
    label: cleanText(value.label) || "مبهم",
    intensity: clampInt(value.intensity, 0, 100),
  };
}

function clampInt(value, min, max) {
  const number = Number.parseInt(String(value), 10);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function cleanText(value) {
  return String(value || "").trim();
}

async function getOrCreateSession(env, telegramId, chatId) {
  const existing = await env.DB.prepare("SELECT * FROM telegram_sessions WHERE telegram_id = ?").bind(telegramId).first();
  if (existing) {
    await env.DB.prepare("UPDATE telegram_sessions SET chat_id = ?, updated_at = ? WHERE telegram_id = ?").bind(chatId, now(), telegramId).run();
    return existing;
  }
  await env.DB.prepare(
    "INSERT INTO telegram_sessions (telegram_id, chat_id, state, created_at, updated_at) VALUES (?, ?, 'awaiting_contact', ?, ?)"
  )
    .bind(telegramId, chatId, now(), now())
    .run();
  return { telegram_id: telegramId, chat_id: chatId, state: "awaiting_contact" };
}

async function linkUser(env, telegramId, chatId, phone, pendingReferralCode) {
  const current = await env.DB.prepare("SELECT * FROM users WHERE phone = ?").bind(phone).first();
  if (current) {
    if (!current.referral_code) {
      await env.DB.prepare("UPDATE users SET referral_code = ? WHERE id = ?").bind(generateReferralCode(), current.id).run();
    }
    await env.DB.batch([
      env.DB.prepare("UPDATE users SET telegram_id = ? WHERE id = ?").bind(telegramId, current.id),
      env.DB.prepare("UPDATE telegram_sessions SET user_id = ?, chat_id = ?, state = 'awaiting_message', pending_referral_code = NULL, updated_at = ? WHERE telegram_id = ?").bind(current.id, chatId, now(), telegramId),
    ]);
    return { userId: current.id, balance: current.credit_balance, created: false };
  }
  const userId = crypto.randomUUID();
  const balance = Number(env.SIGNUP_BONUS_CREDITS || 1);
  const referralCode = generateReferralCode();
  const referrer = pendingReferralCode
    ? await env.DB.prepare("SELECT id FROM users WHERE referral_code = ?").bind(String(pendingReferralCode).toUpperCase()).first()
    : null;
  await env.DB.batch([
    env.DB.prepare("INSERT INTO users (id, phone, telegram_id, credit_balance, created_at, referral_code, referred_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?)").bind(userId, phone, telegramId, balance, now(), referralCode, referrer?.id || null),
    env.DB.prepare("UPDATE telegram_sessions SET user_id = ?, chat_id = ?, state = 'awaiting_message', pending_referral_code = NULL, updated_at = ? WHERE telegram_id = ?").bind(userId, chatId, now(), telegramId),
  ]);
  if (referrer && referrer.id !== userId) {
    await env.DB.prepare("UPDATE users SET credit_balance = credit_balance + 5, referral_awarded_at = COALESCE(referral_awarded_at, ?) WHERE id = ?").bind(now(), referrer.id).run();
  }
  return { userId, balance, created: true };
}

async function getReferral(env, userId) {
  const user = await env.DB.prepare("SELECT referral_code FROM users WHERE id = ?").bind(userId).first();
  let code = user?.referral_code;
  if (!code) {
    code = generateReferralCode();
    await env.DB.prepare("UPDATE users SET referral_code = ? WHERE id = ?").bind(code, userId).run();
  }
  return { code, url: `https://t.me/MeDecoderBot?start=ref_${code}` };
}

function generateReferralCode() {
  return crypto.randomUUID().replace(/-/g, "").slice(0, 8).toUpperCase();
}

function parseStartReferral(text) {
  const [, payload] = text.split(/\s+/, 2);
  if (!payload || !payload.startsWith("ref_")) return null;
  return payload.slice(4).trim().toUpperCase();
}

async function updateSession(env, telegramId, fields) {
  const keys = Object.keys(fields);
  if (!keys.length) return;
  const set = keys.map((key) => `${key} = ?`).join(", ");
  const values = keys.map((key) => fields[key]);
  await env.DB.prepare(`UPDATE telegram_sessions SET ${set}, updated_at = ? WHERE telegram_id = ?`).bind(...values, now(), telegramId).run();
}

async function handleAdmin(request, env, url) {
  const adminToken = request.headers.get("X-Admin-Token");
  if (!env.ADMIN_TOKEN || !adminToken || adminToken !== env.ADMIN_TOKEN) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }
  if (request.method === "GET" && url.pathname === "/admin/users") {
    const limit = Math.min(Number(url.searchParams.get("limit") || 100), 500);
    const q = url.searchParams.get("q");
    const params = [];
    let where = "";
    if (q) {
      where = "WHERE phone LIKE ? OR telegram_id LIKE ? OR referral_code LIKE ?";
      const like = `%${q}%`;
      params.push(like, like, like);
    }
    const rows = await env.DB.prepare(
      `SELECT
        id,
        phone,
        telegram_id,
        credit_balance,
        referral_code,
        referred_by_user_id,
        created_at,
        (SELECT COUNT(*) FROM users ru WHERE ru.referred_by_user_id = users.id) AS referral_count,
        (SELECT COUNT(*) FROM decodes d WHERE d.user_id = users.id) AS decodes_count,
        (SELECT COUNT(*) FROM decodes d WHERE d.user_id = users.id AND d.paid_json IS NOT NULL) AS paid_decodes_count,
        (SELECT MAX(created_at) FROM decodes d WHERE d.user_id = users.id) AS last_decode_at
      FROM users ${where} ORDER BY created_at DESC LIMIT ?`
    ).bind(...params, limit).all();
    return json({ items: rows.results || [] });
  }
  if (request.method === "GET" && url.pathname === "/admin/activity") {
    const limit = Math.min(Number(url.searchParams.get("limit") || 80), 200);
    const q = url.searchParams.get("q");
    const params = [];
    let where = "";
    if (q) {
      where = "WHERE phone LIKE ? OR user_id LIKE ? OR event_type LIKE ? OR detail LIKE ?";
      const like = `%${q}%`;
      params.push(like, like, like, like);
    }
    const rows = await env.DB.prepare(
      `WITH activity AS (
        SELECT
          'signup:' || id AS id,
          id AS user_id,
          phone AS phone,
          telegram_id AS telegram_id,
          'signup' AS event_type,
          'ثبت‌نام تلگرام' AS title,
          'اعتبار: ' || credit_balance || ' | کد معرفی: ' || COALESCE(referral_code, '-') AS detail,
          NULL AS status,
          created_at AS created_at
        FROM users
        UNION ALL
        SELECT
          'free:' || d.id AS id,
          d.user_id AS user_id,
          u.phone AS phone,
          u.telegram_id AS telegram_id,
          'free_decode' AS event_type,
          'تحلیل رایگان تلگرام' AS title,
          'رابطه: ' || d.relationship_type || ' | هدف: ' || d.user_goal AS detail,
          NULL AS status,
          d.created_at AS created_at
        FROM decodes d
        LEFT JOIN users u ON u.id = d.user_id
        UNION ALL
        SELECT
          'paid:' || d.id AS id,
          d.user_id AS user_id,
          u.phone AS phone,
          u.telegram_id AS telegram_id,
          'paid_decode' AS event_type,
          'تحلیل کامل تلگرام' AS title,
          'رابطه: ' || d.relationship_type || ' | هدف: ' || d.user_goal AS detail,
          'paid' AS status,
          COALESCE(d.paid_at, d.created_at) AS created_at
        FROM decodes d
        LEFT JOIN users u ON u.id = d.user_id
        WHERE d.paid_json IS NOT NULL
      )
      SELECT *
      FROM activity
      ${where}
      ORDER BY created_at DESC
      LIMIT ?`
    ).bind(...params, limit).all();
    return json({ items: rows.results || [], total: rows.results?.length || 0, limit });
  }
  if (request.method === "GET" && url.pathname === "/admin/metrics") {
    const users = await env.DB.prepare("SELECT COUNT(*) AS c FROM users").first();
    const decodes = await env.DB.prepare("SELECT COUNT(*) AS c FROM decodes").first();
    const paid = await env.DB.prepare("SELECT COUNT(*) AS c FROM decodes WHERE paid_json IS NOT NULL").first();
    const referrals = await env.DB.prepare("SELECT COUNT(*) AS c FROM users WHERE referred_by_user_id IS NOT NULL").first();
    const credits = await env.DB.prepare("SELECT COALESCE(SUM(credit_balance), 0) AS s FROM users").first();
    const broadcastable = await env.DB.prepare("SELECT COUNT(*) AS c FROM users WHERE telegram_id IS NOT NULL").first();
    return json({
      users: users.c || 0,
      free_decodes: decodes.c || 0,
      paid_decodes: paid.c || 0,
      referrals: referrals.c || 0,
      total_credits: credits.s || 0,
      broadcastable_users: broadcastable.c || 0,
      payments: 0,
      contacts: 0,
    });
  }
  if (request.method === "POST" && url.pathname === "/admin/credits/grant-all") {
    const body = await request.json().catch(() => ({}));
    const credits = clampInt(body.credits ?? 5, -1000, 1000);
    const result = await env.DB.prepare("UPDATE users SET credit_balance = credit_balance + ?").bind(credits).run();
    return json({ ok: true, updated_users: result.meta?.changes || 0 });
  }
  if (request.method === "POST" && url.pathname === "/admin/credits/grant") {
    const body = await request.json().catch(() => ({}));
    const credits = clampInt(body.credits ?? 0, -1000, 1000);
    const user = body.user_id
      ? await env.DB.prepare("SELECT id FROM users WHERE id = ?").bind(body.user_id).first()
      : await findUserByPhone(env, body.phone || "");
    if (!user) return json({ ok: false, error: "user_not_found" }, 404);
    await env.DB.prepare("UPDATE users SET credit_balance = credit_balance + ? WHERE id = ?").bind(credits, user.id).run();
    const updated = await env.DB.prepare("SELECT id, credit_balance FROM users WHERE id = ?").bind(user.id).first();
    return json({ ok: true, user_id: updated.id, credit_balance: updated.credit_balance });
  }
  if (request.method === "POST" && url.pathname === "/admin/broadcast") {
    const body = await request.json().catch(() => ({}));
    const text = cleanText(body.text);
    if (!text) return json({ ok: false, error: "text_required" }, 400);
    const rows = await env.DB.prepare("SELECT id, phone, telegram_id, referral_code FROM users WHERE telegram_id IS NOT NULL").all();
    let sent = 0;
    let failed = 0;
    const results = [];
    for (const row of rows.results || []) {
      try {
        await sendMessage(env, row.telegram_id, text);
        sent += 1;
        results.push({
          user_id: row.id,
          phone: row.phone,
          telegram_id: row.telegram_id,
          referral_code: row.referral_code,
          status: "sent",
        });
      } catch (error) {
        failed += 1;
        results.push({
          user_id: row.id,
          phone: row.phone,
          telegram_id: row.telegram_id,
          referral_code: row.referral_code,
          status: "failed",
          error: error?.message || "send_failed",
        });
      }
    }
    return json({ ok: true, sent, failed, results });
  }
  return json({ ok: false, error: "not_found" }, 404);
}

async function sendMessage(env, chatId, text, replyMarkup) {
  const payload = { chat_id: chatId, text, parse_mode: "HTML" };
  if (replyMarkup) payload.reply_markup = replyMarkup;
  await telegramApi(env, "sendMessage", payload);
}

async function answerCallback(env, callbackQueryId) {
  if (!callbackQueryId) return;
  await telegramApi(env, "answerCallbackQuery", { callback_query_id: callbackQueryId });
}

async function telegramApi(env, method, payload) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Telegram ${method} failed: ${response.status}`);
  return response.json();
}

async function syncLiaraTelegramLink(env, phone, telegramId) {
  if (!env.LIARA_API_URL || !env.TELEGRAM_BRIDGE_SECRET) return;
  try {
    await fetch(`${env.LIARA_API_URL.replace(/\/$/, "")}/auth/telegram-link`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-telegram-bridge-secret": env.TELEGRAM_BRIDGE_SECRET,
      },
      body: JSON.stringify({ phone, telegram_id: String(telegramId) }),
    });
  } catch (_) {
    // Best-effort sync. Telegram onboarding must still work if Liara is unreachable.
  }
}

function contactKeyboard() {
  return {
    keyboard: [[{ text: "اشتراک‌گذاری شماره موبایل", request_contact: true }]],
    resize_keyboard: true,
    one_time_keyboard: true,
  };
}

function relationshipKeyboard() {
  return { inline_keyboard: RELATIONSHIPS.map(([key, label]) => [{ text: label, callback_data: `rel:${key}` }]) };
}

function goalKeyboard() {
  return { inline_keyboard: GOALS.map(([key, label]) => [{ text: label, callback_data: `goal:${key}` }]) };
}

function paidKeyboard(decodeId) {
  return {
    inline_keyboard: [
      [{ text: "ساخت پاسخ قابل ارسال - ۱ اعتبار", callback_data: `paid:${decodeId}` }],
      [{ text: "شارژ اعتبار", callback_data: "buy" }],
    ],
  };
}

function buyKeyboard() {
  return { inline_keyboard: [[{ text: "فعلاً بعداً وصل می‌شود", callback_data: "buy" }]] };
}

function normalizePhone(value) {
  let clean = value.replace(/[۰-۹]/g, (digit) => "۰۱۲۳۴۵۶۷۸۹".indexOf(digit)).replace(/\D/g, "");
  if (clean.startsWith("0098")) clean = clean.slice(2);
  if (clean.startsWith("98") && clean.length === 12) return `0${clean.slice(2)}`;
  if (clean.startsWith("9") && clean.length === 10) return `0${clean}`;
  return clean;
}

function phoneVariants(value) {
  const normalized = normalizePhone(String(value || ""));
  const variants = new Set([normalized]);
  if (normalized.startsWith("0")) {
    variants.add(`98${normalized.slice(1)}`);
    variants.add(`+98${normalized.slice(1)}`);
  }
  return [...variants].filter(Boolean);
}

async function findUserByPhone(env, phone) {
  const variants = phoneVariants(phone);
  if (!variants.length) return null;
  const placeholders = variants.map(() => "?").join(", ");
  return env.DB.prepare(`SELECT id FROM users WHERE phone IN (${placeholders})`).bind(...variants).first();
}

function escapeHtml(value) {
  return String(value || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function now() {
  return new Date().toISOString();
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
