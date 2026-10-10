/* Verified access alternatives only; bibliographic records remain unchanged. */
(function () {
  const replacements = Object.freeze({
    'https://arxiv.org/abs/2502.14143': 'https://arxiv.org/pdf/2502.14143',
    'https://arxiv.org/abs/2410.23472': 'https://arxiv.org/pdf/2410.23472',
    'https://doi.org/10.48550/arXiv.1511.03246': 'https://arxiv.org/pdf/1511.03246',
    'https://arxiv.org/abs/2407.01294': 'https://arxiv.org/pdf/2407.01294',
    'https://arxiv.org/abs/2406.13843': 'https://arxiv.org/pdf/2406.13843',
    'https://arxiv.org/abs/2503.05731': 'https://arxiv.org/pdf/2503.05731',
    'https://icml.cc/virtual/2025/51008': 'https://arxiv.org/pdf/2402.04247',
    'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5030173': 'https://arxiv.org/pdf/2412.07780'
  });
  function preferEvidencePDF(card) {
    return {...card, Evidence_URL: replacements[card.Evidence_URL] || card.Evidence_URL,
      ...(Array.isArray(card.Evidence_References) ? {Evidence_References: card.Evidence_References.map(ref =>
        ({...ref, url: replacements[ref.url] || ref.url}))} : {})};
  }
  if (typeof module !== 'undefined') module.exports = {replacements, preferEvidencePDF};
  if (typeof window !== 'undefined') window.preferEvidencePDF = preferEvidencePDF;
})();
