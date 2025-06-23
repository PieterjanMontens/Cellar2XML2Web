const { DateTime } = require('luxon');     // for pretty dates
const slugify      = s => s.toLowerCase()
                            .replace(/\W+/g,'-')
                            .replace(/(^-|-$)/g,'');

module.exports = eleventyConfig => {

  /* ---------- Collections ---------- */
  eleventyConfig.addCollection('maps', collectionApi => {
    const items = collectionApi.globalData.sitemap;

    // Build nested {issued -> collection -> docType -> [records]}
    const tree = {};
    for (const r of items) {
      (tree[r.issued]          ??= {});
      (tree[r.issued][r.collection]           ??= {});
      (tree[r.issued][r.collection][r.docType]??= []).push(r);
    }
    return tree;
  });

  /* ---------- Filters ---------- */
  eleventyConfig.addFilter('prettyDate', d =>
    DateTime.fromISO(d).toFormat('dd LLL yyyy'));

  /* ---------- Passthrough ---------- */
  eleventyConfig.addPassthroughCopy({ './templates/assets': 'assets' });

  return {
    dir: { input: 'templates', output: '_site' },
    htmlTemplateEngine: 'njk',
    dataTemplateEngine: 'njk'
  };
};
