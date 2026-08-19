function passesFilter(title, { include = [], exclude = [] } = {}) {
  const value = String(title || '').toLocaleLowerCase();
  return include.some(term => value.includes(String(term).toLocaleLowerCase()))
    && !exclude.some(term => value.includes(String(term).toLocaleLowerCase()));
}

function filterJobs(jobs, config) {
  return jobs.filter(job => passesFilter(job.title, config));
}

module.exports = { passesFilter, filterJobs };
