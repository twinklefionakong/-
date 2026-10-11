import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,read_json
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
s=read_json(ROOT/'evaluation/summary.json'); manifest=read_json(ROOT/'data/manifest.json')
out=ROOT/'output';out.mkdir(exist_ok=True)
c=canvas.Canvas(str(out/'conclusion.pdf'),pagesize=A4); c.setTitle('第三周作业A：银行半年报问答结论');c.setAuthor('')
w,h=A4;c.setFillColor(HexColor('#12364d'));c.rect(0,h-105,w,105,fill=1,stroke=0);c.setFillColor(HexColor('#ffffff'));c.setFont('CN',22);c.drawString(36,h-47,'12家银行半年报：问答与证据边界');c.setFont('CN',10);c.drawString(36,h-73,'第三周作业 A | 2026 年上半年 | 补交版本 · 2026-10-11')
body=ParagraphStyle('body',fontName='CN',fontSize=10,leading=15,textColor=HexColor('#263d4b'))
small=ParagraphStyle('small',parent=body,fontSize=8.6,leading=12)
heading=ParagraphStyle('heading',parent=body,fontSize=12,leading=18,textColor=HexColor('#176a74'))
def para(text,y,style=body):
    p=Paragraph(text,style);_,ph=p.wrap(w-72,h);p.drawOn(c,36,y-ph);return y-ph-8
y=h-125
metrics=[('8/10','严格答案正确率'),('39/53 · 73.6%','证据义务完整覆盖'),('7/9','可回答题完整证据')]
for i,(value,label) in enumerate(metrics):
    x=36+i*177;c.setFillColor(HexColor('#eef5f6'));c.roundRect(x,y-62,169,62,6,fill=1,stroke=0);c.setFillColor(HexColor('#176a74'));c.setFont('CN',17 if i!=1 else 14);c.drawString(x+10,y-26,value);c.setFillColor(HexColor('#526b7a'));c.setFont('CN',9);c.drawString(x+10,y-46,label)
y-=78
y=para('材料与方法',y,heading)
y=para(f"12份全文、{sum(m['pages'] for m in manifest):,}页、10,227块、685张有边框表。正文按页切块，保留公司、章节、PDF页与原文；表格按行列保存。LSA向量 + BM25经RRF融合，指标聚焦后读取完整原页，全景每家公司独立取3页，DeepSeek依据白名单证据作答。",y)
y=para('评价分开报告，部分正确不计正确',y,heading)
y=para('严格正确8/10：可回答题7/9、全年利润拒答1/1；两道全景题均为部分正确。证据覆盖39/53：7道局部题17/17、资产质量全景10/12、原因/措施全景12/24。候选公司12/12仅表示找到候选，不能当作证据覆盖。部分义务不计完整，拒答题不进入证据覆盖分母。',y)
table_data=[['题型','最终表现','证据 / 原因'],['Q01-07：单公司事实、比较、原因','7/7正确','完整证据17/17'],['Q08：2026全年利润','正确拒答','半年报不包含全年实绩'],['Q09：12家集团不良贷款率','部分正确，计0分','10/12；漏读释义导致错排除北京'],['Q10：12家净息差原因/措施','部分正确，计0分','12/24；漏召专项页，部分过度拒答']]
table=Table([[Paragraph(t,small) for t in row] for row in table_data],colWidths=[195,115,w-72-310]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e5eef2')),('GRID',(0,0),(-1,-1),.4,HexColor('#cedbe2')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));_,th=table.wrap(w-72,h);table.drawOn(c,36,y-th);y-=th+13
y=para('哪类答得好，哪类翻车，为什么',y,heading)
y=para('本实验中，单公司明确指标与期间的事实查询、百分点计算和分红状态答得较好。全景题容易受公司释义、集团/局部业务口径和跨页专项分析影响：首轮曾把农业银行县域1.05%当集团值；复测修复为1.25%，仍误排除北京银行。原因题漏读北京PDF35、华夏PDF50、招商PDF38等页，“未召回”不等于“未披露”。',y)
y=para('边界与可核查交付',y,heading)
y=para('首轮6/10→复测8/10，是同10题修复对照，无独立测试集。LSA为语料统计向量，非预训练语义embedding；无边框、跨页表格未全部结构化，关键数回原页核对。采用固定每公司页数，动态补证循环仍未实现。核查由Codex完成，非第三方人工评委。11份巨潮官方附件SHA256与输入一致；建设银行找到的版本不同，原附件链接待确认，未混用。',y,small)
y=para('代码含下载/解析/索引/问答/复跑脚本；evaluation中保存两轮原始答案、全量召回原文、独立参考答案与逐公司判分；附件另含真实问答页面截图。',y,small)
y=para('一句话结论：同一批财报，有明确期间、口径和出处的事实问题适合建库；跨公司全景与原因归纳还需要逐公司补证、读释义和原表，微调不能替代缺失证据。',y,body)
assert y>28,('One-page overflow',y)
c.setFillColor(HexColor('#70838f'));c.setFont('CN',8);c.drawString(36,18,'评分采用严格口径；真实错误保留，不把召回覆盖当答案正确。');c.drawRightString(w-36,18,'1 / 1');c.save();print(out/'conclusion.pdf')
