from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "evaluation_conclusion.pdf"
PAGE = pymupdf.paper_rect("a4")

INK = (0.075, 0.14, 0.23)
BLUE = (0.06, 0.31, 0.58)
PALE = (0.92, 0.95, 0.98)
LINE = (0.76, 0.82, 0.88)
GREEN = (0.09, 0.49, 0.34)
RED = (0.72, 0.22, 0.20)
MUTED = (0.34, 0.42, 0.51)
WHITE = (1, 1, 1)


def text(page, box, value, size=9, color=INK, align=0, font="cn"):
    return page.insert_textbox(
        pymupdf.Rect(*box), value, fontsize=size, fontname=font,
        color=color, align=align, lineheight=1.22,
    )


def rect(page, box, fill=None, stroke=None, width=0.7):
    page.draw_rect(
        pymupdf.Rect(*box), color=stroke, fill=fill, width=width,
    )


def main():
    OUTPUT.parent.mkdir(exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE.width, height=PAGE.height)
    page.insert_font(
        fontname="cn",
        fontfile="/System/Library/Fonts/Hiragino Sans GB.ttc",
    )
    w = PAGE.width

    # Header
    rect(page, (0, 0, w, 112), fill=INK)
    text(page, (36, 27, 430, 50), "2026 H1 · RAG EVALUATION", 8.5, (0.63, 0.83, 0.95))
    text(page, (36, 50, 450, 86), "银行半年报问答系统｜一页评测结论", 21, WHITE)
    text(page, (36, 88, 520, 105), "11 家银行 · 11,260 个内容块 · 向量 + BM25 · 10 道人工判定题", 8.5, (0.78, 0.84, 0.90))

    # Score card
    rect(page, (36, 132, 178, 235), fill=PALE, stroke=LINE)
    text(page, (50, 145, 165, 164), "最终答案准确率", 9, MUTED)
    page.insert_text((50, 197), "6 / 10", fontsize=25, fontname="cn", color=BLUE)
    text(page, (50, 211, 165, 229), "Top-8 完整证据覆盖：9 / 10", 7.8, MUTED)

    text(page, (198, 132, 557, 151), "核心判断", 11, BLUE)
    text(page, (198, 157, 557, 203),
         "系统已经能稳定找到单家公司财务摘要和合并利润表中的金额；主要短板不在“有没有召回”，而在“从多个相似数字中选哪个、是否统一单位并完成比较”。",
         10.2, INK)
    rect(page, (198, 211, 557, 235), fill=(0.98, 0.95, 0.89), stroke=None)
    text(page, (208, 217, 548, 232), "严格判定：答案必须明确给出正确数值与口径；仅召回正确块不算答对。", 8.3, (0.47, 0.31, 0.10))

    # Evaluation matrix
    text(page, (36, 258, 557, 278), "10 道题结果", 11, BLUE)
    rows = [
        ("01", "招商银行营业收入", "摘要金额", True, "首条命中"),
        ("02", "工商银行营业收入", "正文金额", True, "正文 + 报表互证"),
        ("03", "建设银行营业收入", "摘要金额", True, "集团口径明确"),
        ("04", "成都银行营业收入", "表格金额", True, "正确块排第 2"),
        ("05", "浙商银行营业收入", "摘要金额", True, "双来源一致"),
        ("06", "北京银行归母净利润", "易混指标", False, "把每股收益/总净利当前置"),
        ("07", "华夏银行不良贷款率", "整体/分项", False, "整体 1.50% 排第 3"),
        ("08", "中国银行营业收入", "合并报表", True, "合并口径正确"),
        ("09", "招行/建行/工行收入排序", "跨公司", False, "建行集团收入未进 Top-8"),
        ("10", "北京/成都/浙商净利比较", "跨公司", False, "证据已到但未换算排序"),
    ]
    x0, y0, row_h = 36, 282, 25
    widths = [31, 174, 77, 48, 191]
    headers = ["题", "问题", "类型", "结果", "记录"]
    x = x0
    for label, width in zip(headers, widths):
        rect(page, (x, y0, x + width, y0 + 24), fill=INK, stroke=WHITE, width=.35)
        text(page, (x + 5, y0 + 6, x + width - 4, y0 + 20), label, 8.2, WHITE)
        x += width
    for index, row in enumerate(rows):
        y = y0 + 24 + index * row_h
        fill = WHITE if index % 2 == 0 else (0.965, 0.975, 0.985)
        x = x0
        values = [row[0], row[1], row[2], "答对" if row[3] else "答错", row[4]]
        for col, (value, width) in enumerate(zip(values, widths)):
            rect(page, (x, y, x + width, y + row_h), fill=fill, stroke=LINE, width=.35)
            color = GREEN if col == 3 and row[3] else RED if col == 3 else INK
            text(page, (x + 5, y + 6, x + width - 4, y + 21), value, 7.7, color)
            x += width

    # Findings
    section_y = 575
    text(page, (36, section_y, 557, section_y + 20), "哪类题表现好｜哪类题翻车｜为什么", 11, BLUE)
    gap, col_w = 10, (521 - 20) / 3
    cards = [
        ("表现好", GREEN,
         "单公司、明确指标、财务摘要或合并利润表中的金额题。6 道答对题均属于这类；公司名过滤和 BM25 对指标词、数字很有效。"),
        ("容易翻车", RED,
         "同页出现整体/分项、总净利润/归母净利润、每股收益等相似指标时会选错；跨公司题还要求多证据聚合、单位换算与排序。"),
        ("下一步", BLUE,
         "为指标加入“整体口径/归母/本集团”精确加权；跨公司检索按“每家公司 + 同一指标”分别召回，再用结构化数值抽取完成单位统一与比较。"),
    ]
    for i, (title, accent, body) in enumerate(cards):
        x = 36 + i * (col_w + gap)
        rect(page, (x, section_y + 27, x + col_w, 745), fill=WHITE, stroke=LINE)
        rect(page, (x, section_y + 27, x + 5, 745), fill=accent)
        text(page, (x + 15, section_y + 40, x + col_w - 10, section_y + 60), title, 10, accent)
        text(page, (x + 15, section_y + 68, x + col_w - 12, 731), body, 8.4, INK)

    text(page, (36, 776, 557, 801),
         "结论：当前系统适合“带出处的事实核查”，尚不适合直接承担复杂口径判断与跨公司自动分析。详细逐题记录见 evaluation/evaluation_report.md。",
         8.8, INK)
    page.draw_line((36, 812), (557, 812), color=LINE, width=.6)
    text(page, (36, 818, 557, 834), "评测日期：2026-09-29　｜　答案准确率 60%　｜　完整召回覆盖率 90%", 7.5, MUTED)

    doc.set_metadata({"title": "银行半年报问答系统一页评测结论", "author": "Qwen Knowledge Base"})
    doc.subset_fonts()
    doc.save(OUTPUT, garbage=4, deflate=True)
    doc.close()
    print(f"PDF 已生成：{OUTPUT}")


if __name__ == "__main__":
    main()
