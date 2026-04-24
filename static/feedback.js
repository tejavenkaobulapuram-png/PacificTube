/**
 * Feedback System - Frontend Logic
 * Handles feedback submission and management UI
 */

let allFeedback = [];
let currentRating = 0;
let currentOverallRating = 'neutral';

// Open feedback submission modal
function openFeedbackModal() {
    document.getElementById('feedbackModal').style.display = 'flex';
    resetFeedbackForm();
}

// Close feedback submission modal
function closeFeedbackModal() {
    document.getElementById('feedbackModal').style.display = 'none';
}

// Reset feedback form
function resetFeedbackForm() {
    currentRating = 0;
    currentOverallRating = 'neutral';
    document.getElementById('feedbackRating').value = '0';
    document.getElementById('feedbackCategory').value = '';
    document.getElementById('feedbackImportance').value = '中';
    document.getElementById('feedbackText').value = '';
    document.getElementById('overallRating').value = 'neutral';
    
    // Reset star display
    document.querySelectorAll('.star').forEach(star => {
        star.textContent = '☆';
        star.classList.remove('active');
    });
    
    // Reset overall rating buttons
    document.querySelectorAll('.overall-btn').forEach(btn => {
        btn.classList.remove('active');
    });
}

// Star rating interaction
document.addEventListener('DOMContentLoaded', function() {
    const stars = document.querySelectorAll('.star');
    
    stars.forEach(star => {
        star.addEventListener('click', function() {
            currentRating = parseInt(this.getAttribute('data-rating'));
            document.getElementById('feedbackRating').value = currentRating;
            
            // Update star display
            stars.forEach((s, index) => {
                if (index < currentRating) {
                    s.textContent = '★';
                    s.classList.add('active');
                } else {
                    s.textContent = '☆';
                    s.classList.remove('active');
                }
            });
        });
        
        // Hover effect
        star.addEventListener('mouseenter', function() {
            const rating = parseInt(this.getAttribute('data-rating'));
            stars.forEach((s, index) => {
                if (index < rating) {
                    s.textContent = '★';
                } else {
                    s.textContent = '☆';
                }
            });
        });
    });
    
    // Reset to current rating on mouse leave
    document.getElementById('starRating').addEventListener('mouseleave', function() {
        stars.forEach((s, index) => {
            if (index < currentRating) {
                s.textContent = '★';
            } else {
                s.textContent = '☆';
            }
        });
    });
});

// Set overall rating
function setOverallRating(rating) {
    currentOverallRating = rating;
    document.getElementById('overallRating').value = rating;
    
    // Update button styles
    document.querySelectorAll('.overall-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.querySelector(`.overall-btn[data-rating="${rating}"]`).classList.add('active');
}

// Submit feedback
async function submitFeedback() {
    const rating = parseInt(document.getElementById('feedbackRating').value);
    const category = document.getElementById('feedbackCategory').value;
    const importance = document.getElementById('feedbackImportance').value;
    const feedbackText = document.getElementById('feedbackText').value.trim();
    const overallRating = document.getElementById('overallRating').value;
    
    // Validation
    if (rating === 0) {
        alert('評価を選択してください');
        return;
    }
    
    if (!category) {
        alert('カテゴリーを選択してください');
        return;
    }
    
    if (!feedbackText) {
        alert('詳細なフィードバックを入力してください');
        return;
    }
    
    try {
        const response = await fetch('/api/feedback/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rating: rating,
                category: category,
                importance: importance,
                feedbackText: feedbackText,
                overallRating: overallRating
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Success - close modal without alert popup
            closeFeedbackModal();
        } else {
            alert('エラー: ' + data.message);
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
        alert('フィードバックの送信中にエラーが発生しました');
    }
}

// Load feedback data for feedback management page
async function loadFeedbackDataForPage() {
    try {
        // Load feedback list
        const listResponse = await fetch('/api/feedback/list');
        const listData = await listResponse.json();
        
        if (listData.success) {
            allFeedback = listData.feedback;
            displayFeedbackList(allFeedback);
        }
        
        // Load statistics
        const statsResponse = await fetch('/api/feedback/stats');
        const statsData = await statsResponse.json();
        
        if (statsData.success) {
            displayStatistics(statsData.stats);
        }
    } catch (error) {
        console.error('Error loading feedback data:', error);
        alert('データの読み込み中にエラーが発生しました');
    }
}

// Display statistics
function displayStatistics(stats) {
    // Total count and average rating
    document.getElementById('totalFeedbackCount').textContent = stats.totalCount;
    document.getElementById('averageRating').innerHTML = stats.averageRating.toFixed(1) + ' <span class="star">★</span>';
    
    // Overall rating counts
    document.getElementById('positiveCount').textContent = stats.overallRatingBreakdown.positive || 0;
    document.getElementById('negativeCount').textContent = stats.overallRatingBreakdown.negative || 0;
    
    // Detailed count
    document.getElementById('detailedCount').textContent = stats.detailedCount || 0;
}

// Display feedback list in table format
function displayFeedbackList(feedbackList) {
    const tableBody = document.getElementById('feedbackTableBody');
    tableBody.innerHTML = '';
    
    if (feedbackList.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="no-data">データがありません</td></tr>';
        return;
    }
    
    feedbackList.forEach((feedback, index) => {
        const row = document.createElement('tr');
        
        const importanceClass = {
            '緊急': 'urgent',
            '高': 'high',
            '中': 'medium',
            '低': 'low'
        }[feedback.importance] || 'medium';
        
        const statusClass = {
            'new': 'new',
            'reviewed': 'reviewed',
            'resolved': 'resolved'
        }[feedback.status] || 'new';
        
        const statusText = {
            'new': '新規',
            'reviewed': '確認済み',
            'resolved': '解決済み'
        }[feedback.status] || '新規';
        
        const overallIcon = feedback.overallRating === 'positive' ? '👍' : 
                           feedback.overallRating === 'negative' ? '👎' : '➖';
        
        const stars = '★'.repeat(feedback.rating) + '☆'.repeat(5 - feedback.rating);
        
        const datetime = new Date(feedback.timestamp).toLocaleString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        row.innerHTML = `
            <td class="row-number">${index + 1}</td>
            <td class="datetime-cell">${datetime}</td>
            <td><span class="category-badge">${escapeHtml(feedback.category)}</span></td>
            <td><span class="importance-badge importance-${importanceClass}">${escapeHtml(feedback.importance)}</span></td>
            <td class="rating-stars">${stars}</td>
            <td class="overall-rating-icon">${overallIcon}</td>
            <td class="feedback-content">${escapeHtml(feedback.feedbackText)}</td>
            <td class="action-buttons">
                <button class="action-btn btn-edit" onclick='openDetailModal(${JSON.stringify(feedback).replace(/'/g, "&apos;")})'>詳細</button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Filter feedback with search
function filterFeedback() {
    const searchText = document.getElementById('searchBox').value.toLowerCase();
    const categoryFilter = document.getElementById('filterCategory').value;
    const importanceFilter = document.getElementById('filterImportance').value;
    const statusFilter = document.getElementById('filterStatus').value;
    
    let filtered = allFeedback;
    
    // Search filter
    if (searchText) {
        filtered = filtered.filter(f => 
            f.userName.toLowerCase().includes(searchText) ||
            f.category.toLowerCase().includes(searchText) ||
            f.feedbackText.toLowerCase().includes(searchText) ||
            (f.adminMemo && f.adminMemo.toLowerCase().includes(searchText))
        );
    }
    
    // Category filter
    if (categoryFilter) {
        filtered = filtered.filter(f => f.category === categoryFilter);
    }
    
    // Importance filter
    if (importanceFilter) {
        filtered = filtered.filter(f => f.importance === importanceFilter);
    }
    
    // Status filter
    if (statusFilter) {
        filtered = filtered.filter(f => f.status === statusFilter);
    }
    
    displayFeedbackList(filtered);
}

// Reset all filters
function resetFilters() {
    document.getElementById('searchBox').value = '';
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterImportance').value = '';
    document.getElementById('filterStatus').value = '';
    displayFeedbackList(allFeedback);
}

// Update feedback status
async function updateFeedbackStatus(feedbackId, partitionKey, newStatus) {
    try {
        const response = await fetch('/api/feedback/update-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                feedbackId: feedbackId,
                partitionKey: partitionKey,
                status: newStatus
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Success - reload data without alert popup
            await loadFeedbackData(); // Reload data
        } else {
            alert('エラー: ' + data.message);
        }
    } catch (error) {
        console.error('Error updating status:', error);
        alert('ステータス更新中にエラーが発生しました');
    }
}

// Export feedback to Excel (CSV format)
function exportFeedbackToExcel() {
    if (allFeedback.length === 0) {
        alert('エクスポートするデータがありません');
        return;
    }
    
    // Create CSV content
    const headers = ['NO.', '日時', 'ユーザー', 'メールアドレス', 'カテゴリー', '重要度', '評価', '総合評価', 'フィードバック内容', '管理者メモ', 'ステータス'];
    const rows = allFeedback.map((feedback, index) => {
        const datetime = new Date(feedback.timestamp).toLocaleString('ja-JP');
        const rating = '★'.repeat(feedback.rating);
        const overall = feedback.overallRating === 'positive' ? '高評価' : 
                       feedback.overallRating === 'negative' ? '低評価' : '中立';
        const status = {
            'new': '新規',
            'reviewed': '確認済み',
            'resolved': '解決済み'
        }[feedback.status] || '新規';
        
        return [
            index + 1,
            datetime,
            feedback.userName,
            feedback.userEmail,
            feedback.category,
            feedback.importance,
            rating,
            overall,
            `"${feedback.feedbackText.replace(/"/g, '""')}"`, // Escape quotes
            `"${(feedback.adminMemo || '').replace(/"/g, '""')}"`,
            status
        ];
    });
    
    // Combine headers and rows
    const csvContent = [headers.join(',')]
        .concat(rows.map(row => row.join(',')))
        .join('\n');
    
    // Add BOM for Excel UTF-8 support
    const bom = '\uFEFF';
    const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // Create download link
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `feedback_export_${new Date().toISOString().slice(0,10)}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Feedback detail modal functions
let currentFeedback = null;

function openDetailModal(feedback) {
    currentFeedback = feedback;
    const modal = document.getElementById('feedbackDetailModal');
    
    // Populate modal with feedback data
    document.getElementById('detailFeedbackText').textContent = feedback.feedbackText;
    document.getElementById('detailStatus').value = feedback.status;
    document.getElementById('detailAdminMemo').value = feedback.adminMemo || '';
    
    modal.style.display = 'flex';
}

function closeDetailModal() {
    document.getElementById('feedbackDetailModal').style.display = 'none';
    currentFeedback = null;
}

async function updateFeedbackDetail() {
    if (!currentFeedback) {
        alert('エラー: フィードバック情報が見つかりません');
        return;
    }
    
    const newStatus = document.getElementById('detailStatus').value;
    const adminMemo = document.getElementById('detailAdminMemo').value.trim();
    
    try {
        const response = await fetch('/api/feedback/update-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                feedbackId: currentFeedback.id,
                partitionKey: currentFeedback.date,
                status: newStatus,
                adminMemo: adminMemo
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Success - close modal and reload without alert popup
            closeDetailModal();
            await loadFeedbackDataForPage(); // Reload data
        } else {
            alert('エラー: ' + data.message);
        }
    } catch (error) {
        console.error('Error updating feedback:', error);
        alert('更新中にエラーが発生しました');
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close modals on outside click
window.onclick = function(event) {
    const feedbackModal = document.getElementById('feedbackModal');
    const detailModal = document.getElementById('feedbackDetailModal');
    
    if (event.target === feedbackModal) {
        closeFeedbackModal();
    }
    
    if (event.target === detailModal) {
        closeDetailModal();
    }
}
