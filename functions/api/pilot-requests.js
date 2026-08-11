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

const csvValue = (value) => `"${String(value || "").replace(/"/g, '""')}"`;

async function ensureSchema(db) {
  await db.batch([
    db.prepare(
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
    db.prepare(
      `CREATE INDEX IF NOT EXISTS idx_pilot_requests_submitted_at
        ON pilot_requests(submitted_at)`
    ),
  ]);
}

function hasAccess(request, env) {
  const expected = clean(env.PILOT_REQUESTS_ACCESS_TOKEN, 500);
  if (!expected) return { ok: false, status: 503, message: "Pilot request access is not configured yet." };

  const url = new URL(request.url);
  const authorization = request.headers.get("authorization") || "";
  const bearer = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7) : "";
  const provided = clean(request.headers.get("x-pilot-token") || bearer || url.searchParams.get("token"), 500);

  if (provided !== expected) {
    return { ok: false, status: 401, message: "Enter the pilot request access key." };
  }

  return { ok: true };
}

async function listLeads(env) {
  if (!env.PILOT_REQUESTS_DB) {
    throw new Error("Pilot request database is not configured.");
  }

  await ensureSchema(env.PILOT_REQUESTS_DB);

  const result = await env.PILOT_REQUESTS_DB.prepare(
    `SELECT
      id,
      name,
      email,
      company,
      role,
      workflow,
      page,
      submitted_at AS submittedAt
    FROM pilot_requests
    ORDER BY submitted_at DESC
    LIMIT 100`
  ).all();

  return result.results || [];
}

async function deleteLead(env, id) {
  if (!env.PILOT_REQUESTS_DB) {
    throw new Error("Pilot request database is not configured.");
  }

  await ensureSchema(env.PILOT_REQUESTS_DB);
  await env.PILOT_REQUESTS_DB.prepare("DELETE FROM pilot_requests WHERE id = ?").bind(id).run();
}

async function deleteTestLeads(env) {
  if (!env.PILOT_REQUESTS_DB) {
    throw new Error("Pilot request database is not configured.");
  }

  await ensureSchema(env.PILOT_REQUESTS_DB);
  const result = await env.PILOT_REQUESTS_DB.prepare(
    `DELETE FROM pilot_requests
    WHERE lower(email) IN (
      'production-test@example.com',
      'preview-alias@example.com',
      'preview-test-2@example.com',
      'live-inbox-test@example.com',
      'status-copy-test@example.com',
      'final-live-check@example.com'
    )
    RETURNING id`
  ).all();

  return result.results || [];
}

async function readDeletePayload(request) {
  const type = request.headers.get("content-type") || "";
  if (!type.includes("application/json")) return {};
  return request.json();
}

function csv(leads) {
  const headers = ["Submitted", "Name", "Email", "Company", "Role", "Workflow", "Page"];
  const rows = leads.map((lead) => [
    lead.submittedAt,
    lead.name,
    lead.email,
    lead.company,
    lead.role,
    lead.workflow,
    lead.page,
  ]);

  return [headers, ...rows].map((row) => row.map(csvValue).join(",")).join("\n");
}

export async function onRequestGet({ request, env }) {
  const access = hasAccess(request, env);
  if (!access.ok) return json({ ok: false, message: access.message }, access.status);

  try {
    const leads = await listLeads(env);
    const url = new URL(request.url);

    if (url.searchParams.get("format") === "csv") {
      return new Response(csv(leads), {
        headers: {
          "content-type": "text/csv; charset=utf-8",
          "content-disposition": "attachment; filename=amo-helix-pilot-requests.csv",
          "cache-control": "no-store",
        },
      });
    }

    return json({ ok: true, leads });
  } catch (error) {
    return json({ ok: false, message: "Pilot requests could not be loaded." }, 502);
  }
}

export async function onRequestDelete({ request, env }) {
  const access = hasAccess(request, env);
  if (!access.ok) return json({ ok: false, message: access.message }, access.status);

  try {
    const body = await readDeletePayload(request);
    const id = clean(body.id, 80);
    const deleteTests = body.deleteTests === true;

    if (deleteTests) {
      const deleted = await deleteTestLeads(env);
      return json({ ok: true, deleted: deleted.length });
    }

    if (!id) {
      return json({ ok: false, message: "Select a pilot request to delete." }, 400);
    }

    await deleteLead(env, id);
    return json({ ok: true, deleted: 1 });
  } catch (error) {
    return json({ ok: false, message: "Pilot request could not be deleted." }, 502);
  }
}

export function onRequestOptions() {
  return json({ ok: true });
}
