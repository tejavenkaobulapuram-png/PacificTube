// Pacific Tube - Frontend JavaScript

let allVideos = [];
let filteredVideos = [];
let currentFolder = null;
let currentQuery = '';
let currentSort = 'relevance';
let selectedUploaders = new Set();
let searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadFolders();
    loadVideos();
    setupSearchListener();
    setupSearchHistory();
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

// Display videos in grid
function displayVideos(videos) {
    const videoGrid = document.getElementById('videoGrid');
    videoGrid.innerHTML = '';

    videos.forEach(video => {
        const card = createVideoCard(video);
        videoGrid.appendChild(card);
        
        // Load thumbnail from backend
        loadThumbnail(video.id);
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
        </div>
    `;

    // Highlight matching text in title
    const highlightedTitle = currentQuery ? highlightText(video.name, currentQuery) : escapeHtml(video.name);
    
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
                    ${escapeHtml(video.uploader || '不明')}
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
function openModal(video) {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('videoPlayer');
    const title = document.getElementById('modalTitle');
    const date = document.getElementById('modalDate');
    const size = document.getElementById('modalSize');

    title.textContent = video.name;
    date.textContent = `更新日: ${formatDate(video.lastModified)}`;
    size.textContent = `サイズ: ${formatFileSize(video.size)}`;

    player.src = video.url;
    modal.style.display = 'flex';

    // Store current video ID and video object for engagement actions
    window.currentVideoId = video.id;
    window.currentVideo = video;
    
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

    // Increment view count
    incrementViewCount(video.id, video.name);

    // Load engagement data (likes, dislikes, comments)
    loadEngagement(video.id);
    
    // Load subtitles for this video
    loadSubtitles(video.id);
    
    // Load chapters/timestamps for this video
    loadChapters(video.id);
    
    // Load related videos from same folder
    loadRelatedVideos(video);

    // Close on background click
    modal.onclick = (e) => {
        if (e.target === modal) {
            closeModal();
        }
    };
}

// Increment view count when video is played
async function incrementViewCount(videoId, videoName) {
    try {
        const response = await fetch(`/api/view/${encodeURIComponent(videoId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: videoName })
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

// Close video player modal
function closeModal() {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('videoPlayer');

    modal.style.display = 'none';
    player.pause();
    player.src = '';
    
    // Remove all subtitle tracks
    const tracks = player.querySelectorAll('track');
    tracks.forEach(track => track.remove());
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
            console.log('No subtitles available for this video');
            return;
        }
        
        const data = await response.json();
        if (!data.success || !data.subtitles || data.subtitles.length === 0) {
            console.log('No subtitles found');
            return;
        }
        
        console.log(`📝 Found ${data.subtitles.length} subtitle(s):`, data.subtitles);
        
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
        console.log('Subtitles OFF');
    } else {
        // Enable selected track
        if (player.textTracks[index]) {
            player.textTracks[index].mode = 'showing';
            window.currentSubtitleIndex = index;
            if (ccButton) ccButton.classList.add('active');
            const langName = window.availableSubtitles[index]?.label || 'Subtitles';
            console.log(`Subtitles ON: ${langName}`);
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
async function handleLike() {
    if (!window.currentVideoId) return;
    
    const likeBtn = document.getElementById('likeBtn');
    
    // Prevent multiple simultaneous requests (fixes race condition)
    if (isLikeProcessing || likeBtn.disabled) {
        console.log('⏳ Like request already in progress, ignoring click');
        return;
    }
    
    // Lock and disable button
    isLikeProcessing = true;
    likeBtn.disabled = true;
    likeBtn.style.pointerEvents = 'none';
    likeBtn.style.opacity = '0.5';
    
    try {
        const response = await fetch(`/api/like/${encodeURIComponent(window.currentVideoId)}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            console.error('Failed to toggle like');
            return;
        }
        
        const data = await response.json();
        console.log('Like response:', data); // Debug log
        
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
async function handleDislike() {
    if (!window.currentVideoId) return;
    
    const dislikeBtn = document.getElementById('dislikeBtn');
    
    // Prevent multiple simultaneous requests (fixes race condition)
    if (isDislikeProcessing || dislikeBtn.disabled) {
        console.log('⏳ Dislike request already in progress, ignoring click');
        return;
    }
    
    // Lock and disable button
    isDislikeProcessing = true;
    dislikeBtn.disabled = true;
    dislikeBtn.style.pointerEvents = 'none';
    dislikeBtn.style.opacity = '0.5';
    
    try {
        const response = await fetch(`/api/dislike/${encodeURIComponent(window.currentVideoId)}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            console.error('Failed to toggle dislike');
            return;
        }
        
        const data = await response.json();
        console.log('Dislike response:', data); // Debug log
        
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
        console.error('Error toggling dislike:', error);
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
function switchToVideo(video) {
    const player = document.getElementById('videoPlayer');
    
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
    
    // Update video source
    player.src = video.url;
    
    // Update current video ID
    window.currentVideoId = video.id;
    
    // Reset engagement button states
    const likeBtn = document.getElementById('likeBtn');
    const dislikeBtn = document.getElementById('dislikeBtn');
    if (likeBtn) likeBtn.classList.remove('active');
    if (dislikeBtn) dislikeBtn.classList.remove('active');
    
    // Increment view count
    incrementViewCount(video.id, video.name);
    
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
