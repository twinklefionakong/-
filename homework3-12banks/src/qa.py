import os, json, urllib.request, re
from common import configured, ROOT
SYSTEM='''你是银行半年报问答助手。只能依据给出的证据回答，不使用外部知识补数。
每个事实句和表格数据必须引用 [块ID]；只能引用本轮证据白名单中的ID。
数字必须核对公司、2026年上半年/2026年6月末、集团或母行、单位、当期/比较期，保留表头与脚注条件。
年度报告、全年结果及下半年未披露信息必须明确缺数据。涉及排名时，任何公司或口径缺失都不能声称完整排名。
全景题逐公司给出证据；搜索到候选块不等于该公司的问题已覆盖。没有直接支持的明确写“证据不足”，最后说明已支持几家/需几家。
原因分析只归纳报告明确披露的原因，不把推测写成因果。简洁作答。'''
def answer(q,evidence):
    if not configured():
        return {'answer':'尚未配置 DeepSeek，以下仅为检索原文；不作为已生成答案或准确率评测。','mode':'retrieval_only','citation_valid':True,'cited_ids':[]}
    payload={'model':os.getenv('DEEPSEEK_MODEL','deepseek-chat'),'temperature':0,'max_tokens':4500,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':q+'\n\n证据：\n'+ '\n\n'.join(f"[{c['id']}] {c['company']} | {c['report']} | 章节 {c['section']} | PDF第{c['pdf_page']}页 | 印刷页 {c['printed_page']}\n{c['text']}" for c in evidence)}]}
    req=urllib.request.Request(os.getenv('DEEPSEEK_BASE_URL','https://api.deepseek.com').rstrip('/')+'/chat/completions',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']})
    with urllib.request.urlopen(req,timeout=180) as response: result=json.load(response)
    text=result['choices'][0]['message']['content']; ids=re.findall(r'\[([^\[\]\n]+)\]',text); allowed={c['id'] for c in evidence}; invalid=[i for i in ids if i not in allowed]
    if invalid: return {'answer':'生成结果引用了不在证据白名单中的 ID，已拒绝显示，请重新取证。','mode':'rejected','citation_valid':False,'invalid_ids':invalid,'raw_answer':text,'cited_ids':ids,'usage':result.get('usage')}
    return {'answer':text,'mode':'deepseek','model':result.get('model'),'citation_valid':True,'cited_ids':ids,'usage':result.get('usage')}
