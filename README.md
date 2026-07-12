# 🧠 Jarvis OS: Local-First AI Knowledge Engine

![Status: Alpha](https://img.shields.io/badge/Status-Alpha%20(v0.3)-blue)
![Architecture: Local](https://img.shields.io/badge/Architecture-Local_First-success)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

**Jarvis OS** is not just another news aggregator. It is a local-first, AI-driven personal operating system that reads the internet, mathematically clusters information (Semantic Clustering), stores it in long-term memory (ChromaDB), and generates intelligent daily briefings straight into your **Obsidian Vault**.

No API Keys. No cloud dependencies. Zero data sold to third parties. Everything runs entirely on your local machine.

---

## ✨ The "Why" (Solving the RAG Provenance Problem)

Most Retrieval-Augmented Generation (RAG) systems turn data into a "text soup". When you ask an AI where a fact came from, it often hallucinates the source. 

Jarvis solves the **Provenance Problem** by forcing a flat vector database (ChromaDB) to act relationally:
1. 🧲 **Semantic Deduplication**: We don't process 10 articles about the exact same topic. We cluster them using `cosine_similarity` and calculate the mathematical centroid (`np.mean`) of the event.
2. 🔗 **Relational Vector Tracing**: Every generated event gets a unique `cluster_id`. The raw articles are saved separately but stamped with the exact same ID. If Jarvis makes a claim, it can instantly fetch the exact URLs that formed that specific memory.
3. 🗂️ **Topic-Aware Pipeline**: We eliminate the "Lost in the Middle" LLM context-window truncation by strictly partitioning the memory processing by categories (Financial, Tech, Health, Geopolitics).

---

## 🏗️ System Architecture

```text
[EXTERNAL]                      [JARVIS OS - CORE ARCHITECTURE]                [OUTPUT]

(1) RSS Feeds -----------------> |  Ingestion Layer  |
                                 |  (feedparser)     |
                                 +---------+---------+
                                           v
                                 +-------------------+
(2) NLP & Math ----------------> | Processing Layer  | ---> [Entity Extraction]
                                 | (SentenceTransformers, spaCy)
                                 +---------+---------+
                                           v
(3) Persistent RAG Memory <====> |   Memory Layer    | <==> [ ChromaDB ]
                                 | (Relational UUIDs)|
                                 +---------+---------+
                                           v
(4) LLM Synthesis <============> |Intelligence Layer | <==> [ Ollama / Llama 3 ]
                                 | (Topic-Aware)     |
                                 +---------+---------+
                                           v
(5) Knowledge Management ------> |  Interface Layer  | =======> [ Obsidian Vault ]

🚀 Tech Stack
Brain (LLM): Ollama (running Llama 3 locally)

Embeddings: sentence-transformers (all-MiniLM-L6-v2) for blazing-fast CPU vectorization.

Vector Database: ChromaDB (Persistent local storage)

NLP & Entities: spaCy (en_core_web_sm)

Math & Clustering: scikit-learn, NumPy

🗺️ Project Roadmap
Jarvis is being built in distinct Micro-Milestones, adding intelligence layers progressively:

[x] v0.1: Ingestion & Output - Fail-safe RSS fetching and Markdown formatting.

[x] v0.2: The Smart Engine - Semantic Clustering, mathematical deduplication, and entity extraction.

[x] v0.3: The Brain - ChromaDB integration, JSON backups, and Relational UUID mapping.

[ ] v0.4: Advanced Analytics - The Impact_Score equation (Mathematical Panic Button).

[ ] v0.5: Interfaces - Local dashboard, historical RAG search engine, and Knowledge Graphs.

[ ] v0.6: Plugin Marketplace - Scalable modular fetchers for Reddit, YouTube, and arXiv.

[ ] v1.0: Voice & Wake Word - Integration with openWakeWord and TTS for hands-free operation.

🤝 Contributing
Are you passionate about Local AI, Data Engineering, or Hybrid RAG systems? Pull Requests (PRs) optimizing our clustering logic, adding new LLM wrappers, or building data plugins are highly encouraged!
