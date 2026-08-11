const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

const clean = (value, max = 2000) =>
  String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);

const validEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
const DEFAULT_PILOT_REQUEST_TO = "frameleads@gmail.com";

async function readPayload(request) {
  const type = request.headers.get("content-type") || "";

  if (type.includes("application/json")) {
    return request.json();
  }

  const form = await request.formData();
  return Object.fromEntries(form.entries());
}

async function storeLead(env, lead) {
  if (!env.PILOT_REQUESTS_DB) return false;

  await env.PILOT_REQUESTS_DB.batch([
    env.PILOT_REQUESTS_DB.prepare(
      `CREATE TABLE IF NOT EXISTS pilot_requests (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        company TEXT NOT NULL,
        role TEXT,
        workflow TEXT NOT NULL,
        page TEXT,
        user_agent TEXT,
        ip TEXT,
        submitted_at TEXT NOT NULL
      )`
    ),
    env.PILOT_REQUESTS_DB.prepare(
      `CREATE INDEX IF NOT EXISTS idx_pilot_requests_submitted_at
        ON pilot_requests(submitted_at)`
    ),
  ]);

  await env.PILOT_REQUESTS_DB.prepare(
    `INSERT INTO pilot_requests (
      id,
      name,
      email,
      company,
      role,
      workflow,
      page,
      user_agent,
      ip,
      submitted_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      crypto.randomUUID(),
      lead.name,
      lead.email,
      lead.company,
      lead.role,
      lead.workflow,
      lead.page,
      lead.userAgent,
      lead.ip,
      lead.submittedAt
    )
    .run();

  return true;
}

async function sendWebhook(env, lead) {
  if (!env.PILOT_REQUEST_WEBHOOK_URL) return false;

  const headers = { "content-type": "application/json" };
  if (env.PILOT_REQUEST_WEBHOOK_SECRET) {
    headers.authorization = `Bearer ${env.PILOT_REQUEST_WEBHOOK_SECRET}`;
  }

  const response = await fetch(env.PILOT_REQUEST_WEBHOOK_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(lead),
  });

  if (!response.ok) {
    throw new Error("Pilot request webhook rejected the submission.");
  }

  return true;
}

async function sendResendEmail(env, message) {
  if (!env.RESEND_API_KEY || !env.PILOT_REQUEST_FROM) return false;

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.RESEND_API_KEY}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      from: env.PILOT_REQUEST_FROM,
      to: [message.to],
      reply_to: message.replyTo,
      subject: message.subject,
      text: message.text,
    }),
  });

  if (!response.ok) {
    throw new Error("Pilot request email provider rejected the submission.");
  }

  return true;
}

async function sendInternalPilotEmail(env, lead) {
  const to = clean(env.PILOT_REQUEST_TO, 254) || DEFAULT_PILOT_REQUEST_TO;

  if (!env.RESEND_API_KEY || !env.PILOT_REQUEST_FROM) return false;

  const subject = `AMO Helix pilot request: ${lead.company}`;
  const text = [
    "New AMO Helix pilot request",
    "",
    `Name: ${lead.name}`,
    `Email: ${lead.email}`,
    `Company: ${lead.company}`,
    `Role: ${lead.role || "Not provided"}`,
    `Workflow: ${lead.workflow}`,
    `Page: ${lead.page}`,
    `Submitted: ${lead.submittedAt}`,
    `IP: ${lead.ip || "Unknown"}`,
  ].join("\n");

  return sendResendEmail(env, {
    to,
    replyTo: lead.email,
    subject,
    text,
  });
}

async function sendRequesterConfirmationEmail(env, lead) {
  const replyTo = clean(env.PILOT_REQUEST_TO, 254) || DEFAULT_PILOT_REQUEST_TO;

  if (!env.RESEND_API_KEY || !env.PILOT_REQUEST_FROM) return false;

  const subject = "AMO Helix pilot request received";
  const text = [
    `Hi ${lead.name},`,
    "",
    "We received your AMO Helix pilot request.",
    "",
    "What we have on file:",
    `Company: ${lead.company}`,
    `Workflow: ${lead.workflow}`,
    "",
    "We will review the workflow and follow up with the next step.",
    "",
    "AMO Helix",
  ].join("\n");

  return sendResendEmail(env, {
    to: lead.email,
    replyTo,
    subject,
    text,
  });
}

async function sendFormSubmitEmail(env, lead) {
  const to = clean(env.PILOT_REQUEST_TO, 254) || DEFAULT_PILOT_REQUEST_TO;
  if (env.RESEND_API_KEY || env.PILOT_REQUEST_DISABLE_FORMSUBMIT === "true") return false;

  const response = await fetch(`https://formsubmit.co/ajax/${encodeURIComponent(to)}`, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      _subject: `AMO Helix pilot request: ${lead.company}`,
      _template: "table",
      _captcha: "false",
      _replyto: lead.email,
      name: lead.name,
      email: lead.email,
      company: lead.company,
      role: lead.role || "Not provided",
      workflow: lead.workflow,
      page: lead.page,
      submitted_at: lead.submittedAt,
    }),
  });

  if (!response.ok) {
    throw new Error("Pilot request email fallback rejected the submission.");
  }

  return true;
}

export async function onRequestPost({ request, env }) {
  let body;

  try {
    body = await readPayload(request);
  } catch (error) {
    return json({ ok: false, message: "Please check the form and try again." }, 400);
  }

  if (clean(body.website, 200)) {
    return json({ ok: true });
  }

  const lead = {
    name: clean(body.name, 160),
    email: clean(body.email, 254).toLowerCase(),
    company: clean(body.company, 180),
    role: clean(body.role, 180),
    workflow: clean(body.workflow, 2200),
    page: clean(body.page, 500),
    submittedAt: new Date().toISOString(),
    userAgent: clean(request.headers.get("user-agent"), 500),
    ip: clean(request.headers.get("cf-connecting-ip"), 80),
  };

  if (!lead.name || !validEmail(lead.email) || !lead.company || !lead.workflow) {
    return json({ ok: false, message: "Please complete the required fields with a valid work email." }, 400);
  }

  try {
    const storedInD1 = await storeLead(env, lead);
    let deliveredByWebhook = false;
    let deliveredByEmail = false;

    try {
      deliveredByWebhook = await sendWebhook(env, lead);
    } catch (error) {
      deliveredByWebhook = false;
    }

    try {
      deliveredByEmail = await sendInternalPilotEmail(env, lead);
    } catch (error) {
      deliveredByEmail = false;
    }

    try {
      await sendRequesterConfirmationEmail(env, lead);
    } catch (error) {
      // The lead has already been saved and the internal alert remains the source of truth.
    }

    try {
      deliveredByEmail = deliveredByEmail || (await sendFormSubmitEmail(env, lead));
    } catch (error) {
      deliveredByEmail = false;
    }

    if (!storedInD1 && !deliveredByWebhook && !deliveredByEmail) {
      return json(
        {
          ok: false,
          message: "Pilot request delivery is not configured yet.",
        },
        503
      );
    }

    return json({ ok: true });
  } catch (error) {
    return json(
      {
        ok: false,
        message: "We could not send the request. Please try again.",
      },
      502
    );
  }
}

export function onRequestOptions() {
  return json({ ok: true });
}
