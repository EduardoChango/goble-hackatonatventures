// JavaScript común: avisos (pop-up y notificación del sistema), ubicación y panel de demo.
(function () {
  const $ = (s) => document.querySelector(s);

  // ---- Service worker (PWA) ----
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  // ---- Avisos ----
  const cola = [];
  let actual = null;

  function mostrarSiguiente() {
    const popup = $('#popup');
    actual = cola.shift() || null;
    if (!actual) { popup.hidden = true; return; }
    $('#popup-titulo').textContent = actual.titulo;
    $('#popup-cuerpo').textContent = actual.cuerpo;
    $('#popup-accion').textContent = actual.dosis ? 'Ya la tomé' : 'Ver';
    popup.hidden = false;
  }

  function notificarSistema(a) {
    // Solo si la app no está a la vista: si la están mirando, basta el pop-up.
    if (!document.hidden || !('Notification' in window) || Notification.permission !== 'granted') return;
    const opciones = { body: a.corto, icon: '/static/icons/icon-192.png', tag: a.titulo + a.cuerpo, data: { url: a.url } };
    if (navigator.serviceWorker && navigator.serviceWorker.ready) {
      navigator.serviceWorker.ready.then((reg) => reg.showNotification(a.titulo, opciones));
    } else {
      new Notification(a.titulo, opciones);
    }
  }

  function recibir(avisos) {
    avisos.forEach((a) => { cola.push(a); notificarSistema(a); });
    if (!actual && cola.length) mostrarSiguiente();
  }

  async function consultar() {
    try {
      const r = await fetch('/api/avisos', { cache: 'no-store' });
      recibir((await r.json()).avisos || []);
    } catch (e) { /* sin conexión: se intenta de nuevo */ }
  }

  $('#popup-cerrar').addEventListener('click', mostrarSiguiente);
  $('#popup-accion').addEventListener('click', async () => {
    const a = actual;
    if (a && a.dosis) {
      await fetch('/plan/tomar', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'id=' + encodeURIComponent(a.dosis) + '&volver=/' });
      mostrarSiguiente();
      if (['/', '/plan'].includes(location.pathname)) location.reload();
    } else if (a && a.url) {
      location.href = a.url;
    } else {
      mostrarSiguiente();
    }
  });

  setInterval(consultar, 4000);
  consultar();

  // ---- Activar notificaciones del sistema (necesita un toque del usuario) ----
  function mostrarEstadoAvisos() {
    const el = $('#avisos-estado');
    if (!el) return;
    if (!('Notification' in window)) { el.textContent = 'Este navegador no permite notificaciones.'; return; }
    const p = Notification.permission;
    el.textContent = p === 'granted' ? 'Avisos activados en este dispositivo.'
      : p === 'denied' ? 'Bloqueaste las notificaciones. Actívalas en los ajustes del navegador.'
      : 'Aún no activaste los avisos.';
  }
  window.activarAvisos = function () {
    if (!('Notification' in window)) { mostrarEstadoAvisos(); return; }
    Notification.requestPermission().then(mostrarEstadoAvisos);
  };
  mostrarEstadoAvisos();

  // ---- Ubicación ----
  window.usarUbicacion = function (guardar) {
    const estado = $('#ubic-estado');
    if (!navigator.geolocation) { if (estado) estado.textContent = 'Este dispositivo no da la ubicación. Escribe la dirección.'; return; }
    if (estado) estado.textContent = 'Buscando tu ubicación…';
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const { latitude: lat, longitude: lng } = pos.coords;
      if (guardar) {
        await fetch('/api/ubicacion', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lat, lng }) });
        location.reload();
      } else {
        $('#lat').value = lat; $('#lng').value = lng;
        if (estado) estado.textContent = 'Ubicación lista (' + lat.toFixed(4) + ', ' + lng.toFixed(4) + ').';
      }
    }, () => { if (estado) estado.textContent = 'No se pudo obtener la ubicación. Revisa el permiso del navegador.'; },
    { enableHighAccuracy: true, timeout: 10000 });
  };

  // ---- Panel de demo ----
  const demo = $('#demo');
  $('#demo-abrir').addEventListener('click', () => {
    demo.hidden = !demo.hidden;
    $('#demo-abrir').setAttribute('aria-expanded', String(!demo.hidden));
  });
  demo.addEventListener('click', async (e) => {
    const b = e.target.closest('button[data-accion]');
    if (!b) return;
    const cuerpo = { accion: b.dataset.accion, hora: b.dataset.hora, tipo: b.dataset.tipo };
    await fetch('/api/simular', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) });
    demo.hidden = true;
    if (cuerpo.accion === 'reset') { location.href = '/'; return; }
    await consultar();
  });
})();
