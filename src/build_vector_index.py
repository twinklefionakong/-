import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


CHUNKS_PATH = Path("data/chunks/chunks.jsonl")
OUTPUT_DIR = Path("indexes/vector")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_PATH = OUTPUT_DIR / "embeddings.npy"
METADATA_PATH = OUTPUT_DIR / "metadata.jsonl"


records = []

with CHUNKS_PATH.open(encoding="utf-8") as input_file:
    for line in input_file:
        records.append(json.loads(line))

texts = []


def record_signature(record):
    return (
        record["company"],
        record["report_period"],
        record["section"],
        record["content_type"],
        record["content"],
    )


old_vectors = {}

if EMBEDDINGS_PATH.exists() and METADATA_PATH.exists():
    previous_embeddings = np.load(EMBEDDINGS_PATH)
    previous_records = []

    with METADATA_PATH.open(encoding="utf-8") as input_file:
        previous_records = [json.loads(line) for line in input_file]

    if len(previous_records) == len(previous_embeddings):
        for record, vector in zip(previous_records, previous_embeddings):
            old_vectors[record["chunk_id"]] = (
                record_signature(record),
                vector,
            )

missing_records = []
missing_positions = []
embeddings = [None] * len(records)

for position, record in enumerate(records):
    cached = old_vectors.get(record["chunk_id"])

    if cached and cached[0] == record_signature(record):
        embeddings[position] = cached[1]
    else:
        missing_positions.append(position)
        missing_records.append(record)

print(f"内容块总数：{len(records)}")
print(f"复用旧向量：{len(records) - len(missing_records)}")
print(f"需要新生成：{len(missing_records)}")

if missing_records:
    for record in missing_records:
        texts.append(
            f"公司：{record['company']}\n"
            f"报告期：{record['report_period']}\n"
            f"章节：{record['section']}\n"
            f"内容类型：{record['content_type']}\n"
            f"{record['content']}"
        )

    print("正在加载 BGE 中文向量模型……")
    model = SentenceTransformer(
        "BAAI/bge-small-zh-v1.5",
        device="cpu",
    )
    model.max_seq_length = 512

    new_embeddings = model.encode(
        texts,
        batch_size=16,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    for position, vector in zip(missing_positions, new_embeddings):
        embeddings[position] = vector

embeddings = np.asarray(embeddings, dtype="float32")

np.save(EMBEDDINGS_PATH, embeddings)

with METADATA_PATH.open("w", encoding="utf-8") as output_file:
    for record in records:
        output_file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )

print(f"完成，向量形状：{embeddings.shape}")
print(f"向量文件：{EMBEDDINGS_PATH}")
print(f"元数据文件：{METADATA_PATH}")
