import json
import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path


CHUNKS_PATH = Path("data/chunks/chunks.jsonl")
OUTPUT_DIR = Path("indexes/bm25")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = OUTPUT_DIR / "bm25_index.pkl"


def tokenize(text):
    text = text.lower()
    parts = re.findall(
        r"[\u4e00-\u9fff]+|[a-z0-9_.%+-]+",
        text,
    )

    tokens = []

    for part in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            # 单个汉字
            tokens.extend(part)

            # 中文二元词组
            tokens.extend(
                part[index:index + 2]
                for index in range(len(part) - 1)
            )
        else:
            tokens.append(part)

    return tokens


documents = []

with CHUNKS_PATH.open(encoding="utf-8") as input_file:
    for line in input_file:
        record = json.loads(line)
        documents.append(record["content"])

postings = defaultdict(list)
document_lengths = []

for document_id, document in enumerate(documents):
    tokens = tokenize(document)
    frequencies = Counter(tokens)
    document_lengths.append(len(tokens))

    for token, frequency in frequencies.items():
        postings[token].append(
            (document_id, frequency)
        )

    if (document_id + 1) % 500 == 0:
        print(
            f"已处理 {document_id + 1}/{len(documents)} 个块"
        )

average_length = (
    sum(document_lengths) / len(document_lengths)
    if document_lengths
    else 0
)

index_data = {
    "document_count": len(documents),
    "average_length": average_length,
    "document_lengths": document_lengths,
    "postings": dict(postings),
}

with INDEX_PATH.open("wb") as output_file:
    pickle.dump(
        index_data,
        output_file,
        protocol=pickle.HIGHEST_PROTOCOL,
    )

print(f"完成，共索引 {len(documents)} 个内容块")
print(f"BM25索引：{INDEX_PATH}")
