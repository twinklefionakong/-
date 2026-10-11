# 12 家银行半年报：混合检索问答与逐题核查

第三周作业 A 的补交版本。12 份用户下载的 2026 年半年报全文，经正文/表格抽取后建本地 LSA 向量与 BM25 索引；使用 DeepSeek 生成带出处答案。重点将证据覆盖与答案正确率分开，并保留真实失败案例。

## 真实结果

- 严格答案正确率 **8/10**：可回答题 7/9，未披露全年数据拒答 1/1。两道全景题部分正确，均不计正确。
- 完整证据义务覆盖 **39/53（73.6%）**；可回答题完整覆盖 **7/9**。候选公司 12/12 不等于证据覆盖 12/12。
- 首轮答案 6/10、完整证据题 5/9；原记录保存在 `evaluation/baseline_results.json`。改进指标定位/原页读取后复测同 10 题，属于开发集修复对照，没有独立测试集。
- Q09：修复县域值误当集团值后，仍因漏读北京银行公司释义错误排除其集团值；厦门银行口径说明也不充分。
- Q10：漏召北京、华夏、招商、兴业等专项原因/措施页。模型的“本轮未召回”有时写成“报告未披露”，不能据此判正确。

评分是 Codex 对原报告完整相关页、表头、脚注与释义的核查，**不是第三方人工评委评分**。参见 `evaluation/gold.json`（参考答案与逐公司覆盖）、`report.md`（逐题判分）、`results.json`（完整召回原文、实际答案、引用、模型、时间、token usage 和单通道召回对照）。运行 `review.py` 只是汇总已记录核查判断，不是自动证明正确率。

## 材料与来源

工商、建设、农业、中国、交通、招商、兴业、光大、华夏、北京、厦门、郑州共 12 家。报告来源由提交者声明为 **巨潮资讯网 https://www.cninfo.com.cn/**。原始 PDF 不上传；文件名、页数与 SHA256 见 `data/manifest.json`。

本次使用用户已下载的文件，并反查巨潮官方附件：**11/12份下载SHA256与输入完全一致**，链接与下载核验见 `data/manifest.json` 和 `data/source_verification.json`。建设银行发现的A股简体版本与输入繁体/国际准则版本不一致，保留候选链接但不将其认作本文件来源；其准确附件URL仍待确认，不能用该候选替换本轮财报。

`scripts/download_reports.py` 提供巨潮查询及官方附件下载流程，只接受对应公司/年份/全文，发现多份候选或无法找到即停止自动选择，不替换年份。`data/verified_source_urls.json` 保存11份已验证下载链接，可用 `--urls data/verified_source_urls.json --download` 下载。建设银行需单独提供与原SHA256一致的繁体版，否则只重建11家库，不能复现本轮12家成绩。接口若变化，可手动核对巨潮附件。重新下载后须核对SHA256，版本不同可能导致页码和成绩变化。

## 本地运行

建议 Python 3.12；以下命令在本目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

在 `.env` 填入 `DEEPSEEK_API_KEY`，不上传 `.env`。服务地址默认 `https://api.deepseek.com`，模型 `deepseek-chat`。这里是本地程序调用远程 API，无需部署模型。没有 key 时只展示检索状态，不把摘录当作模型答案计分。

将 12 份 PDF 放在 `reports/`，文件名为 `银行简称：报告名.pdf`，例如 `建设银行：二零二六年半年度报告.pdf`。

```powershell
.\.venv\Scripts\python.exe scripts/extract.py --reports reports --workers 3
.\.venv\Scripts\python.exe scripts/build_index.py
.\.venv\Scripts\python.exe app.py
```

打开 http://127.0.0.1:8765 。问答页面可提问、切换检索通道、按公司取证、核查原文、回放保存的评测，并链接到 PDF 页。若 PDF 在 `reports/` 中，可将环境变量 `REPORTS_DIR` 指向它（见 app.py）。默认也兼容本作业工作区的 `银行2026半年报/`。

```powershell
# 从巨潮发现报告；先检查候选，再使用 --download
.\.venv\Scripts\python.exe scripts/download_reports.py --year 2026
.\.venv\Scripts\python.exe scripts/download_reports.py --year 2026 --download
# 复跑会调用API并产生费用；默认保留已有成功结果。
# 要生成一轮新记录，先手动备份并移走 evaluation/results.json。
.\.venv\Scripts\python.exe scripts/evaluate.py
```

## 方法与限制

1. 正文按页切块（上限约1600字符，不跨页）；保留公司、报告、期间、章节、PDF页和可识别印刷页。
2. 有边框表格按坐标抽取为二维行列，生成带首行/页首上下文的行块，完整二维表存 `data/tables/`。**无边框/复杂跨页表并非全部结构化成功**，保留等宽列间距，并在数字核查时回原页；没有以解析成功替代准确性验证。
3. 中文繁简统一用于检索，原文保留。向量为字符2-4gram TF-IDF → 192维 SVD/LSA → L2余弦，随机种子42；BM25用 jieba，通道各取40候选，RRF常数60。
4. LSA是语料统计向量，**不是BGE/Qwen等预训练embedding**，同义改写与语义归纳能力有限。这一限制是本次结果的一部分，不把词法向量包装为大模型语义向量。
5. 指标别名聚焦、指标命中加权、子组合降权；局部问题读4个完整原页，全景每家读3页。路由不含公司财务值、标准答案或标准页码。
6. 生成上下文仅包含真正读取的原页，ID白名单拒绝幻构引用。**ID有效不等于句子正确**，事实支持由逐页评测核对；不足就明说。
7. 章节标签来自书签或页头启发式，个别乱码/延续标题可能误标；PDF物理页码是可靠定位主键。没有完整实现课件的动态证据循环或图谱，当前固定每公司3页仍会漏召。

## 对照第三课与批改要求

- 第61-63页：全景必须逐公司取证，不能用高分碎块代表行业。
- 第90-92页：问题路由→双通道候选→读原页→逐项覆盖检查→带出处作答。本项目落实路由、双通道、原页与核查记录，并明确动态循环仍未实现。
- 10题仅1道营收题；另有净息差、资产质量、资本、分红、原因、未披露拒答和两道全景题。
- 原始答案不因判错而删改；参考答案、证据表现、答案判分分别保存。

## 交付物

- `output/conclusion.pdf`：一页结论。
- `output/qa_page.jpg`、`output/panorama_page.jpg`：真实页面截图。
- `evaluation/report.md`、`results.json`、`gold.json`、`baseline_results.json`：逐题审计证据。
- `submission.txt`：提交文本（三行）。

API key只在服务端读取，页面、评测和截图不包含密钥。PDF、全量提取与索引不入仓库；评测保存必要原文以便核查。
