
# ---------- 회사별 분해 (계약 마스터 기반 지표) ----------
def _cm_rows(co): return cm[co]
def _costclass(rows):
    g=collections.defaultdict(lambda:{'인원':0,'월급여':0})
    for r in rows:
        k=str(r.get('인건비구분') or '미분류')
        g[k]['인원']+=1; g[k]['월급여']+=cn(r.get('월급여'))
    tot=sum(v['월급여'] for v in g.values())
    return [{'구분':k,'인원':v['인원'],'월급여':round(v['월급여']),'연환산':round(v['월급여']*12),
             '1인평균연봉':round(v['월급여']*12/v['인원']) if v['인원'] else 0,
             '비중':round(v['월급여']/tot,4) if tot else 0} for k,v in g.items()]
def _saldist(rows):
    sal=sorted(cn(r.get('계약연봉')) for r in rows if cn(r.get('계약연봉'))>0)
    if not sal: return None,[]
    q=lambda p: sal[min(len(sal)-1,int(len(sal)*p))]
    dist={'인원':len(sal),'최소':round(sal[0]),'p25':round(q(.25)),'중위':round(q(.5)),
          'p75':round(q(.75)),'p90':round(q(.9)),'최대':round(sal[-1]),'평균':round(sum(sal)/len(sal))}
    bands=[{'구간':lab,'인원':sum(1 for s in sal if lo<=s<hi)} for lo,hi,lab in BANDS]
    return dist,bands
def _byjob(rows):
    job=collections.defaultdict(list)
    for r in rows:
        if cn(r.get('계약연봉'))>0: job[str(r.get('직종') or '미분류')].append(cn(r['계약연봉']))
    return [{'직종':k,'인원':len(v),'중위연봉':round(sorted(v)[len(v)//2]),
             '평균연봉':round(sum(v)/len(v)),'최소':round(min(v)),'최대':round(max(v))}
            for k,v in sorted(job.items(),key=lambda x:-len(x[1]))]
def _fixot(rows):
    ot=[r for r in rows if cn(r.get('연장시수(월)'))>0]
    if not ot: return None,[]
    f={'대상':len(ot),
       '평균연장시수':round(sum(cn(r['연장시수(월)']) for r in ot)/len(ot),1),
       '평균가산시수':round(sum(cn(r.get('연장1.5%시수(월)')) for r in ot)/len(ot),1),
       '월고정연장수당합':round(sum(cn(r.get('고정연장수당')) for r in ot)),
       '최대연장시수':round(max(cn(r['연장시수(월)']) for r in ot),1),
       '법정한도':52,'주52시간초과위험':sum(1 for r in ot if cn(r['연장시수(월)'])>52)}
    c=collections.Counter()
    for r in ot:
        h=cn(r['연장시수(월)'])
        c['20시간 이하' if h<=20 else '20~40시간' if h<=40 else '40~52시간' if h<=52 else '52시간 초과']+=1
    ORD=['20시간 이하','20~40시간','40~52시간','52시간 초과']
    return f,[{'구간':k,'인원':c[k]} for k in ORD if c[k]]

byco={}
for co in ['코코도르','코코도르팜']:
    rws=_cm_rows(co)
    sd,sb=_saldist(rws); fo,fb=_fixot(rws)
    byco[co]={'costClass':_costclass(rws),'salaryDist':sd,'salaryBands':sb,
              'salaryByJob':_byjob(rws),'fixedOT':fo,'fixedOTBands':fb,
              '계약인원':len(rws)}
allrows=cm['코코도르']+cm['코코도르팜']
sd,sb=_saldist(allrows); fo,fb=_fixot(allrows)
byco['전체']={'costClass':out['costClass'],'salaryDist':sd,'salaryBands':sb,
              'salaryByJob':_byjob(allrows),'fixedOT':fo,'fixedOTBands':fb,
              '계약인원':len(allrows)}
out['byCompany']=byco
out['byCompanyNote']='계약 마스터(2024-09-30) 기준입니다. 급여대장(2026-02)과 시점이 달라 인원수가 다를 수 있습니다.'
json.dump(out,open('hrdata.json','w'),ensure_ascii=False)
for k,v in byco.items():
    print(k,'계약인원',v['계약인원'],'| 제조/판관',[(c['구분'],c['인원']) for c in v['costClass']],
          '| 중위연봉',(v['salaryDist'] or {}).get('중위'),'| 고정연장',(v['fixedOT'] or {}).get('평균연장시수'))
