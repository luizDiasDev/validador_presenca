const OFFLINE_HTML = `<!doctype html><html lang="pt-br"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ADSUM</title>
<body style="font-family:sans-serif;background:#F7F3EA;color:#1F2A3C;padding:32px;text-align:center">
<h1 style="color:#0F1B2E">ADSUM</h1>
<p>Sem conexão com a internet. O check-in precisa de internet para validar o QR Code e a localização.</p>
</body></html>`;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") return;
  event.respondWith(
    fetch(event.request).catch(
      () => new Response(OFFLINE_HTML, { headers: { "Content-Type": "text/html; charset=utf-8" } })
    )
  );
});
