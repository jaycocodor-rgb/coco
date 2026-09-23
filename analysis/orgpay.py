# -*- coding: utf-8 -*-
# 조직도(2026-09-28) 부서 ↔ 급여대장(2026-02) 소속 매핑 후 부서별 급여 산출
import json, collections
d=json.load(open('hrdata.json')); org=d['orgNow']; emp=d['employees']

# 확실한 것만 매핑 (이름이 같거나 명백한 개칭)
MAP={'음성생산':['음성생산'],'온라인물류':['온라인물류','온라인물류*'],'본사물류':['본사물류'],
     '음성물류':['음성물류'],'포장':['포장'],'구매':['구매'],'재무/인사':['재무/인사'],
     '해외B2B':['해외B2B'],'디자인연구소':['디자인연구소'],'오일연구소':['오일연구소'],
     '총무':['총무'],'기획':['기획'],'CX':['CX'],'마케팅':['마케팅그룹'],
     '디자인':['디자인그룹'],'음성SCM':['음성관리']}

bysos=collections.defaultdict(lambda:{'인원':0,'급여':0})
for e in emp:
    if e['법인']!='코코도르': continue
    g=bysos[e['소속']]; g['인원']+=1; g['급여']+=e['지급총액']

used=set()
rows=[]
for u in org['units']:
    for t in u['팀']:
        srcs=MAP.get(t['부서'])
        if srcs:
            used.update(srcs)
            pn=sum(bysos[s]['인원'] for s in srcs); pv=sum(bysos[s]['급여'] for s in srcs)
            rows.append({'본부':u['본부'],'부서':t['부서'],'그룹':t.get('그룹'),
                         '조직도인원':t['표기인원'],'급여소속':' + '.join(srcs),
                         '급여인원':pn,'급여총액':round(pv),
                         '1인평균':round(pv/pn) if pn else 0,'매핑':True})
        else:
            rows.append({'본부':u['본부'],'부서':t['부서'],'그룹':t.get('그룹'),
                         '조직도인원':t['표기인원'],'급여소속':None,
                         '급여인원':None,'급여총액':None,'1인평균':None,'매핑':False})
org['부서급여']=rows
# 본부 합계 (매핑된 부서만)
uni={}
for r in rows:
    u=uni.setdefault(r['본부'],{'본부':r['본부'],'조직도인원':0,'급여인원':0,'급여총액':0,
                                '부서수':0,'매핑부서':0})
    u['조직도인원']+=r['조직도인원']; u['부서수']+=1
    if r['매핑']: u['급여인원']+=r['급여인원']; u['급여총액']+=r['급여총액']; u['매핑부서']+=1
units=sorted(uni.values(),key=lambda x:-x['조직도인원'])
for u in units:
    u['1인평균']=round(u['급여총액']/u['급여인원']) if u['급여인원'] else None
    u['완전매핑']=u['매핑부서']==u['부서수']
org['본부급여']=units
# 급여대장에만 있는 소속 (조직 개편으로 사라졌거나 매핑 불가)
un=[{'소속':k,'인원':v['인원'],'급여총액':round(v['급여'])}
    for k,v in bysos.items() if k not in used]
org['미매핑소속']=sorted(un,key=lambda x:-x['급여총액'])
mapped=sum(r['급여총액'] for r in rows if r['매핑'])
totkr=sum(v['급여'] for v in bysos.values())
org['급여메타']={'급여기준':'2026-02 급여대장 지급총액 (㈜코코도르 140명)',
  '조직도기준일':org['기준일'],
  '매핑부서':sum(1 for r in rows if r['매핑']),'전체부서':len(rows),
  '매핑급여':round(mapped),'코코도르총급여':round(totkr),
  '매핑률':round(mapped/totkr,3),
  '주의':'조직도(2026-09-28)와 급여대장(2026-02)은 7개월 차이가 있고 그 사이 영업 조직이 개편됐습니다. '
        '부서명이 그대로거나 명백히 개칭된 경우만 매핑했고, 영업1~4·본사SCM은 대응 소속을 특정할 수 없어 비웠습니다.'}
d['orgNow']=org
json.dump(d,open('hrdata.json','w'),ensure_ascii=False)
m=org['급여메타']
print(f"매핑 {m['매핑부서']}/{m['전체부서']} 부서 · 급여 {m['매핑급여']:,}원 / {m['코코도르총급여']:,}원 ({m['매핑률']*100:.1f}%)")
print()
for u in units:
    v=f"{u['급여총액']:>12,}원" if u['급여인원'] else '          —'
    print(f"  {u['본부']:12s} 조직도{u['조직도인원']:>3}명  급여{str(u['급여인원'] or '-'):>4}명 {v}  매핑 {u['매핑부서']}/{u['부서수']}")
print()
print('급여대장에만 있는 소속:')
for x in org['미매핑소속']: print(f"  {x['소속']:12s} {x['인원']:>3}명 {x['급여총액']:>12,}원")
