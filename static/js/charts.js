document.addEventListener('DOMContentLoaded', () => {
  if (!window.Chart) return;
  Chart.defaults.font.family = 'DM Sans'; Chart.defaults.color = '#718096';
  const adherence = document.getElementById('adherenceChart');
  if (adherence) { const value = Number(adherence.dataset.adherence || 0); new Chart(adherence, { type: 'doughnut', data: { datasets: [{ data: [value, 100 - value], backgroundColor: ['#15b8a6', '#e7f5f3'], borderWidth: 0, borderRadius: 12 }] }, options: { cutout: '78%', plugins: { legend: { display: false }, tooltip: { enabled: false } } } }); }
  const activity = document.getElementById('activityChart');
  if (activity) { const values = JSON.parse(activity.dataset.values); new Chart(activity, { type: 'bar', data: { labels: ['5d ago','4d ago','3d ago','2d ago','Yesterday','Today'], datasets: [{ data: values, backgroundColor: '#85ded2', hoverBackgroundColor: '#15b8a6', borderRadius: 8, maxBarThickness: 34 }] }, options: { responsive: true, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { stepSize: 1 }, border: { display: false }, grid: { color: '#eef3f5' } } }, plugins: { legend: { display: false } } } }); }
  const appointments = document.getElementById('appointmentChart');
  if (appointments) { const values = JSON.parse(appointments.dataset.values); new Chart(appointments, { type: 'line', data: { labels: ['Jan','Feb','Mar','Apr','May','Jun'], datasets: [{ data: values, borderColor: '#7673dd', pointBackgroundColor: '#7673dd', pointRadius: 4, tension: .42, fill: true, backgroundColor: 'rgba(118,115,221,.10)' }] }, options: { scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { stepSize: 1 }, border: { display: false }, grid: { color: '#eef3f5' } } }, plugins: { legend: { display: false } } } }); }
});
