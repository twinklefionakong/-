import torch
from sentence_transformers import SentenceTransformer

device = "mps" if torch.backends.mps.is_available() else "cpu"
print("使用设备：", device)

model = SentenceTransformer(
    "Qwen/Qwen3-Embedding-0.6B",
    device=device,
)

documents = [
    "北京是中国的首都。",
    "上海是中国重要的金融中心。",
    "苹果公司生产 MacBook 电脑。",
]

query = ["中国的首都在哪里？"]

document_vectors = model.encode(
    documents,
    normalize_embeddings=True,
)

query_vectors = model.encode(
    query,
    prompt_name="query",
    normalize_embeddings=True,
)

scores = model.similarity(query_vectors, document_vectors)

for text, score in sorted(
    zip(documents, scores[0].tolist()),
    key=lambda item: item[1],
    reverse=True,
):
    print(f"{score:.4f}  {text}")
