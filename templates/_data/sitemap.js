/**
 * Reads sitemap.xml (written by Web-Builder) and converts it into
 * an array of JS objects so Nunjucks/Liquid templates can iterate.
 *
 * Returns e.g.
 * [
 *   {
 *     loc: 'http://data.europa.eu/eli/C/2025/3157/oj',
 *     title: '',
 *     num: '3157',
 *     issued: '2025-06-20',
 *     collection: 'http://publications.europa.eu/resource/authority/document-collection/OJ-C',
 *     docType: 'http://publications.europa.eu/resource/authority/resource-type/DEC'
 *   },
 *   ...
 * ]
 */
const fs = require('fs');
const { XMLParser } = require('fast-xml-parser');
const path = require('path');
const runDir  = process.env.RUN_DIR || process.cwd();

module.exports = () => {
  const xmlPath = path.join(runDir, 'sitemap.xml');

  if (!fs.existsSync(xmlPath)) {
    throw new Error(
      `[sitemap.js] sitemap.xml not found at ${xmlPath} — aborting build.`
    );
  }

  const xml = fs.readFileSync(xmlPath, 'utf8');
  const parser = new XMLParser({ ignoreAttributes:false });
  const data = parser.parse(xml);

  const urlset = data.urlset.url || [];

  if (urlset.length === 0) {
    throw new Error(
      "[sitemap.js] sitemap.xml parsed OK but contains no <url> entries."
    );
  }

  return urlset.map(u => ({
    loc:           u.loc,
    title:         u['akn4eu:docTitle']?.literal ?? '',
    num:           u['akn4eu:num'],
    issued:        u['dcterms:issued'],
    collection:    u['dcterms:isPartOf']['@_rdf:datatype']
                     ? u['dcterms:isPartOf']['#text']
                     : u['dcterms:isPartOf'],
    docType:       u['akn4eu:docType']['#text'] ?? u['akn4eu:docType']
  }));
};
