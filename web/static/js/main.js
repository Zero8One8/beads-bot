/* Магия Камней — основной JS */

// ── QUIZ ─────────────────────────────────────────
const quiz = {
  steps: [],
  current: 0,
  answers: {},

  init() {
    this.steps = Array.from(document.querySelectorAll('.quiz-step'));
    if (!this.steps.length) return;
    this.updateProgress();
    this.steps[0].classList.add('active');
  },

  select(el, value) {
    el.closest('.quiz-options').querySelectorAll('.quiz-opt')
      .forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    this.answers[`q${this.current}`] = value;

    setTimeout(() => this.next(), 300);
  },

  next() {
    if (!this.answers[`q${this.current}`]) return;
    this.steps[this.current].classList.remove('active');
    this.current++;
    if (this.current < this.steps.length) {
      this.steps[this.current].classList.add('active');
      this.updateProgress();
    } else {
      this.submit();
    }
  },

  updateProgress() {
    document.querySelectorAll('.quiz-dot').forEach((dot, i) => {
      dot.classList.toggle('done', i < this.current);
      dot.classList.toggle('active', i === this.current);
    });
  },

  async submit() {
    const loadEl = document.getElementById('quiz-loading');
    const resultEl = document.getElementById('quiz-result');
    if (loadEl) loadEl.style.display = 'block';

    try {
      const res = await fetch('/api/quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: this.answers })
      });
      const data = await res.json();

      if (loadEl) loadEl.style.display = 'none';
      if (resultEl && data.ok) {
        document.getElementById('result-emoji').textContent = data.emoji;
        document.getElementById('result-title').textContent = data.title;
        document.getElementById('result-desc').textContent = data.short_desc;
        document.getElementById('result-link').href = data.url;
        document.getElementById('result-order').href = `/order?stone=${data.stone_id}`;
        resultEl.style.display = 'block';
      }
    } catch(e) {
      if (loadEl) loadEl.style.display = 'none';
      alert('Ошибка. Попробуйте ещё раз.');
    }
  }
};

// ── ORDER FORM ────────────────────────────────────
async function submitOrder(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('[type=submit]');
  btn.disabled = true;
  btn.textContent = 'Отправляем...';

  const data = {
    name: form.name.value,
    phone: form.phone.value,
    request: form.request?.value || '',
    stone: form.stone?.value || '',
    size: form.size?.value || '',
    budget: form.budget?.value || '',
  };

  try {
    const res = await fetch('/api/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await res.json();

    if (result.ok) {
      form.style.display = 'none';
      document.getElementById('form-success').style.display = 'block';
    } else {
      alert(result.error || 'Ошибка. Попробуйте ещё раз.');
      btn.disabled = false;
      btn.textContent = 'Отправить заявку';
    }
  } catch(e) {
    alert('Ошибка соединения.');
    btn.disabled = false;
    btn.textContent = 'Отправить заявку';
  }
}

function closeSiteEntryPopup() {
  const overlay = document.getElementById('site-entry-popup');
  if (!overlay) return;
  overlay.classList.remove('visible');
  overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
}

function createSiteEntryPopup() {
  if (window.__siteEntryPopupShown) return;
  window.__siteEntryPopupShown = true;

  const overlay = document.createElement('div');
  overlay.id = 'site-entry-popup';
  overlay.className = 'site-popup-overlay';
  overlay.innerHTML = `
    <div class="site-popup">
      <button class="site-popup-close" type="button" aria-label="Закрыть окно">×</button>
      <div class="site-popup-content">
        <h2>Добро пожаловать на Магию Камней</h2>
        <p>Приятно, что вы здесь. Пройдите бесплатный квиз — он поможет подобрать камень под вашу энергию.</p>
        <div class="site-popup-actions">
          <a href="/quiz" class="btn btn--gold">Пройти квиз</a>
          <button id="site-popup-close-button" class="btn btn--outline" type="button">Закрыть</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  overlay.querySelector('.site-popup-close').addEventListener('click', closeSiteEntryPopup);
  overlay.querySelector('#site-popup-close-button').addEventListener('click', closeSiteEntryPopup);
  overlay.addEventListener('click', event => {
    if (event.target === overlay) closeSiteEntryPopup();
  });

  requestAnimationFrame(() => overlay.classList.add('visible'));
}

// ── INIT ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  quiz.init();
  if (['/', '/index.html'].includes(location.pathname)) {
    createSiteEntryPopup();
  }

  const orderForm = document.getElementById('order-form');
  if (orderForm) orderForm.addEventListener('submit', submitOrder);

  // Отметить активную ссылку
  const path = location.pathname;
  document.querySelectorAll('.nav__links a').forEach(a => {
    if (a.getAttribute('href') === path) a.classList.add('active');
  });
});
