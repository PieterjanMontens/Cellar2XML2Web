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

module.exports = () => {
  const xmlPath = path.join(__dirname, '..', 'sitemap.xml');
  if (!fs.existsSync(xmlPath)) return [];

  const xml = fs.readFileSync(xmlPath, 'utf8');
  const parser = new XMLParser({ ignoreAttributes:false });
  const data = parser.parse(xml);

  const urlset = data.urlset.url || [];
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
