<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:sm="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:lg="http://legalgraph.eu/ns/1.0"
    exclude-result-prefixes="lg">
  <xsl:mode streamable="yes"/>
  <xsl:output method="xml" indent="yes"/>

  <xsl:template match="/">
    <sm:urlset>
      <xsl:apply-templates select="//result"/>
    </sm:urlset>
  </xsl:template>

  <xsl:template match="result">
    <sm:url>
      <sm:loc><xsl:value-of select="str"/></sm:loc>
      <lg:oj_collection><xsl:value-of select="oj_collection"/></lg:oj_collection>
      <lg:resource_type><xsl:value-of select="resource_type"/></lg:resource_type>
      <lg:creating_agents><xsl:value-of select="creating_agents"/></lg:creating_agents>
      <xsl:if test="title"><sm:title><xsl:value-of select="title"/></sm:title></xsl:if>
    </sm:url>
  </xsl:template>
</xsl:stylesheet>
