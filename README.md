# 🚀 JSON to JMX - Automated API Performance Optimization System

> An intelligent, end-to-end automated workflow for discovering APIs, testing their performance, and optimizing them with human-in-the-loop feedback.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)



## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [📂 Repository Structure](#repository-structure)
- [📊 Workflow Diagram](#-workflow-diagram)
- [🚀 How the System Works](#how-the-system-works)
- [💻 Usage Guide](#-usage-guide)
- [📊 Understanding Output Files](#-understanding-output-files)
- [🤝 Contributing](#-contributing)



## 🎯 Overview

**json_to_jmx** is an end-to-end automated workflow system that bridges the gap between API discovery and performance testing. It enables both technical and non-technical users to:

1. ✅ **Automatically scan a target URL** and extract all available APIs
2. ✅ **Generate a Postman collection** from discovered API endpoints
3. ✅ **Convert Postman (.json) to JMeter (.jmx)** using a custom Python converter
4. ✅ **Execute full JMeter performance tests** inside Docker (no installation needed)
5. ✅ **Collect comprehensive results** (CSV + HTML dashboards)
6. ✅ **Enable human-in-loop verification** of API performance
7. ✅ **Support optimization cycles** - rerun with different parameters until satisfied



---
## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Auto-Extract APIs** | Crawls target URL and discovers all API endpoints |
| 📦 **Postman Collection Generation** | Auto-generates Postman-compatible JSON collections |
| 🔄 **Smart Conversion** | Converts Postman → JMX with `convert_postman_to_jmx.py` |
| 🐳 **Docker-Integrated JMeter** | Runs JMeter in Docker (no manual setup required) |
| 📈 **Rich Reports** | Generates HTML + CSV performance dashboards |
| 🔄 **Human-in-Loop Optimization** | Interactive workflow for performance tuning |
| 🤖 **MCP Server Integration** | Exposes tools for Claude Desktop & AI agents `postman_to_jmx` and `run_jmeter` |
| 📊 **Real-Time Monitoring** | Track test progress with live dashboards |
| 🎯 **Rerun Capability** | Easy test reruns with different configurations |


---
## Repository Structure
```
|--- server.py                        # MCP server exposing tools
|--- convert_postman_to_jmx.py        # Postman -> JMX converter
|--- mcp.json                         # MCP config file
|--- README.md 
```
---


## How the system works?

### Step 1 : Extract APIs from the URL
Your agent crawls the target URL and find all API endpoints

### Step 2: Generate Postman collection
All detected APIs are stored in a Postman-style JSON file.

### Step 3: Convert Postman collection to JMX
This uses the included Python script:
```python 
converter = PostmanToJMeterConverter()
converter.convert("collection.json", "output.jmx")
```

### Step 4: Run Jmeter
The MCP tool `run_jmeter` runs:
```bash
docker run --rm -v $PWD:/jmeter justb4/jmeter:latest -n -t output.jmx -l results.csv
```

### Step 5. Human-in-loop approval
You check the performance, if not satisfied, ask the agent to optimize and re-run

---

## Usage guide (MCP Tool Integration)
Start the server:
```bash
python server.py
```
The project exposes two MCP tools so any MCP-capable client (claude desktop etc.) can orchestrate the full performance-test loop.

---
## Understanding Output Files
| File  | Purpose|
|-------|--------|
|`output.jmx`|Jmeter Test Plan|
|`results.csv`|Raw performance results|
|`index.html`|Interactive performance dashboard|

## 🤝 Contributing
Feel free to open issues or contribute improvements


# Happy Testing! 