# -*- coding: utf-8 -*-
"""직군 분류 — 사무직(영업직/관리직) · 센터직(물류/생산) · 해외
   급여대장 2026-02 「소속」을 기준으로 분류한다. 조직도(2026-09-28)는 시점이 달라
   부서명이 일치하지 않으므로 분류 근거로 쓰지 않는다."""
import json, collections, re

d = json.load(open('hrdata.json', encoding='utf-8'))
emps = d['employees']

# ── 소속 → (직군, 세부, 파트라벨, 사업장) ────────────────────────────
SALES_DIRECT = ['전략영업팀','온라인영업','해외온라인','영업관리','해외B2B','국내B2B','쿠팡그룹']
SALES_SUPPORT= ['마케팅그룹','디자인그룹']
ADMIN        = ['구매','상품그룹','재무/인사','디자인연구소','총무','기획','오일연구소','CX','임원']
LOGI         = {'온라인물류*':'본사','온라인물류':'본사','본사물류':'본사','음성물류':'음성'}
PROD         = {'음성생산':'음성','음성관리':'음성','포장':'음성','품질':'음성',
                '용인생산':'용인','원예운영':'고성','고성':'고성'}

def classify(e):
    dept, co = e['소속'], e['법인']
    if not dept or dept == '미지정':
        return ('미지정','미지정','소속 미지정','—')
    if dept in SALES_DIRECT:   return ('사무직','영업직', dept, '본사')
    if dept in SALES_SUPPORT:  return ('사무직','영업직', dept, '본사')
    if dept in ADMIN:          return ('사무직','관리직', dept, '본사')
    if dept in LOGI:           return ('센터직','물류',   dept, LOGI[dept])
    if dept in PROD:           return ('센터직','생산',   dept, PROD[dept])
    raise SystemExit('미분류 소속: %r (%s)' % (dept, co))

for e in emps:
    jc, sub, part, site = classify(e)
    e['직군'], e['직군세부'], e['파트'], e['사업장'] = jc, sub, part, site
    e['영업구분'] = ('직접영업' if e['소속'] in SALES_DIRECT else
                    '영업지원' if e['소속'] in SALES_SUPPORT else '')

# ── 분류 검산: 인원 합이 전체와 맞는지 ───────────────────────────────
tot = len(emps)
chk = collections.Counter(e['직군'] for e in emps)
assert sum(chk.values()) == tot, '직군 합 불일치'

d['jobClassMap'] = {
    '사무직': {'영업직': {'직접영업': SALES_DIRECT, '영업지원': SALES_SUPPORT},
              '관리직': ADMIN},
    '센터직': {'물류': LOGI, '생산': PROD},
}
d['jobClassMeta'] = {
    '기준': '한국 2026-02 급여대장 「소속」 154명',
    '주의': [
        '마케팅그룹·디자인그룹은 조직도상 전략영업팀 하위라 영업직에 넣되 「영업지원」으로 따로 표기했습니다.',
        '본사물류는 본사에 있으나 업무가 물류라 센터직으로 분류했습니다.',
        '음성관리·품질은 음성 사업장 소속이라 센터직 생산에 포함했습니다.',
        '소속이 비어 있는 3명은 어느 직군에도 넣지 않고 「미지정」으로 남겼습니다. (검증 R13)',
        '대만법인 15명은 별도 급여대장이라 이 표에 들어가지 않습니다. 해외 블록에서 따로 봅니다.',
    ],
}
json.dump(d, open('hrdata.json','w'), ensure_ascii=False)

# ── 콘솔 검산 출력 ───────────────────────────────────────────────────
def agg(rows):
    return (len(rows), sum(r['지급총액'] for r in rows), sum(r['연장수당계'] for r in rows))
print('총원', tot)
for jc in ['사무직','센터직','미지정']:
    rs = [e for e in emps if e['직군']==jc]; n,p,o = agg(rs)
    print(f'{jc:5s} {n:3d}명 {p:>12,}  연장 {o:>10,}')
    for sub in sorted({e['직군세부'] for e in rs}):
        ss=[e for e in rs if e['직군세부']==sub]; n2,p2,o2=agg(ss)
        print(f'   └ {sub:6s} {n2:3d}명 {p2:>12,}  연장 {o2:>10,}')
