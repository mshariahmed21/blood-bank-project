(() => {
  let lastTitle = document.title;
  async function poll() {
    try {
      const response = await fetch('/api/notifications', { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      for (const item of (data.latest || [])) {
        if ('Notification' in window && Notification.permission === 'granted' && document.hidden) {
          const notice = new Notification('رسالة جديدة | قطرة حياة', { body: item.body || 'وصلتك رسالة جديدة' });
          notice.onclick = () => { window.focus(); window.location.href = item.url; };
        } else if (!document.hidden) {
          document.title = 'رسالة جديدة · قطرة حياة';
          setTimeout(() => { document.title = lastTitle; }, 3500);
        }
      }
    } catch (_) { /* best effort */ }
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  poll();
  setInterval(poll, 15000);
  const button = document.getElementById('enable-notifications');
  const status = document.getElementById('notification-status');
  if (button && status) {
    if (!('Notification' in window)) { button.hidden = true; status.textContent = 'هذا المتصفح لا يدعم إشعارات سطح المكتب.'; }
    button.addEventListener('click', async () => {
      const permission = await Notification.requestPermission();
      status.textContent = permission === 'granted' ? 'تم السماح بإشعارات المتصفح أثناء استخدام الموقع.' : 'لم يتم السماح بالإشعارات؛ ستظهر التنبيهات داخل الموقع عند فتحه.';
    });
  }
})();
