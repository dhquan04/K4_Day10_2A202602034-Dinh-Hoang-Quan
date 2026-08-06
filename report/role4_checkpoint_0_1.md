# Báo cáo Role 4 — RAG & Agent

**Nhóm:** ChickenFarmer
**Vai trò:** RAG & Agent owner
**Phạm vi:** `src/retrieval/`, `data/embeddings/`
**Checkpoint:** CP0 và CP1

## Checkpoint 0 — Khởi động, contract & ingestion raw

### Mục tiêu phần việc

Xác định data contract giữa Cleaning và RAG, chốt cấu hình embedding/index, và chuẩn bị các truy vấn kiểm tra cho checkpoint tiếp theo. Checkpoint này chưa build Chroma collection hoặc chạy embedding chính thức.

### Input của RAG/index

Theo `LocalEmbeddingIndex._build_documents()` trong `src/retrieval/index.py`, cleaned DataFrame phải có các cột sau:

```text
paper_id
title
text_for_embedding
published
authors_joined
categories_joined
summary
abs_url
pdf_url
```

Trong đó, `text_for_embedding` là nội dung được vector hóa. Các trường còn lại được lưu làm metadata phục vụ semantic search, exact lookup và trả lời factual.

### Output của RAG/index

- ChromaDB collection chứa embeddings, document text và metadata.
- Embedding manifest JSON gồm backend, embedding model, collection name, persist path và danh sách documents.
- Search result gồm `paper_id`, `title`, score, content và metadata.
- Agent có thể semantic search hoặc exact lookup theo `paper_id`/exact title.

### Cấu hình đã chốt

| Hạng mục           | Giá trị                                  |
| -------------------- | ------------------------------------------ |
| Embedding model      | `sentence-transformers/all-MiniLM-L6-v2` |
| Retrieval`top_k`   | `4`                                      |
| Chroma persist path  | `data/chroma/`                           |
| Baseline collection  | `papers-baseline`                        |
| Corrupted collection | `papers-corrupted`                       |
| Repaired collection  | `papers-repaired`                        |

### Artifact embeddings theo trạng thái

| Trạng thái | Embedding manifest                                   |
| ------------ | ---------------------------------------------------- |
| Baseline     | `data/embeddings/papers_embeddings.json`           |
| Corrupted    | `data/embeddings/papers_embeddings_corrupted.json` |
| Repaired     | `data/embeddings/papers_embeddings_repaired.json`  |

Ba collection và manifest phải được tách biệt; corruption không được ghi đè dữ liệu baseline.

### Metadata tối thiểu trong Chroma

```text
paper_id, title, published, authors_joined, categories_joined,
summary, abs_url, pdf_url
```

### Agent và smoke test dự kiến

Agent sử dụng hai tools:

- `semantic_search_papers(query, top_k=4)`: tìm kiếm ngữ nghĩa trong local corpus.
- `lookup_paper(paper_id_or_title)`: tìm chính xác theo paper ID hoặc title.

Agent phải dùng tool trước khi trả lời câu hỏi factual và không trả lời vượt quá thông tin trong corpus. Ở checkpoint 2 sẽ dùng một `paper_id`/title thật để kiểm tra exact lookup, cùng 2–3 semantic queries về chủ đề, tác giả, ngày xuất bản hoặc category.

### Kết luận CP0

Đã xác định data contract, cấu hình embedding/index, metadata, naming convention và kế hoạch smoke test. Chưa có thao tác build embedding hoặc collection ở checkpoint này.

## Checkpoint 1 — Cleaning, data model & quality gates

### Mục tiêu phần việc

Xác minh cleaned dataset tương thích với `LocalEmbeddingIndex` trước khi build collection `papers-baseline` ở checkpoint 2.

### Contract cho `text_for_embedding`

Mỗi document cần có nội dung rõ nghĩa, không rỗng. Cấu trúc đề xuất:

```text
Title: <title>
Authors: <authors_joined>
Categories: <categories_joined>
Published: <published>
Summary: <summary>
```

Yêu cầu:

- Có title và summary thật.
- Không còn HTML, khoảng trắng dư thừa hoặc noise.
- Không lặp trường vô ích.
- Đủ nội dung để phân biệt các paper khi semantic retrieval.

### Checklist khi nhận clean artifact

| Hạng mục               | Điều kiện cần xác minh                                   |
| ------------------------ | ------------------------------------------------------------- |
| `paper_id`             | Không null, unique, ổn định từ raw đến index           |
| `title`                | Không null hoặc rỗng                                       |
| `summary`              | Không rỗng; nếu thiếu phải có quy tắc filter rõ ràng |
| `text_for_embedding`   | Không null/rỗng, có ý nghĩa khi đọc thử               |
| `published`            | Định dạng ngày nhất quán                                |
| `authors_joined`       | String, không phải list hoặc`NaN`                        |
| `categories_joined`    | String, không phải list hoặc`NaN`                        |
| `abs_url`, `pdf_url` | String an toàn; có thể rỗng nếu source không cung cấp  |
| `age_days`             | Có để phục vụ freshness monitoring                       |

### Công việc kiểm tra của role RAG

1. Mở clean CSV/JSON hoặc DataFrame do role Cleaning bàn giao.
2. Đối chiếu các cột bắt buộc với `_build_documents()` trong `src/retrieval/index.py`.
3. Kiểm tra `paper_id` không rỗng, không trùng; kiểm tra `title`, `summary` và `text_for_embedding` không rỗng.
4. Đọc thủ công 3–5 dòng `text_for_embedding` để kiểm tra title/summary đầy đủ, không noise hoặc lặp vô ích.
5. Kiểm tra metadata không chứa kiểu dữ liệu phức tạp, list hay `NaN` gây lỗi khi ghi Chroma.
6. Ghi lại số record clean; số này sẽ là số document dự kiến trong embedding manifest và collection baseline ở CP2.
7. Chọn một `paper_id`/exact title và 2–3 semantic queries từ dữ liệu thật cho smoke test CP2.
8. Báo lại role Cleaning mọi lỗi schema kèm cột, row hoặc ví dụ cụ thể; chỉ xác nhận handoff khi schema đạt contract.

### Trạng thái hiện tại và tiêu chí hoàn thành

Đã bổ sung pre-index guard `validate_index_input()` trong
`src/retrieval/index.py`. Guard được gọi ngay trước khi `LocalEmbeddingIndex.build()`
và sẽ chặn index nếu thiếu cột, DataFrame rỗng, `paper_id` rỗng/trùng, trường
bắt buộc rỗng/null, hoặc metadata không phải scalar. Các trường metadata tùy
chọn (`authors_joined`, `categories_joined`, `abs_url`, `pdf_url`) được phép là
chuỗi rỗng theo clean contract, nhưng không được là null.

Đã kiểm tra syntax và chạy smoke test cho guard: một row hợp lệ có metadata tùy
chọn rỗng được pass; `paper_id` trùng và `text_for_embedding` rỗng bị reject
đúng như mong đợi.

Hiện chưa có clean artifact thực tế trong `data/clean/`; lệnh
`python script/validate_clean.py` trả về `SKIP` đúng như thiết kế. Vì vậy phần
xác minh handoff trên dữ liệu thật vẫn chờ role Cleaning hoàn thành
`build_clean_dataframe()` và ghi clean CSV/JSON.

CP1 hoàn tất khi:

- [ ] Cleaned DataFrame có đủ schema cho index.
- [ ] `paper_id` unique; `text_for_embedding` và metadata hợp lệ.
- [ ] Có số lượng record clean đã xác minh.
- [ ] Có một exact-lookup query và 2–3 semantic queries từ dữ liệu thật.
- [ ] Các vấn đề data contract đã được phản hồi cho role Cleaning, nếu có.
- [ ] Chưa build hoặc ghi đè collection `papers-baseline`.

### Kết luận CP1

Role RAG sẽ chỉ chuyển sang build MiniLM embeddings và Chroma collection ở checkpoint 2 sau khi clean schema được xác minh. Việc này bảo đảm baseline index, evaluation và so sánh corrupted/repaired dùng dữ liệu có contract ổn định.
