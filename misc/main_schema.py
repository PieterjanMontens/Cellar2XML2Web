#!/usr/bin/env python

from graphviz import Digraph
import pathlib

dot = Digraph("C2X2W_v2", format="png")

# Nodes
dot.node("CP", "Control Panel\n(HTML+JS)", shape="component")
dot.node("QA", "Query Agent\n(Python)", shape="box")
dot.node("SB", "Sitemap Builder\n(Python+XSLT)", shape="box")
dot.node("WB", "Web Builder\n(Python+Eleventy)", shape="box")
dot.node("WA", "Web Agent\n(Python)", shape="box")

dot.node("STAGE", "Staging HTML\n(/srv/staging)", shape="folder")
dot.node("PROD", "Production HTML\n(/srv/prod)", shape="folder")

dot.node("Kafka", "Kafka Broker", shape="cylinder")
dot.node("SR", "Schema Registry", shape="component")
dot.node("ZK", "ZooKeeper", shape="component")

# Data flow edges
dot.edge("CP", "Kafka", label="cmd.query_agent")
dot.edge("Kafka", "QA", label="cmd.query_agent")

dot.edge("QA", "Kafka", label="raw.sparql.out")
dot.edge("Kafka", "SB", label="raw.sparql.out")

dot.edge("SB", "Kafka", label="raw.sitemap.out")
dot.edge("Kafka", "WB", label="raw.sitemap.out")

dot.edge("WB", "STAGE", label="write\n_site files", style="bold")

# Web agent commands
dot.edge("Kafka", "WA", label="cmd.web_agent.deploy\ncmd.web_agent.clean")

# Web agent serving directories
dot.edge("WA", "STAGE", label="serve staging", style="bold")
dot.edge("WA", "PROD", label="promote\ncopy", style="bold")

# Control panel browsing links
dot.edge("CP", "STAGE", label="preview link", style="dotted")
dot.edge("CP", "PROD", label="prod link", style="dotted")

# Logs and heartbeats
for agent, hb in [("QA","hb_query_agent"),("SB","hb_sitemap_builder"),
                  ("WB","hb_web_builder"),("WA","hb_web_agent")]:
    dot.edge(agent, "Kafka", label=hb, style="dashed")

for agent in ["QA","SB","WB","WA","WA"]:
    dot.edge(agent, "Kafka", label="logs_app", style="dotted")

# Infra dependencies
dot.edge("Kafka", "SR", style="dashed")
dot.edge("Kafka", "ZK", style="dashed")

# Render output
file_path = pathlib.Path("./C2X2W_architecture_v2")
dot.render(str(file_path))
print(str(file_path) + ".png")
