// ------------------- API CONFIG -------------------
//const API_BASE = 'http://localhost:8000/api/server';
const API_BASE = 'https://diplom.cloudpub.ru/api/server'
let accessToken = localStorage.getItem('access_token') || null;
let refreshToken = localStorage.getItem('refresh_token') || null;

// Состояние плеера
let currentTrack = null;
let audio = new Audio();
let isPlaying = false;
let isRadioMode = false;
let radioQueue = [];
let radioCurrentIndex = -1;
let radioLastId = null;
let currentRadioStation = null;

// Список лайков и индекс
let likesList = [];
let currentLikesIndex = -1;

// DOM элементы
const welcomePage = document.getElementById('welcomePage');
const mainApp = document.getElementById('mainApp');
const tracksGrid = document.getElementById('tracksGrid');
const radioGrid = document.getElementById('radioGrid');
const playerBar = document.getElementById('playerBar');
const playPauseBtn = document.getElementById('playPauseBtn');
const prevTrackBtn = document.getElementById('prevTrackBtn');
const nextTrackBtn = document.getElementById('nextTrackBtn');
const progressSlider = document.getElementById('progressSlider');
const currentTimeSpan = document.getElementById('currentTime');
const durationSpan = document.getElementById('duration');
const nowTrackTitle = document.getElementById('nowTrackTitle');
const nowTrackArtist = document.getElementById('nowTrackArtist');
const volumeSlider = document.getElementById('volumeSlider');
const trackCoverImg = document.getElementById('trackCover');
const homePage = document.getElementById('homePage');
const likesPage = document.getElementById('likesPage');
const radioPage = document.getElementById('radioPage');
const logoutBtn = document.getElementById('logoutMainBtn');

// Модалки
const loginModal = document.getElementById('loginModal');
const registerModal = document.getElementById('registerModal');

// ---- вспомогательные функции ----
function showModal(modal) { modal.style.display = 'flex'; }
function hideModals() { loginModal.style.display = 'none'; registerModal.style.display = 'none'; }

function logout() {
    console.log('[DEBUG] Выход из системы');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    accessToken = null;
    refreshToken = null;
    isRadioMode = false;
    audio.pause();
    playerBar.style.display = 'none';
    mainApp.style.display = 'none';
    welcomePage.style.display = 'flex';
    welcomePage.classList.add('active-page');
    mainApp.classList.remove('active-page');
    // остальные страницы не нужно чистить, они скрыты
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active-page'));
    homePage.classList.remove('active-page');
    likesPage.classList.remove('active-page');
    radioPage.classList.remove('active-page');
    welcomePage.style.display = 'flex';
    likesList = [];
    currentLikesIndex = -1;
    radioQueue = [];
    radioCurrentIndex = -1;
}

function getFullCoverUrl(uri) {
    if (!uri) return '';
    if (uri.startsWith('http')) return uri;
    return `${API_BASE}${uri}`;
}

// ---- API вызовы ----
async function registerUser(username, password) {
    const resp = await fetch(`${API_BASE}/user/register`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    return resp;
}

async function loginUser(login, password) {
    const resp = await fetch(`${API_BASE}/user/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Login: login, Password: password })
    });
    return resp;
}

async function fetchLikesPlaylist() {
    if (!accessToken) return [];
    try {
        const resp = await fetch(`${API_BASE}/track/playlist/likes/all`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (resp.ok) {
            const data = await resp.json();
            return data?.Tracks || [];
        }
        const resp2 = await fetch(`${API_BASE}/track/playlist/likes/${accessToken}/all`);
        if (resp2.ok) {
            const data = await resp2.json();
            return data?.Tracks || [];
        }
        console.warn('[API] Не удалось загрузить лайки');
        return [];
    } catch(e) {
        console.error('[API] Ошибка загрузки лайков:', e);
        return [];
    }
}

async function fetchRadioStations() {
    try {
        const resp = await fetch(`${API_BASE}/track/radio/`);
        if (resp.ok) return await resp.json();
        return [];
    } catch(e) {
        console.error('[API] Ошибка загрузки радиостанций:', e);
        return [];
    }
}

async function fetchRadioTracks(stationTag, lastId = null) {
    const body = { Station: stationTag, LastIdTrack: lastId };
    try {
        const resp = await fetch(`${API_BASE}/track/radio/`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (resp.ok) return await resp.json();
        return { Tracks: [], LastIdTrack: null };
    } catch(e) {
        console.error('[API] Ошибка загрузки треков радио:', e);
        return { Tracks: [], LastIdTrack: null };
    }
}

function getStreamUrl(serverId) {
    return `${API_BASE}/track/listen/${serverId}`;
}

function extractArtistName(trackObj) {
    let artists = trackObj.Artists;
    if (!artists) return 'Unknown Artist';
    if (typeof artists === 'number') return `Artist ${artists}`;
    if (typeof artists === 'object' && artists.Name) return artists.Name;
    if (Array.isArray(artists) && artists.length) {
        let first = artists[0];
        if (typeof first === 'object' && first.Name) return first.Name;
        if (typeof first === 'number') return `Artist ${first}`;
    }
    return 'Unknown Artist';
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : (m === '<' ? '&lt;' : '&gt;'));
}

// ---- рендеры (лайки, радио) ----
async function renderLikes() {
    if (!accessToken) return;
    tracksGrid.innerHTML = '<div>Загрузка...</div>';
    const tracks = await fetchLikesPlaylist();
    if (!tracks.length) {
        tracksGrid.innerHTML = '<div>Нет понравившихся треков</div>';
        likesList = [];
        currentLikesIndex = -1;
        return;
    }
    likesList = tracks.map(t => ({
        id: t.Id,
        title: t.Name,
        artist: extractArtistName(t),
        serverId: t.Id,
        url: null,
        coverUri: getFullCoverUrl(t.URI || '')
    }));
    tracksGrid.innerHTML = '';
    likesList.forEach((track, idx) => {
        const card = document.createElement('div');
        card.className = 'track-card';
        const coverHtml = track.coverUri
            ? `<img class="track-cover-img" src="${escapeHtml(track.coverUri)}" alt="cover">`
            : `<div class="cover-icon">🎵</div>`;
        card.innerHTML = `
            ${coverHtml}
            <div class="title">${escapeHtml(track.title)}</div>
            <div class="artist">${escapeHtml(track.artist)}</div>
            <button class="play-btn" data-index="${idx}">▶ Воспроизвести</button>
        `;
        tracksGrid.appendChild(card);
    });
    document.querySelectorAll('#tracksGrid .play-btn').forEach(btn => {
        btn.onclick = () => {
            const idx = parseInt(btn.getAttribute('data-index'));
            if (idx >= 0 && idx < likesList.length) {
                currentLikesIndex = idx;
                const track = likesList[idx];
                if (!track.url) track.url = getStreamUrl(track.serverId);
                isRadioMode = false;
                playTrack(track);
            }
        };
    });
}

async function renderRadioStations() {
    radioGrid.innerHTML = '<div>Загрузка...</div>';
    const stations = await fetchRadioStations();
    if (!stations.length) {
        radioGrid.innerHTML = '<div>Нет доступных станций</div>';
        return;
    }
    radioGrid.innerHTML = '';
    stations.forEach(station => {
        const card = document.createElement('div');
        card.className = 'station-card';
        card.innerHTML = `
            <div class="cover-icon">📻</div>
            <div class="title">${escapeHtml(station)}</div>
            <div class="artist">Радиостанция</div>
            <button class="play-btn radio-start" data-station="${station}">▶ Слушать</button>
        `;
        radioGrid.appendChild(card);
    });
    document.querySelectorAll('.radio-start').forEach(btn => {
        btn.onclick = () => startRadioStation(btn.getAttribute('data-station'));
    });
}

// ---- радио логика ----
async function startRadioStation(stationName) {
    isRadioMode = true;
    currentRadioStation = stationName;
    radioQueue = [];
    radioCurrentIndex = -1;
    radioLastId = null;
    await loadMoreRadioTracks();
}

async function loadMoreRadioTracks() {
    if (!currentRadioStation) return;
    const data = await fetchRadioTracks(`genre:${currentRadioStation}`, radioLastId);
    if (data.Tracks && data.Tracks.length) {
        const newTracks = data.Tracks.map(t => ({
            title: t.Name,
            artist: extractArtistName(t),
            url: getStreamUrl(t.Id),
            serverId: t.Id,
            coverUri: getFullCoverUrl(t.URI || '')
        }));
        radioQueue.push(...newTracks);
        radioLastId = data.LastIdTrack;
        if (radioCurrentIndex === -1 && radioQueue.length) {
            radioCurrentIndex = 0;
            playTrack(radioQueue[0]);
        }
    }
}

async function downloadPC(){
    const resp = await fetch(`${API_BASE}/../../download/PC`, {
            method: 'GET', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
}

// ---- общий плеер ----
function playTrack(track) {
    if (!track || !track.url) return;
    currentTrack = track;
    audio.src = track.url;
    audio.load();
    audio.play().catch(e => console.log(e));
    isPlaying = true;
    playPauseBtn.innerText = '⏸️';
    nowTrackTitle.innerText = track.title;
    nowTrackArtist.innerText = track.artist || 'Космический исполнитель';
    if (track.coverUri) {
        trackCoverImg.src = track.coverUri;
        trackCoverImg.style.display = 'block';
    } else {
        trackCoverImg.src = '';
        trackCoverImg.style.display = 'none';
    }
    playerBar.style.display = 'flex';
}

audio.addEventListener('loadedmetadata', () => {
    durationSpan.innerText = formatTime(audio.duration);
    progressSlider.max = 100;
});

audio.addEventListener('timeupdate', () => {
    if (audio.duration) {
        const percent = (audio.currentTime / audio.duration) * 100;
        progressSlider.value = percent;
        currentTimeSpan.innerText = formatTime(audio.currentTime);
    }
});

audio.addEventListener('ended', () => {
    if (isRadioMode) {
        nextTrack();
    } else {
        if (likesList.length > 0 && currentLikesIndex < likesList.length - 1) {
            nextTrackBtn.onclick();
        } else {
            audio.pause();
            isPlaying = false;
            playPauseBtn.innerText = '▶️';
        }
    }
});

playPauseBtn.onclick = () => {
    if (!currentTrack) return;
    if (audio.paused) { audio.play(); playPauseBtn.innerText = '⏸️'; }
    else { audio.pause(); playPauseBtn.innerText = '▶️'; }
};

progressSlider.addEventListener('input', (e) => {
    if (audio.duration) audio.currentTime = (e.target.value / 100) * audio.duration;
});

volumeSlider.oninput = (e) => audio.volume = e.target.value / 100;

function nextTrack() {
    if (isRadioMode) {
        if (radioCurrentIndex + 1 < radioQueue.length) {
            radioCurrentIndex++;
            playTrack(radioQueue[radioCurrentIndex]);
        } else {
            loadMoreRadioTracks().then(() => {
                if (radioCurrentIndex + 1 < radioQueue.length) {
                    radioCurrentIndex++;
                    playTrack(radioQueue[radioCurrentIndex]);
                } else {
                    isRadioMode = false;
                    playerBar.style.display = 'none';
                }
            });
        }
    } else {
        if (likesList.length > 0 && currentLikesIndex < likesList.length - 1) {
            currentLikesIndex++;
            const track = likesList[currentLikesIndex];
            if (!track.url) track.url = getStreamUrl(track.serverId);
            playTrack(track);
        }
    }
}

function prevTrack() {
    if (isRadioMode) {
        if (radioCurrentIndex > 0) {
            radioCurrentIndex--;
            playTrack(radioQueue[radioCurrentIndex]);
        }
    } else {
        if (likesList.length > 0 && currentLikesIndex > 0) {
            currentLikesIndex--;
            const track = likesList[currentLikesIndex];
            if (!track.url) track.url = getStreamUrl(track.serverId);
            playTrack(track);
        } else if (audio.currentTime > 5) {
            audio.currentTime = 0;
        }
    }
}

prevTrackBtn.onclick = prevTrack;
nextTrackBtn.onclick = nextTrack;

function formatTime(sec) {
    if (isNaN(sec)) return '0:00';
    let mins = Math.floor(sec / 60);
    let remainSec = Math.floor(sec % 60);
    return `${mins}:${remainSec < 10 ? '0' + remainSec : remainSec}`;
}

// ---- навигация между страницами (home, likes, radio) ----
function switchToPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active-page'));
    if (pageId === 'home') {
        homePage.classList.add('active-page');
        // не нужно ничего загружать, статические новости
    } else if (pageId === 'likes') {
        likesPage.classList.add('active-page');
        renderLikes();
    } else if (pageId === 'radio') {
        radioPage.classList.add('active-page');
        renderRadioStations();
    }
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-link[data-page="${pageId}"]`);
    if (activeNav) activeNav.classList.add('active');
}

document.querySelectorAll('.nav-link[data-page]').forEach(link => {
    link.onclick = () => switchToPage(link.getAttribute('data-page'));
});

// ---- авторизация ----
document.getElementById('submitLoginBtn').onclick = async () => {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    const msgDiv = document.getElementById('loginMessage');
    if (!username || !password) { msgDiv.innerText = 'Заполните поля'; return; }
    try {
        const resp = await loginUser(username, password);
        const data = await resp.json();
        if (resp.ok && data.AccessToken && data.RefreshToken) {
            accessToken = data.AccessToken;
            refreshToken = data.RefreshToken;
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('refresh_token', refreshToken);
            hideModals();
            welcomePage.style.display = 'none';
            mainApp.style.display = 'block';
            // После входа показываем главную страницу
            switchToPage('home');
            msgDiv.innerText = '';
        } else {
            msgDiv.innerText = data.detail || 'Ошибка входа';
        }
    } catch (e) {
        msgDiv.innerText = 'Сервер недоступен';
    }
};

document.getElementById('submitRegisterBtn').onclick = async () => {
    const username = document.getElementById('regUsername').value.trim();
    const password = document.getElementById('regPassword').value.trim();
    const msgDiv = document.getElementById('regMessage');
    if (!username || !password) { msgDiv.innerText = 'Заполните поля'; return; }
    try {
        const resp = await registerUser(username, password);
        if (resp.ok) {
            msgDiv.innerText = '✅ Успех! Теперь войдите.';
            setTimeout(() => hideModals(), 1500);
            document.getElementById('regUsername').value = '';
            document.getElementById('regPassword').value = '';
        } else {
            const data = await resp.json();
            msgDiv.innerText = data.detail || 'Ошибка регистрации';
        }
    } catch (e) { msgDiv.innerText = 'Ошибка сети'; }
};

document.getElementById('welcomeLoginBtn').onclick = () => showModal(loginModal);
document.getElementById('welcomeRegisterBtn').onclick = () => showModal(registerModal);
logoutBtn.onclick = logout;
window.onclick = e => { if (e.target === loginModal || e.target === registerModal) hideModals(); };

// ---- обработка скачивания ПК-версии ----
// ---- обработка скачивания ПК-версии (простой способ) ----
document.getElementById('downloadPcBtn').addEventListener('click', (e) => {
    e.preventDefault();
    // Перенаправление на URL файла – браузер сам начнёт скачивание
    window.location.href = `${API_BASE}/../../download/PC`;
});

// ---- инициализация ----
if (accessToken) {
    welcomePage.style.display = 'none';
    mainApp.style.display = 'block';
    switchToPage('home');   // по умолчанию открываем главную
} else {
    mainApp.style.display = 'none';
    welcomePage.style.display = 'flex';
    welcomePage.classList.add('active-page');
}

// звёзды
function generateStars() {
    const container = document.getElementById('starsContainer');
    for (let i = 0; i < 200; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        const size = Math.random() * 3 + 1;
        star.style.width = size + 'px';
        star.style.height = size + 'px';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDuration = (Math.random() * 2 + 1) + 's';
        star.style.animationDelay = (Math.random() * 5) + 's';
        container.appendChild(star);
    }
}
generateStars();