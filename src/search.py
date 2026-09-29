import json
import math
import pickle
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


VECTOR_PATH = Path("indexes/vector/embeddings.npy")
METADATA_PATH = Path("indexes/vector/metadata.jsonl")
BM25_PATH = Path("indexes/bm25/bm25_index.pkl")

QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


def tokenize(text):
    text = text.lower()
    parts = re.findall(
        r"[\u4e00-\u9fff]+|[a-z0-9_.%+-]+",
        text,
    )

    tokens = []

    for part in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part)
            tokens.extend(
                part[index:index + 2]
                for index in range(len(part) - 1)
            )
        else:
            tokens.append(part)

    return tokens


def calculate_bm25(query, index):
    document_count = index["document_count"]
    average_length = index["average_length"]
    document_lengths = index["document_lengths"]
    postings = index["postings"]

    scores = np.zeros(document_count, dtype="float32")
    k1 = 1.5
    b = 0.75

    for token in set(tokenize(query)):
        token_postings = postings.get(token)

        if not token_postings:
            continue

        document_frequency = len(token_postings)

        idf = math.log(
            1
            + (
                document_count
                - document_frequency
                + 0.5
            )
            / (document_frequency + 0.5)
        )

        for document_id, frequency in token_postings:
            length = document_lengths[document_id]

            denominator = frequency + k1 * (
                1 - b + b * length / average_length
            )

            scores[document_id] += (
                idf
                * frequency
                * (k1 + 1)
                / denominator
            )

    return scores


def top_indices(scores, count=30):
    return np.argsort(scores)[::-1][:count]


def reciprocal_rank_fusion(vector_ids, bm25_ids):
    combined = defaultdict(float)
    rank_constant = 20

    for rank, document_id in enumerate(vector_ids, start=1):
        combined[int(document_id)] += (
            1.0 / (rank_constant + rank)
        )

    for rank, document_id in enumerate(bm25_ids, start=1):
        combined[int(document_id)] += (
            1.5 / (rank_constant + rank)
        )

    return sorted(
        combined.items(),
        key=lambda item: item[1],
        reverse=True,
    )


def adjust_scope_ranking(query, fused_results, metadata):
    """Prefer consolidated/group evidence unless the user asks for parent-only data."""
    asks_for_parent = any(
        term in query
        for term in ("母公司", "本行口径", "公司口径")
    )
    adjusted = []

    for document_id, score in fused_results:
        content = metadata[document_id]["content"]
        section = metadata[document_id]["section"]

        if asks_for_parent:
            if "公司利润表" in content or "本行" in content:
                score += 0.035
        else:
            if "本集团" in content or "合并" in content:
                score += 0.025
            if "主要会计数据和财务指标" in content:
                score += 0.025
            if "财务摘要" in section or "财务摘要" in content[:200]:
                score += 0.065
            if "公司利润表" in content and "合并" not in content:
                score -= 0.040

        adjusted.append((document_id, score))

    return sorted(
        adjusted,
        key=lambda item: item[1],
        reverse=True,
    )


print("正在加载索引……")

embeddings = np.load(VECTOR_PATH)

metadata = []

with METADATA_PATH.open(encoding="utf-8") as input_file:
    for line in input_file:
        metadata.append(json.loads(line))

with BM25_PATH.open("rb") as input_file:
    bm25_index = pickle.load(input_file)

if len(metadata) != len(embeddings):
    raise RuntimeError("向量数量与元数据数量不一致")

model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5",
    device="cpu",
)

model.max_seq_length = 512

print("检索系统已就绪。输入 exit 退出。")

while True:
    query = input("\n请输入问题：").strip()

    if query.lower() in {"exit", "quit"}:
        break

    if not query:
        continue

    query_embedding = model.encode(
        [QUERY_INSTRUCTION + query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]

    vector_scores = embeddings @ query_embedding
    bm25_scores = calculate_bm25(query, bm25_index)
    mentioned_companies = list(
        dict.fromkeys(
            record["company"]
            for record in metadata
            if record["company"] in query
        )
    )

    if mentioned_companies:
        for document_id, record in enumerate(metadata):
            if record["company"] not in mentioned_companies:
                vector_scores[document_id] = -np.inf
                bm25_scores[document_id] = -np.inf

    vector_ids = top_indices(vector_scores, 30)
    bm25_ids = top_indices(bm25_scores, 30)

    fused_results = reciprocal_rank_fusion(
        vector_ids,
        bm25_ids,
    )
    fused_results = adjust_scope_ranking(
        query,
        fused_results,
        metadata,
    )

    results = []
    seen_pages = set()

    # 全景题先为每家公司保留两个不同页面，避免单家公司占满结果。
    if len(mentioned_companies) > 1:
        for company in mentioned_companies:
            company_count = 0
            for document_id, score in fused_results:
                record = metadata[document_id]
                page_key = (record["company"], record["pdf_page"])

                if record["company"] != company or page_key in seen_pages:
                    continue

                seen_pages.add(page_key)
                results.append((document_id, score))
                company_count += 1

                if company_count == 2:
                    break

        results.sort(key=lambda item: item[1], reverse=True)

    for document_id, score in fused_results:
        record = metadata[document_id]
        page_key = (
            record["company"],
            record["pdf_page"],
        )

        if page_key in seen_pages:
            continue

        seen_pages.add(page_key)
        results.append((document_id, score))

        if len(results) == 8:
            break

    print("\n召回结果：")

    for result_rank, (document_id, rrf_score) in enumerate(
        results,
        start=1,
    ):
        record = metadata[document_id]
        content = record["content"].replace("\n", " ")
        preview = content[:500]

        print("\n" + "=" * 70)
        print(f"排名：{result_rank}")
        print(
            f"出处：{record['company']}，"
            f"{record['report_period']}，"
            f"PDF第{record['pdf_page']}页"
        )
        print(f"章节：{record['section']}")
        print(f"类型：{record['content_type']}")
        print(f"RRF分数：{rrf_score:.6f}")
        print(f"内容：{preview}")
