(() => {
  const escape = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  let categories = new Map();
  const ready = fetch('data/heart_l3_categories.json?v=20261025').then(response => {
    if (!response.ok) throw new Error('L3 definitions could not be loaded.');
    return response.json();
  }).then(rows => {
    if (rows.length !== 55 || new Set(rows.map(row => row.L3_ID)).size !== 55) throw new Error('The L3 definition catalog is incomplete.');
    categories = new Map(rows.map(row => [row.L3_ID, row]));
  });
  function html(id) {
    const category = categories.get(id);
    if (!category) return '';
    return `<section class="detail-section l3-definition"><h3>L3 category definition</h3><p class="source-note">${escape(category.L3_ID)} · ${escape(category.L3_Name_en)} · <span lang="ko">${escape(category.L3_Name_ko)}</span></p><p>${escape(category.L3_Definition_en)}</p><p lang="ko">${escape(category.L3_Definition_ko)}</p><p class="source-note">Definitions revised 25 October 2026 · <a href="data/heart_l3_categories.csv" download>Download all 55 definitions as CSV</a> · <a href="data/heart_l3_categories.json" download>JSON</a></p></section>`;
  }
  window.HEARTL3 = {ready, html};
})();
