// PacificTube Dashboard JavaScript
// Handles data fetching from Application Insights and chart rendering

let trendChart = null;
let folderChart = null;
let videoChart = null;

// Change time period
function changePeriod(period) {
    window.location.href = `/dashboard/${period}`;
}

// Load all dashboard data
async function loadDashboardData(period) {
    showLoading(true);
    
    try {
        // Load metrics cards
        await loadMetrics(period);
        
        // Load trend chart
        await loadTrendChart(period);
        
        // Load pie charts
        await loadFolderChart(period);
        await loadVideoChart(period);
        
        // Load active users
        await loadActiveUsers(period);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        alert('データの読み込みに失敗しました: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Load metrics cards
async function loadMetrics(period) {
    const response = await fetch(`/api/dashboard/metrics/${period}`);
    const data = await response.json();
    
    document.getElementById('totalEvents').textContent = formatNumber(data.totalEvents);
    document.getElementById('userLogins').textContent = formatNumber(data.userLogins);
    document.getElementById('videoViews').textContent = formatNumber(data.videoViews);
    document.getElementById('searches').textContent = formatNumber(data.searches);
    document.getElementById('comments').textContent = formatNumber(data.comments);
    document.getElementById('likes').textContent = formatNumber(data.likes);
    document.getElementById('dislikes').textContent = formatNumber(data.dislikes);
    document.getElementById('uniqueVideos').textContent = formatNumber(data.uniqueVideos);
    
    // Populate data period row with ACTUAL date range from backend
    const dateRange = `${data.dateRangeStart} to ${data.dateRangeEnd}`;
    document.getElementById('dateRange').textContent = dateRange;
    document.getElementById('eventCount').textContent = formatNumber(data.totalEvents);
}

// Load trend line chart
async function loadTrendChart(period) {
    const response = await fetch(`/api/dashboard/trend/${period}`);
    const data = await response.json();
    
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (trendChart) {
        trendChart.destroy();
    }
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(item => item.date),
            datasets: [{
                label: 'イベント数',
                data: data.map(item => item.count),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#667eea'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

// Load folder distribution pie chart
async function loadFolderChart(period) {
    const response = await fetch(`/api/dashboard/folders/${period}`);
    const data = await response.json();
    
    const ctx = document.getElementById('folderPieChart').getContext('2d');
    
    if (folderChart) {
        folderChart.destroy();
    }
    
    folderChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map(item => item.folder),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: [
                    '#667eea',
                    '#764ba2',
                    '#f093fb',
                    '#4facfe',
                    '#00f2fe',
                    '#43e97b',
                    '#38f9d7',
                    '#fa709a',
                    '#fee140',
                    '#30cfd0'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Load top videos pie chart
async function loadVideoChart(period) {
    const response = await fetch(`/api/dashboard/videos/${period}`);
    const data = await response.json();
    
    const ctx = document.getElementById('videoPieChart').getContext('2d');
    
    if (videoChart) {
        videoChart.destroy();
    }
    
    videoChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map(item => truncateText(item.video, 30)),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: [
                    '#667eea',
                    '#764ba2',
                    '#f093fb',
                    '#4facfe',
                    '#00f2fe',
                    '#43e97b',
                    '#38f9d7',
                    '#fa709a',
                    '#fee140',
                    '#30cfd0'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Load active users grid
async function loadActiveUsers(period) {
    const response = await fetch(`/api/dashboard/active-users/${period}`);
    const data = await response.json();
    
    // Update total active users count
    const totalCountElement = document.getElementById('totalActiveUsers');
    if (totalCountElement) {
        totalCountElement.textContent = `${data.length} Total`;
    }
    
    // Populate Top Active Users (Top 8)
    const topUsersGrid = document.getElementById('topUsersGrid');
    topUsersGrid.innerHTML = '';
    
    if (data.length === 0) {
        topUsersGrid.innerHTML = '<p style="color: #718096; text-align: center; padding: 40px;">データがありません</p>';
    } else {
        const topUsers = data.slice(0, 8); // Show top 8 users
        topUsers.forEach((user, index) => {
            const rank = index + 1;
            const rankClass = rank <= 3 ? `rank-${rank}` : 'rank-other';
            
            const userCard = document.createElement('div');
            userCard.className = 'top-user-card';
            userCard.innerHTML = `
                <div class="rank-badge ${rankClass}">#${rank}</div>
                <div class="top-user-email">${escapeHtml(user.userEmail || user.userName)}</div>
                <div class="top-user-stats">
                    <div class="top-stat-item">
                        <div class="top-stat-icon">📆</div>
                        <div class="top-stat-label">ACTIVE DAYS</div>
                        <div class="top-stat-value">${formatNumber(user.activeDays || 0)}</div>
                    </div>
                    <div class="top-stat-item">
                        <div class="top-stat-icon">❓</div>
                        <div class="top-stat-label">QUERIES</div>
                        <div class="top-stat-value">${formatNumber(user.searches || 0)}</div>
                    </div>
                    <div class="top-stat-item">
                        <div class="top-stat-icon">⚠️</div>
                        <div class="top-stat-label">RISK TABLES</div>
                        <div class="top-stat-value">${formatNumber(user.videoViews || 0)}</div>
                    </div>
                    <div class="top-stat-item">
                        <div class="top-stat-icon">📥</div>
                        <div class="top-stat-label">DOWNLOADS</div>
                        <div class="top-stat-value">${formatNumber(user.downloads || 0)}</div>
                    </div>
                </div>
                <div class="top-user-last-seen">
                    ⏰ Last seen: ${user.lastSeen || 'Unknown'}
                </div>
            `;
            topUsersGrid.appendChild(userCard);
        });
    }
    
    // Populate All Users Table
    const usersTableBody = document.getElementById('usersTableBody');
    usersTableBody.innerHTML = '';
    
    if (data.length > 0) {
        data.forEach(user => {
            const totalActivities = (user.logins || 0) + (user.videoViews || 0) + (user.searches || 0) + (user.comments || 0);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="user-email-cell">${escapeHtml(user.userEmail || user.userName)}</td>
                <td><strong>${formatNumber(totalActivities)}</strong></td>
                <td>
                    <div class="activity-breakdown">
                        <span class="activity-badge">
                            <span class="icon">📆</span>
                            <span class="count">${formatNumber(user.activeDays || 0)}</span>
                        </span>
                        <span class="activity-badge">
                            <span class="icon">⚠️</span>
                            <span class="count">${formatNumber(user.videoViews || 0)}</span>
                        </span>
                        <span class="activity-badge">
                            <span class="icon">📥</span>
                            <span class="count">${formatNumber(user.downloads || 0)}</span>
                        </span>
                        <span class="activity-badge">
                            <span class="icon">❓</span>
                            <span class="count">${formatNumber(user.searches || 0)}</span>
                        </span>
                    </div>
                </td>
                <td class="last-seen-cell">${user.lastSeen || 'Unknown'}</td>
            `;
            usersTableBody.appendChild(row);
        });
    }
    
    // Add search functionality
    const searchInput = document.getElementById('userSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = usersTableBody.querySelectorAll('tr');
            
            rows.forEach(row => {
                const email = row.querySelector('.user-email-cell').textContent.toLowerCase();
                if (email.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
}

// Export dashboard data
async function exportData() {
    alert('Excel エクスポート機能は開発中です');
    // TODO: Implement Excel export
}

// Show/hide loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}

// Utility functions
function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    return num.toLocaleString('ja-JP');
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
