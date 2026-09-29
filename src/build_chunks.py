import json
import re
from pathlib import Path


INPUT_DIR = Path("data/parsed_pages")
OUTPUT_DIR = Path("data/chunks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPANIES = {
    "600015": "华夏银行",
    "600016": "民生银行",
    "600036": "招商银行",
    "601169": "北京银行",
    "601328": "交通银行",
    "601398": "工商银行",
    "601838": "成都银行",
    "601916": "浙商银行",
    "601939": "建设银行",
    "601988": "中国银行",
    "601998": "中信银行",
}

REPORT_PERIOD = "2026年半年报"

NUMBER_PATTERN = re.compile(
    r"^[（(]?-?[\d,]+(?:\.\d+)?%?[）)]?$"
)

CHAPTER_PATTERN = re.compile(
    r"^(第[一二三四五六七八九十百0-9]+[章节])\s*([^\n]{2,45})$"
)
NUMBERED_SECTION_PATTERN = re.compile(
    r"^([1-9]\d*)[.、]?\s*([^\d\n][^\n]{1,40})$"
)
APPENDIX_PATTERN = re.compile(r"^附录\s+(.{2,40})$")
MAIN_SECTION_TITLES = {
    "释义",
    "重要提示",
    "财务摘要",
    "财务概要",
    "会计数据和财务指标摘要",
    "财务报表分析",
    "财务报告",
    "财务报表",
    "中期财务报告",
    "中期财务报表",
    "审阅报告及中期财务报表",
    "审阅报告及中期财务报告",
    "外部审计师审阅报告及财务报告",
    "外部审计师审阅报告及中期财务报表",
    "公司基本情况",
    "公司基本情况简介",
    "公司简介",
    "公司简介和主要财务指标",
    "管理层讨论与分析",
    "讨论与分析",
    "公司治理、环境和社会",
    "公司治理",
    "环境、社会与治理(ESG)",
    "股本变动及股东情况",
    "股份变动及股东情况",
    "股份变动和股东情况",
    "董事、高级管理人员书面确认意见",
    "重要事项",
    "备查文件",
    "备查文件目录",
}


def clean_heading(title):
    title = re.sub(r"[.。·…]{2,}.*$", "", title)
    title = re.sub(r"\s+\d+$", "", title)
    return title.strip(" ：:.-")


def is_main_heading(title):
    compact = re.sub(r"\s+", "", clean_heading(title))
    return compact in {
        re.sub(r"\s+", "", item)
        for item in MAIN_SECTION_TITLES
    }


def detect_section(text, current_section):
    chapter_candidates = []
    numbered_candidates = []
    plain_candidates = []
    appendix_candidates = []

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())

        # 工商银行的财务报告作为正文后的“附件”重新起页。
        if line == "附件" and current_section.startswith("11. 备查文件"):
            plain_candidates.append("9. 审阅报告及中期财务报告")

        chapter_match = CHAPTER_PATTERN.match(line)
        if chapter_match and is_main_heading(chapter_match.group(2)):
            chapter_candidates.append(
                f"{chapter_match.group(1)} "
                f"{clean_heading(chapter_match.group(2))}"
            )

        numbered_match = NUMBERED_SECTION_PATTERN.match(line)
        if numbered_match and is_main_heading(numbered_match.group(2)):
            numbered_candidates.append(
                f"{numbered_match.group(1)}. "
                f"{clean_heading(numbered_match.group(2))}"
            )

        appendix_match = APPENDIX_PATTERN.match(line)
        if appendix_match:
            appendix_candidates.append(
                f"附录 {clean_heading(appendix_match.group(1))}"
            )

        if is_main_heading(line) and len(clean_heading(line)) <= 24:
            # 部分银行的主章节没有“第X章/节”或数字编号。
            plain_candidates.append(clean_heading(line))

    # 正式章/节标题优先。每组去重后只有一个标题才更新，目录页会被排除。
    # 财务报告内可能出现“公司治理”等附注标题，不能降级成新的主章节。
    if "财务报告" in current_section or "财务报表" in current_section:
        plain_candidates = [
            item for item in plain_candidates
            if "财务报告" in item or "财务报表" in item
        ]

    for candidates in (
        chapter_candidates,
        numbered_candidates,
        appendix_candidates,
        plain_candidates,
    ):
        candidates = list(dict.fromkeys(candidates))
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return current_section

    return current_section


def normalize_table_row(row):
    cells = [" ".join(str(cell).split()) for cell in row]

    if not any(cells):
        return None

    numeric_index = None

    for index, cell in enumerate(cells):
        if NUMBER_PATTERN.match(cell):
            numeric_index = index
            break

    if numeric_index is None:
        return [cell for cell in cells if cell]

    label_cells = cells[:numeric_index]
    values = cells[numeric_index:]

    label = "".join(cell for cell in label_cells if cell).strip()

    # 修复“营业收入 17 | 8,181”之类的断列
    match = re.match(
        r"^(.*[\u4e00-\u9fff])\s*([0-9]+)$",
        label,
    )

    if match and values:
        label = match.group(1).strip()
        values[0] = match.group(2) + values[0]

    if label:
        return [label] + [value for value in values if value]

    return [cell for cell in cells if cell]


def table_to_text(table):
    clean_rows = []

    for row in table["rows"]:
        clean_row = normalize_table_row(row)

        if clean_row:
            clean_rows.append(" | ".join(clean_row))

    return "\n".join(clean_rows)


def split_text(text, chunk_size=800, overlap=120):
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


output_path = OUTPUT_DIR / "chunks.jsonl"
chunk_count = 0

with output_path.open("w", encoding="utf-8") as output_file:
    for input_path in sorted(INPUT_DIR.glob("*.jsonl")):
        stock_code = input_path.stem[:6]
        company = COMPANIES.get(stock_code, stock_code)
        current_section = "未识别章节"

        with input_path.open(encoding="utf-8") as input_file:
            for line in input_file:
                page = json.loads(line)
                pdf_page = page["pdf_page"]
                text = page["text"]

                current_section = detect_section(
                    text,
                    current_section,
                )

                # 正文块
                for part_number, content in enumerate(
                    split_text(text),
                    start=1,
                ):
                    chunk_count += 1

                    record = {
                        "chunk_id": (
                            f"{stock_code}_p{pdf_page}_"
                            f"text_{part_number}"
                        ),
                        "company": company,
                        "stock_code": stock_code,
                        "report_period": REPORT_PERIOD,
                        "section": current_section,
                        "pdf_page": pdf_page,
                        "content_type": "text",
                        "content": content,
                        "source_file": page["source_file"],
                    }

                    output_file.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                # 表格块
                for table_number, table in enumerate(
                    page["tables"],
                    start=1,
                ):
                    table_text = table_to_text(table)

                    if not table_text:
                        continue

                    chunk_count += 1

                    record = {
                        "chunk_id": (
                            f"{stock_code}_p{pdf_page}_"
                            f"table_{table_number}"
                        ),
                        "company": company,
                        "stock_code": stock_code,
                        "report_period": REPORT_PERIOD,
                        "section": current_section,
                        "pdf_page": pdf_page,
                        "content_type": "table",
                        "content": table_text,
                        "source_file": page["source_file"],
                    }

                    output_file.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

print(f"完成，共生成 {chunk_count} 个内容块")
print(f"输出：{output_path}")
