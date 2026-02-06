import { client } from './api.js';

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function pluralize(count, singular, plural) {
  return count === 1 ? singular : plural;
}

// Fixed thresholds for activity levels
const ACTIVITY_THRESHOLDS = {
  L1: 1,   // 1-4 puzzles
  L2: 5,   // 5-9 puzzles
  L3: 10,  // 10-19 puzzles
  L4: 20   // 20+ puzzles
};

function getActivityLevel(count) {
  if (count === 0) return 0;
  if (count < ACTIVITY_THRESHOLDS.L2) return 1;
  if (count < ACTIVITY_THRESHOLDS.L3) return 2;
  if (count < ACTIVITY_THRESHOLDS.L4) return 3;
  return 4;
}

function formatDate(date) {
  return date.toISOString().split('T')[0];
}

function renderHeatmap(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const { daily_counts, max_count, total_days, total_attempts } = data;

  // Calculate date range (52 weeks ending today, aligned to start on Sunday)
  const today = new Date();
  const endDate = new Date(today);
  
  // Go back to find the start of the current week (Sunday)
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - 364); // Go back ~52 weeks
  // Align to Sunday
  while (startDate.getDay() !== 0) {
    startDate.setDate(startDate.getDate() - 1);
  }

  // Build grid data
  const weeks = [];
  let currentDate = new Date(startDate);
  let currentWeek = [];
  
  while (currentDate <= endDate) {
    const dateStr = formatDate(currentDate);
    const dayData = daily_counts[dateStr] || { total: 0, correct: 0, incorrect: 0 };
    const level = getActivityLevel(dayData.total);
    
    currentWeek.push({
      date: dateStr,
      total: dayData.total,
      correct: dayData.correct,
      incorrect: dayData.incorrect,
      level,
      dayOfWeek: currentDate.getDay(),
      month: currentDate.getMonth(),
      dayOfMonth: currentDate.getDate()
    });
    
    if (currentDate.getDay() === 6) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
    
    currentDate.setDate(currentDate.getDate() + 1);
  }
  
  if (currentWeek.length > 0) {
    weeks.push(currentWeek);
  }

  // Generate month labels
  const monthLabels = [];
  let lastMonth = -1;
  weeks.forEach((week, weekIndex) => {
    const firstDayOfWeek = week[0];
    if (firstDayOfWeek && firstDayOfWeek.month !== lastMonth && firstDayOfWeek.dayOfMonth <= 7) {
      monthLabels.push({ weekIndex, month: MONTHS[firstDayOfWeek.month] });
      lastMonth = firstDayOfWeek.month;
    }
  });

  // Render HTML
  container.innerHTML = `
    <div class="heatmap-wrapper">
      <div class="heatmap-summary">
        <span class="heatmap-total">${total_attempts.toLocaleString()} ${pluralize(total_attempts, 'puzzle', 'puzzles')}</span>
        <span class="heatmap-days">${total_days} active ${pluralize(total_days, 'day', 'days')}</span>
      </div>
      <div class="heatmap-container">
        <div class="heatmap-days-labels">
          ${DAYS_OF_WEEK.filter((_, i) => i % 2 === 1).map(d => `<span>${d}</span>`).join('')}
        </div>
        <div class="heatmap-grid-wrapper">
          <div class="heatmap-months">
            ${monthLabels.map(m => `<span style="grid-column: ${m.weekIndex + 1}">${m.month}</span>`).join('')}
          </div>
          <div class="heatmap-grid" style="grid-template-columns: repeat(${weeks.length}, 12px)">
            ${weeks.map(week => `
              <div class="heatmap-week">
                ${Array(7).fill(0).map((_, dayIndex) => {
                  const day = week.find(d => d.dayOfWeek === dayIndex);
                  if (!day) return '<div class="heatmap-cell empty"></div>';
                  const tooltip = day.total === 0 
                    ? `${day.date}: No activity`
                    : `${day.date}: ${day.total} ${pluralize(day.total, 'puzzle', 'puzzles')} (✓${day.correct} ✗${day.incorrect})`;
                  return `<div class="heatmap-cell level-${day.level}" 
                    data-tooltip="${tooltip}"
                    data-date="${day.date}" data-total="${day.total}"></div>`;
                }).join('')}
              </div>
            `).join('')}
          </div>
        </div>
      </div>
      <div class="heatmap-legend">
        <span>Less</span>
        <div class="heatmap-cell level-0"></div>
        <div class="heatmap-cell level-1"></div>
        <div class="heatmap-cell level-2"></div>
        <div class="heatmap-cell level-3"></div>
        <div class="heatmap-cell level-4"></div>
        <span>More</span>
      </div>
    </div>
  `;
}

async function loadHeatmap(containerId) {
  try {
    const data = await client.stats.activityHeatmap();
    renderHeatmap(containerId, data);
  } catch (err) {
    console.error('Failed to load heatmap:', err);
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = '<div class="heatmap-error">Failed to load activity data</div>';
    }
  }
}

export { loadHeatmap, renderHeatmap };
