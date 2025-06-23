const { DateTime } = require('luxon');     // for pretty dates
const sitemap      = require('./_data/sitemap.js')();
const slugify      = s => s.toLowerCase()
                            .replace(/\W+/g,'-')
                            .replace(/(^-|-$)/g,'');

module.exports = eleventyConfig => {

  /* ---------- Collections ---------- */
  eleventyConfig.addCollection('maps', collectionApi => {
    // const first = collectionApi.getAll()[0];
    // const items = first ? first.data.sitemap : [];
    // const items = sitemap;
    const sitemap = require('./_data/sitemap.js')(); 

    // Build nested {issued -> collection -> docType -> [records]}
    //const tree = {};
    //for (const r of items) {
    //  (tree[r.issued]          ??= {});
    //  (tree[r.issued][r.collection]           ??= {});
    //  (tree[r.issued][r.collection][r.docType]??= []).push(r);
    //}
    //return tree;


      // Build: [{ issued, collection, docTypeMap }, ...]
      const out = [];
      for (const r of sitemap) {
        let issued      = r.issued;
        let collection  = r.collection;
        let docTypeMap  = out.find(o => o.issued === issued && o.collection === collection);

        if (!docTypeMap) {
          docTypeMap = { issued, collection, items: {} };
          out.push(docTypeMap);
        }
        (docTypeMap.items[r.docType] ??= []).push(r);
      }
      return out;   // <-- array; pagination-friendly
  });

  /* ---------- Filters ---------- */
  eleventyConfig.addFilter('prettyDate', d =>
    DateTime.fromISO(d).toFormat('dd LLL yyyy'));

  eleventyConfig.addFilter('slug', slugify);

  /* ---------- Passthrough ---------- */
  eleventyConfig.addPassthroughCopy({ './templates/assets': 'assets' });

  return {
    dir: {
        input: 'templates',
        output: '_site' },
    htmlTemplateEngine: 'njk',
    dataTemplateEngine: 'njk'
  };
};
