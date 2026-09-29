import json
from pathlib import Path

from retrieval import HybridSearcher, compose_evidence_answer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "evaluation"
OUTPUT_DIR.mkdir(exist_ok=True)

QUESTIONS = [
    {
        "id": 1,
        "category": "单公司·摘要金额",
        "question": "招商银行2026年上半年营业收入是多少？",
        "expected": "1,781.81亿元（178,181百万元）",
        "correct": True,
        "diagnosis": "首条即命中财务指标摘要，数值与单位完整。",
    },
    {
        "id": 2,
        "category": "单公司·正文金额",
        "question": "工商银行2026年上半年营业收入是多少？",
        "expected": "4,658.59亿元（465,859百万元）",
        "correct": True,
        "diagnosis": "首条正文直接给出金额和同比增幅，另有合并利润表交叉验证。",
    },
    {
        "id": 3,
        "category": "单公司·摘要金额",
        "question": "建设银行2026年上半年营业收入是多少？",
        "expected": "4,365.29亿元（436,529百万元）",
        "correct": True,
        "diagnosis": "首条命中财务摘要，集团口径明确。",
    },
    {
        "id": 4,
        "category": "单公司·表格金额",
        "question": "成都银行2026年上半年营业收入是多少？",
        "expected": "127.75948亿元（12,775,948千元）",
        "correct": True,
        "diagnosis": "正确总额位于第2条合并利润表；第1条是地区分布表，存在轻微干扰。",
    },
    {
        "id": 5,
        "category": "单公司·摘要金额",
        "question": "浙商银行2026年上半年营业收入是多少？",
        "expected": "332.56亿元（33,256百万元）",
        "correct": True,
        "diagnosis": "首条财务概要与第2条公司业务概要均给出相同结果。",
    },
    {
        "id": 6,
        "category": "单公司·易混指标",
        "question": "北京银行2026年上半年归属于母公司股东的净利润是多少？",
        "expected": "159.00亿元（15,900百万元）",
        "correct": False,
        "diagnosis": "正确块已在第4条召回，但答案错误摘取第1条每股收益和第2条净利润/扣非净利润表。",
    },
    {
        "id": 7,
        "category": "单公司·整体/分项口径",
        "question": "华夏银行2026年6月末不良贷款率是多少？",
        "expected": "1.50%",
        "correct": False,
        "diagnosis": "正确整体口径在第3条；答案优先摘取公司贷款1.13%和个人贷款2.85%，混淆整体与分项。",
    },
    {
        "id": 8,
        "category": "单公司·合并报表",
        "question": "中国银行2026年上半年营业收入是多少？",
        "expected": "3,569.03亿元（356,903百万元）",
        "correct": True,
        "diagnosis": "首条合并及母公司利润表命中集团营业收入，口径正确。",
    },
    {
        "id": 9,
        "category": "跨公司·收入排序",
        "question": "比较招商银行、建设银行和工商银行2026年上半年营业收入，哪家最高？",
        "expected": "工商银行4,658.59亿元 > 建设银行4,365.29亿元 > 招商银行1,781.81亿元；工商银行最高。",
        "correct": False,
        "diagnosis": "三家公司均有召回，但建设银行保留块是境外业务而非集团收入；答案也没有执行统一单位换算和排序。",
    },
    {
        "id": 10,
        "category": "跨公司·净利润比较",
        "question": "比较北京银行、成都银行和浙商银行2026年上半年归属于母公司股东的净利润。",
        "expected": "北京银行159.00亿元 > 浙商银行78.24亿元 > 成都银行69.04519亿元。",
        "correct": False,
        "diagnosis": "三家公司均被召回，但北京银行首选块是总净利润而非归母净利润；答案未统一百万元/千元单位，也未形成排序。",
    },
]


def main():
    searcher = HybridSearcher()
    records = []
    for item in QUESTIONS:
        results = searcher.search(item["question"])
        answer = compose_evidence_answer(item["question"], results)
        recalled = []
        for result in results:
            recalled.append(
                {
                    "rank": result["rank"],
                    "chunk_id": result["chunk_id"],
                    "company": result["company"],
                    "section": result["section"],
                    "pdf_page": result["pdf_page"],
                    "content_type": result["content_type"],
                    "rrf_score": result["score"],
                    "preview": " ".join(result["content"].split())[:360],
                }
            )
        records.append({**item, "system_answer": answer, "recalled_chunks": recalled})

    json_path = OUTPUT_DIR / "evaluation_results.json"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 银行半年报问答系统评测记录",
        "",
        "- 评测题数：10",
        "- 跨公司题：2",
        f"- 答对：{sum(item['correct'] for item in records)}/10",
        "- 判定规则：最终展示答案必须给出正确数值和口径；仅在较低排名召回正确块不算答对。",
        "",
    ]
    for item in records:
        lines.extend(
            [
                f"## Q{item['id']}｜{item['category']}｜{'答对' if item['correct'] else '答错'}",
                "",
                f"**问题：** {item['question']}",
                "",
                f"**标准答案：** {item['expected']}",
                "",
                "**系统答案：**",
                "",
                item["system_answer"].replace("\n", "  \n"),
                "",
                f"**判定与原因：** {item['diagnosis']}",
                "",
                "**召回块：**",
                "",
            ]
        )
        for block in item["recalled_chunks"]:
            lines.append(
                f"- R{block['rank']} `{block['chunk_id']}`｜{block['company']}｜"
                f"{block['section']}｜PDF第{block['pdf_page']}页｜{block['content_type']}｜"
                f"RRF {block['rrf_score']:.6f}  \n  {block['preview']}"
            )
        lines.append("")

    markdown_path = OUTPUT_DIR / "evaluation_report.md"
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"评测完成：{json_path}")
    print(f"详细报告：{markdown_path}")


if __name__ == "__main__":
    main()
