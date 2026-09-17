# -*- coding: utf-8 -*-
import json, datetime, collections, re
def n(v):
    if v is None: return 0
    if isinstance(v,(int,float)): return v
    try: return float(str(v).replace(',','').strip())
    except: return 0

NP='국민연금4.75%'; HI='건강보험료3.595%'; LTC='장기요양보험료건보료의 13.14%'; EI='고용보험0.9%'
# 지급 항목 (계약 / 변동)
CONTRACT=['기본급','고정연장수당','직책수당','장거리유류비','식대']
VARIABLE=['연장근로수당','휴일특근수당','야근교통비','야간수당','연차수당','연가보상비','상여','출장비','기타수당','상품권지급','소급급여','무급휴가','무급휴가차감']
PAY=CONTRACT+VARIABLE
DED=[NP,HI,LTC,EI,'소득세','지방소득세','건강보험정산','노인장기요양정산','연말정산소득세','연말정산지방소득세','기지급분','상품권 기지급분','상품권기지급','기타공제']

co=json.load(open('pay_2602_코코도르.json')); pam=json.load(open('pay_2602_코코도르팜.json'))
for r in co: r['법인']='코코도르'
for r in pam: r['법인']='코코도르팜'
rows=co+pam
roster={r['성명']:r for r in json.load(open('roster.json'))}

TODAY=datetime.date(2026,2,28)
def tenure(r):
    d=r.get('입사일')
    if not d or str(d).strip() in ('',' ','None'): return None
    try: dt=datetime.date.fromisoformat(str(d)[:10])
    except: return None
    return round((TODAY-dt).days/365.25,1)

out={}
# ---------- 사원 레코드 ----------
emp=[]
for r in rows:
    rec={'직원번호':r.get('직원번호'),'성명':str(r['성명']).strip(),'법인':r['법인'],
         '소속':(str(r.get('소속')).strip() if r.get('소속') else '미지정'),
         '직책':(str(r.get('직책')).strip() if r.get('직책') else '-'),
         '입사일':str(r.get('입사일'))[:10] if r.get('입사일') else None,
         '근속년수':tenure(r)}
    for c in PAY+DED+['지급총액','과세합계','공제총액','실지급액']:
        rec[c]=round(n(r.get(c)))
    rec['계약급여']=sum(rec[c] for c in CONTRACT)
    rec['변동급여']=sum(rec[c] for c in VARIABLE)
    rec['연장수당계']=rec['고정연장수당']+rec['연장근로수당']+rec['휴일특근수당']+rec['야간수당']
    emp.append(rec)
emp.sort(key=lambda x:-x['지급총액'])
out['employees']=emp
out['asOf']='2026-02'
out['headcount']={'전체':len(emp),'코코도르':len(co),'코코도르팜':len(pam)}

# ---------- 1. 부서별 인건비 ----------
dept=collections.defaultdict(lambda: collections.defaultdict(float))
for e in emp:
    d=dept[e['소속']]
    d['인원']+=1; d['지급총액']+=e['지급총액']; d['기본급']+=e['기본급']
    d['계약급여']+=e['계약급여']; d['변동급여']+=e['변동급여']; d['연장수당계']+=e['연장수당계']
    d['고정연장수당']+=e['고정연장수당']; d['연장근로수당']+=e['연장근로수당']
    d['휴일특근수당']+=e['휴일특근수당']; d['직책수당']+=e['직책수당']
    d['기타수당']+=e['기타수당']; d['출장비']+=e['출장비']; d['상여']+=e['상여']
    d['야근교통비']+=e['야근교통비']; d['연차수당']+=e['연차수당']+e['연가보상비']
    if e['근속년수'] is not None: d['근속합']+=e['근속년수']; d['근속인원']+=1
deptList=[]
for k,v in dept.items():
    row={'소속':k,**{kk:round(vv) for kk,vv in v.items()}}
    row['1인평균']=round(v['지급총액']/v['인원'])
    row['평균근속']=round(v['근속합']/v['근속인원'],1) if v.get('근속인원') else None
    row['변동비중']=round(v['변동급여']/v['지급총액'],4) if v['지급총액'] else 0
    row['연장비중']=round(v['연장수당계']/v['지급총액'],4) if v['지급총액'] else 0
    deptList.append(row)
deptList.sort(key=lambda x:-x['지급총액'])
out['byDept']=deptList

# 법인별
corp=collections.defaultdict(lambda: collections.defaultdict(float))
for e in emp:
    c=corp[e['법인']]; c['인원']+=1
    for k in ['지급총액','기본급','계약급여','변동급여','연장수당계','공제총액','실지급액']: c[k]+=e[k]
out['byCorp']=[{'법인':k,**{kk:round(vv) for kk,vv in v.items()},'1인평균':round(v['지급총액']/v['인원'])} for k,v in corp.items()]

# ---------- 5. 수당 현황 ----------
allow=[]
for c in PAY:
    tot=sum(e[c] for e in emp); cnt=sum(1 for e in emp if e[c]!=0)
    if tot==0 and cnt==0: continue
    allow.append({'항목':c,'구분':'계약항목' if c in CONTRACT else '변동항목','총액':round(tot),
                  '수령인원':cnt,'1인평균':round(tot/cnt) if cnt else 0,
                  '비중':round(tot/sum(e['지급총액'] for e in emp),4)})
allow.sort(key=lambda x:-abs(x['총액']))
out['allowances']=allow

# 수당별 부서 분포 (상위 변동수당)
adist={}
for c in ['연장근로수당','휴일특근수당','야근교통비','기타수당','출장비','직책수당','연차수당','상여']:
    dd=collections.defaultdict(float); cnt=collections.defaultdict(int)
    for e in emp:
        if e[c]: dd[e['소속']]+=e[c]; cnt[e['소속']]+=1
    adist[c]=sorted([{'소속':k,'금액':round(v),'인원':cnt[k]} for k,v in dd.items()],key=lambda x:-x['금액'])
out['allowanceByDept']=adist


# ---------- 3. 급여/수당 오류 검증 ----------
MINWAGE_H=10320; MINWAGE_M=round(MINWAGE_H*209)   # 2026년 최저임금 시급 10,320원 × 209h
CAP_NP=302575
MONTH_START=datetime.date(2026,2,1); MONTH_END=datetime.date(2026,2,28)

def pdate(s):
    try: return datetime.date.fromisoformat(str(s)[:10])
    except: return None

# 상태 판정: 휴직 / 중도입사 / 중도퇴사 / 정상
for e in emp:
    rr=roster.get(e['성명'],{})
    e['퇴사일']=rr.get('퇴사일')
    hire=pdate(e['입사일']); quit_=pdate(rr.get('퇴사일'))
    st=[]
    if hire and MONTH_START<=hire<=MONTH_END: st.append('중도입사')
    if quit_ and MONTH_START<=quit_<=MONTH_END: st.append('중도퇴사')
    # 휴직 추정: 건강보험료가 당월 과세소득 기준 요율보다 현저히 큼 (보수월액 기준 부과)
    if e[HI]>0 and e['과세합계']>0 and e[HI] > e['과세합계']*0.03595*1.8: st.append('휴직(추정)')
    e['재직상태']='·'.join(st) if st else '정상'

issues=[]
def add(sev,rule,who,dept,desc,delta=None,note=None):
    issues.append({'심각도':sev,'검증항목':rule,'대상':who,'소속':dept,'내용':desc,
                   '차이':(round(delta) if delta is not None else None),'참고':note})

for e in emp:
    st=e['재직상태']
    calc=sum(e[c] for c in PAY)
    if abs(calc-e['지급총액'])>1: add('치명','R1 지급총액 합계',e['성명'],e['소속'],f"지급항목 합계 {calc:,}원 ≠ 지급총액 {e['지급총액']:,}원",e['지급총액']-calc)
    dcalc=sum(e[c] for c in DED)
    if abs(dcalc-e['공제총액'])>1: add('치명','R2 공제총액 합계',e['성명'],e['소속'],f"공제항목 합계 {dcalc:,}원 ≠ 공제총액 {e['공제총액']:,}원",e['공제총액']-dcalc)
    if abs((e['지급총액']-e['공제총액'])-e['실지급액'])>1:
        add('치명','R3 실지급액',e['성명'],e['소속'],f"지급−공제 {e['지급총액']-e['공제총액']:,}원 ≠ 실지급액 {e['실지급액']:,}원",e['실지급액']-(e['지급총액']-e['공제총액']))
    if e[HI]>0:
        exp=e[HI]*0.1314
        if e[LTC]==0:
            add('참고','R4 장기요양 미공제',e['성명'],e['소속'],
                f"건강보험 {e[HI]:,}원 공제, 장기요양 0원 — 외국인 가입제외 신청 대상으로 추정. 신청서 보관 여부 확인 필요",None,'외국인 추정')
        elif abs(e[LTC]-exp)>max(100,exp*0.02):
            add('주의','R4 장기요양 요율',e['성명'],e['소속'],f"건강보험 {e[HI]:,}원 × 13.14% = {round(exp):,}원이나 실제 {e[LTC]:,}원 ({e[LTC]/e[HI]*100:.2f}%)",e[LTC]-exp)
    elif e[LTC]>0:
        add('주의','R4 장기요양 요율',e['성명'],e['소속'],f"건강보험 0원인데 장기요양 {e[LTC]:,}원 공제",e[LTC])
    if e['과세합계']>0 and e[EI]>0:
        exp=e['과세합계']*0.009
        if abs(e[EI]-exp)>max(500,exp*0.03):
            add('주의','R5 고용보험 요율',e['성명'],e['소속'],f"과세 {e['과세합계']:,}원 × 0.9% = {round(exp):,}원이나 실제 {e[EI]:,}원",e[EI]-exp)
    if e[NP]>CAP_NP+10:
        add('주의','R6 국민연금 상한',e['성명'],e['소속'],f"상한 {CAP_NP:,}원 초과 ({e[NP]:,}원)",e[NP]-CAP_NP)
    if e[NP]<0:
        add('주의','R6 국민연금 음수',e['성명'],e['소속'],f"국민연금 공제액이 음수 ({e[NP]:,}원) — 정산 반영 여부 확인",e[NP])
    if e['지급총액']>MINWAGE_M and e[NP]==0 and e[HI]==0 and st=='정상':
        add('치명','R7 4대보험 미가입',e['성명'],e['소속'],
            f"지급총액 {e['지급총액']:,}원(최저임금 초과)인데 국민연금·건강보험 모두 0원 — 취득신고 누락 의심 (입사 {e['입사일']})")
    if 0 < e['계약급여'] < MINWAGE_M:
        if st=='정상':
            add('치명','R8 최저임금 미달',e['성명'],e['소속'],
                f"계약급여 {e['계약급여']:,}원 < 2026년 최저임금 월환산 {MINWAGE_M:,}원 — 단시간근로 계약 여부 확인 필요",e['계약급여']-MINWAGE_M)
        else:
            add('참고','R8 최저임금(정상사유)',e['성명'],e['소속'],
                f"계약급여 {e['계약급여']:,}원이 월환산 최저임금 미만이나 '{st}' 사유로 일할계산된 것으로 보임",None,st)
    if e['고정연장수당']>0 and e['기본급']==0:
        add('치명','R9 기본급 누락',e['성명'],e['소속'],f"고정연장수당 {e['고정연장수당']:,}원 지급, 기본급 0원")
    if e['과세합계']>MINWAGE_M and e['소득세']==0 and e['연말정산소득세']==0:
        add('주의','R10 소득세 미징수',e['성명'],e['소속'],f"과세소득 {e['과세합계']:,}원인데 소득세 0원")
    if e['소득세']>0:
        exp=e['소득세']*0.1
        if abs(e['지방소득세']-exp)>max(50,exp*0.02):
            add('주의','R11 지방소득세',e['성명'],e['소속'],f"소득세 {e['소득세']:,}원 × 10% = {round(exp):,}원이나 실제 {e['지방소득세']:,}원",e['지방소득세']-exp)

names=collections.Counter(e['소속'] for e in emp)
norm=collections.defaultdict(list)
for k in names: norm[re.sub(r'[^가-힣A-Za-z0-9]','',k)].append(k)
for base,variants in norm.items():
    if len(variants)>1:
        tot=sum(sum(e['지급총액'] for e in emp if e['소속']==v) for v in variants)
        add('치명','R12 부서명 표기 불일치','조직 마스터',' / '.join(variants),
            f"동일 부서가 {len(variants)}가지로 등록됨 — "+', '.join(f'{v}({names[v]}명)' for v in variants)+f". 부서별 집계 {tot:,}원이 분리 집계됨",None,'집계 왜곡')
for e in emp:
    if e['소속']=='미지정':
        add('치명','R13 소속 미지정',e['성명'],'미지정',f"소속 부서가 비어 있음 (지급총액 {e['지급총액']:,}원) — 부서별 인건비 집계에서 누락")
    if not e['입사일'] or e['근속년수'] is None:
        add('주의','R14 입사일 누락',e['성명'],e['소속'],'입사일 없음 — 근속수당·연차일수 산정 불가')

pset={e['성명'] for e in emp}
for nm,r in roster.items():
    if nm not in pset and not r.get('퇴사일'):
        add('주의','R15 명부-대장 불일치',nm,str(r.get('소속')),f"직원명부상 재직(입사 {r.get('입사일')})이나 2026-02 급여대장에 없음 — 퇴사 미반영 또는 지급누락")
for e in emp:
    if e['성명'] not in roster:
        add('주의','R15 명부-대장 불일치',e['성명'],e['소속'],'급여대장에는 있으나 직원명부에 없음 — 명부 미등록')

# R16 집계표 vs 급여대장 대사
AGG={'기본급':354945436+23464728,'고정연장수당':80294840+4755750,'연장근로수당':17305750+1271000,
     '휴일특근수당':6789000+341000,'야근교통비':1020000+40000,'직책수당':2000000+0,
     '출장비':2610000+0,'상여':4000000+0,'기타수당':6150000+0}
for k,v in AGG.items():
    actual=sum(e[k] for e in emp)
    if abs(actual-v)>1:
        add('치명','R16 집계표 대사',f'{k}',' 전사',
            f"집계표 {v:,}원 ≠ 급여대장 합계 {actual:,}원",actual-v,'집계표/대장 불일치')

# R17 연장수당 집계시트 대사 (연장 시트)
OT_SHEET={'코코도르':{'연장근로수당':17305750,'휴일특근수당':6789000,'야근교통비':1020000},
          '코코도르팜':{'연장근로수당':1325250,'휴일특근수당':286750,'야근교통비':40000}}
for corp_,d in OT_SHEET.items():
    for k,v in d.items():
        actual=sum(e[k] for e in emp if e['법인']==corp_)
        if abs(actual-v)>1:
            add('치명','R17 연장수당 시트 대사',f'{corp_} {k}',corp_,
                f"'연장' 시트 {v:,}원 ≠ 급여대장 {actual:,}원",actual-v,'시트간 불일치')

sev_order={'치명':0,'주의':1,'참고':2}
issues.sort(key=lambda x:(sev_order[x['심각도']],x['검증항목'],-abs(x['차이'] or 0)))
out['issues']=issues
out['issueSummary']=[{'심각도':k,'건수':v} for k,v in sorted(collections.Counter(i['심각도'] for i in issues).items(),key=lambda x:sev_order[x[0]])]
byrule=collections.OrderedDict()
for i in issues:
    r=byrule.setdefault(i['검증항목'],{'검증항목':i['검증항목'],'심각도':i['심각도'],'건수':0,'금액영향':0})
    r['건수']+=1; r['금액영향']+=abs(i['차이'] or 0)
out['issueByRule']=sorted(byrule.values(),key=lambda x:(sev_order[x['심각도']],-x['건수']))
out['statusMix']=[{'상태':k,'인원':v} for k,v in collections.Counter(e['재직상태'] for e in emp).most_common()]
out['rules']=[
 {'코드':'R1','항목':'지급총액 합계','기준':'16개 지급항목의 합 = 지급총액'},
 {'코드':'R2','항목':'공제총액 합계','기준':'14개 공제항목의 합 = 공제총액'},
 {'코드':'R3','항목':'실지급액','기준':'지급총액 − 공제총액 = 실지급액'},
 {'코드':'R4','항목':'장기요양보험','기준':'장기요양 = 건강보험 × 13.14% (외국인 가입제외 예외)'},
 {'코드':'R5','항목':'고용보험','기준':'고용보험 = 과세합계 × 0.9%'},
 {'코드':'R6','항목':'국민연금','기준':f'0 ≤ 공제액 ≤ 상한 {CAP_NP:,}원'},
 {'코드':'R7','항목':'4대보험 가입','기준':'최저임금 초과 정상재직자는 국민연금·건강보험 가입 필수'},
 {'코드':'R8','항목':'최저임금','기준':f'계약급여 ≥ 월환산 {MINWAGE_M:,}원 (시급 {MINWAGE_H:,}원×209h). 휴직·중도입퇴사는 예외'},
 {'코드':'R9','항목':'기본급 누락','기준':'고정연장수당 지급자는 기본급 필수'},
 {'코드':'R10','항목':'소득세','기준':'과세소득 발생 시 소득세 징수'},
 {'코드':'R11','항목':'지방소득세','기준':'지방소득세 = 소득세 × 10%'},
 {'코드':'R12','항목':'부서명 표준화','기준':'동일 부서 단일 표기'},
 {'코드':'R13','항목':'소속 지정','기준':'급여 대상자 전원 소속 보유'},
 {'코드':'R14','항목':'입사일','기준':'근속·연차 산정용 입사일 보유'},
 {'코드':'R15','항목':'명부-대장 대조','기준':'직원명부 재직자 = 급여대장 인원'},
 {'코드':'R16','항목':'집계표 대사','기준':'집계 시트 항목별 금액 = 급여대장 합계'},
 {'코드':'R17','항목':'연장수당 시트 대사','기준':'연장 시트 금액 = 급여대장 연장수당 합계'},
]

# ---------- 2 & 6. 월별 인건비 / 매출대비 인건비 ----------
# 출처: '2506 인건비통합 3년간 비용.xlsx' (2023-01~2025-05), 급여파일 집계시트(2025-06, 2026-02), 급여파일 메모(2025-10~2026-02)
M23_REV=[2306983835,2635421559,3183143959,3368703131,3293427291,3001379039,3094981550,3432999780,3455981761,3948805140,3279205220,3927282265]
M23_LAB=[386041014,393177717,401556296,422782947,570019551,405721016,405581887,423434180,455975897,445035491,436027015,489245126]
M24_REV=[3393233580,3433028533,3690790533,4105523583,4874670347,4572658281,3776677754,4824276063,3577318511,3309124722,4694405774,4509363751]
M24_LAB=[447386760,474809319,446891077,507460798,596885141,506747046,451797258,469630087,488910365,489998355,496710976,521186259]
M24_OT =[11635000+1027500,22220000+1237500,21280000+3110546,30364192+1778110,58055625+7641563,22360000+1325285,
         4523664+455500,12687500+1218912,23507500+2546184,15012500+2584236,15485000+1417500,18107500+1599912]
M25_REV=[3619988948,2633208128,5273750837,3053256457,None,None,None,None,None,None,None,None]
M25_LAB=[514707237,480523482,494742060,480531118,502973785,483554557,None,None,None,431625548,439226943,417948497]
M25_OT =[15789000+4340890,10588250+1724342,19276250+1706228,11103500+1195750,28352375+9611091,
         (2611750+960500)+(4107500+1057144),None,None,None,None,None,None]
M26_LAB=[426044607,526035286,None,None,None,None,None,None,None,None,None,None]
# ERP 전사 매출 (SKU 손익 사령탑 대시보드와 동일 기준)
ERP25=[4045404551,3247176773,5896428095,3471838905,3480231819,3014324479,4730333839,3709672625,4765105526,4319037503,3490428326,5020905322]
ERP26=[3463685428,3296090299,4290264719,4505427314,4008475702,3717877651,4341292063,3410555596,None,None,None,None]

def series(year,rev,lab,ot=None,erp=None):
    r=[]
    for i in range(12):
        row={'월':f'{year}-{i+1:02d}','매출':rev[i] if rev else None,'인건비':lab[i],
             '연장수당':(ot[i] if ot else None),'ERP매출':(erp[i] if erp else None)}
        base = row['ERP매출'] or row['매출']
        row['인건비율']=round(lab[i]/base,4) if (lab[i] and base) else None
        r.append(row)
    return r
out['monthly']={
 '2023':series(2023,M23_REV,M23_LAB),
 '2024':series(2024,M24_REV,M24_LAB,M24_OT),
 '2025':series(2025,M25_REV,M25_LAB,M25_OT,ERP25),
 '2026':series(2026,None,M26_LAB,None,ERP26),
}
out['yearly']=[
 {'연도':'2023','매출':sum(M23_REV),'인건비':sum(M23_LAB),'인건비율':round(sum(M23_LAB)/sum(M23_REV),4),'출처':'3개년 인건비 통합(법인 합산 매출)'},
 {'연도':'2024','매출':sum(M24_REV),'인건비':sum(M24_LAB),'인건비율':round(sum(M24_LAB)/sum(M24_REV),4),'출처':'3개년 인건비 통합(법인 합산 매출)'},
 {'연도':'2025','매출':sum(ERP25),'인건비':None,'인건비율':None,'출처':'ERP 전사 매출 / 인건비 일부월 결측'},
 {'연도':'2026','매출':sum(x for x in ERP26 if x),'인건비':None,'인건비율':None,'출처':'ERP 전사 매출 1~8월 / 인건비 1~2월'},
]
# 인건비 카테고리 월별 (집계시트 확보월)
out['categoryMonthly']=[
 {'월':'2025-01','기본급':338560232+27064240,'고정연장수당':69009493+4786691,'추가연장수당':14129500+2629750,'휴일특근수당':689500+1711140,'야근교통비':970000,'연차수당':265782,'직책수당':2400000+300000,'출장비':3010000+585000,'기타수당':2600000,'상여':0,'무급휴가차감':-123656,'지급합계':431906446+37276821},
 {'월':'2025-02','기본급':343476745+26749240,'고정연장수당':71836529+4776771,'추가연장수당':9307750+1643000,'휴일특근수당':170500+81342,'야근교통비':1110000,'연차수당':1598000,'직책수당':2600000+300000,'출장비':2720000+380000,'기타수당':2600000,'상여':400000,'무급휴가차감':-136904,'지급합계':435382620+34530353},
 {'월':'2025-03','기본급':341465064+26857240,'고정연장수당':72590404+4716431,'추가연장수당':11517500+1276000,'휴일특근수당':6858750+430228,'야근교통비':900000,'연차수당':361080,'직책수당':2300000+300000,'출장비':4000000+400000,'기타수당':2900000,'상여':0,'무급휴가차감':-193548,'지급합계':442986750+34179899},
 {'월':'2025-04','기본급':336629513+28728510,'고정연장수당':74155756+5120161,'추가연장수당':8060000+1185750,'휴일특근수당':2123500,'야근교통비':920000+10000,'연차수당':395270+412376,'직책수당':2400000+300000,'출장비':3690000+400000,'기타수당':3900000,'상여':0,'무급휴가차감':-318750-94444,'지급합계':431904248+36262353},
 {'월':'2025-05','기본급':338745729+25714599,'고정연장수당':74206689+4458091,'추가연장수당':16189750+3820750,'휴일특근수당':11422625+5790341,'야근교통비':740000,'연차수당':371110+419143,'직책수당':2400000+200000,'출장비':1860000+310000,'기타수당':4750000,'상여':9300000,'무급휴가차감':-362162,'지급합계':460057075+40812924},
 {'월':'2025-06','기본급':356259980+24645902,'고정연장수당':76625590+4357435,'추가연장수당':2611750+960500,'휴일특근수당':4107500+1057144,'야근교통비':970000+90000,'연차수당':758336+140420,'직책수당':2000000+300000,'출장비':2210000+360000,'기타수당':5650000,'상여':0,'무급휴가차감':0,'지급합계':451293156+32261401},
 {'월':'2026-02','기본급':354945436+23464728,'고정연장수당':80294840+4755750,'추가연장수당':17305750+1271000,'휴일특근수당':6789000+341000,'야근교통비':1020000+40000,'연차수당':2599856,'직책수당':2000000,'출장비':2610000,'기타수당':6150000,'상여':4000000,'무급휴가차감':-3500000-2333334,'지급합계':474414882+27639144},
]

# ---------- 7. 조직 구조 ----------
def band(y):
    if y is None: return '미상'
    if y<1: return '1년 미만'
    if y<3: return '1~3년'
    if y<5: return '3~5년'
    if y<10: return '5~10년'
    return '10년 이상'
ten=collections.defaultdict(lambda:{'인원':0,'인건비':0})
for e in emp:
    b=ten[band(e['근속년수'])]; b['인원']+=1; b['인건비']+=e['지급총액']
ORDER=['1년 미만','1~3년','3~5년','5~10년','10년 이상','미상']
out['tenure']=[{'구간':k,'인원':ten[k]['인원'],'인건비':ten[k]['인건비'],
                '1인평균':round(ten[k]['인건비']/ten[k]['인원'])} for k in ORDER if k in ten]

FUNC={'생산·물류':['음성생산','용인생산','온라인물류','온라인물류*','본사물류','음성물류','포장','음성관리','원예운영','고성'],
      '영업·마케팅':['전략영업팀','해외온라인','온라인영업','영업관리','국내B2B','해외B2B','쿠팡그룹','마케팅그룹','CX'],
      '상품·연구개발':['상품그룹','디자인연구소','디자인그룹','오일연구소','품질','기획'],
      '경영지원':['재무/인사','총무','구매','임원','미지정']}
fmap={d:f for f,ds in FUNC.items() for d in ds}
fn=collections.defaultdict(lambda:{'인원':0,'인건비':0,'변동급여':0})
for e in emp:
    f=fmap.get(e['소속'],'기타'); fn[f]['인원']+=1; fn[f]['인건비']+=e['지급총액']; fn[f]['변동급여']+=e['변동급여']
out['byFunction']=sorted([{'기능':k,**v,'1인평균':round(v['인건비']/v['인원']),
                           '인원비중':round(v['인원']/len(emp),4),'인건비비중':round(v['인건비']/sum(e['지급총액'] for e in emp),4)}
                          for k,v in fn.items()],key=lambda x:-x['인건비'])
out['foreignCount']=sum(1 for e in emp if re.search(r'[A-Z]{2,}',str(e['성명'])))

# ---------- 8. 인건비 절감 방안 (정량) ----------
TOT=sum(e['지급총액'] for e in emp); ANN=TOT*12
fixOT=sum(e['고정연장수당'] for e in emp)
varOT=sum(e['연장근로수당']+e['휴일특근수당'] for e in emp)
commute=sum(e['야근교통비'] for e in emp)
etc=sum(e['기타수당'] for e in emp)
trip=sum(e['출장비'] for e in emp)
newbies=sum(1 for e in emp if (e['근속년수'] or 9)<1)
REPLACE_COST=4_500_000   # 1인 재채용·교육·생산성손실 추정 단가

out['costBase']={'월인건비':round(TOT),'연환산':round(ANN),'인원':len(emp),
                 '고정연장수당':round(fixOT),'실적연장수당':round(varOT),'야근교통비':round(commute),
                 '기타수당':round(etc),'출장비':round(trip),'연장수당총계':round(fixOT+varOT)}
out['savings']=[
 {'번호':1,'과제':'실적연장·휴일특근 사전승인제','현황':f'추가연장+휴일특근 월 {varOT:,.0f}원 (연 {varOT*12:,.0f}원), 수령 {sum(1 for e in emp if e["연장근로수당"] or e["휴일특근수당"])}명',
  '방법':'주 12시간 한도 시스템 차단 + 파트장 사전승인 없는 연장 미인정, 연장 상위 부서 4곳(본사물류·재무/인사·전략영업팀·포장) 우선 적용',
  '절감률':0.20,'연절감액':round(varOT*12*0.20),'난이도':'중','기간':'1개월','리스크':'단기 납기 부하 → 생산 피크기 예외 승인 절차 병행'},
 {'번호':2,'과제':'고정연장수당(포괄임금) 실근로 대비 재설계','현황':f'고정연장수당 월 {fixOT:,.0f}원 (총액의 {fixOT/TOT*100:.1f}%), 연 {fixOT*12:,.0f}원, {sum(1 for e in emp if e["고정연장수당"])}명 수령',
  '방법':'근태 실측으로 고정연장 시간 대비 실근로 괴리 구간 산출 → 신규 입사자부터 실적연동형으로 전환(기존자 불이익변경 금지 준수)',
  '절감률':0.08,'연절감액':round(fixOT*12*0.08),'난이도':'상','기간':'6개월','리스크':'취업규칙 불이익변경 → 기존 인원 소급 적용 불가, 신규자부터 단계 적용'},
 {'번호':3,'과제':'1년 미만 조기이직 방지','현황':f'근속 1년 미만 {newbies}명 ({newbies/len(emp)*100:.0f}%), 1~3년 포함 시 {sum(1 for e in emp if (e["근속년수"] or 9)<3)}명 ({sum(1 for e in emp if (e["근속년수"] or 9)<3)/len(emp)*100:.0f}%)',
  '방법':'입사 90일 온보딩 체크포인트(30/60/90일 면담) + 부서별 멘토 지정. 조기이직 30% 감소 시 재채용·교육비 회피',
  '절감률':0.30,'연절감액':round(newbies*0.30*REPLACE_COST),'난이도':'중','기간':'3개월','리스크':'효과 측정에 12개월 소요 — 분기 이직률로 선행 관리'},
 {'번호':4,'과제':'야근교통비·기타수당 지급기준 표준화','현황':f'야근교통비 월 {commute:,.0f}원({sum(1 for e in emp if e["야근교통비"])}명), 기타수당 월 {etc:,.0f}원({sum(1 for e in emp if e["기타수당"])}명)',
  '방법':'기타수당 15명 지급사유 전수 점검 → 상시성 항목은 기본급/직책수당으로 편입, 일회성은 승인기준 문서화',
  '절감률':0.15,'연절감액':round((commute+etc)*12*0.15),'난이도':'하','기간':'1개월','리스크':'개인별 실수령 감소 → 편입 방식으로 총액 유지 설계'},
 {'번호':5,'과제':'출장비 정산 기준 재정비','현황':f'출장비 월 {trip:,.0f}원, {sum(1 for e in emp if e["출장비"])}명 / 출장 고정지급 5,000,000원 별도 운영',
  '방법':'실비정산 원칙 전환, 고정 출장수당은 실제 출장일수 연동. 출장 시트상 일수 대비 단가 적정성 검증',
  '절감률':0.12,'연절감액':round(trip*12*0.12),'난이도':'하','기간':'2개월','리스크':'영업활동 위축 → 일수 기준 상한제로 설계'},
 {'번호':6,'과제':'급여 데이터 정합성 확보(간접효과)','현황':f'검증 미스 {len([i for i in out["issues"] if i["심각도"]=="치명"])}건(치명) — 4대보험 미가입 1건, 부서명 분리집계 1건, 소속 미지정 3명',
  '방법':'4대보험 취득신고 즉시 보정, 부서 마스터 단일화, 소속 미지정 해소. 과태료·소급보험료 리스크 차단',
  '절감률':0.0,'연절감액':0,'난이도':'하','기간':'즉시','리스크':'미조치 시 국민연금·건보 소급징수 + 과태료 발생'},
]
out['savingsTotal']=sum(s['연절감액'] for s in out['savings'])

# ---------- 9~11. 인재 전략 ----------
out['talentFacts']={
 '총인원':len(emp),'외국인추정':out['foreignCount'],
 '근속1년미만':newbies,'근속3년미만':sum(1 for e in emp if (e['근속년수'] or 9)<3),
 '근속10년이상':sum(1 for e in emp if (e['근속년수'] or 0)>=10),
 '평균근속':round(sum(e['근속년수'] for e in emp if e['근속년수'] is not None)/sum(1 for e in emp if e['근속년수'] is not None),1),
 '직책보유':sum(1 for e in emp if e['직책'] not in ('님','-','None')),
 '생산물류비중':round(sum(1 for e in emp if fmap.get(e['소속'])=='생산·물류')/len(emp),4),
 '월인건비':round(TOT),'1인평균':round(TOT/len(emp)),
 '식대':sum(e['식대'] for e in emp),
}
json.dump(out,open('hrdata.json','w'),ensure_ascii=False)
print('WROTE hrdata.json keys=',len(out))

# ---------- 4. 개인별 급여 히스토리 (2025-07 계약급여 대비) ----------
import openpyxl as _ox
_wb=_ox.load_workbook('payroll2508.xlsx',data_only=True)
prev={}
for _sh in ['코코도르_급여총괄','코팜_급여총괄']:
    for _r in _wb[_sh].iter_rows(min_row=3,values_only=True):
        _no,_nm=_r[2],_r[3]
        if not _nm or not str(_nm).strip() or not _no: continue
        try: _b=float(_r[11] or 0); _f=float(_r[13] or 0); _c=float(_r[14] or 0)
        except: continue
        prev[str(_no).strip()]={'기본급':round(_b),'고정연장수당':round(_f),
                                '계약급여':round(_c if _c else _b+_f),'소속':_r[4],'직책':_r[7]}
matched=0; org_moves=[]
for e in emp:
    p=prev.get(str(e['직원번호']).strip()) if e['직원번호'] else None
    if p and p['계약급여']>0:
        matched+=1
        e['전기계약급여']=p['계약급여']; e['전기소속']=p['소속']; e['전기직책']=p['직책']
        e['인상액']=e['계약급여']-p['계약급여']
        e['인상률']=round((e['계약급여']-p['계약급여'])/p['계약급여'],4)
        if p['소속'] and str(p['소속']).strip()!=e['소속']:
            org_moves.append({'성명':e['성명'],'2025-07':str(p['소속']).strip(),'2026-02':e['소속'],
                              '직책변화':f"{p['직책']} → {e['직책']}" if str(p['직책'])!=e['직책'] else e['직책']})
    else:
        e['전기계약급여']=None; e['인상액']=None; e['인상률']=None; e['전기소속']=None; e['전기직책']=None
out['historyMeta']={'비교기준월':'2025-07','대상월':'2026-02','매칭인원':matched,'전체인원':len(emp),
  '비고':'2025-07 파일의 급여총괄 시트는 연봉 산정용이라 월 실지급이 아닌 계약급여(기본급+고정연장수당)만 비교 가능. 2025년 전사 급여내역 원본은 암호화되어 열람 불가.'}
out['orgMoves']=org_moves
_ups=[e for e in emp if e['인상률'] is not None and e['재직상태']=='정상']
out['raiseStats']={'비교대상':len(_ups),'인상자':sum(1 for e in _ups if e['인상액']>0),'동결':sum(1 for e in _ups if e['인상액']==0),
  '감액':sum(1 for e in _ups if e['인상액']<0),
  '평균인상률':round(sum(e['인상률'] for e in _ups)/len(_ups),4) if _ups else 0,
  '중위인상률':round(sorted(e['인상률'] for e in _ups)[len(_ups)//2],4) if _ups else 0,
  '총인상액':round(sum(e['인상액'] for e in _ups)),'월인건비영향':round(sum(e['인상액'] for e in _ups)),'주의':'휴직·중도입퇴사자는 계약급여가 일할·감액되어 비교에서 제외'}
json.dump(out,open('hrdata.json','w'),ensure_ascii=False)
print('history matched',matched,'org moves',len(org_moves))
print(out['raiseStats'])

_clean=[e for e in _ups if abs(e['인상률'])<1.0]
out['raiseStats']['정상범위대상']=len(_clean)
out['raiseStats']['평균인상률_이상치제외']=round(sum(e['인상률'] for e in _clean)/len(_clean),4) if _clean else 0
out['raiseStats']['이상치']=[{'성명':e['성명'],'소속':e['소속'],'전기':e['전기계약급여'],'당기':e['계약급여'],'인상률':e['인상률']}
                          for e in _ups if abs(e['인상률'])>=1.0]
out['raiseBands']=[]
for lo,hi,lab in [(-9,-0.0001,'감액'),(0,0.0001,'동결'),(0.0001,0.03,'0~3%'),(0.03,0.05,'3~5%'),(0.05,0.10,'5~10%'),(0.10,9,'10% 이상')]:
    g=[e for e in _ups if lo<=e['인상률']<hi] if lab!='동결' else [e for e in _ups if e['인상액']==0]
    if lab=='감액': g=[e for e in _ups if e['인상액']<0]
    out['raiseBands'].append({'구간':lab,'인원':len(g),'금액':round(sum(e['인상액'] for e in g))})
json.dump(out,open('hrdata.json','w'),ensure_ascii=False)
print('trimmed mean',out['raiseStats']['평균인상률_이상치제외'],'bands',out['raiseBands'])
