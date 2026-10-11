"""Apply independently checked reference answers and an explicit, conservative rubric.
This file records review judgments; it is not an automatic judge and never changes answers.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,read_json,write_json,normalize
results=read_json(ROOT/'evaluation/results.json')
gold={
'Q01':{'answer':'465,859百万元人民币；2026年1-6月；合并集团口径。','source_pages':{'工商银行':[13,18]},'obligations':['本期集团营业收入与单位/期间'],'covered':1},
'Q02':{'answer':'净息差/净利息收益率1.37%，2025年同期1.40%，下降3BP；净利差为1.26%，不能替代。','source_pages':{'建设银行':[8,14]},'obligations':['本期净息差','上年同期净息差','基点变动'],'covered':3},
'Q03':{'answer':'集团不良贷款率0.94%，拨备覆盖率385.10%；2026年6月30日。','source_pages':{'招商银行':[9,11]},'obligations':['集团不良贷款率','集团拨备覆盖率'],'covered':2},
'Q04':{'answer':'集团核心一级资本充足率10.80%，2025年末11.08%，下降0.28个百分点。','source_pages':{'农业银行':[11,74,271]},'obligations':['本期集团指标','上年末集团指标','百分点变动'],'covered':3},
'Q05':{'answer':'拟派每10股1.190元人民币（税前/含税）；尚待股东会批准。','source_pages':{'中国银行':[5,66,116]},'obligations':['拟派中期普通股股利金额','截至报告披露的批准状态'],'covered':2},
'Q06':{'answer':'利息净收入728.04亿元（72,804百万元），同比下降1.29%；资产利率下行和业务结构变动，息差收窄。','source_pages':{'兴业银行':[11,18,29]},'obligations':['本期利息净收入','同比变化','报告明确说明的原因'],'covered':3},
'Q07':{'answer':'集团2026年6月末1.68%，2025年末1.71%，下降0.03个百分点。PDF8声明除特别注明外为集团数据。','source_pages':{'郑州银行':[8,9,29]},'obligations':['本期集团不良贷款率','上年末指标','百分点变动'],'covered':3},
'Q08':{'answer':'不能从2026年半年报获得2026年全年归母净利润；应拒绝给全年准确值，可区分上半年数据。','source_pages':{'招商银行':[1,7]},'obligations':[],'covered':0},
}
npl={'中国银行':(1.22,[7,10]),'交通银行':(1.30,[10,27]),'光大银行':(1.44,[10,18]),'兴业银行':(1.08,[13,44]),'农业银行':(1.25,[11]),'北京银行':(1.30,[6,15]),'华夏银行':(1.50,[6,11]),'厦门银行':(0.73,[2,7]),'工商银行':(1.29,[13,15]),'建设银行':(1.29,[8,9]),'招商银行':(0.94,[9,23]),'郑州银行':(1.68,[8,9])}
gold['Q09']={'answer':'厦门0.73 < 招商0.94 < 兴业1.08 < 中国1.22 < 农业1.25 < 工商=建设1.29 < 交通=北京1.30 < 光大1.44 < 华夏1.50 < 郑州1.68（%）。北京PDF6的公司/本公司定义含附属机构；厦门PDF2明确默认合并；郑州PDF8默认集团。','source_pages':{c:v[1] for c,v in npl.items()},'obligations':['每家公司当期集团数值+可核对口径' for _ in npl],'covered':10,'company_review':{c:{'expected_value':v[0],'source_pages':v[1],'evidence_status':'部分' if c in ['北京银行','厦门银行'] else '已覆盖','why':'数值已召回但未读默认合并/公司释义页' if c in ['北京银行','厦门银行'] else '召回原页包含当期指标及集团上下文；原报告交叉核对'} for c,v in npl.items()}}
nim={
'中国银行':([13],'贷款LPR重定价、市场利率下行；净息差同比+1BP，不能称净息差下降。','量价协同、强化存款成本管控。',[True,True]),
'交通银行':([29,30],'收益率下降压力与成本率下降幅度差异；净息差同比+2BP。','量价平衡、定价策略、存款重定价、优化资产负债结构。',[True,True]),
'光大银行':([19,20,55],'净息差同比+2BP，主要负债成本率降低，不能强加下降前提。','PDF55：加强源头性结算性资金吸收、优化结构、负债成本下行。',[True,False]),
'兴业银行':([17,18],'资产利率下行和业务结构变动，净息差同比-15BP。','PDF17：低成本负债/高收益资产结构；压降高成本、长期限存款。',[True,False]),
'农业银行':([16,17,20],'支持实体经济、利率下行使生息资产收益率下降，净息差同比-4BP。','召回未给出直接针对净息差的具体举措；不能把财务结果当行动或从一般业务章节推断。',[True,False]),
'北京银行':([15,35,36],'需求不足、贷款重定价、市场利率走低，净息差同比-5BP。','高成本负债管控、期限优化、核心存款经营、稳定资产收益。',[False,False]),
'华夏银行':([16,50,51],'净息差同比+5BP，资产负债结构改善、负债成本下行。','结构与定价精细化；低成本存款、严控高成本存款、主动定价。',[False,False]),
'厦门银行':([22,23],'净息差同比+6BP，业务结构优化与负债成本管控协同。','业务结构优化与负债成本管控；不虚构未披露压力。',[True,True]),
'工商银行':([19,21],'净息差同比-1BP；资产收益率与负债成本率均下降，需区分净利差同比+1BP。','成本改善与资产负债结构优化；PDF21具体负债管理与自律倡议。',[False,True]),
'建设银行':([8,14],'净息差同比-3BP；全表收益率/成本率变动须区分，不能把负债改善说成压力原因。','资产负债协同、结构改善、定价管理、前期降息释放。',[False,True]),
'招商银行':([38],'LPR重定价、零售信贷需求不足、债券收益率下降、负债成本改善空间有限。','资产负债组合管理、有效资产组织、高质量存款、集团资金统筹。',[False,False]),
'郑州银行':([17,40,44],'LPR重定价、息差收窄；净息差同比-12BP。','PDF40/44：综合收益精细化管理、优化负债期限、压降融资成本；须说明非专门净息差段落。',[True,False])}
gold['Q10']={'answer':'逐家核对原因/期间状态与应对措施；不能预设全部净息差下降，不能把行业综述当各行原因。参考company_review；对非直接措施保持克制。','source_pages':{c:v[0] for c,v in nim.items()},'obligations':['每家公司原因/期间状态','每家公司直接措施']*12,'covered':sum(sum(v[3]) for v in nim.values()),'company_review':{c:{'source_pages':v[0],'expected_cause_or_status':v[1],'expected_measures':v[2],'cause_covered':v[3][0],'measures_covered':v[3][1],'evidence_status':'已覆盖' if all(v[3]) else '部分' if any(v[3]) else '缺证据','note':'完整=直接支撑所需解释；仅数表或一般业务未计完整。部分不计分；没有原文不能宣称报告本身没有披露。'} for c,v in nim.items()}}
errors={'Q09':'部分正确：农业银行误用县域值已修复，但北京银行公司释义PDF6未读，被错误排除；厦门合并声明PDF2未读，排名中纳入同时称口径不明，自相矛盾。并列1.30%也未完整呈现。','Q10':'部分正确：漏召北京PDF35、华夏PDF50、招商PDF38、兴业PDF17等专项原因/措施页。对多家公司将“本轮未召回”写成“报告未披露”；部分原因与措施关系解释不足，末尾完整支持名单与正文不一致。'}
for item in results:
    g=gold[item['id']]; denominator=len(g['obligations']); verdict='部分正确' if item['id'] in errors else ('正确拒答' if item['id']=='Q08' else '正确')
    item['review']={'verdict':verdict,'strict_correct':item['id'] not in errors,'gold':g['answer'],'source_pages':g['source_pages'],'evidence_covered':g['covered'],'evidence_required':denominator,'coverage_display':f"{g['covered']}/{denominator}" if denominator else 'N/A · 拒答题','full_evidence_covered':g['covered']==denominator if denominator else None,'error':errors.get(item['id'],'未发现影响题目要求的数值、口径或出处错误。' if denominator else '准确拒答未披露全年值；不计可回答题证据覆盖分母。'),'judge':'人工式逐页独立核对；由Codex核查，非独立人工评委','visual_source_review':True}
write_json(ROOT/'evaluation/gold.json',gold); write_json(ROOT/'evaluation/results.json',results)
covered=sum(x['review']['evidence_covered'] for x in results); required=sum(x['review']['evidence_required'] for x in results)
full=sum(x['review']['full_evidence_covered'] is True for x in results); answerable=sum(x['review']['evidence_required']>0 for x in results)
summary={'evidence_covered':covered,'evidence_required':required,'evidence_coverage_display':f'{covered}/{required} · {covered/required:.1%}','full_evidence_questions':full,'answerable_questions':answerable,'full_question_coverage':f'{full}/{answerable}','strict_correct':8,'total':10,'strict_accuracy_display':'8/10 · 80%','answerable_correct':'7/9','refusal_correct':'1/1','partial_correct':2,'baseline_strict_correct':6,'baseline_full_question_coverage':'5/9','evaluation_limit':'同10题首轮失败后修复复测；无独立测试集；LSA非预训练语义向量；核查由Codex完成，建议本人抽检；并不将12/12候选公司当证据覆盖。'}
write_json(ROOT/'evaluation/summary.json',summary)
lines=['# 逐题评测与出处核查','', '## 判分规则','', '正确必须同时满足数值/单位/期间/集团口径、题目全部子问和引用支持；部分正确计0分。引用ID有效仅证明ID存在。证据覆盖在看最终答案前按原文核查，和答案是否正确独立。', '',f"- 严格答案准确率：8/10；可回答题7/9；拒答题1/1。",f"- 证据义务完整覆盖：{covered}/{required}（{covered/required:.1%}）；按题全部义务覆盖：{full}/{answerable}。",'- Q09每家一个复合义务（数值+期间+集团）；Q10每家两个义务（原因/期间状态、措施），部分不计完整；Q08拒答题不纳入证据覆盖分母。', '- 首轮：6/10，完整证据题5/9。保留 baseline_results.json；修复同题重跑不代表泛化。','- 评分由Codex逐页核查并保存参考记录，不冒称第三方人工评审。','']
for x in results:
    v=x['review']; lines.extend([f"## {x['id']} | {x['type']} | {v['verdict']}",'',f"**问题：** {x['question']}",'',f"**参考答案：** {v['gold']}",'',f"**证据覆盖：** {v['coverage_display']}；**错误/边界：** {v['error']}",'', '**独立核对原页：** '+str(v['source_pages']),'','**实际系统答案（原样保留）：**','',x['answer'],'','**召回与原页读取：**',''])
    for rank,c in enumerate(x['evidence'],1):
        lines.extend([f"- R{rank} `{c['id']}` | {c['company']} | {c['section']} | PDF{c['pdf_page']}，印刷页{c['printed_page']} | 候选`{c.get('candidate_id',c['id'])}` | LSA={c['vector_score']:.4f} / BM25={c['bm25_score']:.4f} / RRF={c['score']:.6f}", '  - 原文摘录：'+normalize(c['text'])[:240]])
    if x['id'] in ['Q09','Q10']:
        lines.extend(['','**逐公司覆盖核查：**','','```json',__import__('json').dumps(gold[x['id']]['company_review'],ensure_ascii=False,indent=2),'```'])
    lines.extend(['','完整实际证据、答案、模型名、时间、token usage 和单通道对照保存在 `results.json`，不是仅列摘要。',''])
(ROOT/'evaluation/report.md').write_text('\n'.join(lines),encoding='utf-8')
print(summary)
