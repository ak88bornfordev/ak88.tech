// ===== Mobile nav toggle =====
const navToggle = document.querySelector('.nav-toggle');
const sidebar = document.querySelector('.sidebar');
if (navToggle && sidebar) {
  navToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.querySelectorAll('.nav-main a').forEach(a => {
    a.addEventListener('click', () => sidebar.classList.remove('open'));
  });
}

// ===== Scroll spy for in-page sections =====
const sections = document.querySelectorAll('article[id], section[id]');
const navLinks = document.querySelectorAll('.nav-main a[href^="#"]');
if (sections.length && navLinks.length) {
  const spy = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        navLinks.forEach(l => l.classList.remove('active'));
        const active = document.querySelector(`.nav-main a[href="#${entry.target.id}"]`);
        if (active) active.classList.add('active');
      }
    });
  }, { rootMargin: '-40% 0px -50% 0px' });
  sections.forEach(s => spy.observe(s));
}

// ===== Animate skill bars when visible =====
const skillFills = document.querySelectorAll('.skill-fill');
if (skillFills.length) {
  const skillObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.width = entry.target.dataset.percent + '%';
        skillObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });
  skillFills.forEach(f => skillObserver.observe(f));
}

// ===== Terminal typing effect =====
const termOut = document.querySelector('[data-typing]');
if (termOut) {
  const lines = JSON.parse(termOut.dataset.typing);
  let li = 0, ci = 0;
  const target = termOut;
  function typeNext() {
    if (li >= lines.length) return;
    const line = lines[li];
    if (ci <= line.length) {
      target.textContent = lines.slice(0, li).join('\n') + (li > 0 ? '\n' : '') + line.slice(0, ci);
      ci++;
      setTimeout(typeNext, 22 + Math.random() * 30);
    } else {
      li++; ci = 0;
      setTimeout(typeNext, 380);
    }
  }
  typeNext();
}

// ===== Contact form (front-end only) =====
const form = document.getElementById('contact-form');
if (form) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const msg = document.getElementById('form-msg');
    msg.textContent = '> Сообщение отправлено. Отвечу в течение дня.';
    msg.style.color = 'var(--green-ok)';
    form.reset();
  });
}

// ===== Blog filters =====
const filterBtns = document.querySelectorAll('.filter-btn');
const blogRows = document.querySelectorAll('.blog-row[data-tags]');
if (filterBtns.length && blogRows.length) {
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tag = btn.dataset.filter;
      blogRows.forEach(row => {
        const tags = row.dataset.tags.split(',');
        row.style.display = (tag === 'all' || tags.includes(tag)) ? 'grid' : 'none';
      });
    });
  });
}
