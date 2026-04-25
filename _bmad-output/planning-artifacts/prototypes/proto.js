(() => {
  const page = document.body.dataset.page || '';

  function startFakeProgress(containerId, total = 12, intervalMs = 800) {
    const el = document.getElementById(containerId);
    if (!el) return;
    let processed = 0;
    el.textContent = `Processed: ${processed} / ${total} • Status: Connecting • Errors: 0`;
    const id = setInterval(() => {
      processed = Math.min(total, processed + Math.ceil(Math.random() * 2));
      if (processed >= total) {
        el.textContent = `Processed: ${total} / ${total} • Status: Complete • Errors: 0`;
        clearInterval(id);
      } else {
        el.textContent = `Processed: ${processed} / ${total} • Status: Running • Errors: 0`;
      }
    }, intervalMs);
  }

  if (page === 'dashboard' || page === 'results') {
    // start a demo progress updater
    startFakeProgress('live-progress', 12, 600);
  }

  if (page === 'job') {
    const startBtn = document.getElementById('start-job');
    const ta = document.getElementById('urls');
    const err = document.getElementById('job-error');
    if (startBtn && ta) {
      startBtn.addEventListener('click', () => {
        const urls = ta.value.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
        const invalid = urls.filter(u => !/^https?:\/\/.+\..+/.test(u));
        if (invalid.length) {
          err.textContent = 'Invalid URLs detected. Example: https://example.com/product/1';
          err.style.display = 'block';
          return;
        }
        err.style.display = 'none';
        startBtn.textContent = 'Starting…';
        startBtn.disabled = true;
        setTimeout(() => { window.location.href = 'dashboard.html'; }, 700);
      });
    }
  }

  if (page === 'export') {
    document.querySelectorAll('button[data-export]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const kind = btn.dataset.export || 'txt';
        const orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Generating…';
        await new Promise(r => setTimeout(r, 800));
        const blob = new Blob([`Formulation Wiki export (${kind})\nGenerated at ${new Date().toISOString()}`], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `formulation-export.${kind === 'md' ? 'md' : kind === 'csv' ? 'csv' : 'zip'}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        btn.textContent = 'Done';
        setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 900);
      });
    });
  }

})();
