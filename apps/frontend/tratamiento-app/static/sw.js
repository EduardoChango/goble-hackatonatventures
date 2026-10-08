// Service worker: hace la app instalable y muestra notificaciones.
// Para avisar con la app CERRADA hace falta Web Push desde el servidor (siguiente paso, ver README).
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});

self.addEventListener('push', (e) => {
  let d = {};
  try { d = e.data.json(); } catch (_) {}
  e.waitUntil(self.registration.showNotification(d.titulo || 'Mi tratamiento', {
    body: d.corto || '', icon: '/static/icons/icon-192.png', data: { url: d.url || '/' },
  }));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((lista) => {
    for (const c of lista) {
      if ('focus' in c) { c.navigate(url); return c.focus(); }
    }
    return clients.openWindow(url);
  }));
});
