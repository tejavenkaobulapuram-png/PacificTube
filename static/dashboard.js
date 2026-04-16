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
    
    const usersGrid = document.getElementById('usersGrid');
    usersGrid.innerHTML = '';
    
    if (data.length === 0) {
        usersGrid.innerHTML = '<p style="color: #718096; text-align: center; padding: 40px;">データがありません</p>';
        return;
    }
    
    data.forEach(user => {
        const userCard = document.createElement('div');
        userCard.className = 'user-card';
        userCard.innerHTML = `
            <div class="user-name">
                👤 ${escapeHtml(user.userName)}
            </div>
            <div class="user-stats">
                <div class="stat-item">
                    <span class="stat-label">ログイン</span>
                    <span class="stat-value">${formatNumber(user.logins)}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">動画視聴</span>
                    <span class="stat-value">${formatNumber(user.videoViews)}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">検索</span>
                    <span class="stat-value">${formatNumber(user.searches)}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">コメント</span>
                    <span class="stat-value">${formatNumber(user.comments)}</span>
                </div>
            </div>
        `;
        usersGrid.appendChild(userCard);
    });
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
