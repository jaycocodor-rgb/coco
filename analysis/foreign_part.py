
# ---------- 외국인 급여대장 ----------
FOREIGN_RE=re.compile(r'[A-Z]{2,}')
LTC_K='장기요양보험료건보료의 13.14%'; HI_K='건강보험료3.595%'; NP_K='국민연금4.75%'; EI_K='고용보험0.9%'

# 명부 전체(재직+퇴사)에서 외국인 추출
fro={}
for nm,r in roster.items():
    if FOREIGN_RE.search(str(nm)):
        fro[nm]={'성명':nm,'직원번호':r.get('직원번호'),'소속_명부':r.get('소속'),
                 '입사일':r.get('입사일'),'그룹입사일':r.get('그룹입사일'),'퇴사일':r.get('퇴사일')}
# 급여대장 기준 외국인
payf={e['성명']:e for e in emp if FOREIGN_RE.search(str(e['성명']))}
for nm,e in payf.items():
    fro.setdefault(nm,{'성명':nm,'직원번호':e['직원번호'],'소속_명부':None,
                       '입사일':e['입사일'],'그룹입사일':None,'퇴사일':e.get('퇴사일')})

_w={w['성명']:w for w in out['workforce']}
_r={x['성명']:x for x in raises}
rows=[]
for nm,base in fro.items():
    e=payf.get(nm); w=_w.get(nm,{}); rr=_r.get(nm,{})
    row={'성명':nm,'직원번호':base['직원번호'],
         '소속':(e['소속'] if e else base['소속_명부']) or '미지정',
         '법인':(e['법인'] if e else None),'직책':(e['직책'] if e else None),
         '입사일':base['입사일'] or (e['입사일'] if e else None),
         '퇴사일':base['퇴사일'],
         '근속년수':(e['근속년수'] if e else None),
         '재직':bool(e) and not base['퇴사일'],
         '재직상태':(e['재직상태'] if e else '퇴사')}
    if e:
        row.update({
          '기본급':e['기본급'],'고정연장수당':e['고정연장수당'],
          '연장근로수당':e['연장근로수당'],'휴일특근수당':e['휴일특근수당'],
          '야근교통비':e['야근교통비'],'직책수당':e['직책수당'],
          '기타수당':e['기타수당'],'상여':e['상여'],'출장비':e['출장비'],
          '연차수당':e['연차수당']+e['연가보상비'],
          '수당계':e['지급총액']-e['기본급'],
          '지급총액':e['지급총액'],'과세합계':e['과세합계'],
          '공제총액':e['공제총액'],'실지급액':e['실지급액'],
          '국민연금':e[NP_K],'건강보험':e[HI_K],'장기요양':e[LTC_K],'고용보험':e[EI_K],
          '장기요양가입':('가입제외' if (e[HI_K]>0 and e[LTC_K]==0) else ('가입' if e[LTC_K]>0 else '건보없음')),
          '연장시간':w.get('연장시간',0),'휴일근무일수':w.get('휴일근무일수',0),
          '계약_2024_09':rr.get('T0_2024_09'),'계약_2025_07':rr.get('T1_2025_07'),
          '계약_2026_02':e['계약급여'],
          '누적인상률':rr.get('누적인상률'),'연환산인상률':rr.get('연환산_누적'),'등급':rr.get('등급')})
    else:
        for k in ['기본급','고정연장수당','연장근로수당','휴일특근수당','야근교통비','직책수당','기타수당',
                  '상여','출장비','연차수당','수당계','지급총액','과세합계','공제총액','실지급액',
                  '국민연금','건강보험','장기요양','고용보험','연장시간','휴일근무일수',
                  '계약_2024_09','계약_2025_07','계약_2026_02','누적인상률','연환산인상률','등급']:
            row[k]=None
        row['장기요양가입']=None
    rows.append(row)
rows.sort(key=lambda r:-(r['지급총액'] or -1))          # 6. 총급여 지급액 내림차순
out['foreignLedger']=rows

act=[r for r in rows if r['재직'] and r['지급총액']]
TOTF=sum(r['지급총액'] for r in act)
out['foreignSummary']={
 '명부총원':len(rows),'재직':len(act),'퇴사':sum(1 for r in rows if r['퇴사일']),
 '전체대비인원비중':round(len(act)/len(emp),4),
 '월급여총액':round(TOTF),'연환산':round(TOTF*12),
 '전체대비금액비중':round(TOTF/sum(e['지급총액'] for e in emp),4),
 '1인평균':round(TOTF/len(act)),'전사1인평균':out['talentFacts']['1인평균'],
 '기본급계':round(sum(r['기본급'] for r in act)),
 '수당계':round(sum(r['수당계'] for r in act)),
 '수당비중':round(sum(r['수당계'] for r in act)/TOTF,4),
 '장기요양가입제외':sum(1 for r in act if r['장기요양가입']=='가입제외'),
 '장기요양가입':sum(1 for r in act if r['장기요양가입']=='가입'),
 '평균근속':round(sum(r['근속년수'] for r in act if r['근속년수'] is not None)/
                sum(1 for r in act if r['근속년수'] is not None),1),
 '식별기준':'성명에 로마자 표기가 포함된 인원. 원본에 국적 항목이 없어 표기 기반으로 식별했습니다.'}

# 1. 월별 인원수 / 5. 월별 입사자수  (입사일·퇴사일로 재구성)
def _ym(s):
    try:
        d=datetime.date.fromisoformat(str(s)[:10]); return d.year*12+d.month-1
    except: return None
START=2023*12+0; END=2026*12+1        # 2023-01 ~ 2026-02
mon=[]
for k in range(START,END+1):
    y,m=divmod(k,12); ym=f'{y}-{m+1:02d}'
    cnt=hire=leave=0
    for r in rows:
        h=_ym(r['입사일']); q=_ym(r['퇴사일'])
        if h is None: continue
        if h<=k and (q is None or q>=k): cnt+=1
        if h==k: hire+=1
        if q==k: leave+=1
    mon.append({'월':ym,'인원':cnt,'입사':hire,'퇴사':leave})
out['foreignMonthly']=mon
out['foreignMonthlyNote']=('재직 인원수는 입사일·퇴사일로 역산한 값입니다. 퇴사일이 직원명부에 기재된 인원만 '
  '감소로 반영되므로, 과거 시점 인원은 실제보다 많게 잡힐 수 있습니다. 급여대장이 확보된 달은 2026-02 뿐입니다.')

# 부서별 / 근무지별
fd=collections.defaultdict(lambda:{'인원':0,'지급총액':0,'수당계':0,'연장시간':0})
for r in act:
    g=fd[r['소속']]; g['인원']+=1; g['지급총액']+=r['지급총액']; g['수당계']+=r['수당계']; g['연장시간']+=r['연장시간'] or 0
out['foreignByDept']=sorted([{'소속':k,**{kk:round(vv,1) for kk,vv in v.items()},
   '1인평균':round(v['지급총액']/v['인원']),'수당비중':round(v['수당계']/v['지급총액'],4)}
   for k,v in fd.items()],key=lambda x:-x['지급총액'])

# 인상률 분포
_fr=[r for r in act if r['연환산인상률'] is not None]
out['foreignRaise']={'비교가능':len(_fr),
  '중위연환산':round(sorted(r['연환산인상률'] for r in _fr)[len(_fr)//2],4) if _fr else None,
  '평균연환산':round(sum(r['연환산인상률'] for r in _fr)/len(_fr),4) if _fr else None,
  '전사중위':out['raiseSummary']['연환산_중위'],
  '등급분포':[{'등급':g,'인원':sum(1 for r in _fr if r['등급']==g)} for g in ['A','B','C','D']]}
json.dump(out,open('hrdata.json','w'),ensure_ascii=False)
print('외국인 명부',len(rows),'재직',len(act))
print(json.dumps(out['foreignSummary'],ensure_ascii=False,indent=1))
print('인상률',json.dumps(out['foreignRaise'],ensure_ascii=False))
print('최근 6개월 인원:',[(m['월'],m['인원'],m['입사']) for m in mon[-6:]])
