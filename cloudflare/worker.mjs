/**
 * SocietyOS Cloudflare Worker: React static assets + optional same-origin API proxy.
 * This file DOES NOT run the Python FastAPI backend on Cloudflare.
 * Configure API_BACKEND_URL (e.g. https://api.example.com) if an API host exists.
 */
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);

    if (incoming.pathname === '/__deployment/status') {
      return jsonResponse({
        service: 'societyos',
        cloudflare_worker: 'running',
        static_assets: 'configured',
        api_proxy_configured: Boolean((env.API_BACKEND_URL || '').trim()),
        fastapi_hosted_here: false,
      });
    }

    if (incoming.pathname === '/api' || incoming.pathname.startsWith('/api/')) {
      const configured = (env.API_BACKEND_URL || '').trim();
      if (!configured) {
        return jsonResponse({
          detail: 'API backend is not connected. Set API_BACKEND_URL in Cloudflare Worker settings to an independently hosted FastAPI API.',
        }, 503);
      }

      let upstream;
      try {
        upstream = new URL(configured);
      } catch (_) {
        return jsonResponse({detail: 'Invalid API_BACKEND_URL configuration.'}, 503);
      }
      if (upstream.protocol !== 'https:' && upstream.protocol !== 'http:') {
        return jsonResponse({detail: 'API_BACKEND_URL must be an HTTP(S) URL.'}, 503);
      }
      if (upstream.origin === incoming.origin) {
        return jsonResponse({detail: 'API_BACKEND_URL must not point back to this Worker.'}, 503);
      }

      const target = new URL(upstream.origin);
      const prefix = upstream.pathname.replace(/\/+$/, '');
      target.pathname = `${prefix}${incoming.pathname}`;
      target.search = incoming.search;
      try {
        // Using Request as the second argument preserves streamed bodies and
        // authorization headers for POST/PUT without buffering request data.
        const forwarded = new Request(target.toString(), request);
        forwarded.headers.delete('host');
        return await fetch(forwarded);
      } catch (error) {
        // Do not expose internal upstream host or secrets to clients.
        return jsonResponse({detail: 'API backend could not be reached.'}, 502);
      }
    }

    return env.ASSETS.fetch(request);
  },
};
