// ==========================================================================
// Avito Radar Pro — Telegram Mini App (TMA) Client Logic
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Telegram WebApp SDK if running inside Telegram
  if (window.Telegram && window.Telegram.WebApp) {
    try {
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand();
      if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
      if (tg.setHeaderColor) tg.setHeaderColor('#000000');
      if (tg.setBackgroundColor) tg.setBackgroundColor('#000000');
    } catch (e) {
      console.warn('Telegram WebApp init notice:', e);
    }
  }

  // State
  let currentTab = 'ads';
  const tabTitles = {
    ads: 'Объявления',
    deals: 'Сделки',
    favorites: 'Избранное',
    calculator: 'Калькулятор маржи',
    tasks: 'Задачи',
    items: 'Каталог',
    logs: 'Консоль',
    settings: 'Настройки'
  };

  let isWorkerRunning = false;
  let allAds = [];
  let allDeals = [];
  let allFavorites = [];
  let allBlacklist = [];
  let allTasks = [];
  let allItemsStore = {};

  // Navigation Bar Elements
  const pageTitle = document.getElementById('pageTitle');
  const botStatusSub = document.getElementById('botStatusSub');
  const btnToggleWorker = document.getElementById('btnToggleWorker');
  const workerIconSvg = document.getElementById('workerIconSvg');
  const searchSubHeader = document.getElementById('searchSubHeader');
  const btnRunOnce = document.getElementById('btnRunOnce');
  const btnHeaderFavs = document.getElementById('btnHeaderFavs');
  const headerFavBadge = document.getElementById('headerFavBadge');

  // Tab Navigation Elements
  const tabItems = document.querySelectorAll('.tg-tab-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const subViewPills = document.querySelectorAll('.sub-view-pill');
  const tabbarIndicator = document.getElementById('tabbarIndicator');
  const segmentedIndicator = document.getElementById('segmentedIndicator');
  const segmentedSubHeader = document.getElementById('segmentedSubHeader');
  const adsCountBadge = document.getElementById('adsCountBadge');
  const dealsCountBadge = document.getElementById('dealsCountBadge');
  const favCountBadge = document.getElementById('favCountBadge');
  const tasksCountBadge = document.getElementById('tasksCountBadge');

  function triggerHaptic(type = 'selection') {
    try {
      if (window.Telegram?.WebApp?.HapticFeedback) {
        if (type === 'selection') window.Telegram.WebApp.HapticFeedback.selectionChanged();
        else if (type === 'light') window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        else if (type === 'medium') window.Telegram.WebApp.HapticFeedback.impactOccurred('medium');
        else if (type === 'success') window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
      }
    } catch (e) {}
  }

  const tabOrder = ['ads', 'deals', 'calculator', 'tasks', 'settings'];
  const segOrder = ['ads', 'deals', 'favorites', 'tasks'];

  function switchTab(targetTab) {
    currentTab = targetTab;
    triggerHaptic('selection');

    // Update active tab buttons in bottom bar & animated indicator
    const tabIdx = tabOrder.indexOf(targetTab);
    tabItems.forEach(item => {
      if (item.dataset.tab === targetTab) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    if (tabbarIndicator) {
      if (tabIdx !== -1) {
        tabbarIndicator.style.opacity = '1';
        tabbarIndicator.style.transform = `translateX(${tabIdx * 100}%)`;
      } else {
        tabbarIndicator.style.opacity = '0';
      }
    }

    // Update sub-view pills in segmented header & animated indicator
    const segIdx = segOrder.indexOf(targetTab);
    subViewPills.forEach(pill => {
      if (pill.dataset.subview === targetTab) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });

    if (segmentedIndicator && segIdx !== -1) {
      segmentedIndicator.style.transform = `translateX(${segIdx * 100}%)`;
    }

    // Toggle segmented subheader visibility
    if (segmentedSubHeader) {
      if (segIdx !== -1) {
        segmentedSubHeader.style.display = 'block';
      } else {
        segmentedSubHeader.style.display = 'none';
      }
    }

    // Update active tab pane
    tabPanes.forEach(pane => {
      if (pane.id === `pane-${targetTab}`) {
        pane.classList.add('active');
      } else {
        pane.classList.remove('active');
      }
    });

    // Update page title
    if (pageTitle) {
      pageTitle.textContent = tabTitles[targetTab] || 'Объявления';
    }

    // Toggle search bar depending on tab
    if (searchSubHeader) {
      if (targetTab === 'ads' || targetTab === 'deals' || targetTab === 'favorites') {
        searchSubHeader.style.display = 'flex';
      } else {
        searchSubHeader.style.display = 'none';
      }
    }

    // Refresh specific tab contents
    if (targetTab === 'ads') loadAds();
    if (targetTab === 'deals') loadDeals();
    if (targetTab === 'favorites') loadFavorites();
    if (targetTab === 'tasks') loadTasks();
    if (targetTab === 'items') loadItems();
    if (targetTab === 'logs') loadLogs();
    if (targetTab === 'settings') loadSettings();
  }

  tabItems.forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.tab;
      if (target) switchTab(target);
    });
  });

  subViewPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const target = pill.dataset.subview;
      if (target) switchTab(target);
    });
  });

  if (btnHeaderFavs) {
    btnHeaderFavs.addEventListener('click', () => switchTab('favorites'));
  }

  // Containers
  const adsContainer = document.getElementById('adsContainer');
  const adsFilterBar = document.getElementById('adsFilterBar');
  const btnClearAds = document.getElementById('btnClearAds');
  const adsCountHeader = document.getElementById('adsCountHeader');

  const dealsContainer = document.getElementById('dealsContainer');
  const favoritesContainer = document.getElementById('favoritesContainer');
  const tasksContainer = document.getElementById('tasksContainer');
  const itemsListContainer = document.getElementById('itemsListContainer');
  const itemsTaskFilter = document.getElementById('itemsTaskFilter');
  const logsTerminalContent = document.getElementById('logsTerminalContent');
  const blacklistContainer = document.getElementById('blacklistContainer');

  // Search & Actions
  const dealSearchInput = document.getElementById('dealSearchInput');
  const btnClearDeals = document.getElementById('btnClearDeals');
  const btnRefreshLogs = document.getElementById('btnRefreshLogs');

  // Modal (Add Task)
  const taskModal = document.getElementById('taskModal');
  const btnOpenAddTaskModal = document.getElementById('btnOpenAddTaskModal');
  const btnCloseTaskModal = document.getElementById('btnCloseTaskModal');
  const taskForm = document.getElementById('taskForm');
  const taskId = document.getElementById('taskId');
  const taskModel = document.getElementById('taskModel');
  const taskCity = document.getElementById('taskCity');
  const taskMinPrice = document.getElementById('taskMinPrice');
  const taskMaxPrice = document.getElementById('taskMaxPrice');
  const taskThreadId = document.getElementById('taskThreadId');
  const presetPills = document.querySelectorAll('.preset-pill');

  // Settings Elements
  const settingBotToken = document.getElementById('settingBotToken');
  const settingChatId = document.getElementById('settingChatId');
  const settingThreadId = document.getElementById('settingThreadId');
  const switchSendPhotos = document.getElementById('switchSendPhotos');
  const switchFilterDefects = document.getElementById('switchFilterDefects');
  const proxiesTextarea = document.getElementById('proxiesTextarea');
  const btnSaveProxies = document.getElementById('btnSaveProxies');
  const btnSaveSettings = document.getElementById('btnSaveSettings');
  const btnTestTelegram = document.getElementById('btnTestTelegram');
  const profileStatusText = document.getElementById('profileStatusText');

  // Calculator Elements
  const calcBuyPrice = document.getElementById('calcBuyPrice');
  const calcExpenses = document.getElementById('calcExpenses');
  const calcSellPrice = document.getElementById('calcSellPrice');
  const calcNetProfit = document.getElementById('calcNetProfit');
  const calcMarginPct = document.getElementById('calcMarginPct');
  const calcRoiPct = document.getElementById('calcRoiPct');
  const calcTotalCost = document.getElementById('calcTotalCost');
  const calcExpBtns = document.querySelectorAll('.calc-exp-btn');

  // Money Formatter
  function formatMoney(num) {
    if (!num) return '0 ₽';
    return Number(num).toLocaleString('ru-RU') + ' ₽';
  }

  // Toast Notification
  function showToast(message) {
    const toast = document.getElementById('iosToast');
    const msg = document.getElementById('toastMsg');
    if (!toast || !msg) return;
    msg.textContent = message;
    toast.style.display = 'inline-flex';
    setTimeout(() => {
      toast.style.display = 'none';
    }, 2400);
  }

  // ==========================================================================
  // Worker Status
  // ==========================================================================
  async function loadStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      isWorkerRunning = data.running;

      if (data.running) {
        if (botStatusSub) {
          botStatusSub.className = 'navbar-sub online';
          botStatusSub.textContent = `бот • в сети (${data.uptime || 'активен'})`;
        }
        if (btnToggleWorker) {
          btnToggleWorker.classList.add('active-running');
          btnToggleWorker.title = 'Остановить сканирование';
        }
        if (workerIconSvg) {
          workerIconSvg.innerHTML = '<rect x="6" y="6" width="12" height="12"/>';
        }
        if (profileStatusText) {
          profileStatusText.innerHTML = '<span class="status-pulse-dot"></span> бот активен • в сети';
        }
      } else {
        if (botStatusSub) {
          botStatusSub.className = 'navbar-sub';
          botStatusSub.textContent = 'бот • остановлен';
        }
        if (btnToggleWorker) {
          btnToggleWorker.classList.remove('active-running');
          btnToggleWorker.title = 'Запустить сканирование';
        }
        if (workerIconSvg) {
          workerIconSvg.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"/>';
        }
        if (profileStatusText) {
          profileStatusText.innerHTML = '<span class="status-pulse-dot" style="background:#8e8e93;box-shadow:none;"></span> бот остановлен';
        }
      }

      // Badges
      if (adsCountBadge) {
        const count = data.ads_count || data.items_count || 0;
        adsCountBadge.style.display = count > 0 ? 'inline-flex' : 'none';
        adsCountBadge.textContent = count;
      }
      if (adsCountHeader) {
        const count = data.ads_count || data.items_count || 0;
        adsCountHeader.textContent = `${count} шт.`;
      }
      if (dealsCountBadge) {
        const count = data.deals_count || 0;
        dealsCountBadge.style.display = count > 0 ? 'inline-flex' : 'none';
        dealsCountBadge.textContent = count;
      }
      if (favCountBadge) {
        const count = data.favorites_count || 0;
        favCountBadge.style.display = count > 0 ? 'inline-flex' : 'none';
        favCountBadge.textContent = count;
      }
      if (headerFavBadge) {
        const count = data.favorites_count || 0;
        headerFavBadge.textContent = count;
      }
      if (tasksCountBadge) {
        const count = data.tasks_count || 0;
        tasksCountBadge.style.display = count > 0 ? 'inline-flex' : 'none';
        tasksCountBadge.textContent = count;
      }
    } catch (e) {
      if (botStatusSub) {
        botStatusSub.className = 'navbar-sub';
        botStatusSub.textContent = 'офлайн';
      }
    }
  }

  // Master Toggle Worker
  if (btnToggleWorker) {
    btnToggleWorker.addEventListener('click', async () => {
      const endpoint = isWorkerRunning ? '/api/worker/stop' : '/api/worker/start';
      try {
        const res = await fetch(endpoint, { method: 'POST' });
        const data = await res.json();
        showToast(data.message || 'Статус обновлен');
        await loadStatus();
        loadLogs();
      } catch (err) {
        showToast('Ошибка переключения');
      }
    });
  }

  // Quick Scan (Run Once)
  if (btnRunOnce) {
    btnRunOnce.addEventListener('click', async () => {
      showToast('Запуск сканирования...');
      try {
        await fetch('/api/worker/run-once', { method: 'POST' });
        setTimeout(() => {
          loadAds();
          loadDeals();
          loadFavorites();
          loadItems();
          loadLogs();
          loadStatus();
          showToast('Поиск завершен!');
        }, 3200);
      } catch (err) {
        showToast('Ошибка запроса');
      }
    });
  }

  // ==========================================================================
  // Ads Feed (Все новые объявления с Авито)
  // ==========================================================================
  async function loadAds() {
    try {
      const res = await fetch('/api/ads');
      allAds = await res.json();
      renderAds();
      if (adsCountHeader) adsCountHeader.textContent = `${allAds.length} шт.`;
      if (adsCountBadge) {
        adsCountBadge.textContent = allAds.length;
        adsCountBadge.style.display = allAds.length > 0 ? 'inline-flex' : 'none';
      }
    } catch (e) {
      console.error('Failed to load ads:', e);
    }
  }

  let activeAdFilter = 'all';
  const adsFilterChips = document.querySelectorAll('#adsFilterBar .ios-chip');
  adsFilterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      triggerHaptic('light');
      adsFilterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeAdFilter = chip.dataset.filter || 'all';
      renderAds();
    });
  });

  if (btnClearAds) {
    btnClearAds.addEventListener('click', async () => {
      if (!confirm('Очистить ленту объявлений?')) return;
      await fetch('/api/ads/clear', { method: 'POST' });
      showToast('Лента объявлений очищена');
      loadAds();
      loadStatus();
    });
  }

  function renderAds() {
    if (!adsContainer) return;
    const q = (dealSearchInput ? dealSearchInput.value : '').toLowerCase().trim();
    let filtered = allAds.filter(a =>
      `${a.title || ''} ${a.city || ''} ${a.task_name || ''} ${a.memory || ''}`.toLowerCase().includes(q)
    );

    if (activeAdFilter === 'profit') {
      filtered = filtered.filter(a => (a.profit || 0) > 0);
    } else if (activeAdFilter === 'ip13') {
      filtered = filtered.filter(a => (a.title || '').includes('13'));
    } else if (activeAdFilter === 'ip14') {
      filtered = filtered.filter(a => (a.title || '').includes('14'));
    } else if (activeAdFilter === 'ip12') {
      filtered = filtered.filter(a => (a.title || '').includes('12'));
    } else if (activeAdFilter === 'ip11') {
      filtered = filtered.filter(a => (a.title || '').includes('11'));
    }

    if (filtered.length === 0) {
      adsContainer.innerHTML = `
        <div class="tg-empty-feed">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
            <line x1="12" y1="18" x2="12.01" y2="18"/>
          </svg>
          <h4>Нет объявлений по выбранному фильтру</h4>
          <p>Нажмите кнопку «Скан» вверху, чтобы обновить ленту с Авито.</p>
        </div>
      `;
      return;
    }

    adsContainer.innerHTML = filtered.map(a => {
      const pct = a.avg_price > 0 && a.profit > 0 ? Math.round(((a.profit) / a.avg_price) * 100) : 0;
      const isFav = allFavorites.some(f => String(f.id) === String(a.id));
      const defaultPlaceholder = "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&auto=format&fit=crop";
      const photoSrc = a.image || defaultPlaceholder;

      return `
        <article class="tg-deal-bubble">
          <!-- Offer Photo Header -->
          <div class="bubble-photo-wrap">
            <img src="${photoSrc}" class="bubble-photo-img" loading="lazy" alt="${a.title}" onerror="this.src='${defaultPlaceholder}'">
            <div class="bubble-photo-badges">
              <span class="ios-badge-city">${a.city || 'Авито'}</span>
              ${pct > 0 ? `<span class="ios-badge-discount">-${pct}%</span>` : `<span class="ios-badge-city" style="background:rgba(10,132,255,0.75);">⚡ Новое</span>`}
            </div>
          </div>

          <!-- Offer Body (Info & Price) -->
          <div class="bubble-body">
            <div class="bubble-title">${a.title}</div>
            <div class="bubble-subtitle">
              <span>📍 ${a.city || 'Город'}</span>
              ${a.memory ? `<span>• 💾 ${a.memory}</span>` : ''}
              ${a.avg_price > 0 ? `<span>• ~${formatMoney(a.avg_price)} рынок</span>` : ''}
            </div>

            <!-- Price Row -->
            <div class="bubble-price-row">
              <div class="price-main">${formatMoney(a.price)}</div>
              ${a.profit > 0 ? `
                <div class="profit-chip">
                  <span>выгода</span>
                  <strong>+${formatMoney(a.profit)}</strong>
                </div>
              ` : ''}
            </div>

            <!-- Apple iOS Action Bar -->
            <div class="bubble-action-bar">
              <a href="${a.url}" target="_blank" rel="noopener noreferrer" class="ios-btn primary" style="flex:1.8;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                <span>На Авито</span>
              </a>
              <button type="button" class="ios-btn tinted fav-ad-btn ${isFav ? 'is-fav' : ''}" data-id="${a.id}" style="flex:1.4;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                <span>${isFav ? 'В избранном' : 'В избранное'}</span>
              </button>
              <button type="button" class="ios-btn success calc-ad-btn" data-buy="${a.price}" data-sell="${a.avg_price || a.price}" style="flex:1.1;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/></svg>
                <span>Маржа</span>
              </button>
              <button type="button" class="ios-btn destructive icon-only delete-ad-btn" data-id="${a.id}" title="Скрыть объявление">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>
        </article>
      `;
    }).join('');

    // Attach listeners
    adsContainer.querySelectorAll('.delete-ad-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        await fetch('/api/ads/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        showToast('Объявление скрыто');
        loadAds();
        loadStatus();
      });
    });

    adsContainer.querySelectorAll('.fav-ad-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        const ad = allAds.find(a => String(a.id) === String(id));
        if (ad) {
          await fetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ad)
          });
          showToast('⭐ Сохранено в Избранное');
          loadFavorites();
          loadStatus();
        }
      });
    });

    adsContainer.querySelectorAll('.calc-ad-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const buy = parseInt(e.currentTarget.dataset.buy) || 0;
        const sell = parseInt(e.currentTarget.dataset.sell) || buy;
        if (calcBuyPrice) calcBuyPrice.value = buy;
        if (calcSellPrice) calcSellPrice.value = sell;
        if (calcExpenses) calcExpenses.value = 0;
        updateCalculator();
        switchTab('calculator');
      });
    });
  }

  // ==========================================================================
  // Deals Feed
  // ==========================================================================
  async function loadDeals() {
    try {
      const res = await fetch('/api/deals');
      allDeals = await res.json();
      renderDeals();
    } catch (e) {
      console.error('Failed to load deals:', e);
    }
  }

  let activeDealFilter = 'all';
  const dealsFilterChips = document.querySelectorAll('#dealsFilterBar .ios-chip');
  dealsFilterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      triggerHaptic('light');
      dealsFilterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeDealFilter = chip.dataset.filter || 'all';
      renderDeals();
    });
  });

  function renderDeals() {
    if (!dealsContainer) return;
    const q = (dealSearchInput ? dealSearchInput.value : '').toLowerCase().trim();
    let filtered = allDeals.filter(d =>
      `${d.title || ''} ${d.city || ''} ${d.task_name || ''} ${d.memory || ''}`.toLowerCase().includes(q)
    );

    if (activeDealFilter === 'profit10k') {
      filtered = filtered.filter(d => (d.profit || 0) >= 10000);
    } else if (activeDealFilter === 'ip13') {
      filtered = filtered.filter(d => (d.title || '').includes('13'));
    } else if (activeDealFilter === 'ip14') {
      filtered = filtered.filter(d => (d.title || '').includes('14'));
    } else if (activeDealFilter === 'ip15') {
      filtered = filtered.filter(d => (d.title || '').includes('15'));
    }

    if (filtered.length === 0) {
      dealsContainer.innerHTML = `
        <div class="tg-empty-feed">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <h4>Пока нет предложений по фильтру</h4>
          <p>Попробуйте выбрать «Все модели» или нажмите «Скан» вверху.</p>
        </div>
      `;
      return;
    }

    dealsContainer.innerHTML = filtered.map(d => {
      const pct = d.avg_price > 0 ? Math.round(((d.avg_price - d.price) / d.avg_price) * 100) : 0;
      const isFav = allFavoritesStore.some(f => String(f.id) === String(d.id));
      const defaultPlaceholder = "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&auto=format&fit=crop";
      const photoSrc = d.image || defaultPlaceholder;

      return `
        <article class="tg-deal-bubble">
          <!-- Offer Photo Header -->
          <div class="bubble-photo-wrap">
            <img src="${photoSrc}" class="bubble-photo-img" loading="lazy" alt="${d.title}" onerror="this.src='${defaultPlaceholder}'">
            <div class="bubble-photo-badges">
              <span class="ios-badge-city">${d.city || 'Авито'}</span>
              ${pct > 0 ? `<span class="ios-badge-discount">-${pct}%</span>` : ''}
            </div>
          </div>

          <!-- Offer Body (Info & Price) -->
          <div class="bubble-body">
            <div class="bubble-title">${d.title}</div>
            <div class="bubble-subtitle">
              <span>📍 ${d.city || 'Город'}</span>
              ${d.memory ? `<span>• 💾 ${d.memory}</span>` : ''}
              ${d.avg_price > 0 ? `<span>• ~${formatMoney(d.avg_price)} рынок</span>` : ''}
            </div>

            <!-- Price Row -->
            <div class="bubble-price-row">
              <div class="price-main">${formatMoney(d.price)}</div>
              ${d.profit > 0 ? `
                <div class="profit-chip">
                  <span>выгода</span>
                  <strong>+${formatMoney(d.profit)}</strong>
                </div>
              ` : ''}
            </div>

            <!-- Apple iOS Action Bar -->
            <div class="bubble-action-bar">
              <a href="${d.url}" target="_blank" rel="noopener noreferrer" class="ios-btn primary" style="flex:1.8;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                <span>На Авито</span>
              </a>
              <button type="button" class="ios-btn tinted fav-deal-btn ${isFav ? 'is-fav' : ''}" data-id="${d.id}" style="flex:1.4;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                <span>${isFav ? 'В избранном' : 'В избранное'}</span>
              </button>
              <button type="button" class="ios-btn success calc-deal-btn" data-buy="${d.price}" data-sell="${d.avg_price}" style="flex:1.1;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/></svg>
                <span>Маржа</span>
              </button>
              <button type="button" class="ios-btn destructive icon-only delete-deal-btn" data-id="${d.id}" title="Скрыть предложение">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>
        </article>
      `;
    }).join('');

    // Attach Action Listeners
    dealsContainer.querySelectorAll('.delete-deal-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        await fetch('/api/deals/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        showToast('Сделка скрыта');
        loadDeals();
        loadStatus();
      });
    });

    dealsContainer.querySelectorAll('.fav-deal-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        const deal = allDeals.find(d => String(d.id) === String(id));
        if (deal) {
          await fetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(deal)
          });
          showToast('⭐ Сохранено в Избранное');
          loadStatus();
        }
      });
    });

    dealsContainer.querySelectorAll('.calc-deal-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const buy = parseInt(e.currentTarget.dataset.buy) || 0;
        const sell = parseInt(e.currentTarget.dataset.sell) || buy;
        if (calcBuyPrice) calcBuyPrice.value = buy;
        if (calcSellPrice) calcSellPrice.value = sell;
        if (calcExpenses) calcExpenses.value = 0;
        updateCalculator();
        switchTab('calculator');
      });
    });

    dealsContainer.querySelectorAll('.bl-deal-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        const seller = e.currentTarget.dataset.seller;
        if (!confirm(`Добавить продавца "${seller || id}" в Чёрный список?`)) return;
        await fetch('/api/blacklist', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, name: seller, reason: 'Блокировка из ленты' })
        });
        await fetch('/api/deals/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        showToast('🚫 Продавец добавлен в ЧС');
        loadDeals();
        loadStatus();
      });
    });
  }

  if (dealSearchInput) {
    dealSearchInput.addEventListener('input', () => {
      if (currentTab === 'ads') renderAds();
      if (currentTab === 'deals') renderDeals();
      if (currentTab === 'favorites') renderFavorites();
    });
  }

  if (btnClearDeals) {
    btnClearDeals.addEventListener('click', async () => {
      if (!confirm('Очистить все сохраненные скидки?')) return;
      await fetch('/api/deals/clear', { method: 'POST' });
      showToast('Лента очищена');
      loadDeals();
      loadStatus();
    });
  }

  // ==========================================================================
  // Favorites Tab
  // ==========================================================================
  async function loadFavorites() {
    try {
      const res = await fetch('/api/favorites');
      allFavorites = await res.json();
      renderFavorites();
      const favHeader = document.getElementById('favCountHeader');
      if (favHeader) favHeader.textContent = `${allFavorites.length} шт.`;
    } catch (e) {
      console.error('Failed to load favorites:', e);
    }
  }

  function renderFavorites() {
    if (!favoritesContainer) return;
    const q = (dealSearchInput ? dealSearchInput.value : '').toLowerCase().trim();
    const filtered = allFavorites.filter(f =>
      `${f.title || ''} ${f.city || ''} ${f.note || ''}`.toLowerCase().includes(q)
    );

    if (filtered.length === 0) {
      favoritesContainer.innerHTML = `
        <div class="tg-empty-feed">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          <h4>В избранном пока пусто</h4>
          <p>Нажимайте кнопку «⭐ В избранное» на карточках в ленте или прямо в боте.</p>
        </div>
      `;
      return;
    }

    favoritesContainer.innerHTML = filtered.map(f => {
      const defaultPlaceholder = "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&auto=format&fit=crop";
      const photoSrc = f.image || defaultPlaceholder;

      return `
        <article class="tg-deal-bubble">
          <!-- Offer Photo Header -->
          <div class="bubble-photo-wrap" style="height: 140px;">
            <img src="${photoSrc}" class="bubble-photo-img" loading="lazy" alt="${f.title}" onerror="this.src='${defaultPlaceholder}'">
            <div class="bubble-photo-badges">
              <span class="ios-badge-city">${f.city || 'Авито'}</span>
              <select class="fav-status-select" data-id="${f.id}" style="pointer-events: auto;">
                <option value="saved" ${f.status === 'saved' ? 'selected' : ''}>📌 Сохранено</option>
                <option value="inspecting" ${f.status === 'inspecting' ? 'selected' : ''}>🔍 На проверке</option>
                <option value="bought" ${f.status === 'bought' ? 'selected' : ''}>✅ Куплен</option>
                <option value="resold" ${f.status === 'resold' ? 'selected' : ''}>💰 Перепродан</option>
              </select>
            </div>
          </div>

          <!-- Offer Body (Info & Price) -->
          <div class="bubble-body">
            <div class="bubble-title">${f.title}</div>
            <div class="bubble-subtitle">
              <span>📍 ${f.city || 'Город'}</span>
              ${f.avg_price > 0 ? `<span>• ~${formatMoney(f.avg_price)} рынок</span>` : ''}
            </div>

            <!-- Price Row -->
            <div class="bubble-price-row">
              <div class="price-main">${formatMoney(f.price)}</div>
              ${f.profit > 0 ? `
                <div class="profit-chip">
                  <span>выгода</span>
                  <strong>+${formatMoney(f.profit)}</strong>
                </div>
              ` : ''}
            </div>

            <!-- Note Box -->
            <div class="fav-note-box">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
              </svg>
              <input type="text" class="fav-note-input" data-id="${f.id}" placeholder="Заметка (договорился на время, торг...)" value="${f.note || ''}">
            </div>

            <!-- Apple iOS Actions -->
            <div class="bubble-action-bar">
              <a href="${f.url}" target="_blank" rel="noopener noreferrer" class="ios-btn primary" style="flex:2;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                <span>На Авито</span>
              </a>
              <button type="button" class="ios-btn success calc-deal-btn" data-buy="${f.price}" data-sell="${f.avg_price}" style="flex:1;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/></svg>
                <span>Маржа</span>
              </button>
              <button type="button" class="ios-btn destructive icon-only delete-fav-btn" data-id="${f.id}" title="Удалить из избранного">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        </article>
      `;
    }).join('');

    // Status change listener
    favoritesContainer.querySelectorAll('.fav-status-select').forEach(sel => {
      sel.addEventListener('change', async (e) => {
        const id = e.currentTarget.dataset.id;
        const status = e.currentTarget.value;
        await fetch('/api/favorites/status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, status })
        });
        showToast('Статус обновлен');
      });
    });

    // Note input change listener (auto-save on blur)
    favoritesContainer.querySelectorAll('.fav-note-input').forEach(inp => {
      inp.addEventListener('blur', async (e) => {
        const id = e.currentTarget.dataset.id;
        const note = e.currentTarget.value.trim();
        await fetch('/api/favorites/status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, note })
        });
      });
    });

    // Delete fav listener
    favoritesContainer.querySelectorAll('.delete-fav-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        await fetch('/api/favorites/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        showToast('Удалено из избранного');
        loadFavorites();
        loadStatus();
      });
    });

    favoritesContainer.querySelectorAll('.calc-deal-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const buy = parseInt(e.currentTarget.dataset.buy) || 0;
        const sell = parseInt(e.currentTarget.dataset.sell) || buy;
        if (calcBuyPrice) calcBuyPrice.value = buy;
        if (calcSellPrice) calcSellPrice.value = sell;
        if (calcExpenses) calcExpenses.value = 0;
        updateCalculator();
        switchTab('calculator');
      });
    });
  }

  // ==========================================================================
  // Resale Margin Calculator
  // ==========================================================================
  function updateCalculator() {
    if (!calcBuyPrice || !calcExpenses || !calcSellPrice) return;
    const buy = parseFloat(calcBuyPrice.value) || 0;
    const exp = parseFloat(calcExpenses.value) || 0;
    const sell = parseFloat(calcSellPrice.value) || 0;

    const totalCost = buy + exp;
    const netProfit = sell - totalCost;
    const marginPct = sell > 0 ? Math.round((netProfit / sell) * 100) : 0;
    const roiPct = totalCost > 0 ? Math.round((netProfit / totalCost) * 100) : 0;

    if (calcNetProfit) {
      calcNetProfit.textContent = (netProfit >= 0 ? '+' : '') + formatMoney(netProfit);
      calcNetProfit.style.color = netProfit >= 0 ? '#30d158' : '#ff453a';
    }
    if (calcMarginPct) calcMarginPct.textContent = `${marginPct}%`;
    if (calcRoiPct) calcRoiPct.textContent = `${roiPct}%`;
    if (calcTotalCost) calcTotalCost.textContent = formatMoney(totalCost);
  }

  if (calcBuyPrice) calcBuyPrice.addEventListener('input', updateCalculator);
  if (calcExpenses) calcExpenses.addEventListener('input', updateCalculator);
  if (calcSellPrice) calcSellPrice.addEventListener('input', updateCalculator);

  calcExpBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      triggerHaptic('light');
      if (btn.dataset.reset) {
        if (calcExpenses) calcExpenses.value = 0;
      } else {
        const add = parseInt(btn.dataset.add) || 0;
        const current = parseInt(calcExpenses.value) || 0;
        if (calcExpenses) calcExpenses.value = current + add;
      }
      updateCalculator();
    });
  });

  // Quick Stepper buttons for buy/sell prices (-1k / +1k)
  document.querySelectorAll('.step-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      triggerHaptic('light');
      const targetId = btn.dataset.target;
      const step = parseInt(btn.dataset.step) || 0;
      const el = document.getElementById(targetId);
      if (el) {
        const val = parseInt(el.value) || 0;
        el.value = Math.max(0, val + step);
        updateCalculator();
      }
    });
  });

  // Save custom calculation directly to Favorites
  const btnSaveCalcToFav = document.getElementById('btnSaveCalcToFav');
  if (btnSaveCalcToFav) {
    btnSaveCalcToFav.addEventListener('click', async () => {
      triggerHaptic('success');
      const buy = parseInt(calcBuyPrice.value) || 0;
      const exp = parseInt(calcExpenses.value) || 0;
      const sell = parseInt(calcSellPrice.value) || 0;
      const profit = sell - (buy + exp);
      const payload = {
        id: Date.now(),
        title: `iPhone (Расчёт: ${formatMoney(buy)} ➔ ${formatMoney(sell)})`,
        price: buy,
        avg_price: sell,
        profit: profit,
        url: 'https://www.avito.ru',
        status: 'inspecting',
        note: `Расходы на ремонт: ${formatMoney(exp)}. Чистая маржа: ${formatMoney(profit)}`
      };
      await fetch('/api/favorites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      showToast('⭐ Расчёт сохранён в Избранное');
      loadFavorites();
      loadStatus();
    });
  }

  // Initial calculation
  updateCalculator();

  // ==========================================================================
  // Tasks (Telegram Inset Group)
  // ==========================================================================
  async function loadTasks() {
    try {
      const res = await fetch('/api/tasks');
      allTasks = await res.json();
      renderTasks();
      updateItemsFilterOptions();
    } catch (e) {
      console.error('Failed to load tasks:', e);
    }
  }

  function renderTasks() {
    if (!tasksContainer) return;
    if (allTasks.length === 0) {
      tasksContainer.innerHTML = `
        <div class="tg-cell">
          <div class="cell-content">
            <span class="cell-sub">Активных задач нет. Добавьте модель для мониторинга.</span>
          </div>
        </div>
      `;
      return;
    }

    tasksContainer.innerHTML = allTasks.map((t, idx) => {
      const isLast = idx === allTasks.length - 1;
      return `
        <div class="tg-cell">
          <div class="cell-icon-box bg-slate">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <circle cx="12" cy="12" r="6"/>
              <circle cx="12" cy="12" r="2"/>
            </svg>
          </div>
          <div class="cell-content">
            <span class="cell-title">${t.model}</span>
            <span class="cell-sub">${t.city} • ${formatMoney(t.min_price)} – ${formatMoney(t.max_price)} ${t.thread_id ? `• Topic #${t.thread_id}` : ''}</span>
          </div>
          <button class="cell-del-btn delete-task-btn" data-id="${t.id}" title="Удалить задачу">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
        ${!isLast ? '<div class="tg-cell-divider"></div>' : ''}
      `;
    }).join('');

    // Attach delete listeners
    tasksContainer.querySelectorAll('.delete-task-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        if (!confirm('Удалить эту поисковую задачу?')) return;
        await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
        showToast('Задача удалена');
        loadTasks();
        loadStatus();
      });
    });
  }

  // Modal Open/Close
  if (btnOpenAddTaskModal) {
    btnOpenAddTaskModal.addEventListener('click', () => {
      if (taskId) taskId.value = '';
      if (taskForm) taskForm.reset();
      if (taskModal) taskModal.classList.add('open');
    });
  }

  if (btnCloseTaskModal) {
    btnCloseTaskModal.addEventListener('click', () => {
      if (taskModal) taskModal.classList.remove('open');
    });
  }

  // Quick Presets
  presetPills.forEach(pill => {
    pill.addEventListener('click', () => {
      if (taskModel) taskModel.value = pill.dataset.model || '';
      if (taskMinPrice) taskMinPrice.value = pill.dataset.min || '';
      if (taskMaxPrice) taskMaxPrice.value = pill.dataset.max || '';
      if (taskCity && !taskCity.value) taskCity.value = 'Кемерово';
    });
  });

  // Save Task Form
  if (taskForm) {
    taskForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const model = taskModel.value.trim();
      const city = taskCity.value.trim();
      const threadIdVal = taskThreadId ? parseInt(taskThreadId.value) || null : null;

      const payload = {
        id: taskId.value || null,
        model: model,
        city: city,
        title: `${model} (${city})`,
        thread_id: threadIdVal,
        min_price: parseInt(taskMinPrice.value) || 0,
        max_price: parseInt(taskMaxPrice.value) || 150000,
        avg_price: 0
      };

      await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      showToast('Задача сохранена');
      taskModal.classList.remove('open');
      loadTasks();
      loadStatus();
    });
  }

  // ==========================================================================
  // Items Catalog
  // ==========================================================================
  async function loadItems() {
    try {
      const res = await fetch('/api/items');
      allItemsStore = await res.json();
      renderItems();
    } catch (e) {
      console.error('Failed to load items:', e);
    }
  }

  function updateItemsFilterOptions() {
    if (!itemsTaskFilter) return;
    const keys = Object.keys(allItemsStore);
    itemsTaskFilter.innerHTML = '<option value="all">Все задачи (' + keys.length + ')</option>';
    keys.forEach(k => {
      const opt = document.createElement('option');
      opt.value = k;
      opt.textContent = `${k} (${allItemsStore[k].length})`;
      itemsTaskFilter.appendChild(opt);
    });
  }

  function renderItems() {
    if (!itemsListContainer) return;
    const selectedTask = itemsTaskFilter ? itemsTaskFilter.value : 'all';

    let list = [];
    Object.keys(allItemsStore).forEach(tName => {
      if (selectedTask === 'all' || selectedTask === tName) {
        allItemsStore[tName].forEach(it => list.push({ ...it, taskName: tName }));
      }
    });

    if (list.length === 0) {
      itemsListContainer.innerHTML = `
        <div class="tg-cell">
          <div class="cell-content">
            <span class="cell-sub">В каталоге пока нет объявлений. Запустите скан.</span>
          </div>
        </div>
      `;
      return;
    }

    itemsListContainer.innerHTML = list.map((it, idx) => {
      const isLast = idx === list.length - 1;
      return `
        <div class="ios-item-card">
          <div class="item-top-row">
            <span class="ios-pill">${it.taskName}</span>
            <span class="item-price">${formatMoney(it.price)}</span>
          </div>
          <div class="item-title">${it.title}</div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
            <a href="${it.url}" target="_blank" rel="noopener noreferrer" class="item-link">
              <span>Открыть на Авито</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M5 12h14"/><polyline points="12 5 19 12 12 19"/>
              </svg>
            </a>
            <button type="button" class="ios-chip fav-item-btn" data-id="${it.id}">
              <span>⭐ В избранное</span>
            </button>
          </div>
        </div>
        ${!isLast ? '<div class="tg-cell-divider" style="margin-left: 16px;"></div>' : ''}
      `;
    }).join('');

    itemsListContainer.querySelectorAll('.fav-item-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        for (const tName in allItemsStore) {
          const it = allItemsStore[tName].find(x => String(x.id) === String(id));
          if (it) {
            await fetch('/api/favorites', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(it)
            });
            showToast('⭐ Добавлено в Избранное');
            loadStatus();
            break;
          }
        }
      });
    });
  }

  if (itemsTaskFilter) {
    itemsTaskFilter.addEventListener('change', renderItems);
  }

  // ==========================================================================
  // Live Logs Console
  // ==========================================================================
  async function loadLogs() {
    try {
      const res = await fetch('/api/logs');
      const data = await res.json();
      if (logsTerminalContent && data.logs) {
        logsTerminalContent.textContent = data.logs.join('');
        logsTerminalContent.scrollTop = logsTerminalContent.scrollHeight;
      }
    } catch (e) {
      if (logsTerminalContent) {
        logsTerminalContent.textContent = 'Ошибка загрузки журнала.';
      }
    }
  }

  if (btnRefreshLogs) {
    btnRefreshLogs.addEventListener('click', () => {
      loadLogs();
      showToast('Логи обновлены');
    });
  }

  // ==========================================================================
  // Settings & Blacklist
  // ==========================================================================
  async function loadSettings() {
    try {
      const res = await fetch('/api/settings');
      const data = await res.json();
      if (settingBotToken) settingBotToken.value = data.bot_token || '';
      if (settingChatId) settingChatId.value = data.chat_id || '';
      if (settingThreadId) settingThreadId.value = data.thread_id || '';

      if (switchSendPhotos) {
        if (data.send_photos !== false) switchSendPhotos.classList.add('active');
        else switchSendPhotos.classList.remove('active');
      }

      if (switchFilterDefects) {
        if (data.filter_defects !== false) switchFilterDefects.classList.add('active');
        else switchFilterDefects.classList.remove('active');
      }

      // Load Proxies
      const pRes = await fetch('/api/proxies');
      const pData = await pRes.json();
      if (proxiesTextarea && pData.proxies) {
        proxiesTextarea.value = pData.proxies.join('\n');
      }

      // Load Blacklist
      loadBlacklist();
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  }

  async function loadBlacklist() {
    if (!blacklistContainer) return;
    try {
      const res = await fetch('/api/blacklist');
      allBlacklist = await res.json();

      if (allBlacklist.length === 0) {
        blacklistContainer.innerHTML = `
          <div class="tg-cell">
            <div class="cell-content">
              <span class="cell-sub">В чёрном списке пока никого нет</span>
            </div>
          </div>
        `;
        return;
      }

      blacklistContainer.innerHTML = allBlacklist.map((b, idx) => {
        const isLast = idx === allBlacklist.length - 1;
        return `
          <div class="blacklist-item">
            <div class="blacklist-info">
              <span class="blacklist-name">${b.name || b.title || b.id}</span>
              <span class="blacklist-reason">${b.reason || 'Заблокирован'} • ${b.added_at || ''}</span>
            </div>
            <button type="button" class="liquid-glass-pill del-bl-btn" data-id="${b.id}" style="color: #ff453a;">
              Разблокировать
            </button>
          </div>
          ${!isLast ? '<div class="tg-cell-divider"></div>' : ''}
        `;
      }).join('');

      blacklistContainer.querySelectorAll('.del-bl-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const id = e.currentTarget.dataset.id;
          await fetch('/api/blacklist/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
          });
          showToast('Продавец разблокирован');
          loadBlacklist();
        });
      });
    } catch (e) {
      console.error('Failed to load blacklist:', e);
    }
  }

  // Toggles
  if (switchSendPhotos) {
    switchSendPhotos.addEventListener('click', () => {
      switchSendPhotos.classList.toggle('active');
    });
  }

  if (switchFilterDefects) {
    switchFilterDefects.addEventListener('click', () => {
      switchFilterDefects.classList.toggle('active');
    });
  }

  if (btnSaveProxies && proxiesTextarea) {
    btnSaveProxies.addEventListener('click', async () => {
      const proxies_text = proxiesTextarea.value;
      const res = await fetch('/api/proxies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proxies_text })
      });
      const data = await res.json();
      showToast(`Сохранено: ${data.count || 0} прокси`);
    });
  }

  if (btnSaveSettings) {
    btnSaveSettings.addEventListener('click', async () => {
      const payload = {
        bot_token: settingBotToken ? settingBotToken.value.trim() : '',
        chat_id: settingChatId ? settingChatId.value.trim() : '',
        thread_id: settingThreadId ? settingThreadId.value.trim() : '',
        send_photos: switchSendPhotos ? switchSendPhotos.classList.contains('active') : true,
        filter_defects: switchFilterDefects ? switchFilterDefects.classList.contains('active') : true
      };

      try {
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        showToast(data.message || 'Настройки сохранены');
      } catch (err) {
        showToast('Ошибка сохранения');
      }
    });
  }

  if (btnTestTelegram) {
    btnTestTelegram.addEventListener('click', async () => {
      showToast('Отправка теста...');
      try {
        const res = await fetch('/api/test-telegram', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast('Уведомление отправлено!');
        } else {
          showToast(data.error || 'Ошибка отправки');
        }
      } catch (err) {
        showToast('Сетевая ошибка');
      }
    });
  }

  // Initial Data Load
  loadStatus();
  loadAds();
  loadDeals();
  loadFavorites();
  loadTasks();
  switchTab('ads');

  // Polling intervals
  setInterval(loadStatus, 4000);
});
