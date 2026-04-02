/**
 * Cloudflare Worker — Investment Dashboard API Proxy
 *
 * Proxies requests to external APIs (Finnhub, FRED, Gemini, DashScope)
 * and injects API keys from environment secrets so they stay hidden
 * from the browser.
 *
 * Environment secrets (set via `wrangler secret put`):
 *   FINNHUB_KEY, FRED_KEY, GEMINI_KEY, DASHSCOPE_KEY
 *
 * Environment variables (set in wrangler.toml):
 *   ALLOWED_ORIGIN — the GitHub Pages origin for CORS
 */

const ROUTES = {
  '/finnhub': handleFinnhub,
  '/fred': handleFRED,
  '/gemini': handleGemini,
  '/dashscope': handleDashScope,
};

export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return corsResponse(env, new Response(null, { status: 204 }));
    }

    const url = new URL(request.url);

    // Health check
    if (url.pathname === '/') {
      return corsResponse(env, Response.json({ status: 'ok', routes: Object.keys(ROUTES) }));
    }

    // Match route by prefix
    for (const [prefix, handler] of Object.entries(ROUTES)) {
      if (url.pathname.startsWith(prefix)) {
        try {
          const resp = await handler(request, url, env);
          return corsResponse(env, resp);
        } catch (e) {
          return corsResponse(env, Response.json({ error: e.message }, { status: 502 }));
        }
      }
    }

    return corsResponse(env, Response.json({ error: 'not found' }, { status: 404 }));
  },
};

// ── Finnhub ──────────────────────────────────────────────
// GET /finnhub/quote?symbol=SPY  →  finnhub.io/api/v1/quote?symbol=SPY&token=KEY
// GET /finnhub/news?category=general  →  finnhub.io/api/v1/news?...&token=KEY
async function handleFinnhub(request, url, env) {
  const key = env.FINNHUB_KEY;
  if (!key) return Response.json({ error: 'FINNHUB_KEY not configured' }, { status: 500 });

  // /finnhub/quote → /api/v1/quote
  const apiPath = url.pathname.replace('/finnhub', '/api/v1');
  const params = new URLSearchParams(url.search);
  params.set('token', key);

  const target = `https://finnhub.io${apiPath}?${params}`;
  const resp = await fetch(target, { signal: AbortSignal.timeout(10000) });
  return new Response(resp.body, { status: resp.status, headers: { 'Content-Type': 'application/json' } });
}

// ── FRED ─────────────────────────────────────────────────
// GET /fred/observations?series_id=DGS10&...  →  api.stlouisfed.org/fred/series/observations?...&api_key=KEY
async function handleFRED(request, url, env) {
  const key = env.FRED_KEY;
  if (!key) return Response.json({ error: 'FRED_KEY not configured' }, { status: 500 });

  const params = new URLSearchParams(url.search);
  params.set('api_key', key);
  params.set('file_type', 'json');

  const target = `https://api.stlouisfed.org/fred/series/observations?${params}`;
  const resp = await fetch(target, { signal: AbortSignal.timeout(15000) });
  return new Response(resp.body, { status: resp.status, headers: { 'Content-Type': 'application/json' } });
}

// ── Gemini ───────────────────────────────────────────────
// POST /gemini  body: { contents, generationConfig }
async function handleGemini(request, url, env) {
  const key = env.GEMINI_KEY;
  if (!key) return Response.json({ error: 'GEMINI_KEY not configured' }, { status: 500 });

  const body = await request.text();
  const target = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${key}`;
  const resp = await fetch(target, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal: AbortSignal.timeout(25000),
  });
  return new Response(resp.body, { status: resp.status, headers: { 'Content-Type': 'application/json' } });
}

// ── DashScope (阿里云百炼) ────────────────────────────────
// POST /dashscope  body: { model, messages, ... }
async function handleDashScope(request, url, env) {
  const key = env.DASHSCOPE_KEY;
  if (!key) return Response.json({ error: 'DASHSCOPE_KEY not configured' }, { status: 500 });

  const body = await request.text();
  const target = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions';
  const resp = await fetch(target, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${key}`,
    },
    body,
    signal: AbortSignal.timeout(30000),
  });
  return new Response(resp.body, { status: resp.status, headers: { 'Content-Type': 'application/json' } });
}

// ── CORS helper ──────────────────────────────────────────
function corsResponse(env, response) {
  const origin = env.ALLOWED_ORIGIN || '*';
  const headers = new Headers(response.headers);
  headers.set('Access-Control-Allow-Origin', origin);
  headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Content-Type');
  headers.set('Access-Control-Max-Age', '86400');
  return new Response(response.body, {
    status: response.status,
    headers,
  });
}
