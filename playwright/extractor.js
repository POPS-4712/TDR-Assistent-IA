const JOB_CARD_SELECTOR = 'li[data-occludable-job-id], ul.jobs-search__results-list li, .jobs-search__results-list li, .base-search-card';

async function extractCards(page, { maxJobsPerSearch, query }) {
  const cards = page.locator(`${JOB_CARD_SELECTOR}:has(a[href*="/jobs/view/"])`);
  const count = Math.min(await cards.count(), maxJobsPerSearch);
  return cards.evaluateAll((elements, details) => {
    const firstText = (element, selector) => element.querySelector(selector)?.textContent || '';
    const firstAttribute = (element, selector, attribute) =>
      element.querySelector(selector)?.getAttribute(attribute) || null;
    return elements.slice(0, details.count).map(card => ({
      title: firstText(card, '.job-card-list__title, .base-search-card__title, strong, a[href*="/jobs/view/"]'),
      company: firstText(card, '.artdeco-entity-lockup__subtitle, .base-search-card__subtitle'),
      location: firstText(card, '.artdeco-entity-lockup__caption, .job-search-card__location, .base-search-card__metadata'),
      link: firstAttribute(card, 'a[href*="/jobs/view/"]', 'href'),
      description: firstText(card, '.job-search-card__snippet, .base-search-card__snippet, [data-test-job-card-description]') || null,
      companyUrl: firstAttribute(card, 'a[href*="/company/"]', 'href'),
      applicationUrl: firstAttribute(card, 'a[href*="/apply/"], a[aria-label*="Apply"], a[aria-label*="Solicitar"]', 'href'),
      searchQuery: details.query,
      scrapedAt: new Date().toISOString(),
    }));
  }, { count, query });
}

module.exports = { JOB_CARD_SELECTOR, extractCards };
