# Báo cáo Role 4 — Checkpoint 2

**Nhóm:** ChickenFarmer  
**Vai trò:** RAG & Agent owner  
**Phạm vi:** `src/retrieval/`, `data/embeddings/`  
**Checkpoint:** CP2 — Test set, RAG index & agent smoke test

## 1. Yêu cầu Role 4 tại CP2

Theo file phân công:

1. Build MiniLM embeddings và Chroma collection `papers-baseline` từ clean data.
2. Test semantic search và exact lookup với query có thể kiểm chứng.
3. Build agent, yêu cầu agent dùng tool trước khi trả lời factual và kiểm tra tool output.

## 2. Cách thực hiện

Entrypoint tái lập:

```powershell
$env:LLM_MODEL="gemini-3.6-flash"
python script/run_role4_cp2.py
```

Script đọc `data/clean/papers_clean.json`, validate input tại retrieval boundary,
build collection baseline, kiểm tra document count, lookup theo ID/title, chạy ba
semantic queries ngôn ngữ tự nhiên có ground-truth document ID, kiểm tra
deterministic QA, sau đó gọi agent và yêu cầu sử dụng lookup tool.

Chroma binary được persist local trong `data/chroma/` và không commit. Manifest
dùng path tương đối `data/chroma` để có thể load lại trên workspace khác.

## 3. Kết quả

| Hạng mục | Kết quả |
| --- | --- |
| Clean input | 24 documents |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Chroma collection | `papers-baseline` |
| Collection count | 24 |
| Manifest count | 24 |
| Exact lookup theo `paper_id` | PASS |
| Exact lookup theo title | PASS |
| Semantic search | PASS, 3/3 query ngôn ngữ tự nhiên trả source paper trong top-k |
| Deterministic factual QA | PASS |
| Agent tool usage | PASS, gọi `lookup_paper` và nhận tool output có nguồn |
| Load lại collection từ manifest khi offline | PASS |

Paper dùng cho exact lookup và agent smoke test:

```text
paper_id: 10.2118/234689-pa
title: SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented
       Framework for Oil and Gas Safety Report Generation
```

Agent trả lời tác giả dựa trên output của `lookup_paper`: Qianwen Cao, Chiyu
Zhang, Junxiong Ning và Gongru Li.

Ba semantic query có thể kiểm chứng:

1. `Which paper proposes a retrieval-augmented framework for oil and gas safety report generation?`
   → `10.2118/234689-pa`.
2. `Which paper uses multimodal agentic retrieval for diagnostic support of jawbone lesions?`
   → `10.1007/s10278-026-02086-9`.
3. `Which paper studies retrieval-augmented language models for cross-market equity time-series forecasting?`
   → `10.21203/rs.3.rs-10178277/v1`.

## 4. Artifacts

| Artifact | Đường dẫn |
| --- | --- |
| Baseline embedding manifest | `data/embeddings/papers_embeddings.json` |
| Chroma baseline collection | `data/chroma/` (local, ignored by Git) |
| Search/lookup/agent evidence | `data/results/agent_demo_answers.json` |
| Reproducible entrypoint | `script/run_role4_cp2.py` |

Evidence JSON không chứa API key. Nó ghi model/provider, source document ID,
retrieval results, agent answer, tên tool đã gọi và tool output dùng làm nguồn.

## 5. Vấn đề tích hợp và cách xử lý

### Gemini model cũ không còn dùng được

- **Triệu chứng:** Gemini trả `404 NOT_FOUND` cho `gemini-2.5-flash` với thông
  báo model không còn cấp cho user mới.
- **Xác minh:** Gemini Models API liệt kê `gemini-3.6-flash` là model hỗ trợ
  `generateContent` cho credential hiện tại.
- **Xử lý:** cập nhật default và `.env.example` sang `gemini-3.6-flash`; không
  sửa hoặc commit `.env` thật.
- **Kết quả:** agent smoke test gọi `lookup_paper` thành công.

### Model embedding cố truy cập mạng khi đã cache

- **Triệu chứng:** load lại index trong sandbox offline vẫn gửi HEAD request tới
  Hugging Face.
- **Xử lý:** ưu tiên `local_files_only=True`, chỉ fallback sang tải mạng khi model
  chưa có trong cache.
- **Kết quả:** manifest và collection load lại offline thành công, count 24.

## 6. Trạng thái CP2

Phần Role 4 đã hoàn tất và có artifact kiểm chứng. `data/eval/test_set.json`
đã được Role 5 tạo sau đó; baseline collection và manifest sẵn sàng để dùng cho
evaluation ở CP3.
