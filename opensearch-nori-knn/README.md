# OpenSearch + Nori + k-NN Dev Stack

This directory provides a Docker-based development stack for running OpenSearch 2.15.0 with the Korean Nori analyzer, custom user dictionaries, and k-NN / neural search support. It mirrors the workflow we use for legal-domain experiments in this monorepo.

## Contents

```
opensearch-nori-knn/
├─ docker-compose.yml
├─ opensearch/
│  ├─ Dockerfile
│  ├─ opensearch.yml
│  └─ userdict_ko.txt
└─ dashboards/
   └─ opensearch_dashboards.yml
```

- **docker-compose.yml** – spins up a single OpenSearch node (analysis-nori preinstalled) and an OpenSearch Dashboards instance with security disabled for local development.
- **opensearch/Dockerfile** – installs the `analysis-nori` plugin on top of the official OpenSearch image. k-NN ships with the base distribution.
- **opensearch/opensearch.yml** – development configuration that disables the security plugin and binds to `0.0.0.0`.
- **opensearch/userdict_ko.txt** – sample custom dictionary entries for legal abbreviations and domain-specific tokens.
- **dashboards/opensearch_dashboards.yml** – disables the security dashboards plugin and points the UI at the local OpenSearch node.

## Usage

1. Build and start the stack:
   ```bash
   docker compose up -d
   ```
2. Verify the cluster:
   ```bash
   curl http://localhost:9200
   docker exec -it opensearch bash -lc "bin/opensearch-plugin list"
   ```
3. Create a k-NN enabled index with the Nori analyzer. Update the embedding `dimension` to match your model output:
   ```bash
   curl -X PUT "http://localhost:9200/legal-texts" \
     -H "Content-Type: application/json" \
     -d @- <<'JSON'
   {
     "settings": {
       "index.knn": true,
       "analysis": {
         "tokenizer": {
           "korean_nori": {
             "type": "nori_tokenizer",
             "decompound_mode": "mixed",
             "user_dictionary": "userdict_ko.txt"
           }
         },
         "analyzer": {
           "korean_legal": {
             "type": "custom",
             "tokenizer": "korean_nori",
             "filter": [
               "lowercase",
               "nori_readingform",
               "nori_part_of_speech"
             ]
           }
         }
       }
     },
     "mappings": {
       "properties": {
         "doc_id": { "type": "keyword" },
         "law_no": { "type": "keyword" },
         "case_name": { "type": "text", "analyzer": "korean_legal" },
         "body": { "type": "text", "analyzer": "korean_legal" },
         "embedding": {
           "type": "knn_vector",
           "dimension": 768,
           "method": {
             "name": "hnsw",
             "space_type": "cosinesimil",
             "engine": "faiss"
           }
         },
         "date": { "type": "date" }
       }
     }
   }
   JSON
   ```
4. Ingest documents by embedding them offline (e.g., Ko-Sentence-BERT) and POSTing them to the `embedding` field.
5. Run hybrid queries that mix BM25 and vector similarity using the [`hybrid` query](https://docs.opensearch.org/latest/query-dsl/compound/hybrid/).

> **Important:** Keep the security plugin enabled and configure TLS/users for any non-development environment.

## Extending the Setup

- Swap `faiss` for `nmslib` in the `knn_vector` mapping when running purely on CPU.
- Expand `userdict_ko.txt` with additional abbreviations (e.g., `형소법`, `민소법`, `대법원`) to stabilize tokenization.
- To run neural search entirely server-side, explore the [Neural Search tutorial](https://docs.opensearch.org/latest/tutorials/vector-search/neural-search-tutorial/).
