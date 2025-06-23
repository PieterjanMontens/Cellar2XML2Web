<xsl:stylesheet version="1.0"
    xmlns:s="http://www.w3.org/2005/sparql-results#"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:akn4eu="http://imfc.europa.eu/akn4eu"
    exclude-result-prefixes="s">

  <xsl:param name="issuedDate" />
  <xsl:param name="lastmodDate" />

  <xsl:output method="xml" indent="yes"/>

  <!-- Define key for grouping by 'eli' -->
  <xsl:key name="by-eli" match="s:result" use="s:binding[@name='eli']/s:literal"/>

  <xsl:template match="/s:sparql">
    <urlset>
      <xsl:for-each select="s:results/s:result[
        generate-id() = generate-id(key('by-eli', s:binding[@name='eli']/s:literal)[1])
      ]">
        <xsl:call-template name="url-entry"/>
      </xsl:for-each>
    </urlset>
  </xsl:template>

  <!-- Template to build each <url> -->
  <xsl:template name="url-entry">
    <xsl:variable name="eli" select="s:binding[@name='eli']/s:literal"/>
    <xsl:variable name="this-group" select="key('by-eli', $eli)"/>

    <url>
      <xsl:if test="$eli">
        <loc><xsl:value-of select="$eli"/></loc>
      </xsl:if>

      <lastmod><xsl:value-of select="$lastmodDate"/></lastmod>
      <changefreq>monthly</changefreq>
      <priority>1</priority>

      <xsl:if test="s:binding[@name='oj_collection']/s:uri">
        <dcterms:isPartOf rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">
          <xsl:value-of select="s:binding[@name='oj_collection']/s:uri"/>
        </dcterms:isPartOf>
      </xsl:if>

      <xsl:if test="s:binding[@name='celex']/s:literal">
        <dcterms:identifier>
          <xsl:value-of select="s:binding[@name='celex']/s:literal"/>
        </dcterms:identifier>
      </xsl:if>

      <!-- dcterms:creator: all unique from group -->
      <xsl:for-each select="$this-group/s:binding[@name='creating_agents']/s:uri">
        <xsl:variable name="uri" select="."/>
        <xsl:if test="not(preceding::s:binding[@name='creating_agents']/s:uri = $uri)">
          <dcterms:creator rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">
            <xsl:value-of select="$uri"/>
          </dcterms:creator>
        </xsl:if>
      </xsl:for-each>

      <xsl:if test="$issuedDate">
        <dcterms:issued><xsl:value-of select="$issuedDate"/></dcterms:issued>
      </xsl:if>

      <xsl:if test="s:binding[@name='oj_number']/s:literal">
        <akn4eu:num>
          <xsl:value-of select="s:binding[@name='oj_number']/s:literal"/>
        </akn4eu:num>
      </xsl:if>

      <xsl:if test="s:binding[@name='resource_type']/s:uri">
        <akn4eu:docType rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">
          <xsl:value-of select="s:binding[@name='resource_type']/s:uri"/>
        </akn4eu:docType>
      </xsl:if>

      <xsl:variable name="docTitleEn" select="$this-group/s:binding[@name='title']/s:literal[@xml:lang='en']"/>
      <xsl:choose>
        <xsl:when test="$docTitleEn">
          <akn4eu:docTitle>
            <xsl:copy-of select="$docTitleEn[1]"/>
          </akn4eu:docTitle>
        </xsl:when>
        <xsl:otherwise>
          <xsl:if test="$this-group/s:binding[@name='title']/s:literal">
            <akn4eu:docTitle>
              <xsl:copy-of select="$this-group/s:binding[@name='title']/s:literal[1]"/>
            </akn4eu:docTitle>
          </xsl:if>
        </xsl:otherwise>
      </xsl:choose>
    </url>
  </xsl:template>
</xsl:stylesheet>
