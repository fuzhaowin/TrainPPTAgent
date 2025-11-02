# personaldb 嵌入模型与向量库配置指南

本文档说明如何在 `personaldb` 服务中配置与使用不同的嵌入模型提供商，以及相关的环境变量与运行示例。

## 支持的嵌入提供商

当前 `EmbeddingModel` 已支持以下提供商（通过 `EMBEDDING_PROVIDER` 选择）：

- aliyun：阿里云 DashScope 兼容 OpenAI 接口
  - 环境变量：`ALI_API_KEY`
- doubao：火山引擎豆包（ARK）兼容 OpenAI 接口
  - 环境变量：`DOUBAO_API_KEY`
- vllm：vLLM 服务（OpenAI 兼容协议）
  - 环境变量：`VLLM_BASE_URL`，`VLLM_API_KEY`（可选）
- xinference：Xinference 服务（OpenAI 兼容协议）
  - 环境变量：`XINFERENCE_BASE_URL`，`XINFERENCE_API_KEY`（可选）
- ollama：Ollama 原生 `/api/embeddings` 接口
  - 环境变量：`OLLAMA_BASE_URL`（默认 `http://127.0.0.1:11434`）
- openai：OpenAI 官方接口
  - 环境变量：`OPENAI_API_KEY`

## 必填通用环境变量

- `EMBEDDING_PROVIDER`：选择上面提供商之一（如 `openai`、`doubao`、`ollama` 等）
- `EMBEDDING_MODEL`：具体嵌入模型名称
  - 示例：
    - OpenAI：`text-embedding-3-large` 或 `text-embedding-3-small`
    - Doubao：`ep-embedding-...`（参考火山引擎控制台）
    - Aliyun：`text-embedding-v1`
    - vLLM/Xinference：按服务暴露的模型名
    - Ollama：如 `mxbai-embed-large`、`nomic-embed-text` 等
- `EMBEDDING_DIM`：可选，设置维度（部分提供商可忽略或由模型默认值决定）

## 向量库配置

`ChromaDB` 用于管理向量的插入、查询与集合管理：

- 环境变量（可选）：
  - `CHROMA_PERSIST_DIR`：持久化目录（默认 `./chromadb_storage`）
  - `CHROMA_HOST` 与 `CHROMA_PORT`：如使用 server 模式
- 主要方法：
  - `create_or_get_collection(collection_name)`
  - `insert_file_vectors(collection, doc_id, texts, metadatas)`
  - `query2collection(collection, query_text, top_k)`
  - `delete_collection(collection_name)`
  - `delete_file_vectors(collection_name, doc_id)`

## 配置示例（.env）

以 OpenAI 为例：

```
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
OPENAI_API_KEY=sk-xxxx
CHROMA_PERSIST_DIR=./chromadb_storage
```

以 Doubao 为例：

```
EMBEDDING_PROVIDER=doubao
EMBEDDING_MODEL=ep-embedding-xxxxxxxx
DOUBAO_API_KEY=xxxxx
```

以 Ollama 为例：

```
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=mxbai-embed-large
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

更多提供商的示例请参考项目根目录 `env_template.txt` 与 `backend/personaldb/env_template`。

## API 与流程概览

`personaldb/main.py` 暴露的关键接口：

- `POST /upload/`：上传本地文件或提供 URL，完成解析、分块与向量化，并写入 ChromaDB
- `POST /search`：根据查询文本在个人知识库中进行向量检索（支持混合检索）
- `GET /files/{user_id}`：列出指定用户的文件

内部流程：

1. `process_file_sync`/`process_and_vectorize_local_file` 解析文档并生成 Markdown/文本分块
2. 通过 `EmbeddingModel` 生成向量（依据 `EMBEDDING_PROVIDER` 与 `EMBEDDING_MODEL`）
3. 使用 `ChromaDB` 写入集合（`collection_name` 通常按用户或业务分组）

## 快速验证

- 运行 `personaldb` 服务后，使用 `curl` 进行搜索：

```
curl -X POST http://127.0.0.1:9100/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","query":"公司季度营收", "top_k":5}'
```

- 上传并向量化：

```
curl -X POST http://127.0.0.1:9100/upload/ \
  -F "user_id=demo" \
  -F "file=@/path/to/file.pdf"
```

返回结果中包含处理状态与向量化信息（如集合名、分块数量等）。

## 常见问题

- 报错 `不支持的EMBEDDING_PROVIDER`：检查 `EMBEDDING_PROVIDER` 是否拼写正确且在支持列表中
- OpenAI 401/403：确认 `OPENAI_API_KEY` 有效，未过期，且未触发速率限制
- Ollama 无法连接：确认本地 `ollama` 服务已启动，且端口与 `OLLAMA_BASE_URL` 一致
- vLLM/Xinference 接口错误：检查 `BASE_URL` 是否包含 `/v1` 路径，确保兼容 OpenAI 协议

## 参考文件

- `backend/personaldb/embedding_utils.py`
- `backend/personaldb/main.py`
- `backend/personaldb/env_template`
- 项目根目录 `env_template.txt`