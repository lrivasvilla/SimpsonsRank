function attachGridSearch(opts){
  const {
    inputId,
    gridId,
    pagerSelector,
    searchUrl,
    type,
    renderCardHtml,
    debounceMs = 250
  } = opts;

  const input = document.getElementById(inputId);
  const grid = document.getElementById(gridId);
  const pager = pagerSelector ? document.querySelector(pagerSelector) : null;
  if (!input || !grid) return;

  function esc(str){
    return (str ?? "").toString()
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;")
      .replaceAll("'","&#039;");
  }

  let timer = null;

  async function remoteSearch(q){
    const url = `${searchUrl}?type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}`;
    const res = await fetch(url);
    const data = await res.json().catch(() => ({results: []}));
    return data.results || [];
  }

  function render(items){
    grid.innerHTML = "";
    if (!items.length){
      grid.innerHTML = `<p class="muted">Sin resultados</p>`;
      return;
    }
    items.forEach(it => {
      const el = document.createElement("article");
      el.className = "card card-trigger";
      el.setAttribute("role","button");
      el.setAttribute("tabindex","0");
      el.innerHTML = renderCardHtml(it, esc);
      grid.appendChild(el);
    });
  }

  async function doSearch(){
    const q = (input.value || "").trim();
    if (!q){
      if (pager) pager.style.display = "";
      window.location.href = window.location.pathname;
      return;
    }
    if (pager) pager.style.display = "none";
    const items = await remoteSearch(q);
    render(items);
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(doSearch, debounceMs);
  });
}