(() => {
  if (!('serviceWorker' in navigator)) return;

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
      .catch((error) => console.warn('Qatrah PWA service worker registration failed:', error));
  });

  let installPrompt = null;
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    installPrompt = event;
    if (document.getElementById('qatrah-install-app')) return;

    const button = document.createElement('button');
    button.id = 'qatrah-install-app';
    button.type = 'button';
    button.className = 'qatrah-install-button';
    button.textContent = '＋ تثبيت التطبيق';
    button.setAttribute('aria-label', 'تثبيت تطبيق قطرة حياة');
    button.addEventListener('click', async () => {
      if (!installPrompt) return;
      installPrompt.prompt();
      await installPrompt.userChoice;
      installPrompt = null;
      button.remove();
    });
    document.body.appendChild(button);
  });

  window.addEventListener('appinstalled', () => {
    document.getElementById('qatrah-install-app')?.remove();
    installPrompt = null;
  });
})();
