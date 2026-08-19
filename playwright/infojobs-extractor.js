const INFOJOBS_JOB_LINK_SELECTOR = [
  'a[href*="/oferta-trabajo/"]',
  'a[href*="/oferta/"]',
  'a[href*="/offer/"]',
  'a[href*="/of-"]',
].join(', ');

function mapInfoJobsCard(card, query, scrapedAt = new Date().toISOString()) {
  const source = card || {};
  return {
    title: source.title || source.name || '',
    company: source.company || source.companyName || '',
    location: source.location || source.city || '',
    link: source.link || source.url || null,
    description: source.description || source.summary || null,
    companyUrl: source.companyUrl || null,
    applicationUrl: source.applicationUrl || null,
    searchQuery: query,
    scrapedAt,
  };
}

async function extractInfoJobsCards(page, { maxJobsPerSearch, query }) {
  const links = page.locator(INFOJOBS_JOB_LINK_SELECTOR);
  const count = Math.min(await links.count(), maxJobsPerSearch);
  return links.evaluateAll((elements, details) => {
    const firstText = (element, selectors) => {
      for (const selector of selectors) {
        const value = element.querySelector(selector)?.textContent;
        if (value && value.trim()) return value;
      }
      return '';
    };
    const firstAttribute = (element, selectors, attribute) => {
      for (const selector of selectors) {
        const value = element.querySelector(selector)?.getAttribute(attribute);
        if (value) return value;
      }
      return null;
    };
    const seen = new Set();
    return elements.slice(0, details.count).map(anchor => {
      const card = anchor.closest('article, li, .ij-OfferCardContent-info, [data-testid*="offer"], [class*="offer"], [class*="job"]')
        || anchor.parentElement || anchor;
      const href = anchor.href || anchor.getAttribute('href');
      if (!href || seen.has(href)) return null;
      seen.add(href);
      const infoItems = [...card.querySelectorAll('.ij-OfferCardContent-description-list-item')]
        .map(item => item.textContent.trim())
        .filter(Boolean);
      const workMode = infoItems.find(value => /^(h[ií]brido|remoto|presencial)$/i.test(value)) || null;
      const contractType = infoItems.find(value => /^(contrato|jornada|temporal|indefinido|aut[oó]nomo|pr[aá]cticas)/i.test(value)) || null;
      return {
        title: firstText(card, ['.ij-OfferCardContent-description-title', 'h1', 'h2', 'h3', '[class*="title"]']) || anchor.textContent || '',
        company: firstText(card, ['.ij-OfferCardContent-description-subtitle', '[class*="company"]', '[data-testid*="company"]']),
        location: firstText(card, ['.ij-OfferCardContent-description-list-item:first-child', '[class*="location"]', '[class*="city"]', '[data-testid*="location"]']),
        link: href,
        description: firstText(card, ['.ij-OfferCardContent-description-description', '[class*="description"]', '[class*="summary"]', '[class*="snippet"]']) || null,
        remote: workMode && /^remoto$/i.test(workMode) ? true : null,
        hybrid: workMode && /^h[ií]brido$/i.test(workMode) ? true : null,
        contractType,
        companyUrl: firstAttribute(card, ['a[href*="/empresa/"]', 'a[href*="/company/"]'], 'href'),
        applicationUrl: firstAttribute(card, ['a[href*="/inscripcion/"]', 'a[href*="/apply/"]'], 'href'),
        searchQuery: details.query,
        scrapedAt: new Date().toISOString(),
      };
    }).filter(Boolean);
  }, { count, query });
}

module.exports = {
  INFOJOBS_JOB_LINK_SELECTOR,
  mapInfoJobsCard,
  extractInfoJobsCards,
  extractCards: extractInfoJobsCards,
};
