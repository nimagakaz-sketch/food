/**
 * Liquid Glass Telegram Mini App Controller
 * Family Menu Planner & Real-Time Supermarket Price Comparator (Пятерочка, Магнит, Лента)
 * Physics and shaders based on liquid-glass-kit by Volodymyr (@vovnx)
 */

(function () {
  'use strict';

  // --- Telegram WebApp SDK Initialization ---
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    try {
      tg.setHeaderColor('#000000');
      tg.setBackgroundColor('#000000');
    } catch (e) {}
  }

  // Haptic feedback helper
  const hap = (() => {
    const w = window.Telegram && Telegram.WebApp;
    const hf = w && w.platform && w.platform !== 'unknown' && w.HapticFeedback;
    const buzz = ms => { try { navigator.vibrate && navigator.vibrate(ms); } catch (e) {} };
    return {
      impact: s => { try { hf ? hf.impactOccurred(s) : buzz(s === 'medium' ? 18 : 10); } catch (e) {} },
      select: () => { try { hf ? hf.selectionChanged() : buzz(6); } catch (e) {} }
    };
  })();

  const $ = id => document.getElementById(id);
  const currentUserId = tg?.initDataUnsafe?.user?.id || 1001;
  const currentUserName = tg?.initDataUnsafe?.user?.first_name || 'Гость';

  // State
  let currentMenuData = null;
  let currentProfileData = null;
  let presetCatalog = {};
  let activeCategory = "Мясо и птица";
  let activeDayIndex = 0;
  let activeViewIndex = 0;

  // --- 1. LIQUID GLASS SHADERS & DISPLACEMENT ENGINE ---
  const isChromium = /Chrome\//.test(navigator.userAgent) && !/CriOS|FxiOS|EdgiOS/.test(navigator.userAgent);
  const surf = x => Math.pow(1 - Math.pow(1 - x, 4), .25);

  function profile(T, B, ior, N = 128) {
    const eta = 1 / ior, p = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      const x = i / N, y = surf(x), dx = x < 1 ? 1e-4 : -1e-4;
      const d = (surf(x + dx) - y) / dx, m = Math.hypot(d, 1), nx = -d / m, ny = -1 / m;
      const k = 1 - eta * eta * (1 - ny * ny);
      if (k < 0) continue;
      const s = Math.sqrt(k);
      p[i] = -(eta * ny + s) * nx * ((y * B + T) / (eta - (eta * ny + s) * ny));
    }
    return p;
  }

  const k0 = (x, y, w) => (y * w + x) * 4 + 3;

  function maps(w, h, r, B, p, mx) {
    const mk = () => {
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      const x = c.getContext('2d');
      return [c, x, x.createImageData(w, h)];
    };
    const [c1, x1, i1] = mk(), [c2, x2, i2] = mk(), a = i1.data, b = i2.data;
    const N = p.length, wB = w - 2 * r, hB = h - 2 * r, Bs = B * 2.5, sx = Math.cos(Math.PI / 3), sy = Math.sin(Math.PI / 3);
    for (let i = 0; i < a.length; i += 4) { a[i] = a[i + 1] = 128; a[i + 3] = 255; }
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const X = x < r ? x - r : x >= w - r ? x - r - wB : 0, Y = y < r ? y - r : y >= h - r ? y - r - hB : 0;
        const d2 = X * X + Y * Y;
        if (d2 > (r + 1) ** 2) continue;
        const d = Math.sqrt(d2);
        if (!d) { b[k0(x, y, w)] = 0; continue; }
        const op = d < r ? 1 : 1 - (d - r), k = (y * w + x) * 4, cs = X / d, sn = Y / d, fs = r - d;
        if (op <= 0) continue;
        if (d2 >= Math.max(r - B, 0) ** 2) {
          const disp = p[Math.min(Math.max(fs / B * N, 0) | 0, N - 1)] || 0;
          a[k] = (128 + (-cs * disp / mx) * 127 * op + .5) | 0;
          a[k + 1] = (128 + (-sn * disp / mx) * 127 * op + .5) | 0;
        }
        if (d2 >= Math.max(r - Bs, 0) ** 2) {
          const dot = Math.abs(cs * sx + (-sn) * sy), edge = Math.sqrt(Math.max(0, 1 - (1 - fs) ** 2)), co = dot * edge, col = (255 * co) | 0;
          b[k] = b[k + 1] = b[k + 2] = col; b[k + 3] = (col * co * op) | 0;
        }
      }
    }
    x1.putImageData(i1, 0, 0); x2.putImageData(i2, 0, 0);
    return [c1.toDataURL(), c2.toDataURL()];
  }

  function filterFor(el, id) {
    const w = el.offsetWidth, h = el.offsetHeight;
    if (w < 2 || h < 2) return '';
    const soft = !!el.dataset.soft, r = h / 2, B = Math.min(h * (soft ? .15 : .34), r - 1);
    const p = profile(h * (soft ? .2 : .42), B, soft ? 1.5 : 1.9);
    const mx = Math.max(...Array.from(p, Math.abs)) || 1, [disp, spec] = maps(w, h, r, B, p, mx);
    return `<filter id="${id}" x="0%" y="0%" width="100%" height="100%">
<feGaussianBlur in="SourceGraphic" stdDeviation="0.2" result="bl"/>
<feImage href="${disp}" x="0" y="0" width="${w}" height="${h}" result="dm"/>
<feDisplacementMap in="bl" in2="dm" scale="${mx * (soft ? .1 : id === 'lg-thumb' ? .45 : .4)}" xChannelSelector="R" yChannelSelector="G" result="dp"/>
<feColorMatrix in="dp" type="saturate" values="5" result="ds"/>
<feImage href="${spec}" x="0" y="0" width="${w}" height="${h}" result="sl"/>
<feComposite in="ds" in2="sl" operator="in" result="sm"/>
<feComponentTransfer in="sl" result="sf"><feFuncA type="linear" slope="${soft ? 0 : id === 'lg-thumb' ? .22 : 1}"/></feComponentTransfer>
<feBlend in="sm" in2="dp" mode="normal" result="ws"/>
<feBlend in="sf" in2="ws" mode="normal"/></filter>`;
  }

  const bar = $('bar'), base = $('base'), fil = $('fil'), thumb = $('thumb'), lens = $('lens'), slens = $('slens');
  const bdEls = [[base, 'bd-base']], glassEls = [[lens, 'lg-thumb']];
  if (slens) glassEls.push([slens, 'lg-slens']);
  bdEls.forEach(([el]) => el.dataset.soft = '1');

  function rebuild() {
    $('defs').innerHTML = glassEls.concat(isChromium ? bdEls : []).map(([el, id]) => filterFor(el, id)).join('');
    glassEls.forEach(([el, id]) => el.style.filter = `url(#${id})`);
    if (isChromium) {
      bdEls.forEach(([el, id]) => {
        const v = `url(#${id}) blur(4px) saturate(1.8)`;
        el.style.backdropFilter = v;
        el.style.webkitBackdropFilter = v;
      });
    }
  }

  let rt;
  const ro = new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(rebuild, 80); });
  glassEls.concat(bdEls).forEach(([el]) => el && ro.observe(el));
  rebuild();

  // --- 2. TAB BAR LIQUID DROPLET PHYSICS LOOP ---
  const tabs = [...$('tabs').children], tabsEl = $('tabs');
  const clone = tabsEl.cloneNode(true);
  clone.removeAttribute('id');
  clone.setAttribute('aria-hidden', 'true');
  clone.querySelectorAll('button').forEach(b => b.tabIndex = -1);
  lens.appendChild(clone);
  const cloneTabs = [...clone.children];

  let dirv = 1, cur = 0, vel = 0, target = 0, press = 0, pvel = 0, down = false, grab = 0, active = 0;
  let pRaw = 0, pT = 0, pV = 0, mv = 0, mvv = 0, zz = 0, zzv = 0, wasMoving = false, lag = 0, lagv = 0;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  let hi = 0;
  function highlight(i) {
    if (i === hi) return;
    hi = i;
    [tabs, cloneTabs].forEach(arr => arr.forEach((el, n) => el.classList.toggle('on', n === i)));
  }

  function setActive(i) {
    highlight(i);
    if (i === active) return;
    active = i;
    if (window.onTabChange) window.onTabChange(i);
  }

  function ptr(e) {
    const rc = tabsEl.getBoundingClientRect(), w = tabs[0].offsetWidth, pad = (rc.width - w * 3) / 2;
    return (e.clientX - rc.left - pad) / w;
  }

  function place(p, now) {
    const raw = p - .5 - grab;
    target = raw < 0 ? raw * .3 : raw > 2 ? 2 + (raw - 2) * .3 : raw;
    if (pT) {
      const dt = Math.max(.008, (now - pT) / 1000);
      pV += ((raw - pRaw) / dt - pV) * .35;
    }
    pRaw = raw; pT = now;
    highlight(clamp(Math.round(raw), 0, 2));
  }

  bar.addEventListener('pointerdown', e => {
    bar.setPointerCapture(e.pointerId); down = true; bar.classList.add('down');
    pV = 0; pT = 0;
    const p = ptr(e);
    grab = Math.abs(p - (cur + .5)) < .5 ? p - (cur + .5) : 0;
    place(p, e.timeStamp);
    hap.select();
  });

  bar.addEventListener('pointermove', e => { if (down) place(ptr(e), e.timeStamp); });

  ['pointerup', 'pointercancel'].forEach(n => bar.addEventListener(n, e => {
    if (!down) return;
    down = false;
    bar.classList.remove('down');
    if (e.timeStamp - pT > 90) pV = 0;
    pV = clamp(pV, -9, 9);
    const dest = clamp(Math.round(pRaw + pV * .1), 0, 2);
    target = dest;
    setActive(dest);
    vel += pV * .22;
    hap.impact('medium');
  }));

  tabs.forEach((el, n) => el.addEventListener('click', () => {
    target = n;
    setActive(n);
    hap.select();
  }));

  const btnSteps = [];

  let last = performance.now();
  (function loop(now) {
    const dt = Math.min(.05, (now - last) / 1000 || .016);
    last = now;
    const k = down ? 210 : 230, c = down ? 22 : 1.6 * Math.sqrt(230), pk = 200, pc = 11;
    const n = 4, h = dt / n;
    for (let i = 0; i < n; i++) {
      vel += (-k * (cur - target) - c * vel) * h;
      cur += vel * h;
      pvel += (-pk * (press - (down ? 1 : 0)) - pc * pvel) * h;
      press += pvel * h;
      lagv += (-180 * (lag - cur) - 2 * Math.sqrt(180) * lagv) * h;
      lag += lagv * h;
    }

    const moving = Math.abs(cur - target) > .1 || Math.abs(vel) > .9;
    if (wasMoving && !moving && !down) zzv -= 2.4;
    if (!wasMoving && moving) zzv += 1.4;
    wasMoving = moving;

    const mk = moving ? 380 : 900, mc = 2 * Math.sqrt(mk);
    for (let i = 0; i < 4; i++) {
      mvv += (-mk * (mv - (moving ? 1 : 0)) - mc * mvv) * (dt / 4);
      mv += mvv * (dt / 4);
    }
    mv = clamp(mv, -.2, 1.6);

    const zt = .02 * clamp(Math.abs(vel) / 6, 0, 1) + .04 * press;
    for (let i = 0; i < 4; i++) {
      zzv += (-170 * (zz - zt) - 1.2 * Math.sqrt(170) * zzv) * (dt / 4);
      zz += zzv * (dt / 4);
    }
    zz = clamp(zz, -.3, .3);

    const g = (mv < 0 && press < .02) ? mv : Math.max(mv, press);
    const st = clamp(Math.abs(vel) * .055, 0, .26) * (down ? 1 : .6);
    const s = 1 + .05 * g + .06 * press, sy = 1 + .24 * g + .16 * press;

    bar.style.setProperty('--x', cur.toFixed(4));

    const sm = (v, m, K) => v <= m - K ? v : m - K * Math.exp(-(v - (m - K)) / K);
    const cx = 12 + cur * 273 + 136.5;
    const horiz = w => [-sm(-(cx - w / 2), 48, 30), sm(cx + w / 2, 891, 30)];
    if (Math.abs(vel) > .6) dirv = Math.sign(vel);

    const jel = clamp((cur - lag) * dirv, -.55, .55);
    let sxv = s * (1 + st) * (1 + .48 * jel) * (1 - .45 * zz), syv = sy * (1 + zz);
    sxv = Math.min(sxv, 1.38);

    let [Lc, Rc] = horiz(252 * sxv);
    const cmp = Math.max(0, 1 - (Rc - Lc) / (252 * sxv));
    vel *= 1 - Math.min(.3, cmp * 4 * dt);
    syv *= 1 + .45 * cmp;

    const h0 = 165 * syv, h1 = sm(h0, 214, 14);
    sxv *= Math.sqrt(h0 / h1);
    syv = h1 / 165;
    [Lc, Rc] = horiz(252 * sxv);

    bar.style.setProperty('--tx', ((Lc + Rc) / 2 - cx).toFixed(3));
    bar.style.setProperty('--sx', ((Rc - Lc) / 252).toFixed(4));
    bar.style.setProperty('--sy', syv.toFixed(4));
    bar.style.setProperty('--p', clamp(g, 0, 1).toFixed(3));

    // Dynamic fluid edge boundary
    const U = bar.offsetWidth / 843, r = 82.5 * syv, cy = 95, ex = r - cy;
    let d = '';
    if (ex > 1.5) {
      const OX = 60, OY = 40, f = (x, y) => ((x + OX) * U).toFixed(1) + ' ' + ((y + OY) * U).toFixed(1);
      const FLAT0 = 95, FLAT1 = 748;
      const phi0 = Math.asin(cy / r), hc = Math.sqrt(r * r - cy * cy);
      const build = (k, side, vert) => {
        const phi1 = Math.asin(Math.min(1, (cy + k * ex) / r)), cc = side > 0 ? Rc - r : Lc + r;
        const px = cc + side * r * Math.cos(phi1), py = -(r * Math.sin(phi1) - cy);
        const tt = -py / Math.cos(phi1), Cx = px + side * tt * Math.sin(phi1), P0x = Cx + side * Math.abs(Cx - px) * 2;
        const xi = cc + side * hc;
        if (side > 0 ? P0x > FLAT1 : P0x < FLAT0) return null;
        const Y = y => vert > 0 ? y : 190 - y;
        let pth = `M${f(xi, Y(0))} L${f(P0x, Y(0))} Q${f(Cx, Y(0))} ${f(px, Y(py))}`;
        for (let a = 1; a <= 8; a++) {
          const ph = phi1 + (phi0 - phi1) * a / 8;
          pth += ` L${f(cc + side * r * Math.cos(ph), Y(-(r * Math.sin(ph) - cy)))}`;
        }
        return pth + ' Z';
      };
      for (const side of [1, -1]) {
        for (const vert of [1, -1]) {
          for (const k of [.95, .65, .4]) {
            const q = build(k, side, vert);
            if (q) { d += q; break; }
          }
        }
      }
    }
    fil.style.clipPath = fil.style.webkitClipPath = d ? `path('${d}')` : 'path("M0 0 Z")';

    btnSteps.forEach(f => f(dt));
    requestAnimationFrame(loop);
  })(performance.now());

  // --- 3. CIRCLE BUTTON GLASS PHYSICS ---
  function glassBtn(btn, lensEl, onClick) {
    if (!btn || !lensEl) return;
    const content = btn.querySelector('.ics') || btn.querySelector('.gc');
    if (content) {
      const cl = content.cloneNode(true);
      cl.className = 'sclone';
      lensEl.appendChild(cl);
    }
    let ox = 0, oy = 0, vx = 0, vy = 0, cx = 1, cy = 1, sp = 0, spv = 0, down = false, pid = null, sx = 0, sy = 0;
    btn.addEventListener('pointerdown', e => {
      btn.setPointerCapture(e.pointerId); pid = e.pointerId; down = true;
      sx = e.clientX; sy = e.clientY;
      hap.select();
    });
    btn.addEventListener('pointermove', e => {
      if (!down || e.pointerId !== pid) return;
      const dx = (e.clientX - sx) * .22, dy = (e.clientY - sy) * .22;
      ox = dx; oy = dy;
    });
    const up = e => {
      if (!down || (e && e.pointerId !== pid)) return;
      down = false; pid = null;
      if (onClick) onClick();
      hap.impact('medium');
    };
    btn.addEventListener('pointerup', up);
    btn.addEventListener('pointercancel', up);

    btnSteps.push(dt => {
      const k = down ? 260 : 150, c = down ? 24 : 9;
      vx += (-k * ox - c * vx) * dt; ox += vx * dt;
      vy += (-k * oy - c * vy) * dt; oy += vy * dt;
      spv += (-190 * (sp - (down ? 1 : 0)) - 14 * spv) * dt; sp += spv * dt;
      sp = Math.max(0, Math.min(1, sp));
      cx = 1 + sp * .12; cy = 1 + sp * .12;
      btn.style.setProperty('--ox', ox.toFixed(2) + 'px');
      btn.style.setProperty('--oy', oy.toFixed(2) + 'px');
      btn.style.setProperty('--cx', cx.toFixed(3));
      btn.style.setProperty('--cy', cy.toFixed(3));
      btn.style.setProperty('--sp', sp.toFixed(3));
    });
  }

  // --- 4. VIEW SWITCHING & TOAST ---
  function switchView(index) {
    activeViewIndex = index;
    const views = [$('v0'), $('v1'), $('v2')];
    views.forEach((v, i) => {
      if (v) v.classList.toggle('on', i === index);
    });
  }
  window.onTabChange = switchView;

  function showToast(text) {
    const pop = $('eggpop');
    if (!pop) return;
    pop.textContent = text;
    pop.classList.remove('show');
    void pop.offsetWidth;
    pop.classList.add('show');
    hap.impact('medium');
  }

  // --- 5. RENDER MENU SCREEN (VIEW 0) ---
  function renderDailyMenu(dayIndex) {
    if (!currentMenuData || !currentMenuData.days || !currentMenuData.days.length) return;
    const day = currentMenuData.days[dayIndex];
    if (!day) return;

    activeDayIndex = dayIndex;

    document.querySelectorAll('#dayScroll .dchip').forEach((chip, idx) => {
      chip.classList.toggle('active', idx === dayIndex);
    });

    $('dayTitleText').textContent = day.day_name.toUpperCase();
    $('dayCaloriesText').textContent = `${day.total_calories.toLocaleString('ru-RU')} ккал`;

    let totalP = 0, totalF = 0, totalC = 0;
    (day.dishes || []).forEach(d => {
      totalP += d.proteins || 0;
      totalF += d.fats || 0;
      totalC += d.carbs || 0;
    });

    $('dayProteinsText').textContent = `${Math.round(totalP)}г`;
    $('dayFatsText').textContent = `${Math.round(totalF)}г`;
    $('dayCarbsText').textContent = `${Math.round(totalC)}г`;

    const container = $('mealsContainer');
    container.innerHTML = '';
    const mealIcons = { breakfast: '🍳', lunch: '🍲', dinner: '🥗' };

    (day.dishes || []).forEach(dish => {
      const item = document.createElement('div');
      item.className = 'meal-item';
      const icon = mealIcons[dish.meal_type] || '🍽';
      const ingsHtml = (dish.ingredients || []).map(ing =>
        `<span class="ing-tag">${ing.name}: <strong>${ing.amount} ${ing.unit}</strong></span>`
      ).join('');

      item.innerHTML = `
        <div class="meal-title-row">
          <span class="meal-type-label">${icon} ${dish.meal_name_ru}</span>
          <span style="font-size:12px; color:#8e8e93;">⏱ ${dish.cooking_time_min} мин</span>
        </div>
        <div class="meal-name">${dish.name}</div>
        <div class="meal-meta">${dish.calories} ккал • Б: ${dish.proteins}г | Ж: ${dish.fats}г | У: ${dish.carbs}г</div>
        <div class="meal-ings">${ingsHtml}</div>
      `;
      container.appendChild(item);
    });
  }

  // --- 6. RENDER PRICES SCREEN (VIEW 1) WITH REAL-TIME INDICATORS ---
  function renderPriceComparison(comp) {
    if (!comp || !comp.stores) return;

    const pya = comp.stores.pyaterochka;
    const mag = comp.stores.magnit;
    const len = comp.stores.lenta;

    if (pya) $('pricePya').textContent = `${Math.round(pya.total_price).toLocaleString('ru-RU')} ₽`;
    if (mag) $('priceMag').textContent = `${Math.round(mag.total_price).toLocaleString('ru-RU')} ₽`;
    if (len) $('priceLen').textContent = `${Math.round(len.total_price).toLocaleString('ru-RU')} ₽`;

    if (comp.checked_at) {
      $('priceCheckedAtLabel').textContent = `Обновлено: ${comp.checked_at}`;
    }

    const boxes = { pyaterochka: $('boxPyaterochka'), magnit: $('boxMagnit'), lenta: $('boxLenta') };
    const diffs = { pyaterochka: $('diffPya'), magnit: $('diffMag'), lenta: $('diffLen') };
    const minTotal = Math.min(pya?.total_price || 0, mag?.total_price || 0, len?.total_price || 0);

    Object.keys(boxes).forEach(k => {
      const s = comp.stores[k];
      const box = boxes[k];
      const diff = diffs[k];
      if (!s || !box || !diff) return;

      if (s.is_cheapest) {
        box.className = 'store-box winner';
        diff.textContent = 'Лучшая цена 🏆';
        diff.className = 'store-diff';
      } else {
        box.className = 'store-box';
        diff.textContent = `+${Math.round(s.total_price - minTotal)} ₽`;
        diff.className = 'store-diff more';
      }
    });

    if (comp.hybrid_recommendation) {
      $('hybridTipText').innerHTML = comp.hybrid_recommendation;
    } else {
      $('hybridTipText').innerHTML = `💡 Покупая в <strong>${comp.cheapest_store}</strong>, вы экономите <strong>${Math.round(comp.max_savings)} ₽</strong>!`;
    }

    const list = $('priceItemsList');
    list.innerHTML = '';
    const items = comp.items || [];
    $('itemsCountBadge').textContent = `${items.length} поз.`;

    items.forEach(it => {
      const row = document.createElement('div');
      row.className = 'p-row';

      const pPya = Math.round(it.price_pyaterochka);
      const pMag = Math.round(it.price_magnit);
      const pLen = Math.round(it.price_lenta);
      const minP = Math.min(pPya, pMag, pLen);

      row.innerHTML = `
        <div style="flex:1;">
          <div class="p-name">${it.product_name}</div>
          <div class="p-sub">${it.amount_needed} ${it.unit} • Выгоднее в: <strong>${it.best_store}</strong></div>
        </div>
        <div class="p-prices">
          <span class="p-badge ${pPya === minP ? 'best' : ''}">Пят ${pPya}₽</span>
          <span class="p-badge ${pMag === minP ? 'best' : ''}">Магн ${pMag}₽</span>
          <span class="p-badge ${pLen === minP ? 'best' : ''}">Лента ${pLen}₽</span>
        </div>
      `;
      list.appendChild(row);
    });
  }

  // --- 7. RENDER PROFILE TAGS WITH 1-CLICK DELETE ---
  function renderProfileTags() {
    if (!currentProfileData) return;

    // 1. Favorites
    const favWrap = $('favTagsContainer');
    favWrap.innerHTML = '';
    const favs = currentProfileData.favorite_products || [];
    $('favCountBadge').textContent = `${favs.length} шт.`;

    if (!favs.length) {
      favWrap.innerHTML = `<span style="font-size:13px; color:#8e8e93;">Список пуст. Добавьте свои любимые продукты выше!</span>`;
    } else {
      favs.forEach(item => {
        const pill = document.createElement('span');
        pill.className = 'tag-pill fav';
        pill.innerHTML = `
          <span>${item}</span>
          <button type="button" class="tag-del-btn" title="Удалить">✕</button>
        `;
        pill.querySelector('.tag-del-btn').addEventListener('click', e => {
          e.stopPropagation();
          deleteItem('favorites', item);
        });
        favWrap.appendChild(pill);
      });
    }

    // 2. Stop-List
    const stopWrap = $('stopTagsContainer');
    stopWrap.innerHTML = '';
    const stops = currentProfileData.stop_list || [];
    $('stopCountBadge').textContent = `${stops.length} шт.`;

    if (!stops.length) {
      stopWrap.innerHTML = `<span style="font-size:13px; color:#8e8e93;">Стоп-лист пуст. Вы можете добавить продукты, которые не любите.</span>`;
    } else {
      stops.forEach(item => {
        const pill = document.createElement('span');
        pill.className = 'tag-pill stop';
        pill.innerHTML = `
          <span>🚫 ${item}</span>
          <button type="button" class="tag-del-btn" title="Удалить">✕</button>
        `;
        pill.querySelector('.tag-del-btn').addEventListener('click', e => {
          e.stopPropagation();
          deleteItem('stop-list', item);
        });
        stopWrap.appendChild(pill);
      });
    }

    // 3. Allergies
    const allgWrap = $('allgTagsContainer');
    allgWrap.innerHTML = '';
    const allgs = currentProfileData.allergies || [];
    allgs.forEach(item => {
      const pill = document.createElement('span');
      pill.className = 'tag-pill allg';
      pill.innerHTML = `
        <span>⚠️ ${item}</span>
        <button type="button" class="tag-del-btn" title="Удалить">✕</button>
      `;
      pill.querySelector('.tag-del-btn').addEventListener('click', e => {
        e.stopPropagation();
        deleteItem('allergies', item);
      });
      allgWrap.appendChild(pill);
    });

    // 4. Steppers & Plan Days
    $('familySizeVal').textContent = currentProfileData.family_size || 2;
    document.querySelectorAll('#periodChips .tg').forEach(el => {
      el.classList.toggle('selected', parseInt(el.dataset.days) === currentProfileData.plan_days);
    });
  }

  // 1-Click Delete item from list
  async function deleteItem(type, item) {
    try {
      const res = await fetch(`/api/profile/${currentUserId}/${type}/${encodeURIComponent(item)}`, {
        method: 'DELETE'
      });
      if (!res.ok) throw new Error('Delete failed');
      currentProfileData = await res.json();
      renderProfileTags();
      showToast(`Удалено: ${item}`);
      // Refresh menu with new exclusions
      loadData(false);
    } catch (e) {
      console.error(e);
      showToast('Ошибка удаления');
    }
  }

  // Add custom item manually
  async function addCustomItem(type) {
    const input = $('customProductInput');
    const val = input.value.trim();
    if (!val) {
      showToast('Введите название продукта');
      input.focus();
      return;
    }

    try {
      const endpoint = type === 'fav' ? 'favorites' : 'stop-list';
      const res = await fetch(`/api/profile/${currentUserId}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item: val })
      });
      if (!res.ok) throw new Error('Add failed');
      currentProfileData = await res.json();
      input.value = '';
      renderProfileTags();
      showToast(type === 'fav' ? `Добавлено в любимые: ${val}` : `Добавлено в стоп-лист: ${val}`);
      // Update menu
      loadData(false);
    } catch (e) {
      console.error(e);
      showToast('Ошибка добавления');
    }
  }

  // --- 8. PRESET CATALOG BY CATEGORIES ---
  async function loadPresetCatalog() {
    try {
      const res = await fetch('/api/catalog/preset');
      if (res.ok) {
        presetCatalog = await res.json();
        renderCategoryItems(activeCategory);
      }
    } catch (e) {
      console.error(e);
    }
  }

  function renderCategoryItems(catName) {
    activeCategory = catName;
    const grid = $('catItemsGrid');
    grid.innerHTML = '';
    const items = presetCatalog[catName] || [];

    document.querySelectorAll('#catStrip .cat-pill').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.cat === catName);
    });

    items.forEach(it => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cat-item-btn';
      btn.innerHTML = `<span>${it.icon} ${it.name}</span>`;
      btn.addEventListener('click', () => {
        // Direct quick add to favorites or stop-list
        const isAlreadyFav = (currentProfileData?.favorite_products || []).includes(it.name);
        if (isAlreadyFav) {
          showToast(`${it.name} уже в любимых!`);
        } else {
          $('customProductInput').value = it.name;
          addCustomItem('fav');
        }
      });
      grid.appendChild(btn);
    });
  }

  // Category Strip clicks
  document.querySelectorAll('#catStrip .cat-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      renderCategoryItems(btn.dataset.cat);
      hap.select();
    });
  });

  // Buttons for custom product adding
  $('btnAddCustomFav')?.addEventListener('click', () => addCustomItem('fav'));
  $('btnAddCustomStop')?.addEventListener('click', () => addCustomItem('stop'));
  $('customProductInput')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addCustomItem('fav');
    }
  });

  // --- 9. DATA LOADING ---
  async function loadData(refresh = false) {
    try {
      const res = await fetch(`/api/menu/${currentUserId}${refresh ? '?refresh=true' : ''}`);
      if (!res.ok) throw new Error('API error');
      currentMenuData = await res.json();

      const profRes = await fetch(`/api/profile/${currentUserId}`);
      if (profRes.ok) {
        currentProfileData = await profRes.json();
        $('headerFamilySub').textContent = `Семья ${currentProfileData.family_size} чел. • ${currentProfileData.plan_days} дн.`;
        renderProfileTags();
      }

      renderDailyMenu(activeDayIndex);
      if (currentMenuData.price_comparison) {
        renderPriceComparison(currentMenuData.price_comparison);
      }

      if (refresh) {
        showToast('Цены и меню обновлены в реальном времени!');
      }
    } catch (err) {
      console.error(err);
      showToast('Ошибка загрузки данных');
    }
  }

  // Family size steppers
  $('btnMinusFamily')?.addEventListener('click', () => {
    let sz = parseInt($('familySizeVal').textContent) || 2;
    if (sz > 1) {
      sz--;
      $('familySizeVal').textContent = sz;
      hap.select();
    }
  });

  $('btnPlusFamily')?.addEventListener('click', () => {
    let sz = parseInt($('familySizeVal').textContent) || 2;
    if (sz < 10) {
      sz++;
      $('familySizeVal').textContent = sz;
      hap.select();
    }
  });

  // Period chips
  document.querySelectorAll('#periodChips .tg').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('#periodChips .tg').forEach(c => c.classList.remove('selected'));
      el.classList.add('selected');
      hap.select();
    });
  });

  // Save Profile and recalculate
  $('btnSaveProfile')?.addEventListener('click', async () => {
    const familySize = parseInt($('familySizeVal').textContent) || 2;
    const planDays = parseInt(document.querySelector('#periodChips .tg.selected')?.dataset.days) || 7;

    const payload = {
      telegram_id: currentUserId,
      username: currentUserName,
      first_name: currentUserName,
      favorite_products: currentProfileData?.favorite_products || [],
      stop_list: currentProfileData?.stop_list || [],
      allergies: currentProfileData?.allergies || [],
      family_size: familySize,
      plan_days: planDays
    };

    try {
      const res = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Failed to save');

      showToast('Профиль сохранен! Меню пересчитано');
      await loadData(false);
      target = 0;
      setActive(0);
      switchView(0);
    } catch (e) {
      console.error(e);
      showToast('Ошибка сохранения');
    }
  });

  // Day Scroll clicks
  document.querySelectorAll('#dayScroll .dchip').forEach((chip, idx) => {
    chip.addEventListener('click', () => {
      renderDailyMenu(idx);
      hap.select();
    });
  });

  // Regenerate & Refresh Buttons
  $('btnRegenerateMenu')?.addEventListener('click', () => {
    loadData(true);
    hap.impact('medium');
  });

  $('btnRefreshPricesLive')?.addEventListener('click', () => {
    loadData(true);
    hap.impact('medium');
  });

  // Quick Circle Action Button in Dock
  glassBtn($('circle'), $('slens'), () => {
    loadData(true);
  });

  // Health Ping Test
  async function testHealthPing() {
    const t0 = performance.now();
    try {
      const res = await fetch('/health', { method: 'HEAD' });
      const ms = Math.round(performance.now() - t0);
      if (res.ok) {
        showToast(`Health Check: HEAD 200 OK (${ms}мс)`);
      } else {
        showToast(`Health Check: ${res.status}`);
      }
    } catch (e) {
      showToast('Health Check: ошибка');
    }
  }
  $('btnTestHealthPing')?.addEventListener('click', testHealthPing);

  // Initial load
  loadPresetCatalog();
  loadData(false);
})();
