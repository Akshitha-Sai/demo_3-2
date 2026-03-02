async function loadTrafficChart() {
  const response = await fetch('/admin/api/traffic-data');
  if (!response.ok) return;
  const data = await response.json();
  const ctx = document.getElementById('trafficChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Requests/min',
        data: data.values,
        borderColor: '#0d6efd',
        tension: 0.2,
        fill: false,
      }]
    },
    options: {responsive: true, maintainAspectRatio: true}
  });
}

loadTrafficChart();
setInterval(loadTrafficChart, 30000);
