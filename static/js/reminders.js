(() => {
  const seen = new Set();
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  function showToast(reminder) {
    const tray = document.getElementById('reminderToasts');
    if (!tray) return;
    const toast = document.createElement('div');
    toast.className = 'toast show reminder-toast';
    const icon = reminder.type === 'appointment' ? 'calendar2-check' : 'capsule';
    toast.innerHTML = `<div class="toast-header"><i class="bi bi-${icon} text-primary me-2"></i><strong class="me-auto">${reminder.title}</strong><button type="button" class="btn-close" data-bs-dismiss="toast"></button></div><div class="toast-body"><b>${reminder.name}</b><br>${reminder.dosage} ${reminder.instruction ? '· ' + reminder.instruction : ''}</div>`;
    tray.append(toast);
    setTimeout(() => toast.remove(), 10000);
  }
  function announce(reminder) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const message = reminder.type === 'appointment' ? `Appointment reminder. ${reminder.name} at ${reminder.dosage}.` : `It is time to take your medicine. ${reminder.name}, ${reminder.dosage}.`;
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(message));
    }
  }
  async function checkReminders() {
    try {
      const response = await fetch('/api/reminders');
      if (!response.ok) return;
      const data = await response.json();
      data.reminders.forEach((reminder) => {
        const key = `${reminder.id}-${new Date().toDateString()}`;
        if (seen.has(key)) return;
        seen.add(key); showToast(reminder);
        if (data.enabled && 'Notification' in window && Notification.permission === 'granted') new Notification(reminder.title, { body: `${reminder.name} · ${reminder.dosage}` });
        if (data.voice) announce(reminder);
      });
    } catch (_) { /* Offline or server unavailable: next check will retry. */ }
  }
  checkReminders();
  setInterval(checkReminders, 60000);
})();
