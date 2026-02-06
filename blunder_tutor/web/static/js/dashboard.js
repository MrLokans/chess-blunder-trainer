  let currentDateFrom = null;
  let currentDateTo = null;
  let configuredUsernames = {};
  let dateChart = null;
  let hourChart = null;
  let currentGameTypeFilters = ['bullet', 'blitz', 'rapid', 'classical'];

  const gameTypeFilter = new FilterPersistence({
    storageKey: 'dashboard-game-type-filters',
    checkboxSelector: '.game-type-filter',
    defaultValues: ['bullet', 'blitz', 'rapid', 'classical']
  });

  function getFirstUsername() {
    return configuredUsernames.lichess_username || configuredUsernames.chesscom_username || null;
  }

  function getPresetDates(preset) {
    const now = new Date();
    const to = now.toISOString().split('T')[0];
    let from = null;

    switch (preset) {
      case '7d':
        from = new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        break;
      case '30d':
        from = new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        break;
      case '90d':
        from = new Date(now - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        break;
      case '1y':
        from = new Date(now - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        break;
      case 'all':
        return { from: null, to: null };
    }
    return { from, to };
  }

  function setPreset(preset) {
    const dates = getPresetDates(preset);
    document.getElementById('dateFrom').value = dates.from || '';
    document.getElementById('dateTo').value = dates.to || '';
    currentDateFrom = dates.from;
    currentDateTo = dates.to;

    // Update active button
    document.querySelectorAll('.filter-presets button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.preset === preset);
    });

    loadStats();
  }

  function applyDateFilter() {
    currentDateFrom = document.getElementById('dateFrom').value || null;
    currentDateTo = document.getElementById('dateTo').value || null;

    // Clear preset buttons active state
    document.querySelectorAll('.filter-presets button').forEach(btn => btn.classList.remove('active'));

    loadStats();
  }

  function clearDateFilter() {
    document.getElementById('dateFrom').value = '';
    document.getElementById('dateTo').value = '';
    currentDateFrom = null;
    currentDateTo = null;

    // Set "All time" as active
    document.querySelectorAll('.filter-presets button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.preset === 'all');
    });

    loadStats();
  }

  function buildUrl(baseUrl, includeGameTypes = false) {
    const params = new URLSearchParams();
    if (currentDateFrom) params.set('start_date', currentDateFrom);
    if (currentDateTo) params.set('end_date', currentDateTo);
    if (includeGameTypes && currentGameTypeFilters.length > 0 && currentGameTypeFilters.length < 4) {
      currentGameTypeFilters.forEach(gt => params.append('game_types', gt));
    }
    const queryString = params.toString();
    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
  }

  async function loadStats() {
    try {
      // Load overview stats (no date filter for overview)
      const overviewResp = await fetch('/api/stats');
      const overview = await overviewResp.json();

      document.getElementById('totalGames').textContent = overview.total_games || 0;
      document.getElementById('analyzedGames').textContent = overview.analyzed_games || 0;
      document.getElementById('totalBlunders').textContent = overview.total_blunders || 0;

      // Calculate progress percentage
      const totalGames = overview.total_games || 0;
      const analyzedGames = overview.analyzed_games || 0;
      const progressPercent = totalGames > 0 ? Math.round((analyzedGames / totalGames) * 100) : 0;

      document.getElementById('progressPercent').textContent = progressPercent + '%';
      document.getElementById('progressFill').style.width = progressPercent + '%';

      // Check for running analysis job
      const analysisStatusResp = await fetch('/api/analysis/status');
      const analysisStatus = await analysisStatusResp.json();

      const statusEl = document.getElementById('analysisJobStatus');
      if (analysisStatus.status === 'running') {
        const percent = analysisStatus.progress_total > 0
          ? Math.round((analysisStatus.progress_current / analysisStatus.progress_total) * 100)
          : 0;
        statusEl.textContent = `Analysis running: ${analysisStatus.progress_current || 0}/${analysisStatus.progress_total || 0} (${percent}%)`;
        statusEl.style.color = 'var(--primary)';
      } else if (analysisStatus.status === 'completed') {
        statusEl.textContent = 'Last analysis: completed';
        statusEl.style.color = 'var(--success)';
      } else if (analysisStatus.status === 'failed') {
        statusEl.innerHTML = 'Last analysis: failed <button class="btn btn-sm" onclick="retryAnalysis()" style="margin-left: 8px; padding: 4px 10px; font-size: 0.75rem;">Retry</button>';
        statusEl.style.color = 'var(--error)';
      } else {
        statusEl.textContent = '';
      }

      // Load and render games by date chart
      await loadDateChart();

      // Load and render games by hour chart
      await loadHourChart();

      // Load blunders by phase (with date and game type filters)
      const phaseResp = await fetch(buildUrl('/api/stats/blunders/by-phase', true));
      const phaseData = await phaseResp.json();

      const phaseBreakdown = document.getElementById('phaseBreakdown');
      const phaseBarContainer = document.getElementById('phaseBarContainer');
      const phaseBar = document.getElementById('phaseBar');

      if (phaseData.total_blunders > 0 && phaseData.by_phase.length > 0) {
        phaseBarContainer.style.display = 'block';

        // Build the stacked bar
        phaseBar.innerHTML = phaseData.by_phase
          .filter(p => p.percentage > 0)
          .map(p => `<div class="phase-bar-segment ${p.phase}" style="width: ${p.percentage}%">${p.percentage > 10 ? p.percentage + '%' : ''}</div>`)
          .join('');

        // Build the phase cards
        phaseBreakdown.innerHTML = phaseData.by_phase.map(p => `
          <div class="phase-card ${p.phase}">
            <div class="phase-name">${p.phase}</div>
            <div class="phase-count">${p.count}</div>
            <div class="phase-percent">${p.percentage}% of blunders</div>
            <div class="phase-cpl">Avg. loss: ${(p.avg_cp_loss / 100).toFixed(1)} pawns</div>
          </div>
        `).join('');
      } else {
        phaseBarContainer.style.display = 'none';
        phaseBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No blunder data available yet. Analyze some games to see your phase breakdown.</div>';
      }

      // Load blunders by color (with date filter and username)
      const username = getFirstUsername();
      let colorUrl = buildUrl('/api/stats/blunders/by-color');
      if (username) {
        colorUrl += (colorUrl.includes('?') ? '&' : '?') + 'username=' + encodeURIComponent(username);
      }
      const colorResp = await fetch(colorUrl);
      const colorData = await colorResp.json();

      const colorBreakdown = document.getElementById('colorBreakdown');
      const colorBarContainer = document.getElementById('colorBarContainer');
      const colorBar = document.getElementById('colorBar');

      if (colorData.total_blunders > 0 && colorData.by_color.length > 0) {
        colorBarContainer.style.display = 'block';

        // Build the comparison bar
        colorBar.innerHTML = colorData.by_color
          .filter(c => c.percentage > 0)
          .map(c => `<div class="color-bar-segment ${c.color}" style="width: ${c.percentage}%">${c.percentage > 15 ? c.percentage + '%' : ''}</div>`)
          .join('');

        // Build the color cards
        colorBreakdown.innerHTML = colorData.by_color.map(c => `
          <div class="color-card ${c.color}">
            <div class="color-name">As ${c.color}</div>
            <div class="color-count">${c.count}</div>
            <div class="color-percent">${c.percentage}% of blunders</div>
            <div class="color-cpl">Avg. loss: ${(c.avg_cp_loss / 100).toFixed(1)} pawns</div>
          </div>
        `).join('');
      } else {
        colorBarContainer.style.display = 'none';
        colorBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No blunder data available yet. Analyze some games to see your color breakdown.</div>';
      }

      // Load blunders by game type (with date filter)
      const gameTypeResp = await fetch(buildUrl('/api/stats/blunders/by-game-type'));
      const gameTypeData = await gameTypeResp.json();

      const gameTypeBreakdown = document.getElementById('gameTypeBreakdown');
      const gameTypeBarContainer = document.getElementById('gameTypeBarContainer');
      const gameTypeBar = document.getElementById('gameTypeBar');
      const gameTypeLegend = document.getElementById('gameTypeLegend');

      // Map for display labels
      const gameTypeLabels = {
        'ultrabullet': 'UltraBullet',
        'bullet': 'Bullet',
        'blitz': 'Blitz',
        'rapid': 'Rapid',
        'classical': 'Classical',
        'correspondence': 'Correspondence',
        'unknown': 'Unknown'
      };

      if (gameTypeData.total_blunders > 0 && gameTypeData.by_game_type.length > 0) {
        gameTypeBarContainer.style.display = 'block';

        // Build the stacked bar
        gameTypeBar.innerHTML = gameTypeData.by_game_type
          .filter(g => g.percentage > 0)
          .map(g => `<div class="game-type-bar-segment ${g.game_type}" style="flex: ${g.percentage}">${g.percentage > 8 ? g.percentage + '%' : ''}</div>`)
          .join('');

        // Build the legend
        const usedTypes = gameTypeData.by_game_type.filter(g => g.count > 0).map(g => g.game_type);
        gameTypeLegend.innerHTML = usedTypes.map(type => `
          <div class="game-type-legend-item">
            <span class="game-type-legend-color ${type}"></span>
            <span>${gameTypeLabels[type] || type}</span>
          </div>
        `).join('');

        // Build the game type cards
        gameTypeBreakdown.innerHTML = gameTypeData.by_game_type
          .filter(g => g.count > 0)
          .map(g => `
            <div class="game-type-card ${g.game_type}">
              <div class="game-type-name">${gameTypeLabels[g.game_type] || g.game_type}</div>
              <div class="game-type-count">${g.count}</div>
              <div class="game-type-percent">${g.percentage}%</div>
            </div>
          `).join('');
      } else {
        gameTypeBarContainer.style.display = 'none';
        gameTypeBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No game type data available yet. Analyze some games to see your blunders by time control.</div>';
      }

      // Load blunders by ECO opening (with date and game type filters)
      const ecoResp = await fetch(buildUrl('/api/stats/blunders/by-eco', true));
      const ecoData = await ecoResp.json();

      const ecoBreakdown = document.getElementById('ecoBreakdown');

      if (ecoData.total_blunders > 0 && ecoData.by_opening.length > 0) {
        ecoBreakdown.innerHTML = `
          <table class="eco-table">
            <thead>
              <tr>
                <th>Opening</th>
                <th>Blunders</th>
                <th>Avg. Loss</th>
                <th>Games</th>
              </tr>
            </thead>
            <tbody>
              ${ecoData.by_opening.map(item => `
                <tr>
                  <td><span class="eco-code">${item.eco_code}</span> ${item.eco_name}</td>
                  <td>${item.count} <span style="color: var(--text-muted); font-size: 0.75rem;">(${item.percentage}%)</span></td>
                  <td>${(item.avg_cp_loss / 100).toFixed(2)} pawns</td>
                  <td>${item.game_count}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      } else {
        ecoBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No opening data available yet. Analyze some games to see your opening breakdown.</div>';
      }

      // Load blunders by tactical pattern (with date filter)
      const tacticalResp = await fetch(buildUrl('/api/stats/blunders/by-tactical-pattern', true));
      const tacticalData = await tacticalResp.json();

      const tacticalBreakdown = document.getElementById('tacticalBreakdown');
      const tacticalBarContainer = document.getElementById('tacticalBarContainer');
      const tacticalBar = document.getElementById('tacticalBar');
      const tacticalLegend = document.getElementById('tacticalLegend');

      // Map pattern names to CSS class names
      const patternToClass = {
        'Fork': 'fork',
        'Pin': 'pin',
        'Skewer': 'skewer',
        'Discovered Attack': 'discovered',
        'Discovered Check': 'discovered',
        'Double Check': 'discovered',
        'Hanging Piece': 'hanging',
        'Back Rank Threat': 'back_rank',
        'Trapped Piece': 'other',
        'None': 'other'
      };

      const patternLabels = {
        'Fork': 'Fork',
        'Pin': 'Pin',
        'Skewer': 'Skewer',
        'Discovered Attack': 'Discovery',
        'Discovered Check': 'Disc. Check',
        'Double Check': 'Double Check',
        'Hanging Piece': 'Hanging',
        'Back Rank Threat': 'Back Rank',
        'Trapped Piece': 'Trapped',
        'None': 'Other'
      };

      if (tacticalData.total_blunders > 0 && tacticalData.by_pattern.length > 0) {
        tacticalBarContainer.style.display = 'block';

        // Build the stacked bar
        tacticalBar.innerHTML = tacticalData.by_pattern
          .filter(p => p.percentage > 0)
          .map(p => {
            const cls = patternToClass[p.pattern] || 'other';
            return `<div class="tactical-bar-segment ${cls}" style="flex: ${p.percentage}">${p.percentage > 8 ? p.percentage + '%' : ''}</div>`;
          })
          .join('');

        // Build the legend
        const uniqueClasses = [...new Set(tacticalData.by_pattern.map(p => patternToClass[p.pattern] || 'other'))];
        tacticalLegend.innerHTML = uniqueClasses.map(cls => {
          const label = Object.entries(patternToClass).find(([k, v]) => v === cls)?.[0] || cls;
          return `
            <div class="tactical-legend-item">
              <span class="tactical-legend-color ${cls}"></span>
              <span>${patternLabels[label] || label}</span>
            </div>
          `;
        }).join('');

        // Build the tactical cards
        tacticalBreakdown.innerHTML = tacticalData.by_pattern
          .filter(p => p.count > 0)
          .map(p => {
            const cls = patternToClass[p.pattern] || 'other';
            const label = patternLabels[p.pattern] || p.pattern;
            return `
              <div class="tactical-card ${cls}">
                <div class="tactical-name">${label}</div>
                <div class="tactical-count">${p.count}</div>
                <div class="tactical-percent">${p.percentage}%</div>
              </div>
            `;
          }).join('');
      } else {
        tacticalBarContainer.style.display = 'none';
        tacticalBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No tactical pattern data available yet. Run a backfill to analyze existing blunders for tactical patterns.</div>';
      }

      // Load game breakdown
      const breakdownResp = await fetch('/api/stats/games');
      const breakdown = await breakdownResp.json();

      const tbody = document.querySelector('#gameBreakdownTable tbody');
      tbody.innerHTML = '';
      (breakdown.items || []).forEach(row => {
        tbody.innerHTML += `
          <tr>
            <td>${row.source}</td>
            <td>${row.username}</td>
            <td>${row.total_games}</td>
            <td>${row.analyzed_games}</td>
            <td>${row.pending_games}</td>
          </tr>
        `;
      });

    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }

  async function loadDateChart() {
    try {
      const resp = await fetch(buildUrl('/api/stats/games/by-date', true));
      const data = await resp.json();

      const container = document.getElementById('dateChartContainer');
      const emptyMsg = document.getElementById('dateChartEmpty');

      if (!data.items || data.items.length === 0) {
        container.style.display = 'none';
        emptyMsg.style.display = 'block';
        return;
      }

      container.style.display = 'block';
      emptyMsg.style.display = 'none';

      const labels = data.items.map(d => d.date);
      const gameCounts = data.items.map(d => d.game_count);
      const accuracies = data.items.map(d => d.avg_accuracy);

      if (dateChart) {
        dateChart.destroy();
      }

      const ctx = document.getElementById('dateChart').getContext('2d');
      dateChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Games Played',
              data: gameCounts,
              backgroundColor: 'rgba(14, 165, 233, 0.7)',
              borderColor: 'rgba(14, 165, 233, 1)',
              borderWidth: 1,
              yAxisID: 'y',
              order: 2
            },
            {
              label: 'Accuracy',
              data: accuracies,
              type: 'line',
              borderColor: 'rgba(34, 197, 94, 1)',
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              borderWidth: 2,
              fill: false,
              tension: 0.3,
              pointRadius: 3,
              yAxisID: 'y1',
              order: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false
          },
          plugins: {
            legend: {
              position: 'top'
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  if (context.dataset.label === 'Accuracy') {
                    return `Accuracy: ${context.raw.toFixed(1)}%`;
                  }
                  return `${context.dataset.label}: ${context.raw}`;
                }
              }
            }
          },
          scales: {
            x: {
              ticks: {
                maxRotation: 45,
                minRotation: 45,
                maxTicksLimit: 15
              }
            },
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              title: {
                display: true,
                text: 'Games'
              },
              beginAtZero: true
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              title: {
                display: true,
                text: 'Accuracy %'
              },
              min: 0,
              max: 100,
              grid: {
                drawOnChartArea: false
              }
            }
          }
        }
      });
    } catch (err) {
      console.error('Failed to load date chart:', err);
    }
  }

  async function loadHourChart() {
    try {
      const resp = await fetch(buildUrl('/api/stats/games/by-hour', true));
      const data = await resp.json();

      const container = document.getElementById('hourChartContainer');
      const emptyMsg = document.getElementById('hourChartEmpty');

      if (!data.items || data.items.length === 0) {
        container.style.display = 'none';
        emptyMsg.style.display = 'block';
        return;
      }

      container.style.display = 'block';
      emptyMsg.style.display = 'none';

      // Fill in missing hours with zeros
      const hourMap = new Map(data.items.map(d => [d.hour, d]));
      const fullData = [];
      for (let h = 0; h < 24; h++) {
        if (hourMap.has(h)) {
          fullData.push(hourMap.get(h));
        } else {
          fullData.push({ hour: h, game_count: 0, avg_accuracy: 0 });
        }
      }

      const labels = fullData.map(d => `${d.hour.toString().padStart(2, '0')}:00`);
      const gameCounts = fullData.map(d => d.game_count);
      const accuracies = fullData.map(d => d.avg_accuracy);

      if (hourChart) {
        hourChart.destroy();
      }

      const ctx = document.getElementById('hourChart').getContext('2d');
      hourChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Games Played',
              data: gameCounts,
              backgroundColor: 'rgba(139, 92, 246, 0.7)',
              borderColor: 'rgba(139, 92, 246, 1)',
              borderWidth: 1,
              yAxisID: 'y',
              order: 2
            },
            {
              label: 'Accuracy',
              data: accuracies,
              type: 'line',
              borderColor: 'rgba(34, 197, 94, 1)',
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              borderWidth: 2,
              fill: false,
              tension: 0.3,
              pointRadius: 3,
              yAxisID: 'y1',
              order: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false
          },
          plugins: {
            legend: {
              position: 'top'
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  if (context.dataset.label === 'Accuracy') {
                    return `Accuracy: ${context.raw.toFixed(1)}%`;
                  }
                  return `${context.dataset.label}: ${context.raw}`;
                }
              }
            }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Hour of Day (UTC)'
              }
            },
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              title: {
                display: true,
                text: 'Games'
              },
              beginAtZero: true
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              title: {
                display: true,
                text: 'Accuracy %'
              },
              min: 0,
              max: 100,
              grid: {
                drawOnChartArea: false
              }
            }
          }
        }
      });
    } catch (err) {
      console.error('Failed to load hour chart:', err);
    }
  }

  async function retryAnalysis() {
    try {
      const resp = await fetch('/api/analysis/start', { method: 'POST' });
      if (resp.ok) {
        loadStats();
      } else {
        const data = await resp.json();
        alert(data.detail || 'Failed to start analysis');
      }
    } catch (err) {
      console.error('Failed to retry analysis:', err);
      alert('Failed to start analysis');
    }
  }

  // Load game type filters from localStorage
  currentGameTypeFilters = gameTypeFilter.load();

  // Add event listeners for game type filter checkboxes
  document.querySelectorAll('.game-type-filter').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      currentGameTypeFilters = gameTypeFilter.save();
      loadStats();
    });
  });

  // Load stats on page load (after loading configured usernames)
  loadConfiguredUsernames().then((usernames) => {
    configuredUsernames = usernames;
    loadStats();
  });

  // Load activity heatmap
  loadHeatmap('activityHeatmap');

  // Initialize WebSocket for real-time updates
  wsClient.connect();
  wsClient.subscribe(['stats.updated', 'job.completed', 'job.progress_updated', 'job.status_changed']);

  // Handle stats updates
  wsClient.on('stats.updated', () => {
    // Reload all dashboard data
    loadStats();
  });

  wsClient.on('job.completed', () => {
    // Reload dashboard when any job completes
    loadStats();
  });

  wsClient.on('job.progress_updated', () => {
    // Update analysis status in real-time
    loadStats();
  });

  wsClient.on('job.status_changed', () => {
    // Update when job status changes
    loadStats();
  });
