import json
import math
import pickle
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = PROJECT_ROOT / "indexes/vector/embeddings.npy"
METADATA_PATH = PROJECT_ROOT / "indexes/vector/metadata.jsonl"
BM25_PATH = PROJECT_ROOT / "indexes/bm25/bm25_index.pkl"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


def tokenize(text):
    parts = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9_.%+-]+", text.lower())
    tokens = []
    for part in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part)
            tokens.extend(part[index:index + 2] for index in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


def calculate_bm25(query, index):
    count = index["document_count"]
    average_length = index["average_length"]
    lengths = index["document_lengths"]
    postings = index["postings"]
    scores = np.zeros(count, dtype="float32")
    k1, b = 1.5, 0.75

    for token in set(tokenize(query)):
        token_postings = postings.get(token)
        if not token_postings:
            continue
        frequency_in_corpus = len(token_postings)
        idf = math.log(1 + (count - frequency_in_corpus + 0.5) / (frequency_in_corpus + 0.5))
        for document_id, frequency in token_postings:
            denominator = frequency + k1 * (1 - b + b * lengths[document_id] / average_length)
            scores[document_id] += idf * frequency * (k1 + 1) / denominator
    return scores


def reciprocal_rank_fusion(vector_ids, bm25_ids):
    combined = defaultdict(float)
    for rank, document_id in enumerate(vector_ids, start=1):
        combined[int(document_id)] += 1.0 / (20 + rank)
    for rank, document_id in enumerate(bm25_ids, start=1):
        combined[int(document_id)] += 1.5 / (20 + rank)
    return sorted(combined.items(), key=lambda item: item[1], reverse=True)


def adjust_scope_ranking(query, fused_results, metadata):
    asks_for_parent = any(term in query for term in ("母公司", "本行口径", "公司口径"))
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
    return sorted(adjusted, key=lambda item: item[1], reverse=True)


class HybridSearcher:
    def __init__(self):
        self.embeddings = np.load(VECTOR_PATH)
        with METADATA_PATH.open(encoding="utf-8") as input_file:
            self.metadata = [json.loads(line) for line in input_file]
        with BM25_PATH.open("rb") as input_file:
            self.bm25_index = pickle.load(input_file)
        if len(self.metadata) != len(self.embeddings):
            raise RuntimeError("向量数量与元数据数量不一致")
        self.companies = sorted({record["company"] for record in self.metadata})
        self.model = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")
        self.model.max_seq_length = 512

    def search(self, query, limit=8):
        query_embedding = self.model.encode(
            [QUERY_INSTRUCTION + query], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        vector_scores = self.embeddings @ query_embedding
        bm25_scores = calculate_bm25(query, self.bm25_index)
        mentioned = [company for company in self.companies if company in query]

        if mentioned:
            for document_id, record in enumerate(self.metadata):
                if record["company"] not in mentioned:
                    vector_scores[document_id] = -np.inf
                    bm25_scores[document_id] = -np.inf

        vector_ids = np.argsort(vector_scores)[::-1][:30]
        bm25_ids = np.argsort(bm25_scores)[::-1][:30]
        fused = reciprocal_rank_fusion(vector_ids, bm25_ids)
        fused = adjust_scope_ranking(query, fused, self.metadata)
        selected, seen_pages = [], set()

        if len(mentioned) > 1:
            for company in mentioned:
                company_count = 0
                for document_id, score in fused:
                    record = self.metadata[document_id]
                    page_key = (record["company"], record["pdf_page"])
                    if record["company"] != company or page_key in seen_pages:
                        continue
                    selected.append((document_id, score))
                    seen_pages.add(page_key)
                    company_count += 1
                    if company_count == 2:
                        break
            selected.sort(key=lambda item: item[1], reverse=True)

        for document_id, score in fused:
            record = self.metadata[document_id]
            page_key = (record["company"], record["pdf_page"])
            if page_key in seen_pages:
                continue
            selected.append((document_id, score))
            seen_pages.add(page_key)
            if len(selected) >= limit:
                break

        results = []
        for rank, (document_id, score) in enumerate(selected[:limit], start=1):
            record = dict(self.metadata[document_id])
            record.update(rank=rank, score=round(float(score), 6))
            results.append(record)
        return results


def _best_excerpt(query, content, max_length=260):
    clean = " ".join(content.split())
    terms = [term for term in ("营业收入", "净利润", "资产", "负债", "贷款", "存款", "不良贷款率", "资本充足率") if term in query]
    position = min((clean.find(term) for term in terms if term in clean), default=-1)
    if position < 0:
        position = 0
    start = max(0, position - 35)
    excerpt = clean[start:start + max_length]
    if start:
        excerpt = "…" + excerpt
    if start + max_length < len(clean):
        excerpt += "…"
    return excerpt


def compose_evidence_answer(query, results):
    """Create a conservative answer without inventing facts outside retrieved evidence."""
    if not results:
        return "没有找到足够相关的年报内容，请换一种问法。"
    mentioned = []
    for result in results:
        if result["company"] in query and result["company"] not in mentioned:
            mentioned.append(result["company"])
    chosen = []
    if len(mentioned) > 1:
        for company in mentioned:
            match = next((item for item in results if item["company"] == company), None)
            if match:
                chosen.append(match)
    else:
        chosen = results[:2]

    lines = ["根据检索到的半年报原文："]
    for item in chosen:
        lines.append(f"{item['company']}：{_best_excerpt(query, item['content'])} [{item['rank']}]")
    lines.append("以上为原文证据摘录；涉及金额或比例时，请以所引 PDF 页面为准。")
    return "\n".join(lines)
