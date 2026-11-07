// Componentes interativos comuns às lições do AI Course.
// Quiz:      <div class="quiz" data-certa="1" data-explicacao="..."><p class="pergunta">...</p><div class="opcoes"><button>A</button><button>B</button></div></div>
//            data-certa é o índice (a partir de 0) da opção correta.
// Código:    <div class="codigo"><pre><code>...</code></pre></div>  (ganha botão "Copiar")
// Diagramas: <pre class="mermaid">graph LR; A-->B</pre>
(() => {
  // Barra de progresso de leitura
  const barra = document.querySelector('.progresso span');
  if (barra) {
    const atualizar = () => {
      const h = document.documentElement.scrollHeight - innerHeight;
      barra.style.width = (h > 0 ? (100 * scrollY / h) : 100) + '%';
    };
    addEventListener('scroll', atualizar, { passive: true });
    atualizar();
  }

  // Quizzes
  document.querySelectorAll('.quiz').forEach(q => {
    const certa = Number(q.dataset.certa);
    const botoes = [...q.querySelectorAll('.opcoes button')];
    const exp = document.createElement('p');
    exp.className = 'explicacao';
    exp.hidden = true;
    const tentar = document.createElement('button');
    tentar.className = 'tentar';
    tentar.type = 'button';
    tentar.textContent = 'Tentar de novo';
    tentar.hidden = true;
    q.append(exp, tentar);
    botoes.forEach((b, i) => {
      b.type = 'button';
      b.addEventListener('click', () => {
        botoes.forEach(x => (x.disabled = true));
        botoes[certa].classList.add('certa');
        if (i !== certa) b.classList.add('errada');
        exp.textContent = (i === certa ? 'Certo. ' : 'Não é bem assim. ') + (q.dataset.explicacao || '');
        exp.hidden = false;
        tentar.hidden = false;
      });
    });
    tentar.addEventListener('click', () => {
      botoes.forEach(x => { x.disabled = false; x.classList.remove('certa', 'errada'); });
      exp.hidden = true;
      tentar.hidden = true;
    });
  });

  // Botão copiar nos blocos de código
  document.querySelectorAll('.codigo').forEach(c => {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = 'Copiar';
    b.addEventListener('click', async () => {
      const texto = c.querySelector('code').innerText;
      try { await navigator.clipboard.writeText(texto); b.textContent = 'Copiado'; }
      catch (e) {
        const r = document.createRange(); r.selectNodeContents(c.querySelector('code'));
        const s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Selecionado';
      }
      setTimeout(() => (b.textContent = 'Copiar'), 1500);
    });
    c.append(b);
  });

  // Diagramas Mermaid (carregados só se a página tiver algum)
  if (document.querySelector('pre.mermaid')) {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js';
    s.onload = () => {
      const escuro = matchMedia('(prefers-color-scheme: dark)').matches;
      window.mermaid.initialize({ startOnLoad: false, theme: escuro ? 'dark' : 'neutral', fontFamily: 'IBM Plex Sans, sans-serif' });
      window.mermaid.run({ querySelector: 'pre.mermaid' });
    };
    document.head.append(s);
  }

  // Marcar a lição como lida (guardado só neste browser; o currículo lê a mesma chave)
  const fim = document.querySelector('[data-marcar-lida]');
  if (fim) {
    const id = fim.dataset.marcarLida;
    let p = {};
    try { p = JSON.parse(localStorage.getItem('ai-expert-progress') || '{}'); } catch (e) {}
    const render = () => (fim.textContent = p[id] ? 'Lição concluída ✓' : 'Marcar lição como concluída');
    fim.addEventListener('click', () => {
      p[id] = !p[id];
      try { localStorage.setItem('ai-expert-progress', JSON.stringify(p)); } catch (e) {}
      render();
    });
    render();
  }
})();
