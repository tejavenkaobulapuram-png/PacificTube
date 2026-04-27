// Pacific Tube - Frontend JavaScript

let allVideos = [];
let filteredVideos = [];
let currentFolder = null;
let currentQuery = '';
let currentSort = 'relevance';
let selectedUploaders = new Set();
let searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
let tokenRefreshInterval = null;  // For 2-minute SAS token refresh

// Persistent user ID (stored in localStorage to work across Azure instances)
function getUserId() {
    let userId = localStorage.getItem('pacifictube_user_id');
    if (!userId) {
        userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('pacifictube_user_id', userId);
        // User ID logged to server only (not exposed in browser console)
    }
    return userId;
}

// Send important logs to server ONLY (visible in Azure Container logs via `az containerapp logs show`)
// SECURITY: Do NOT log to browser console - prevents exposure of sensitive info
function serverLog(event, message, videoId = '') {
    const userId = getUserId();
    
    // Send to backend only (fire and forget - don't wait for response)
    // No browser console logging for security
    fetch('/api/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            event: event,
            message: message,
            user_id: userId,
            video_id: videoId
        })
    }).catch(() => {}); // Silent fail - no console output
}

// Check authentication status and update UI
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/user');
        const data = await response.json();
        
        const loginBtn = document.getElementById('loginBtn');
        const userInfo = document.getElementById('userInfo');
        const userName = document.getElementById('userName');
        
        if (data.auth_enabled) {
            // Authentication is enabled
            if (data.authenticated && data.user) {
                // User is logged in
                loginBtn.style.display = 'none';
                userInfo.style.display = 'flex';
                userName.textContent = data.user.name || data.user.email || 'ユーザー';
            } else {
                // User is not logged in - show login button
                loginBtn.style.display = 'inline-flex';
                userInfo.style.display = 'none';
            }
        } else {
            // Authentication is disabled - hide auth section entirely
            loginBtn.style.display = 'none';
            userInfo.style.display = 'none';
        }
    } catch (error) {
        // Error checking auth - silently hide auth UI and continue
        // App remains functional without authentication
        const loginBtn = document.getElementById('loginBtn');
        const userInfo = document.getElementById('userInfo');
        if (loginBtn) loginBtn.style.display = 'none';
        if (userInfo) userInfo.style.display = 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize user ID on page load
    getUserId();
    checkAuthStatus();  // Check if user is logged in
    loadFolders();
    loadVideos();
    setupSearchListener();
    setupSearchHistory();
    checkForSharedVideo();
});

// Load folder structure from API
async function loadFolders() {
    const folderTree = document.getElementById('folderTree');
    
    try {
        const response = await fetch('/api/folders');
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load folders');
        }

        if (data.folders.length === 0) {
            folderTree.innerHTML = '<div class="loading-folders">フォルダなし</div>';
            return;
        }

        folderTree.innerHTML = '';
        renderFolderTree(data.folders, folderTree);
    } catch (err) {
        console.error('Error loading folders:', err);
        folderTree.innerHTML = '<div class="loading-folders">エラー</div>';
    }
}

// Render folder tree recursively
function renderFolderTree(folders, parentElement, level = 0) {
    folders.forEach(folder => {
        const folderItem = document.createElement('div');
        folderItem.className = 'folder-item';
        
        const hasChildren = folder.children && folder.children.length > 0;
        
        const folderHeader = document.createElement('div');
        folderHeader.className = 'folder-header';
        folderHeader.onclick = () => selectFolder(folder.path, folderHeader);
        
        // Expand/collapse icon (only if has children)
        if (hasChildren) {
            const expandIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            expandIcon.setAttribute('class', 'folder-expand');
            expandIcon.setAttribute('viewBox', '0 0 24 24');
            expandIcon.innerHTML = '<path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>';
            expandIcon.onclick = (e) => {
                e.stopPropagation();
                toggleFolder(folderItem, expandIcon);
            };
            folderHeader.appendChild(expandIcon);
        } else {
            // Add spacer for alignment
            const spacer = document.createElement('div');
            spacer.style.width = '16px';
            folderHeader.appendChild(spacer);
        }
        
        // Folder icon
        const folderIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        folderIcon.setAttribute('class', 'folder-icon');
        folderIcon.setAttribute('viewBox', '0 0 24 24');
        folderIcon.innerHTML = '<path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>';
        folderHeader.appendChild(folderIcon);
        
        // Folder name
        const folderName = document.createElement('span');
        folderName.className = 'folder-name';
        folderName.textContent = folder.name;
        folderHeader.appendChild(folderName);
        
        // Video count badge
        if (folder.video_count > 0) {
            const count = document.createElement('span');
            count.className = 'folder-count';
            count.textContent = folder.video_count;
            folderHeader.appendChild(count);
        }
        
        folderItem.appendChild(folderHeader);
        
        // Render children if exists
        if (hasChildren) {
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'folder-children';
            renderFolderTree(folder.children, childrenContainer, level + 1);
            folderItem.appendChild(childrenContainer);
        }
        
        parentElement.appendChild(folderItem);
    });
}

// Toggle folder expand/collapse
function toggleFolder(folderItem, expandIcon) {
    const children = folderItem.querySelector('.folder-children');
    if (children) {
        children.classList.toggle('expanded');
        expandIcon.classList.toggle('expanded');
    }
}

// Select folder and filter videos
function selectFolder(folderPath, headerElement) {
    currentFolder = folderPath;
    
    // Update active state
    document.querySelectorAll('.folder-header').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    headerElement.classList.add('active');
    
    // Filter videos by folder
    if (folderPath) {
        filteredVideos = allVideos.filter(video => video.folder === folderPath);
    } else {
        filteredVideos = allVideos;
    }
    
    displayVideos(filteredVideos);
    
    // Clear search
    document.getElementById('searchInput').value = '';
}

// Show all videos (home button)
function showAllVideos(event) {
    event.preventDefault();
    currentFolder = null;
    
    // Update active state
    document.querySelectorAll('.folder-header').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    event.currentTarget.classList.add('active');
    
    // Show all videos
    filteredVideos = allVideos;
    displayVideos(filteredVideos);
    
    // Clear search
    document.getElementById('searchInput').value = '';
}

// Load videos from API
async function loadVideos() {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const empty = document.getElementById('empty');
    const videoGrid = document.getElementById('videoGrid');

    // Reset states
    loading.style.display = 'flex';
    error.style.display = 'none';
    empty.style.display = 'none';
    videoGrid.innerHTML = '';

    try {
        const response = await fetch('/api/videos');
        const data = await response.json();

        loading.style.display = 'none';

        if (!data.success) {
            throw new Error(data.error || 'Failed to load videos');
        }

        allVideos = data.videos;
        filteredVideos = allVideos;

        if (allVideos.length === 0) {
            empty.style.display = 'block';
        } else {
            displayVideos(filteredVideos);
        }
    } catch (err) {
        console.error('Error loading videos:', err);
        loading.style.display = 'none';
        error.style.display = 'block';
        document.getElementById('errorText').textContent = `❌ ${err.message}`;
    }
}

// Check for shared video in URL and auto-open
function checkForSharedVideo() {
    // Wait for videos to load first
    const checkInterval = setInterval(() => {
        if (allVideos.length > 0) {
            clearInterval(checkInterval);
            
            // Check URL for video parameter
            const urlParams = new URLSearchParams(window.location.search);
            const videoId = urlParams.get('video');
            
            if (videoId) {
                // Find the video with matching ID
                const video = allVideos.find(v => v.id === videoId);
                
                if (video) {
                    // Small delay to ensure DOM is ready
                    setTimeout(() => openModal(video), 100);
                    
                    // Clean URL (remove parameter) without page reload
                    const cleanUrl = window.location.origin + window.location.pathname;
                    window.history.replaceState({}, document.title, cleanUrl);
                }
            }
        }
    }, 100); // Check every 100ms
    
    // Safety timeout - stop checking after 10 seconds
    setTimeout(() => clearInterval(checkInterval), 10000);
}

// Display videos in grid
function displayVideos(videos) {
    const videoGrid = document.getElementById('videoGrid');
    videoGrid.innerHTML = '';

    videos.forEach(video => {
        const card = createVideoCard(video);
        videoGrid.appendChild(card);
        
        // Load thumbnail from backend
        loadThumbnail(video.id);
        
        // Load watch progress for this video
        loadWatchProgress(video.id);
    });
}

// Load thumbnail from backend API
function loadThumbnail(videoId) {
    const thumbnailDiv = document.querySelector(`[data-video-id="${CSS.escape(videoId)}"] .video-thumbnail`);
    if (!thumbnailDiv) return;
    
    const placeholder = thumbnailDiv.querySelector('.placeholder-thumbnail');
    if (!placeholder) return;
    
    // Create image element
    const img = document.createElement('img');
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'cover';
    img.style.display = 'none'; // Hide until loaded
    
    img.onload = function() {
        // Fade in the thumbnail
        img.style.display = 'block';
        img.style.animation = 'fadeIn 0.3s ease-in';
        // Hide the placeholder icon
        const icon = placeholder.querySelector('.video-icon');
        if (icon) icon.style.display = 'none';
    };
    
    img.onerror = function() {
        console.warn(`Could not load thumbnail for ${videoId}`);
        // Keep showing the placeholder icon
    };
    
    // Set thumbnail URL from backend
    img.src = `/api/thumbnail/${encodeURIComponent(videoId)}`;
    placeholder.appendChild(img);
}

// Load watch progress for thumbnail (YouTube-style blue bar)
async function loadWatchProgress(videoId) {
    try {
        const userId = getUserId();
        const response = await fetch(`/api/watchposition/${encodeURIComponent(videoId)}?user_id=${encodeURIComponent(userId)}`);
        const data = await response.json();
        
        if (data.success && data.position && data.position.percentage > 0) {
            const percentage = data.position.percentage;
            
            // Find the progress bar for this video
            const card = document.querySelector(`[data-video-id="${CSS.escape(videoId)}"]`);
            if (card) {
                const progressBar = card.querySelector('.watch-progress-bar');
                const progressFill = card.querySelector('.watch-progress-fill');
                
                if (progressBar && progressFill && percentage < 95) { // Don't show if completed
                    progressBar.style.display = 'block';
                    progressFill.style.width = percentage + '%';
                }
            }
        }
    } catch (error) {
        // Silently fail - progress bar is optional
        console.debug('No watch progress for:', videoId);
    }
}

// Create video card element
function createVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'video-card';
    card.setAttribute('data-video-id', video.id);
    card.onclick = () => openModal(video);

    const thumbnail = `
        <div class="video-thumbnail">
            <div class="placeholder-thumbnail">
                <svg class="video-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                </svg>
            </div>
            <div class="play-overlay">
                <svg class="play-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                </svg>
            </div>
            <div class="watch-progress-bar" style="display: none;">
                <div class="watch-progress-fill" style="width: 0%"></div>
            </div>
        </div>
    `;

    // Highlight matching text in title and uploader
    const highlightedTitle = currentQuery ? highlightText(video.name, currentQuery) : escapeHtml(video.name);
    const highlightedUploader = currentQuery ? highlightText(video.uploader || '不明', currentQuery) : escapeHtml(video.uploader || '不明');
    
    // Add badge if found in subtitles
    const subtitleBadge = video._foundInSubtitles 
        ? '<span class="subtitle-match-badge">字幕で見つかりました</span>' 
        : '';

    const info = `
        <div class="video-info">
            <h3 class="video-title">${highlightedTitle}</h3>
            ${subtitleBadge}
            <div class="video-meta">
                <span class="meta-item">
                    <svg class="meta-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" />
                    </svg>
                    ${formatViews(video.views)}回視聴
                </span>
                <span class="meta-item uploader-name">
                    <svg class="meta-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                    </svg>
                    ${highlightedUploader}
                </span>
                <span class="meta-item">
                    <svg class="meta-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V10h14v10z" />
                    </svg>
                    ${formatDate(video.lastModified)}
                </span>
                <span class="meta-item">
                    <svg class="meta-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z" />
                    </svg>
                    ${formatFileSize(video.size)}
                </span>
            </div>
        </div>
    `;

    card.innerHTML = thumbnail + info;
    return card;
}

// Open video player modal
async function openModal(video) {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('videoPlayer');
    const title = document.getElementById('modalTitle');
    const date = document.getElementById('modalDate');
    const size = document.getElementById('modalSize');

    title.textContent = video.name;
    date.textContent = `更新日: ${formatDate(video.lastModified)}`;
    size.textContent = `サイズ: ${formatFileSize(video.size)}`;

    // Log video open event to server
    serverLog('VIDEO_OPENED', `User opened video: ${video.name}`, video.id);

    // SECURITY: Fetch video URL with fresh 2-minute SAS token from backend
    // This prevents URL sharing and enables audit logging
    try {
        const userId = localStorage.getItem('pt_user_id') || 'anonymous';
        const urlResponse = await fetch(`/api/video-url/${encodeURIComponent(video.id)}?user_id=${userId}`);
        const urlData = await urlResponse.json();
        
        if (!urlData.success) {
            throw new Error(urlData.error || 'Failed to get video URL');
        }
        
        player.src = urlData.url;
        
        // Store token info for refresh
        window.currentVideoTokenExpires = Date.now() + (urlData.expires_in * 1000);
        
        // Setup token refresh (every 1 minute to stay ahead of 2-min expiration)
        if (window.tokenRefreshInterval) {
            clearInterval(window.tokenRefreshInterval);
        }
        window.tokenRefreshInterval = setInterval(async () => {
            if (document.getElementById('videoModal').style.display === 'block') {
                await refreshVideoToken(video);
            } else {
                clearInterval(window.tokenRefreshInterval);
            }
        }, 60000); // Refresh every 1 minute
        
    } catch (err) {
        console.error('❌ Failed to get video URL:', err);
        alert('ビデオの読み込みに失敗しました。');
        return;
    }
    
    modal.style.display = 'block';
    
    // Hide main content area entirely (YouTube-style)
    const mainLayout = document.querySelector('.main-layout');
    if (mainLayout) {
        mainLayout.style.display = 'none';
    }
    
    // Hide feedback button and privacy banner when video is playing
    const feedbackBtn = document.getElementById('feedbackBtn');
    const privacyBanner = document.querySelector('.privacy-notice-banner');
    if (feedbackBtn) feedbackBtn.style.display = 'none';
    if (privacyBanner) privacyBanner.style.display = 'none';
    
    // Scroll to top to show video immediately
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Store current video ID, name, and object for engagement actions
    window.currentVideoId = video.id;
    window.currentVideoName = video.name;
    window.currentVideo = video;
    
    // ===== DOWNLOAD PROTECTION =====
    // Disable right-click context menu on video
    player.oncontextmenu = function(e) {
        e.preventDefault();
        return false;
    };
    
    // Block download keyboard shortcuts (Ctrl+S, Cmd+S)
    player.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            return false;
        }
    });
    
    // Add controlsList attribute to remove download button
    player.setAttribute('controlsList', 'nodownload');
    // =============================
    
    // ===== TOKEN EXPIRATION CHECK ON PLAY =====
    // When user clicks play after pausing, check if token needs refresh
    // This ensures smooth playback even if paused for a long time
    player.removeEventListener('play', handlePlayWithTokenCheck); // Remove old listener
    player.addEventListener('play', handlePlayWithTokenCheck);
    // ==========================================
    
    // Prevent video from capturing keyboard focus (critical!)
    player.setAttribute('tabindex', '-1');
    
    // Remove any existing keyboard listeners first (prevent duplicates)
    window.removeEventListener('keydown', handleVideoKeyboard, true);
    document.removeEventListener('keydown', handleVideoKeyboard, true);
    player.removeEventListener('keydown', handleVideoKeyboard, true);
    
    // Add keyboard event listener at WINDOW level (catches everything)
    window.addEventListener('keydown', handleVideoKeyboard, true);
    document.addEventListener('keydown', handleVideoKeyboard, true);
    player.addEventListener('keydown', handleVideoKeyboard, true);
    
    // Reset seek state when video loads
    seekAccumulator = 0;
    seekDirection = null;
    lastSeekTime = 0;
    isProgrammaticSeek = false;
    
    // Reset seek state AND blur video when user manually seeks (clicks timeline)
    player.addEventListener('seeking', function() {
        // Only reset if this is a MANUAL seek (user clicked timeline), not programmatic
        if (isProgrammaticSeek) {
            return; // Don't reset accumulator for our own seeks
        }
        
        seekAccumulator = 0;
        seekDirection = null;
        lastSeekTime = 0; // Reset throttle timer
        
        // CRITICAL: Remove focus from video to prevent native controls
        player.blur();
        document.activeElement.blur();
        
        const indicator = document.getElementById('seekIndicator');
        if (indicator) {
            indicator.classList.remove('show');
            indicator.style.display = 'none';
        }
    });
    
    // Reset engagement button states (prevent stuck locks)
    isLikeProcessing = false;
    isDislikeProcessing = false;
    const likeBtn = document.getElementById('likeBtn');
    const dislikeBtn = document.getElementById('dislikeBtn');
    if (likeBtn) {
        likeBtn.disabled = false;
        likeBtn.style.pointerEvents = '';
        likeBtn.style.opacity = '';
    }
    if (dislikeBtn) {
        dislikeBtn.disabled = false;
        dislikeBtn.style.pointerEvents = '';
        dislikeBtn.style.opacity = '';
    }

    // Note: View count tracking happens periodically while playing (every 10 seconds)
    // and also when video is closed (to capture final watch duration)
    
    // Track initial video view when playback actually starts
    player.addEventListener('playing', function initialViewTrack() {
        // Track as soon as video starts playing (even if currentTime is 0)
        if (player.duration > 0) {
            const videoName = window.currentVideoName || 'Unknown';
            const currentTime = Math.max(player.currentTime, 0.1); // Use at least 0.1 to indicate video was opened
            incrementViewCount(window.currentVideoId, videoName, currentTime, player.duration);
        }
    }, { once: true });

    // Load engagement data (likes, dislikes, comments)
    loadEngagement(video.id);
    
    // Load subtitles for this video
    loadSubtitles(video.id);
    
    // Load chapters/timestamps for this video
    loadChapters(video.id);
    
    // Load transcript/mojigokoshi (YouTube-style) for this video
    loadTranscript(video.id, 'ja');  // Default to Japanese
    
    // Load related videos from same folder
    loadRelatedVideos(video);
    
    // Check for saved watch position (resume feature)
    checkResumePosition(video.id, player);
    
    // Start saving watch position periodically
    startWatchPositionTracking(video.id, player);

    // Close on background click
    modal.onclick = (e) => {
        if (e.target === modal) {
            closeModal();
        }
    };
}

// Refresh video token (called periodically to prevent expiration during playback)
async function refreshVideoToken(video) {
    const player = document.getElementById('videoPlayer');
    if (!player || !video) return;
    
    // IMPORTANT: Only refresh if video is actively PLAYING
    // Don't refresh for paused videos - this prevents annoying auto-start behavior
    // (Like YouTube - it doesn't refresh when you pause and go to another tab)
    if (player.paused) {
        serverLog('TOKEN_REFRESH_SKIPPED', 'Video paused - skipping token refresh', video.id);
        return;
    }
    
    // Remember current position
    const currentTime = player.currentTime;
    
    try {
        const userId = localStorage.getItem('pt_user_id') || 'anonymous';
        const urlResponse = await fetch(`/api/video-url/${encodeURIComponent(video.id)}?user_id=${userId}`);
        const urlData = await urlResponse.json();
        
        if (urlData.success) {
            player.src = urlData.url;
            player.currentTime = currentTime;
            
            // Auto-resume playback since we know video was playing
            player.play().catch(() => {}); // Silent fail
            
            serverLog('TOKEN_REFRESHED', 'Token refreshed while playing (expires in 2 min)', video.id);
            window.currentVideoTokenExpires = Date.now() + (urlData.expires_in * 1000);
        }
    } catch (err) {
        serverLog('TOKEN_REFRESH_FAILED', `Error: ${err.message}`, video.id);
        // Don't interrupt playback on refresh failure, token still has ~1 minute
    }
}

// Check and refresh token before playing (for paused videos with expired tokens)
async function ensureFreshToken(video) {
    const now = Date.now();
    const bufferTime = 30000; // 30 seconds buffer
    
    // If token is about to expire or expired, refresh before playing
    if (window.currentVideoTokenExpires && (window.currentVideoTokenExpires - now) < bufferTime) {
        serverLog('TOKEN_EXPIRING', 'Token expired/expiring - refreshing before play', video.id);
        const player = document.getElementById('videoPlayer');
        const currentTime = player.currentTime;
        
        try {
            const userId = localStorage.getItem('pt_user_id') || 'anonymous';
            const urlResponse = await fetch(`/api/video-url/${encodeURIComponent(video.id)}?user_id=${userId}`);
            const urlData = await urlResponse.json();
            
            if (urlData.success) {
                player.src = urlData.url;
                player.currentTime = currentTime;
                window.currentVideoTokenExpires = Date.now() + (urlData.expires_in * 1000);
                serverLog('TOKEN_OBTAINED', 'Fresh token obtained before play', video.id);
            }
        } catch (err) {
            serverLog('TOKEN_ERROR', `Failed to refresh: ${err.message}`, video.id);
        }
    }
}

// Event handler for play - checks token expiration before resuming
// This handles the case where user pauses, goes to another tab, comes back after 5+ minutes
async function handlePlayWithTokenCheck(event) {
    const player = event.target;
    const video = window.currentVideo;
    
    if (!video) return;
    
    // Check if token might be expired (with 30 second buffer)
    const now = Date.now();
    const bufferTime = 30000; // 30 seconds
    
    if (window.currentVideoTokenExpires && (window.currentVideoTokenExpires - now) < bufferTime) {
        // Token expired or about to expire - pause and refresh first
        player.pause();
        serverLog('TOKEN_EXPIRED_ON_PLAY', 'Token expired - refreshing before play', video.id);
        
        try {
            const userId = localStorage.getItem('pt_user_id') || 'anonymous';
            const currentTime = player.currentTime;
            const urlResponse = await fetch(`/api/video-url/${encodeURIComponent(video.id)}?user_id=${userId}`);
            const urlData = await urlResponse.json();
            
            if (urlData.success) {
                player.src = urlData.url;
                player.currentTime = currentTime;
                window.currentVideoTokenExpires = Date.now() + (urlData.expires_in * 1000);
                serverLog('TOKEN_REFRESHED_RESUME', 'Token refreshed - resuming playback', video.id);
                player.play().catch(() => {}); // Silent fail
            }
        } catch (err) {
            serverLog('TOKEN_REFRESH_ERROR', `Error: ${err.message}`, video.id);
            alert('ビデオURLの更新に失敗しました。ページを再読み込みしてください。');
        }
    }
}

// Increment view count when video is played
async function incrementViewCount(videoId, videoName, durationWatched = 0, videoDuration = 0) {
    try {
        const response = await fetch(`/api/view/${encodeURIComponent(videoId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                name: videoName,
                duration_watched: Math.round(durationWatched),
                video_duration: Math.round(videoDuration)
            })
        });
        
        const data = await response.json();
        if (data.success) {
            // Update view count in the video object
            const video = allVideos.find(v => v.id === videoId);
            if (video) {
                video.views = data.views;
            }
        }
    } catch (error) {
        console.error('Error incrementing view count:', error);
    }
}

// ===== RESUME WATCHING FEATURE =====

let watchPositionInterval = null;

async function checkResumePosition(videoId, player) {
    try {
        const userId = getUserId();
        const response = await fetch(`/api/watchposition/${encodeURIComponent(videoId)}?user_id=${encodeURIComponent(userId)}`);
        const data = await response.json();
        
        if (data.success && data.position && data.position.position > 10) {
            const savedPosition = data.position.position;
            const percentage = data.position.percentage;
            
            // Don't resume if near the end (last 5%)
            if (percentage < 95) {
                // Wait for video metadata to load, then auto-resume
                player.addEventListener('loadedmetadata', function() {
                    player.currentTime = savedPosition;
                }, { once: true });
            }
        }
    } catch (error) {
        // Silent fail - resume feature is optional
    }
}

function startWatchPositionTracking(videoId, player) {
    // Clear any existing interval
    if (watchPositionInterval) {
        clearInterval(watchPositionInterval);
    }
    
    // Save position AND watch duration every 10 seconds
    watchPositionInterval = setInterval(() => {
        if (!player.paused && player.currentTime > 0) {
            const position = player.currentTime;
            const duration = player.duration;
            const percentage = (position / duration) * 100;
            
            // Don't save if near the beginning (< 5 sec) or near the end (> 95%)
            if (position > 5 && percentage < 95) {
                saveWatchPosition(videoId, position, duration);
            }
            
            // Also update watch history with current duration (so history page shows real-time data)
            if (duration > 0) {
                const videoName = window.currentVideoName || 'Unknown';
                incrementViewCount(videoId, videoName, position, duration);
            }
        }
    }, 10000); // Every 10 seconds
}

async function saveWatchPosition(videoId, position, duration) {
    try {
        const userId = getUserId();
        await fetch(`/api/watchposition/${encodeURIComponent(videoId)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                position: Math.floor(position),
                duration: Math.floor(duration)
            })
        });
    } catch (error) {
        console.error('Error saving watch position:', error);
    }
}

// Close video player modal
function closeVideoPlayer() {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('videoPlayer');
    
    // Track final watch duration before closing
    if (window.currentVideoId && player.currentTime > 0 && player.duration > 0) {
        const durationWatched = player.currentTime;
        const videoDuration = player.duration;
        const videoName = window.currentVideoName || 'Unknown';
        
        // Send final watch duration to analytics
        incrementViewCount(window.currentVideoId, videoName, durationWatched, videoDuration);
        
        serverLog('VIDEO_CLOSED', `Watch time: ${Math.floor(durationWatched)}s / ${Math.floor(videoDuration)}s`, window.currentVideoId);
    } else if (window.currentVideoId) {
        const watchTime = player.currentTime ? Math.floor(player.currentTime) : 0;
        serverLog('VIDEO_CLOSED', `Watch time: ${watchTime}s`, window.currentVideoId);
    }
    
    // Save final watch position before closing
    if (window.currentVideoId && player.currentTime > 5) {
        saveWatchPosition(window.currentVideoId, player.currentTime, player.duration);
    }
    
    // Clear watch position tracking
    if (watchPositionInterval) {
        clearInterval(watchPositionInterval);
        watchPositionInterval = null;
    }
    
    // Clear token refresh interval (SECURITY)
    if (window.tokenRefreshInterval) {
        clearInterval(window.tokenRefreshInterval);
        window.tokenRefreshInterval = null;
    }

    modal.style.display = 'none';
    
    // Show main content area again (YouTube-style)
    const mainLayout = document.querySelector('.main-layout');
    if (mainLayout) {
        mainLayout.style.display = 'flex';
    }
    
    // Show feedback button and privacy banner when returning to home screen
    const feedbackBtn = document.getElementById('feedbackBtn');
    const privacyBanner = document.querySelector('.privacy-notice-banner');
    if (feedbackBtn) feedbackBtn.style.display = 'block';
    if (privacyBanner) privacyBanner.style.display = 'block';
    
    player.pause();
    player.src = '';
    
    // Remove all subtitle tracks
    const tracks = player.querySelectorAll('track');
    tracks.forEach(track => track.remove());
    
    // Remove keyboard listeners at all levels
    window.removeEventListener('keydown', handleVideoKeyboard, true);
    document.removeEventListener('keydown', handleVideoKeyboard, true);
    player.removeEventListener('keydown', handleVideoKeyboard, true);
}

// Alias for backwards compatibility
function closeModal() {
    closeVideoPlayer();
}

// ==========================================
// YOUTUBE-STYLE SEEK FEATURE
// ==========================================

let seekAccumulator = 0;
let seekTimeout = null;
let seekDirection = null;
let lastSeekTime = 0;
let isProgrammaticSeek = false; // Flag to distinguish programmatic vs manual seeks

// Handle keyboard shortcuts for video player (COMBINED: block native + custom seek)
function handleVideoKeyboard(event) {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('videoPlayer');
    
    // Only handle if modal is open and not typing in input field
    if (modal.style.display !== 'block' || event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    // Only intercept arrow keys (let other keys work normally)
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') {
        return;
    }
    
    // CRITICAL: Aggressively prevent native video controls
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    
    // Arrow Right: Forward 5 seconds
    if (event.key === 'ArrowRight') {
        seekVideo(5);
        return false;
    }
    // Arrow Left: Backward 5 seconds
    else if (event.key === 'ArrowLeft') {
        seekVideo(-5);
        return false;
    }
}

// Seek video and show visual feedback
function seekVideo(seconds) {
    const player = document.getElementById('videoPlayer');
    const indicator = document.getElementById('seekIndicator');
    
    if (!player || !indicator) {
        return;
    }
    
    // Determine direction
    const isForward = seconds > 0;
    const currentDirection = isForward ? 'forward' : 'backward';
    
    // Reset accumulator if direction changed
    if (seekDirection !== null && seekDirection !== currentDirection) {
        seekAccumulator = 0;
    }
    
    seekDirection = currentDirection;
    
    // ALWAYS accumulate (NO throttle for accumulation)
    seekAccumulator += Math.abs(seconds);
    
    // Set flag BEFORE seeking to indicate this is programmatic
    isProgrammaticSeek = true;
    
    // Seek the video
    const newTime = Math.max(0, Math.min(player.duration, player.currentTime + seconds));
    player.currentTime = newTime;
    
    // Reset flag after a short delay
    setTimeout(() => {
        isProgrammaticSeek = false;
    }, 10);
    
    // Update indicator (YouTube style with arrows) - ALWAYS update
    if (isForward) {
        indicator.textContent = `+${seekAccumulator} ►`;
    } else {
        indicator.textContent = `◄ -${seekAccumulator}`;
    }
    indicator.className = `seek-indicator show ${currentDirection}`;
    indicator.style.display = 'block';
    indicator.style.opacity = '1';
    
    // Clear existing timeout
    if (seekTimeout) {
        clearTimeout(seekTimeout);
    }
    
    // Hide indicator after 1 second of no activity
    seekTimeout = setTimeout(() => {
        indicator.classList.remove('show');
        indicator.style.display = 'none';
        indicator.style.opacity = '0';
        seekAccumulator = 0;
        seekDirection = null;
    }, 1000);
}

// Global variable to store available subtitles
window.availableSubtitles = [];
window.currentSubtitleIndex = -1;

// Load subtitles for a video
async function loadSubtitles(videoId) {
    const player = document.getElementById('videoPlayer');
    const ccButton = document.getElementById('ccButton');
    const ccBadge = document.getElementById('ccBadge');
    const subtitleOptions = document.getElementById('subtitleOptions');
    
    try {
        // Remove existing tracks
        const existingTracks = player.querySelectorAll('track');
        existingTracks.forEach(track => track.remove());
        
        // Reset global state
        window.availableSubtitles = [];
        window.currentSubtitleIndex = -1;
        
        // Hide CC button initially
        if (ccButton) ccButton.style.display = 'none';
        
        // Fetch available subtitles
        const response = await fetch(`/api/subtitles/${encodeURIComponent(videoId)}`);
        if (!response.ok) {
            // No subtitles available
            return;
        }
        
        const data = await response.json();
        if (!data.success || !data.subtitles || data.subtitles.length === 0) {
            // No subtitles found
            return;
        }
        
        // SECURITY: Don't log subtitle data (contains SAS token URLs)
        
        // Store available subtitles
        window.availableSubtitles = data.subtitles;
        
        // Show CC button
        if (ccButton) {
            ccButton.style.display = 'flex';
            ccButton.classList.remove('active');
        }
        
        // Build subtitle selector options
        subtitleOptions.innerHTML = '';
        data.subtitles.forEach((subtitle, index) => {
            const option = document.createElement('div');
            option.className = 'subtitle-option';
            option.textContent = subtitle.label;
            option.onclick = () => selectSubtitle(index);
            subtitleOptions.appendChild(option);
        });
        
        // Add subtitle tracks to video player
        data.subtitles.forEach((subtitle, index) => {
            const track = document.createElement('track');
            track.kind = 'subtitles';
            track.label = subtitle.label;
            track.srclang = subtitle.lang;
            track.src = subtitle.url;
            track.id = `subtitle-track-${index}`;
            
            player.appendChild(track);
        });
        
        // Auto-enable first subtitle
        if (data.subtitles.length > 0) {
            selectSubtitle(0);
        }
        
    } catch (error) {
        console.error('Error loading subtitles:', error);
    }
}

// Toggle subtitle selector visibility
function toggleSubtitles() {
    const selector = document.getElementById('subtitleSelector');
    if (selector) {
        selector.style.display = selector.style.display === 'none' ? 'block' : 'none';
    }
}

// Select a subtitle track
function selectSubtitle(index) {
    const player = document.getElementById('videoPlayer');
    const ccButton = document.getElementById('ccButton');
    const ccBadge = document.getElementById('ccBadge');
    const selector = document.getElementById('subtitleSelector');
    
    // Hide selector
    if (selector) selector.style.display = 'none';
    
    if (!player || !player.textTracks) return;
    
    // Disable all tracks
    for (let i = 0; i < player.textTracks.length; i++) {
        player.textTracks[i].mode = 'hidden';
    }
    
    if (index === null || index < 0) {
        // Turn off subtitles
        window.currentSubtitleIndex = -1;
        if (ccButton) ccButton.classList.remove('active');
    } else {
        // Enable selected track
        if (player.textTracks[index]) {
            player.textTracks[index].mode = 'showing';
            window.currentSubtitleIndex = index;
            if (ccButton) ccButton.classList.add('active');
        }
    }
}

// Setup search listener
function setupSearchListener() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearchBtn');
    let searchTimeout = null;
    
    // Show/hide clear button
    searchInput.addEventListener('input', (e) => {
        clearBtn.style.display = e.target.value ? 'flex' : 'none';
    });
    
    // Focus: show search history
    searchInput.addEventListener('focus', () => {
        if (!searchInput.value && searchHistory.length > 0) {
            showSearchHistory();
        }
    });
    
    // Click outside: hide search history
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('searchHistoryDropdown');
        const searchContainer = document.querySelector('.search-container');
        if (!searchContainer.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
    
    searchInput.addEventListener('input', async (e) => {
        const query = e.target.value.toLowerCase().trim();
        currentQuery = query;

        // If video modal is open, close it to show search results
        const videoModal = document.getElementById('videoModal');
        if (videoModal && videoModal.style.display === 'block') {
            closeVideoPlayer();
        }

        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Hide search history when typing
        document.getElementById('searchHistoryDropdown').style.display = 'none';

        // Start with videos in current folder (or all if no folder selected)
        let baseVideos = currentFolder 
            ? allVideos.filter(video => video.folder === currentFolder)
            : allVideos;

        if (query === '') {
            filteredVideos = baseVideos;
            displayVideos(filteredVideos);
            document.getElementById('empty').style.display = 'none';
            document.getElementById('searchFiltersBar').style.display = 'none';
            return;
        }

        // Add to search history
        addToSearchHistory(query);

        // Search in title, uploader, and description (immediate)
        let matchedVideos = baseVideos.filter(video => {
            const nameMatch = video.name.toLowerCase().includes(query);
            const uploaderMatch = video.uploader && video.uploader.toLowerCase().includes(query);
            const descriptionMatch = video.description && video.description.toLowerCase().includes(query);
            return nameMatch || uploaderMatch || descriptionMatch;
        });

        // Display immediate results
        filteredVideos = matchedVideos;
        displayVideos(filteredVideos);
        updateSearchResultInfo(query, false); // false = still searching subtitles
        setupUploaderFilters();

        // Show "searching subtitles" indicator
        const resultCount = document.getElementById('searchResultCount');
        const originalText = resultCount.textContent;
        resultCount.innerHTML = `${originalText} <span style="color: #666; font-size: 12px;">(字幕を検索中...)</span>`;

        // Debounce subtitle search (wait 300ms after user stops typing)
        searchTimeout = setTimeout(async () => {
            try {
                // Search in subtitles via API
                const response = await fetch(`/api/search/subtitles?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.success && data.results.length > 0) {
                    // Add videos found in subtitles that aren't already in results
                    const subtitleVideoIds = data.results.map(r => r.video_id);
                    const additionalVideos = baseVideos.filter(video => 
                        subtitleVideoIds.includes(video.id) && !matchedVideos.find(v => v.id === video.id)
                    );
                    
                    if (additionalVideos.length > 0) {
                        // Mark these as found in subtitles
                        additionalVideos.forEach(v => v._foundInSubtitles = true);
                        filteredVideos = [...matchedVideos, ...additionalVideos];
                        displayVideos(filteredVideos);
                        updateSearchResultInfo(query, true, additionalVideos.length);
                        setupUploaderFilters();
                        // Hide empty state since we found results
                        document.getElementById('empty').style.display = 'none';
                    } else {
                        // No additional results from subtitles
                        updateSearchResultInfo(query, true, 0);
                    }
                } else {
                    // No subtitle matches
                    updateSearchResultInfo(query, true, 0);
                }
                
                // Check if we should show empty state AFTER subtitle search completes
                const empty = document.getElementById('empty');
                const videoGrid = document.getElementById('videoGrid');
                if (filteredVideos.length === 0 && allVideos.length > 0) {
                    videoGrid.innerHTML = '';
                    empty.style.display = 'block';
                    empty.textContent = `ℹ️ "${query}" に一致する動画が見つかりませんでした。タイトル、説明、アップロード者、字幕の内容を検索しました。`;
                    document.getElementById('searchFiltersBar').style.display = 'none';
                } else {
                    empty.style.display = 'none';
                }
            } catch (error) {
                console.error('Subtitle search error:', error);
                updateSearchResultInfo(query, true, 0);
                
                // Check empty state even on error
                const empty = document.getElementById('empty');
                if (filteredVideos.length === 0 && allVideos.length > 0) {
                    empty.style.display = 'block';
                    empty.textContent = `ℹ️ "${query}" に一致する動画が見つかりませんでした。タイトル、説明、アップロード者、字幕の内容を検索しました。`;
                    document.getElementById('searchFiltersBar').style.display = 'none';
                }
            }
        }, 300); // Reduced from 500ms to 300ms for faster response

        // Don't show empty state immediately - wait for subtitle search to complete
        // Just hide it for now if there are immediate results
        const empty = document.getElementById('empty');
        if (matchedVideos.length > 0) {
            empty.style.display = 'none';
        }
    });
}

// Clear search
function clearSearch() {
    const searchInput = document.getElementById('searchInput');
    searchInput.value = '';
    searchInput.focus();
    currentQuery = '';
    document.getElementById('clearSearchBtn').style.display = 'none';
    document.getElementById('searchFiltersBar').style.display = 'none';
    filteredVideos = currentFolder 
        ? allVideos.filter(video => video.folder === currentFolder)
        : allVideos;
    displayVideos(filteredVideos);
    document.getElementById('empty').style.display = 'none';
}

// Search history functions
function setupSearchHistory() {
    // Load from localStorage on init
    searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
}

function addToSearchHistory(query) {
    if (!query || query.length < 2) return;
    
    // Remove if already exists
    searchHistory = searchHistory.filter(item => item !== query);
    
    // Add to beginning
    searchHistory.unshift(query);
    
    // Keep only last 10
    searchHistory = searchHistory.slice(0, 10);
    
    // Save to localStorage
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
}

function showSearchHistory() {
    const dropdown = document.getElementById('searchHistoryDropdown');
    const listDiv = document.getElementById('searchHistoryList');
    
    if (searchHistory.length === 0) {
        dropdown.style.display = 'none';
        return;
    }
    
    listDiv.innerHTML = searchHistory.map(query => `
        <div class="search-history-item" onclick="applySearchHistory('${escapeHtml(query)}')">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
            </svg>
            <span>${escapeHtml(query)}</span>
            <button onclick="event.stopPropagation(); removeFromSearchHistory('${escapeHtml(query)}')">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
            </button>
        </div>
    `).join('');
    
    dropdown.style.display = 'block';
}

function applySearchHistory(query) {
    const searchInput = document.getElementById('searchInput');
    searchInput.value = query;
    searchInput.dispatchEvent(new Event('input'));
    document.getElementById('searchHistoryDropdown').style.display = 'none';
}

function removeFromSearchHistory(query) {
    searchHistory = searchHistory.filter(item => item !== query);
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
    showSearchHistory();
}

// Update search result info
function updateSearchResultInfo(query, subtitleSearchComplete = false, subtitleResults = 0) {
    const resultCount = document.getElementById('searchResultCount');
    const filtersBar = document.getElementById('searchFiltersBar');
    
    if (query) {
        const count = filteredVideos.length;
        let message = `"${query}" の検索結果: ${count}件`;
        
        if (subtitleSearchComplete && subtitleResults > 0) {
            message += ` <span style="color: #00CED1; font-size: 12px;">(字幕から${subtitleResults}件)</span>`;
        }
        
        resultCount.innerHTML = message;
        filtersBar.style.display = 'flex';
    } else {
        filtersBar.style.display = 'none';
    }
}

// Setup uploader filters
function setupUploaderFilters() {
    const uploaderFiltersDiv = document.getElementById('uploaderFilters');
    
    // Get unique uploaders from filtered videos
    const uploaderCounts = {};
    filteredVideos.forEach(video => {
        const uploader = video.uploader || '不明';
        uploaderCounts[uploader] = (uploaderCounts[uploader] || 0) + 1;
    });
    
    // Create filter pills
    uploaderFiltersDiv.innerHTML = Object.entries(uploaderCounts)
        .sort((a, b) => b[1] - a[1])
        .map(([uploader, count]) => `
            <div class="uploader-filter-pill ${selectedUploaders.has(uploader) ? 'active' : ''}" 
                 onclick="toggleUploaderFilter('${escapeHtml(uploader)}')">
                ${escapeHtml(uploader)}
                <span class="count">(${count})</span>
            </div>
        `).join('');
}

function toggleUploaderFilter(uploader) {
    if (selectedUploaders.has(uploader)) {
        selectedUploaders.delete(uploader);
    } else {
        selectedUploaders.add(uploader);
    }
    applySortAndFilter();
}

// Apply sort and filter
function applySortAndFilter() {
    const sortSelect = document.getElementById('sortSelect');
    currentSort = sortSelect.value;
    
    // Start with current search results
    let videos = [...filteredVideos];
    
    // Apply uploader filter
    if (selectedUploaders.size > 0) {
        videos = videos.filter(video => selectedUploaders.has(video.uploader || '不明'));
    }
    
    // Apply sort
    switch (currentSort) {
        case 'date':
            videos.sort((a, b) => (b.lastModified || '').localeCompare(a.lastModified || ''));
            break;
        case 'views':
            videos.sort((a, b) => (b.views || 0) - (a.views || 0));
            break;
        case 'title':
            videos.sort((a, b) => a.name.localeCompare(b.name, 'ja'));
            break;
        case 'relevance':
        default:
            // Keep original search relevance order
            break;
    }
    
    displayVideos(videos);
    setupUploaderFilters(); // Refresh filter pills
}

// Utility: Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// Utility: Format view count (YouTube-style)
function formatViews(views) {
    if (!views || views === 0) return '0';
    
    if (views < 1000) {
        return views.toString();
    } else if (views < 10000) {
        // 1.2K format
        return (views / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    } else if (views < 1000000) {
        // 12K format
        return Math.floor(views / 1000) + 'K';
    } else if (views < 10000000) {
        // 1.2M format
        return (views / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
    } else {
        // 12M format
        return Math.floor(views / 1000000) + 'M';
    }
}

// Utility: Format date
function formatDate(dateString) {
    if (!dateString) return '不明';
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Load engagement data for a video
async function loadEngagement(videoId) {
    try {
        const response = await fetch(`/api/engagement/${encodeURIComponent(videoId)}`);
        if (!response.ok) {
            console.error('Failed to load engagement data');
            return;
        }
        
        const data = await response.json();
        
        // Update counts
        document.getElementById('likeCount').textContent = data.likes || 0;
        document.getElementById('dislikeCount').textContent = data.dislikes || 0;
        document.getElementById('commentsCount').textContent = data.comments_count || 0;
        
        // Set active states based on user's action
        const likeBtn = document.getElementById('likeBtn');
        const dislikeBtn = document.getElementById('dislikeBtn');
        
        likeBtn.classList.remove('active');
        dislikeBtn.classList.remove('active');
        
        if (data.user_action === 'like') {
            likeBtn.classList.add('active');
        } else if (data.user_action === 'dislike') {
            dislikeBtn.classList.add('active');
        }
        
        // Load comments
        loadComments(videoId);
    } catch (error) {
        console.error('Error loading engagement:', error);
    }
}

// Load comments for a video
async function loadComments(videoId) {
    try {
        const response = await fetch(`/api/comments/${encodeURIComponent(videoId)}`);
        if (!response.ok) {
            console.error('Failed to load comments');
            return;
        }
        
        const data = await response.json();
        const comments = data.comments || [];
        const commentsList = document.getElementById('commentsList');
        
        if (comments.length === 0) {
            commentsList.innerHTML = '<div class="comments-empty">No comments yet. Be the first to comment!</div>';
            return;
        }
        
        // Build comments HTML
        commentsList.innerHTML = comments.map(comment => `
            <div class="comment-item">
                <div class="comment-header">
                    <span class="comment-author">${escapeHtml(comment.author || 'Anonymous')}</span>
                    <span class="comment-time">${formatDate(comment.timestamp)}</span>
                </div>
                <div class="comment-text">${escapeHtml(comment.text)}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading comments:', error);
    }
}

// Handle like button click
let isLikeProcessing = false;
let lastLikeClickTime = 0;
async function handleLike() {
    if (!window.currentVideoId) return;
    
    const likeBtn = document.getElementById('likeBtn');
    const now = Date.now();
    
    // Aggressive debounce: Ignore clicks within 1 second
    if (now - lastLikeClickTime < 1000) {
        return;
    }
    
    // Prevent multiple simultaneous requests (fixes race condition)
    if (isLikeProcessing || likeBtn.disabled) {
        return;
    }
    
    // Update last click time
    lastLikeClickTime = now;
    
    // Lock and disable button
    isLikeProcessing = true;
    likeBtn.disabled = true;
    likeBtn.style.pointerEvents = 'none';
    likeBtn.style.opacity = '0.5';
    
    try {
        const response = await fetch(`/api/like/${encodeURIComponent(window.currentVideoId)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: getUserId() })
        });
        
        // Handle rate limiting (429) silently
        if (response.status === 429) {
            return;
        }
        
        if (!response.ok) {
            return;
        }
        
        const data = await response.json();
        
        // Update counts
        document.getElementById('likeCount').textContent = data.likes || 0;
        document.getElementById('dislikeCount').textContent = data.dislikes || 0;
        
        // Update active states
        const dislikeBtn = document.getElementById('dislikeBtn');
        
        likeBtn.classList.remove('active');
        dislikeBtn.classList.remove('active');
        
        if (data.action === 'liked') {
            likeBtn.classList.add('active');
        }
        
        // Small delay to prevent accidental double-clicks
        await new Promise(resolve => setTimeout(resolve, 200));
        
    } catch (error) {
        console.error('Error toggling like:', error);
    } finally {
        // Always re-enable the button
        likeBtn.disabled = false;
        likeBtn.style.pointerEvents = '';
        likeBtn.style.opacity = '';
        isLikeProcessing = false;
    }
}

// Handle dislike button click
let isDislikeProcessing = false;
let lastDislikeClickTime = 0;
async function handleDislike() {
    if (!window.currentVideoId) return;
    
    const dislikeBtn = document.getElementById('dislikeBtn');
    const now = Date.now();
    
    // Aggressive debounce: Ignore clicks within 1 second
    if (now - lastDislikeClickTime < 1000) {
        return;
    }
    
    // Prevent multiple simultaneous requests (fixes race condition)
    if (isDislikeProcessing || dislikeBtn.disabled) {
        return;
    }
    
    // Update last click time
    lastDislikeClickTime = now;
    
    // Lock and disable button
    isDislikeProcessing = true;
    dislikeBtn.disabled = true;
    dislikeBtn.style.pointerEvents = 'none';
    dislikeBtn.style.opacity = '0.5';
    
    try {
        const response = await fetch(`/api/dislike/${encodeURIComponent(window.currentVideoId)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: getUserId() })
        });
        
        // Handle rate limiting (429) silently
        if (response.status === 429) {
            return;
        }
        
        if (!response.ok) {
            return;
        }
        
        const data = await response.json();
        
        // Update counts
        document.getElementById('likeCount').textContent = data.likes || 0;
        document.getElementById('dislikeCount').textContent = data.dislikes || 0;
        
        // Update active states
        const likeBtn = document.getElementById('likeBtn');
        
        likeBtn.classList.remove('active');
        dislikeBtn.classList.remove('active');
        
        if (data.action === 'disliked') {
            dislikeBtn.classList.add('active');
        }
        
        // Small delay to prevent accidental double-clicks
        await new Promise(resolve => setTimeout(resolve, 200));
        
    } catch (error) {
        // Silent fail
    } finally {
        // Always re-enable the button
        dislikeBtn.disabled = false;
        dislikeBtn.style.pointerEvents = '';
        dislikeBtn.style.opacity = '';
        isDislikeProcessing = false;
    }
}

// Submit a new comment
async function submitComment() {
    if (!window.currentVideoId) return;
    
    const authorInput = document.getElementById('authorName');
    const textArea = document.getElementById('commentText');
    const submitBtn = document.querySelector('.submit-comment-btn');
    
    const author = authorInput.value.trim() || 'Anonymous';
    const text = textArea.value.trim();
    
    // Validate
    if (!text) {
        alert('Comment text is required');
        return;
    }
    
    if (text.length > 1000) {
        alert('Comment is too long (max 1000 characters)');
        return;
    }
    
    // Disable button during submission
    submitBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/comment/${encodeURIComponent(window.currentVideoId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                author_name: author
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            alert(`Failed to post comment: ${error.error || 'Unknown error'}`);
            submitBtn.disabled = false;
            return;
        }
        
        const data = await response.json();
        const comment = data.comment;
        
        // Update comments count
        const commentsCount = document.getElementById('commentsCount');
        const currentCount = parseInt(commentsCount.textContent) || 0;
        commentsCount.textContent = currentCount + 1;
        
        // Add comment to list
        const commentsList = document.getElementById('commentsList');
        
        // Remove empty state if present
        const emptyState = commentsList.querySelector('.comments-empty');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Create new comment element
        const commentHtml = `
            <div class="comment-item">
                <div class="comment-header">
                    <span class="comment-author">${escapeHtml(comment.author || 'Anonymous')}</span>
                    <span class="comment-time">${formatDate(comment.timestamp)}</span>
                </div>
                <div class="comment-text">${escapeHtml(comment.text)}</div>
            </div>
        `;
        
        // Insert at the beginning (newest first)
        commentsList.insertAdjacentHTML('afterbegin', commentHtml);
        
        // Clear form
        authorInput.value = '';
        textArea.value = '';
        
    } catch (error) {
        console.error('Error posting comment:', error);
        alert('Failed to post comment');
    } finally {
        submitBtn.disabled = false;
    }
}

// Handle share button click
async function handleShare() {
    if (!window.currentVideoId) return;
    
    // Create URL with video parameter
    const url = window.location.origin + window.location.pathname + '?video=' + encodeURIComponent(window.currentVideoId);
    
    try {
        // Try native share API first (mobile friendly)
        if (navigator.share) {
            await navigator.share({
                title: 'Share Video',
                url: url
            });
        } else {
            // Fallback to clipboard
            await navigator.clipboard.writeText(url);
            
            // Show temporary success message
            const shareBtn = document.querySelector('.engagement-btn:nth-child(3)');
            const originalText = shareBtn.innerHTML;
            shareBtn.innerHTML = '<span class="btn-icon">✓</span><span>Link Copied!</span>';
            shareBtn.style.background = '#065fd4';
            
            setTimeout(() => {
                shareBtn.innerHTML = originalText;
                shareBtn.style.background = '';
            }, 2000);
        }
    } catch (error) {
        console.error('Error sharing:', error);
        alert('Failed to copy link');
    }
}

/* Download feature temporarily disabled (can be restored by uncommenting)
// Handle download button click
async function handleDownload() {
    if (!window.currentVideoId) return;
    
    const downloadBtn = document.querySelector('.engagement-btn:nth-child(4)');
    const originalText = downloadBtn ? downloadBtn.innerHTML : '';
    
    try {
        // Show downloading message
        if (downloadBtn) {
            downloadBtn.innerHTML = '<span class="btn-icon">⏳</span><span>Downloading...</span>';
            downloadBtn.style.background = '#065fd4';
        }
        
        // Create download URL (Flask will stream from blob storage)
        const downloadUrl = `/api/download/${encodeURIComponent(window.currentVideoId)}`;
        
        // Create a temporary link element and click it to trigger download
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Show success message
        if (downloadBtn) {
            downloadBtn.innerHTML = '<span class="btn-icon">✓</span><span>Download started!</span>';
            
            setTimeout(() => {
                downloadBtn.innerHTML = originalText;
                downloadBtn.style.background = '';
            }, 2000);
        }
    } catch (error) {
        console.error('Error downloading:', error);
        alert('Failed to download video. Please try again.');
        
        // Restore button
        if (downloadBtn) {
            downloadBtn.innerHTML = originalText;
            downloadBtn.style.background = '';
        }
    }
}
*/

// Format date for comments
function formatDate(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    // Fallback to full date
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Utility: Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Utility: Highlight matching text
function highlightText(text, query) {
    if (!query || !text) return escapeHtml(text);
    
    const escapedText = escapeHtml(text);
    const escapedQuery = escapeHtml(query);
    
    // Case-insensitive search
    const regex = new RegExp(`(${escapedQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return escapedText.replace(regex, '<span class="highlight">$1</span>');
}

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// ==========================================
// CHAPTERS / TIMESTAMPS FEATURE
// ==========================================

// Load chapters for a video
async function loadChapters(videoId) {
    const chaptersSection = document.getElementById('chaptersSection');
    const chaptersList = document.getElementById('chaptersList');
    const chaptersCount = document.getElementById('chaptersCount');
    
    if (!chaptersSection) return;
    
    // Show loading state
    chaptersSection.style.display = 'block';
    chaptersList.innerHTML = '<div class="chapters-loading">チャプターを読み込んでいます...</div>';
    
    try {
        const response = await fetch(`/api/chapters/${encodeURIComponent(videoId)}`);
        
        if (!response.ok) {
            chaptersSection.style.display = 'none';
            return;
        }
        
        const data = await response.json();
        
        if (!data.success || !data.chapters || data.chapters.length === 0) {
            chaptersSection.style.display = 'none';
            return;
        }
        
        // Display chapters
        chaptersCount.textContent = `${data.chapters.length}`;
        chaptersList.innerHTML = '';
        
        data.chapters.forEach((chapter, index) => {
            const chapterItem = document.createElement('div');
            chapterItem.className = 'chapter-item';
            chapterItem.onclick = () => seekToChapter(chapter.timestamp);
            
            chapterItem.innerHTML = `
                <span class="chapter-timestamp">${formatTimestamp(chapter.timestamp)}</span>
                <div class="chapter-content">
                    <div class="chapter-title">${escapeHtml(chapter.title)}</div>
                    ${chapter.description ? `<div class="chapter-description">${escapeHtml(chapter.description)}</div>` : ''}
                </div>
            `;
            
            chaptersList.appendChild(chapterItem);
        });
        
        // Set up tracking of current chapter based on video time
        setupChapterTracking();
        
    } catch (error) {
        console.error('Error loading chapters:', error);
        chaptersSection.style.display = 'none';
    }
}

// Format timestamp (seconds) to HH:MM:SS or MM:SS
function formatTimestamp(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Seek video to chapter timestamp
function seekToChapter(timestamp) {
    const player = document.getElementById('videoPlayer');
    if (player) {
        player.currentTime = timestamp;
        player.play();
    }
}

// Track current chapter as video plays
function setupChapterTracking() {
    const player = document.getElementById('videoPlayer');
    if (!player) return;
    
    player.addEventListener('timeupdate', updateActiveChapter);
}

// Update which chapter is active based on current time
function updateActiveChapter() {
    const player = document.getElementById('videoPlayer');
    const chapterItems = document.querySelectorAll('.chapter-item');
    
    if (!player || chapterItems.length === 0) return;
    
    const currentTime = player.currentTime;
    
    chapterItems.forEach((item, index) => {
        const timestampText = item.querySelector('.chapter-timestamp').textContent;
        const timestamp = parseTimestamp(timestampText);
        
        // Get next chapter timestamp
        let nextTimestamp = Infinity;
        if (index < chapterItems.length - 1) {
            const nextTimestampText = chapterItems[index + 1].querySelector('.chapter-timestamp').textContent;
            nextTimestamp = parseTimestamp(nextTimestampText);
        }
        
        if (currentTime >= timestamp && currentTime < nextTimestamp) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// Parse timestamp string (HH:MM:SS or MM:SS) to seconds
function parseTimestamp(timeStr) {
    const parts = timeStr.split(':').map(p => parseInt(p, 10));
    if (parts.length === 3) {
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
        return parts[0] * 60 + parts[1];
    }
    return 0;
}

// ==========================================
// TRANSCRIPT/MOJIGOKOSHI FEATURE (YouTube-style)
// ==========================================

// Load transcript (文字起こし) from subtitles
async function loadTranscript(videoId, lang = 'ja') {
    const transcriptSidebar = document.getElementById('transcriptSidebar');
    const transcriptList = document.getElementById('transcriptList');
    
    if (!transcriptSidebar || !transcriptList) return;
    
    // Show loading state
    transcriptSidebar.style.display = 'block';
    transcriptList.innerHTML = '<div class="transcript-loading">字幕を読み込んでいます...</div>';
    
    try {
        const response = await fetch(`/api/transcript/${encodeURIComponent(videoId)}?lang=${lang}`);
        
        if (!response.ok) {
            transcriptSection.style.display = 'none';
            return;
        }
        
        const data = await response.json();
        
        if (!data.success || !data.lines || data.lines.length === 0) {
            transcriptList.innerHTML = '<div class="transcript-empty">字幕がありません</div>';
            return;
        }
        
        // Display transcript lines
        transcriptList.innerHTML = '';
        
        data.lines.forEach((line, index) => {
            const lineItem = document.createElement('div');
            lineItem.className = 'transcript-line';
            lineItem.setAttribute('data-start', line.start);
            lineItem.setAttribute('data-end', line.end);
            lineItem.onclick = () => seekToTranscript(line.start);
            
            lineItem.innerHTML = `
                <span class="transcript-timestamp">${line.start_display}</span>
                <span class="transcript-text">${escapeHtml(line.text)}</span>
            `;
            
            transcriptList.appendChild(lineItem);
        });
        
        // Set up tracking of current transcript line based on video time
        setupTranscriptTracking();
        
    } catch (error) {
        console.error('Error loading transcript:', error);
        transcriptList.innerHTML = '<div class="transcript-error">字幕の読み込みに失敗しました</div>';
    }
}

// Seek video to transcript timestamp
function seekToTranscript(seconds) {
    const player = document.getElementById('videoPlayer');
    if (player) {
        player.currentTime = seconds;
        player.play();
    }
}

// Track and highlight current transcript line as video plays
function setupTranscriptTracking() {
    const player = document.getElementById('videoPlayer');
    if (!player) return;
    
    // Remove existing listener if any
    player.removeEventListener('timeupdate', updateActiveTranscriptLine);
    player.addEventListener('timeupdate', updateActiveTranscriptLine);
}

// Update which transcript line is active based on current time (YouTube-style auto-scroll)
function updateActiveTranscriptLine() {
    const player = document.getElementById('videoPlayer');
    const transcriptLines = document.querySelectorAll('.transcript-line');
    const transcriptList = document.getElementById('transcriptList');
    
    if (!player || transcriptLines.length === 0 || !transcriptList) return;
    
    const currentTime = player.currentTime;
    let activeLineElement = null;
    
    transcriptLines.forEach((line) => {
        const start = parseFloat(line.getAttribute('data-start'));
        const end = parseFloat(line.getAttribute('data-end'));
        
        if (currentTime >= start && currentTime <= end) {
            line.classList.add('active');
            activeLineElement = line;
        } else {
            line.classList.remove('active');
        }
    });
    
    // Auto-scroll to active line (YouTube-style)
    if (activeLineElement) {
        const lineTop = activeLineElement.offsetTop;
        const lineHeight = activeLineElement.offsetHeight;
        const listHeight = transcriptList.offsetHeight;
        const listScrollTop = transcriptList.scrollTop;
        
        // Scroll if active line is not visible
        if (lineTop < listScrollTop || lineTop + lineHeight > listScrollTop + listHeight) {
            // Scroll so active line is in middle of view
            transcriptList.scrollTop = lineTop - (listHeight / 2) + (lineHeight / 2);
        }
    }
}

// ==========================================
// RELATED VIDEOS SIDEBAR FEATURE
// ==========================================

// Load related videos (same folder)
function loadRelatedVideos(currentVideo) {
    const sidebar = document.getElementById('relatedVideosSidebar');
    const videosList = document.getElementById('relatedVideosList');
    
    if (!sidebar || !videosList) return;
    
    // Get videos from the same folder, excluding current video
    const relatedVideos = allVideos.filter(v => 
        v.folder === currentVideo.folder && v.id !== currentVideo.id
    );
    
    if (relatedVideos.length === 0) {
        videosList.innerHTML = '<div class="related-videos-empty">このフォルダには他の動画がありません</div>';
        return;
    }
    
    videosList.innerHTML = '';
    
    relatedVideos.forEach(video => {
        const card = document.createElement('div');
        card.className = 'related-video-card';
        card.onclick = () => switchToVideo(video);
        
        card.innerHTML = `
            <div class="related-video-thumbnail">
                <div class="thumbnail-placeholder">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z" />
                    </svg>
                </div>
            </div>
            <div class="related-video-info">
                <div class="related-video-title">${escapeHtml(video.name)}</div>
                <div class="related-video-meta">${formatViews(video.views)}回視聴</div>
            </div>
        `;
        
        videosList.appendChild(card);
        
        // Load thumbnail for related video
        loadRelatedThumbnail(video.id, card);
    });
}

// Load thumbnail for related video card
function loadRelatedThumbnail(videoId, cardElement) {
    const thumbnailDiv = cardElement.querySelector('.related-video-thumbnail');
    if (!thumbnailDiv) return;
    
    const img = document.createElement('img');
    img.style.display = 'none';
    
    img.onload = function() {
        img.style.display = 'block';
        const placeholder = thumbnailDiv.querySelector('.thumbnail-placeholder');
        if (placeholder) placeholder.style.display = 'none';
    };
    
    img.onerror = function() {
        // Keep showing placeholder
    };
    
    img.src = `/api/thumbnail/${encodeURIComponent(videoId)}`;
    thumbnailDiv.appendChild(img);
}

// Switch to a different video (from related videos)
async function switchToVideo(video) {
    const player = document.getElementById('videoPlayer');
    
    // Track watch duration of previous video before switching
    if (window.currentVideoId && player && player.currentTime > 0 && player.duration > 0) {
        const durationWatched = player.currentTime;
        const videoDuration = player.duration;
        const previousVideoName = window.currentVideoName || 'Unknown';
        
        // Save previous video's watch duration
        incrementViewCount(window.currentVideoId, previousVideoName, durationWatched, videoDuration);
        
        // Save watch position
        if (durationWatched > 5) {
            saveWatchPosition(window.currentVideoId, durationWatched, videoDuration);
        }
        
        serverLog('VIDEO_SWITCHED', `Saved watch time: ${Math.floor(durationWatched)}s / ${Math.floor(videoDuration)}s`, window.currentVideoId);
    }
    
    // Stop current video
    if (player) {
        player.pause();
        
        // Remove existing tracks
        const existingTracks = player.querySelectorAll('track');
        existingTracks.forEach(track => track.remove());
    }
    
    // Update modal with new video
    document.getElementById('modalTitle').textContent = video.name;
    document.getElementById('modalDate').textContent = `更新日: ${formatDate(video.lastModified)}`;
    document.getElementById('modalSize').textContent = `サイズ: ${formatFileSize(video.size)}`;
    
    // SECURITY: Fetch video URL with fresh 2-minute SAS token from backend
    try {
        const userId = localStorage.getItem('pt_user_id') || 'anonymous';
        const urlResponse = await fetch(`/api/video-url/${encodeURIComponent(video.id)}?user_id=${userId}`);
        const urlData = await urlResponse.json();
        
        if (!urlData.success) {
            throw new Error(urlData.error || 'Failed to get video URL');
        }
        
        player.src = urlData.url;
        window.currentVideoTokenExpires = Date.now() + (urlData.expires_in * 1000);
        
        // Update token refresh for new video
        if (window.tokenRefreshInterval) {
            clearInterval(window.tokenRefreshInterval);
        }
        window.currentVideo = video;
        window.tokenRefreshInterval = setInterval(async () => {
            if (document.getElementById('videoModal').style.display === 'block') {
                await refreshVideoToken(video);
            } else {
                clearInterval(window.tokenRefreshInterval);
            }
        }, 60000);
        
    } catch (err) {
        console.error('❌ Failed to get video URL:', err);
        alert('ビデオの読み込みに失敗しました。');
        return;
    }
    
    // Update current video ID and name
    window.currentVideoId = video.id;
    window.currentVideoName = video.name;
    
    // Reset engagement button states
    const likeBtn = document.getElementById('likeBtn');
    const dislikeBtn = document.getElementById('dislikeBtn');
    if (likeBtn) likeBtn.classList.remove('active');
    if (dislikeBtn) dislikeBtn.classList.remove('active');
    
    // Note: View count tracking happens when video is closed (to capture actual watch duration)
    
    // Reload engagement, subtitles, chapters, and related videos
    loadEngagement(video.id);
    loadSubtitles(video.id);
    loadChapters(video.id);
    loadRelatedVideos(video);
    
    // Update active state in related videos list
    updateRelatedVideoActiveState(video.id);
}

// Update active state for related video cards
function updateRelatedVideoActiveState(activeVideoId) {
    const cards = document.querySelectorAll('.related-video-card');
    cards.forEach(card => {
        card.classList.remove('active');
    });
}

// Modal search functions removed - using main header search only (YouTube-style)

// =============================================================================
// TRACK WATCH DURATION WHEN USER NAVIGATES AWAY OR CLOSES PAGE
// =============================================================================
window.addEventListener('beforeunload', function(event) {
    const player = document.getElementById('videoPlayer');
    
    // If a video is currently playing, save final watch duration
    if (window.currentVideoId && player && player.currentTime > 0 && player.duration > 0) {
        const durationWatched = player.currentTime;
        const videoDuration = player.duration;
        const videoName = window.currentVideoName || 'Unknown';
        
        // Use sendBeacon for reliable delivery even during page unload
        // (fetch requests may be cancelled during unload)
        const data = JSON.stringify({
            name: videoName,
            duration_watched: Math.round(durationWatched),
            video_duration: Math.round(videoDuration)
        });
        
        const videoId = window.currentVideoId;
        const url = `/api/view/${encodeURIComponent(videoId)}`;
        
        // Try sendBeacon first (most reliable), fallback to sync fetch
        if (navigator.sendBeacon) {
            navigator.sendBeacon(url, new Blob([data], { type: 'application/json' }));
        }
    }
});
