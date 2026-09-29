import json
import re
from pathlib import Path

PARSED_DIR = Path("data/parsed_pages")
TARGETS = (
    Path("data/chunks/chunks.jsonl"),
    Path("indexes/vector/metadata.jsonl"),
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
            plain_candidates.append(clean_heading(line))

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


def build_section_map():
    section_map = {}

    for input_path in sorted(PARSED_DIR.glob("*.jsonl")):
        stock_code = input_path.stem[:6]
        current_section = "未识别章节"

        with input_path.open(encoding="utf-8") as input_file:
            for line in input_file:
                page = json.loads(line)
                current_section = detect_section(
                    page["text"],
                    current_section,
                )
                section_map[(stock_code, page["pdf_page"])] = current_section

    return section_map


def repair_file(path, section_map):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    updated = 0

    with path.open(encoding="utf-8") as input_file, temporary_path.open(
        "w", encoding="utf-8"
    ) as output_file:
        for line in input_file:
            record = json.loads(line)
            key = (record["stock_code"], record["pdf_page"])
            new_section = section_map.get(key, record["section"])

            if record["section"] != new_section:
                record["section"] = new_section
                updated += 1

            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    temporary_path.replace(path)
    print(f"已更新 {path}：{updated} 条")


section_map = build_section_map()

for target in TARGETS:
    repair_file(target, section_map)
