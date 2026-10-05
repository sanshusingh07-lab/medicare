document.addEventListener('DOMContentLoaded', () => {
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  if (menuToggle && sidebar) menuToggle.addEventListener('click', () => sidebar.classList.toggle('show'));
  document.querySelectorAll('.snooze-btn').forEach((button) => {
    button.addEventListener('click', () => {
      button.disabled = true;
      button.textContent = 'Snoozed 10 min';
      setTimeout(() => { button.disabled = false; button.textContent = 'Snooze'; }, 600000);
    });
  });
  const permission = document.getElementById('notificationPermission');
  if (permission) permission.addEventListener('click', async () => {
    if (!('Notification' in window)) { permission.textContent = 'Not supported by this browser'; return; }
    const value = await Notification.requestPermission();
    permission.innerHTML = value === 'granted' ? '<i class="bi bi-check2"></i> Notifications enabled' : '<i class="bi bi-bell-slash"></i> Permission not granted';
  });
});
