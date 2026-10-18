# -*- coding: utf-8 -*-
"""53필드 인사 마스터(5240 export, 623명)에서 비식별 항목만 뽑아 집계한다.
   생년월일·연락처·이메일·주소·주민번호는 읽지 않는다. 연령은 구간으로만.
   출력: hrdata.json['roster']  (+ hrDiag['과제2020'] 보강은 diag에서)
"""
import openpyxl, json, datetime, collections

wb = openpyxl.load_workbook('recent/baryeong.xlsx', data_only=True)
ws = wb['Sheet']
hdr = [str(ws.cell(1, c).value or '').strip() for c in range(1, ws.max_column+1)]
H = {h: i for i, h in enumerate(hdr)}
def g(row, name):
    i = H.get(name)
    if i is None: return None
    v = row[i]
    return None if v in (None, 'None', '') else v

PII = {'한자성명','영문성명','생년월일','사내전화','휴대전화','비상연락처','사내메일','외부메일','현거주지'}
rows = []
for r in range(2, ws.max_row+1):
    row = [ws.cell(r, c).value for c in range(1, ws.max_column+1)]
    nm = g(row, '성명')
    if not nm: continue
    rows.append(row)

TODAY = datetime.date(2026,10,18)
def dp(v):
    if isinstance(v,(datetime.datetime,datetime.date)): return v.date() if isinstance(v,datetime.datetime) else v
    s=str(v)[:10]
    try: return datetime.date.fromisoformat(s)
    except: return None
def agebucket(v):
    d=dp(v)
    if not d: return '미상'
    a=(TODAY-d).days//365
    return '20대 이하' if a<30 else '30대' if a<40 else '40대' if a<50 else '50대' if a<60 else '60대 이상'

재직 = [r for r in rows if g(r,'재직상태')=='재직']
def dist(name, src=재직, mapf=None):
    c=collections.Counter()
    for r in src:
        v=g(r,name); v=(mapf(v) if mapf else v) or '미기재'
        c[str(v)]+=1
    return [{'값':k,'인원':v} for k,v in c.most_common()]

# 승진 — 승진일자가 입사일과 다르면 승진 이력 있음, 승진연수 보유
seung=[]
for r in 재직:
    sj=dp(g(r,'승진일자')); ij=dp(g(r,'입사일')); yrs=g(r,'승진연수')
    if sj and ij and sj>ij:
        seung.append({'성명':g(r,'성명'),'소속':g(r,'소속'),'직위':g(r,'직위') or g(r,'직책'),
                      '승진일':sj.isoformat(),'승진연수':str(yrs) if yrs else None})
seung.sort(key=lambda x:x['승진일'],reverse=True)

# 학력 보유율 / 전공 보유
학력보유=sum(1 for r in 재직 if g(r,'학력'))
전공보유=sum(1 for r in 재직 if g(r,'전공'))
추천보유=sum(1 for r in 재직 if g(r,'입사추천자'))

out={
    '기준일':'2026-09-16',
    '출처':'5240 인사 마스터 export (직원명부_입퇴사자전체 / 인사발령보고) 623명 · 53필드. 생년월일·연락처·이메일·주소는 읽지 않음',
    '명부총원':len(rows),
    '재직':len(재직),
    '필드수':len(hdr),
    '필드':[h for h in hdr if h not in PII],
    '제외필드':sorted(PII),
    '학력분포':dist('학력'),
    '연령분포':dist('생년월일', mapf=agebucket),   # 생년월일은 구간으로만 환산, 원값 저장 안 함
    '결혼분포':dist('결혼여부'),
    '성별분포':dist('성별'),
    '채용구분':dist('채용구분명'),
    '근무유형':dist('근무유형'),
    '직무분포':dist('직무명'),
    '직원구분':dist('직원구분'),
    '승진이력':seung,
    '집계':{
        '승진이력자':len(seung),
        '학력보유':학력보유,'학력보유율':round(학력보유/max(len(재직),1),3),
        '전공보유':전공보유,
        '추천채용':추천보유,
    },
    '한계':[
        '5240 export 원본입니다. 그룹 9개 법인 재직자 기준이라 코코도르 단독 급여대장(2026-02)과 인원이 다릅니다.',
        '승진 이력은 승진일자가 입사일보다 뒤인 사람만 셌습니다. 입사와 동시 발령은 승진으로 보지 않았습니다.',
        '학력·전공·입사추천자 칸은 빈 사람이 많습니다. 채워진 인원만 집계했습니다.',
        '생년월일은 연령 구간으로만 환산했고 원값은 저장하지 않았습니다. 연락처·이메일·주소는 아예 읽지 않았습니다.',
    ],
}
d=json.load(open('hrdata.json',encoding='utf-8'))
d['roster']=out
json.dump(d,open('hrdata.json','w',encoding='utf-8'),ensure_ascii=False,default=str)
import re
blob=json.dumps(out,ensure_ascii=False)
assert not re.search(r'\d{6}\s*-\s*\d{7}',blob)
assert not re.search(r'01[016-9]-?\d{3,4}-?\d{4}',blob),'휴대폰 노출'
assert '@' not in blob, '이메일 노출'
print('재직',len(재직),'/명부',len(rows))
print('학력',out['학력분포'])
print('연령',out['연령분포'])
print('채용구분',out['채용구분'])
print('승진이력',len(seung),'예:',seung[:3])
print('직원구분',out['직원구분'])
