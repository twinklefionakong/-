# 银行半年报混合检索问答系统

面向中国上市银行半年报的本地知识库。项目对 PDF 正文和表格进行解析，保留公司、章节和 PDF 页码，建立语义向量与 BM25 混合索引，并提供能够提问、查看引用和打开原始 PDF 页面的网页。

## 项目结果

- 行业：银行业
- 公司：11 家上市银行
- 报告：11 份 2026 年半年报
- 内容块：11,260 个
- 检索：BGE 中文向量 + BM25 + 加权倒数排名融合（RRF）
- 引用字段：公司、报告期、章节、PDF 页码、内容类型
- 评测：10 道题，其中 2 道跨公司题
- 严格答案准确率：6/10
- Top-8 完整证据覆盖率：9/10

> 原始 PDF、解析数据和索引没有提交到 Git 仓库。将报告放入 `documents/` 后，可按照下方步骤重新生成。

## 收录公司

华夏银行、民生银行、招商银行、北京银行、交通银行、工商银行、成都银行、浙商银行、建设银行、中国银行和中信银行。

报告应从上交所、深交所或巨潮资讯等官方信息披露网站下载。仓库不再分发报告全文。

## 工作流程

```text
PDF 年报/半年报
    ↓
正文与表格提取
    ↓
按页切块并写入公司、章节、页码
    ↓
BGE 向量索引 + BM25 索引
    ↓
RRF 融合检索与口径排序
    ↓
带出处的证据答案与原 PDF 链接
```

## 目录结构

```text
.
├── app.py                         # 本地问答网页服务器
├── requirements.txt
├── src/
│   ├── extract_pdf.py             # 提取每页正文和表格行列
│   ├── build_chunks.py            # 切块并添加元数据
│   ├── build_vector_index.py      # 建立/增量更新向量索引
│   ├── build_bm25_index.py        # 建立 BM25 索引
│   ├── repair_sections.py         # 修复不同报告的章节标签
│   ├── retrieval.py               # 混合检索和证据答案
│   ├── search.py                  # 终端检索入口
│   ├── run_evaluation.py          # 重跑 10 道评测题
│   └── build_evaluation_pdf.py    # 生成一页评测结论
├── web/
│   └── index.html                 # 问答页面
└── evaluation/
    ├── evaluation_report.md       # 逐题召回和错误分析
    ├── evaluation_results.json    # 机器可读评测记录
    └── evaluation_conclusion.pdf  # 一页结论
```

运行后会生成但不会提交的目录：

```text
documents/          原始 PDF
data/parsed_pages/  逐页解析结果
data/chunks/        内容块
indexes/vector/     向量及元数据
indexes/bm25/       BM25 索引
```

## 环境安装

建议使用 Python 3.10。本项目在 Intel Mac 上完成并测试。

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

语义模型使用 `BAAI/bge-small-zh-v1.5`。首次运行向量构建或检索时会从 Hugging Face 下载模型。该模型负责生成检索向量，不负责生成开放式文本。

## 从 PDF 重建知识库

1. 创建报告目录，并把 PDF 放入其中：

```bash
mkdir -p documents
```

文件名建议以股票代码开头，例如：

```text
600036-招商银行-FY26H1.pdf
601939-建设银行-FY26H1.pdf
```

2. 依次执行：

```bash
python src/extract_pdf.py
python src/build_chunks.py
python src/build_vector_index.py
python src/build_bm25_index.py
```

如果只修复章节标签，不需要重新生成向量：

```bash
python src/repair_sections.py
```

## 启动问答页面

```bash
source .venv/bin/activate
python app.py
```

浏览器访问：

```text
http://127.0.0.1:8000
```

页面会显示：

- 证据摘录答案
- `[1]`、`[2]` 引用编号
- 公司和章节
- PDF 页码
- 正文或表格类型
- RRF 融合分数
- 原始 PDF 对应页面链接

也可以在终端检索：

```bash
python src/search.py
```

## 评测

重新运行 10 道固定题：

```bash
python src/run_evaluation.py
```

重新生成一页 PDF 结论：

```bash
python src/build_evaluation_pdf.py
```

详细结果见 [`evaluation/evaluation_report.md`](evaluation/evaluation_report.md)。报告逐题保存问题、标准答案、系统答案、正确性、错误原因以及 Top-8 召回块。

当前系统擅长单公司、明确指标、财务摘要或合并利润表中的金额题。容易失败的题型包括：

- 整体指标与分项指标同时出现
- 总净利润、归母净利润和每股收益混杂
- 本行与本集团口径混杂
- 跨公司单位换算、证据聚合与排序

## 安全与数据说明

- 不要把 API Key、`.env` 或 shell 配置文件提交到仓库。
- 当前网页使用本地证据摘录，不会把报告内容发送给外部生成式模型。
- 原始报告版权归相应公司及信息披露平台所有。
- 数字和口径应以页面所引用的原始 PDF 为准。

