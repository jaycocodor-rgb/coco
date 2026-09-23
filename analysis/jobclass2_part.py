# -*- coding: utf-8 -*-
"""인건비 분석 메뉴 — 직군 집계 · 해외 인력 · 해외 매출 대비 인건비
   jobclass_part.py 실행 뒤에 돌린다."""
import json, collections

d = json.load(open('hrdata.json', encoding='utf-8'))
emps = d['employees']
tw   = d['taiwan']

def agg(rows):
    n = len(rows)
    pay = sum(r['지급총액'] for r in rows)
    ot  = sum(r['연장수당계'] for r in rows)
    base= sum(r['기본급'] for r in rows)
    return {'인원': n, '인건비': pay, '기본급': base, '연장수당': ot,
            '1인평균': round(pay/n) if n else 0,
            '연장비중': round(ot/pay, 4) if pay else 0}

TOT_N   = len(emps)
TOT_PAY = sum(e['지급총액'] for e in emps)

def withshare(rows, label, **extra):
    a = agg(rows); a['구분'] = label
    a['인원비중']   = round(a['인원']/TOT_N, 4)
    a['인건비비중'] = round(a['인건비']/TOT_PAY, 4) if TOT_PAY else 0
    a.update(extra); return a

# ── 1. 직군 2단 집계 ────────────────────────────────────────────────
tree = []
for jc in ['사무직', '센터직', '미지정']:
    rs = [e for e in emps if e['직군'] == jc]
    if not rs: continue
    node = withshare(rs, jc)
    subs = []
    order = {'사무직': ['영업직','관리직'], '센터직': ['물류','생산'], '미지정': ['미지정']}[jc]
    for sub in order:
        ss = [e for e in rs if e['직군세부'] == sub]
        if ss: subs.append(withshare(ss, sub))
    node['하위'] = subs
    tree.append(node)
d['jobClassTree'] = tree

# ── 2. 영업 파트별 ──────────────────────────────────────────────────
sales = [e for e in emps if e['직군세부'] == '영업직']
parts = []
for part in sorted({e['파트'] for e in sales},
                   key=lambda p: -sum(e['지급총액'] for e in sales if e['파트'] == p)):
    rs = [e for e in sales if e['파트'] == part]
    parts.append(withshare(rs, part, 영업구분=rs[0]['영업구분']))
d['salesParts']   = parts
d['salesSummary'] = {
    '전체': withshare(sales, '영업직 계'),
    '직접영업': withshare([e for e in sales if e['영업구분'] == '직접영업'], '직접영업'),
    '영업지원': withshare([e for e in sales if e['영업구분'] == '영업지원'], '영업지원'),
}

# ── 3. 센터직 물류/생산 × 사업장 ────────────────────────────────────
center = [e for e in emps if e['직군'] == '센터직']
cparts = []
for sub in ['생산', '물류']:
    for part in sorted({e['파트'] for e in center if e['직군세부'] == sub},
                       key=lambda p: -sum(e['지급총액'] for e in center if e['파트'] == p)):
        rs = [e for e in center if e['파트'] == part]
        cparts.append(withshare(rs, part, 세부=sub, 사업장=rs[0]['사업장']))
d['centerParts'] = cparts
d['centerBySite'] = [withshare([e for e in center if e['사업장'] == st], st)
                     for st in sorted({e['사업장'] for e in center},
                                      key=lambda s: -sum(e['지급총액'] for e in center if e['사업장'] == s))]

# ── 4. 관리직 파트별 ────────────────────────────────────────────────
admin = [e for e in emps if e['직군세부'] == '관리직']
d['adminParts'] = [withshare([e for e in admin if e['파트'] == p], p)
                   for p in sorted({e['파트'] for e in admin},
                                   key=lambda p: -sum(e['지급총액'] for e in admin if e['파트'] == p))]

# ── 5. 해외 인력 ────────────────────────────────────────────────────
OVERSEAS_DEPT = ['해외온라인', '해외B2B']
ovs_kr = [e for e in emps if e['소속'] in OVERSEAS_DEPT]
kr_blocks = [withshare([e for e in ovs_kr if e['소속'] == dp], dp) for dp in OVERSEAS_DEPT]
ovs_kr_sum = withshare(ovs_kr, '한국 해외담당')

d['overseas'] = {
    '지사': {'법인': '대만법인', '기준월': tw['기준월'], '인원': tw['인원'],
            '지급계': tw['지급계_KRW'], '회사부담': tw['회사부담_KRW'],
            '총원가': tw['총원가_KRW'], '1인평균': tw['1인평균_KRW'], '환율': tw['환율']},
    '한국담당': {'계': ovs_kr_sum, '부서': kr_blocks},
    '합계': {'인원': tw['인원'] + ovs_kr_sum['인원'],
            '인건비': tw['총원가_KRW'] + ovs_kr_sum['인건비'],
            '1인평균': round((tw['총원가_KRW'] + ovs_kr_sum['인건비']) / (tw['인원'] + ovs_kr_sum['인원']))},
    '국내외국인참고': {'인원': d['foreignSummary']['재직'],
                  '인건비': d['foreignSummary']['월급여총액'],
                  '설명': '국적이 외국인 한국 근무자입니다. 해외 인력(지사·해외담당)과는 다른 집계입니다.'},
}

# ── 6. 해외 매출 대비 인건비 ────────────────────────────────────────
# 출처: ★전사 광고 손익_상세(2026).xlsx 「01. 채널(월)」 2026-01~09 실측
CH26 = {'쿠팡': (9234349094, 9), '아마존': (6727794336, 9),
        '네이버': (1975568790, 9), '자사몰': (1060330848, 9)}
# 출처: COCODOR_대만_1-7월_채널손익_실측분석.xlsx 「01_총괄현황」 (SHOPEE 특판+직영, TWD)
TW_SHOPEE_TWD, TW_MONTHS = 24795387, 7
tw_rev_m = round(TW_SHOPEE_TWD * tw['환율'] / TW_MONTHS)
amz_m    = round(CH26['아마존'][0] / CH26['아마존'][1])

rows = [
    {'구분': '해외온라인 (아마존)', '인력': '한국 해외온라인 6명',
     '월매출': amz_m, '월인건비': kr_blocks[0]['인건비'], '인원': kr_blocks[0]['인원'],
     '인건비율': round(kr_blocks[0]['인건비'] / amz_m, 4),
     '매출출처': '전사 광고 손익 2026-01~09 실측 월평균'},
    {'구분': '대만법인 (SHOPEE)', '인력': '대만 지사 15명',
     '월매출': tw_rev_m, '월인건비': tw['총원가_KRW'], '인원': tw['인원'],
     '인건비율': round(tw['총원가_KRW'] / tw_rev_m, 4),
     '매출출처': '대만 채널손익 2026-01~07 실측 월평균 (SHOPEE만)'},
    {'구분': '해외B2B (수출)', '인력': '한국 해외B2B 4명',
     '월매출': None, '월인건비': kr_blocks[1]['인건비'], '인원': kr_blocks[1]['인원'],
     '인건비율': None, '매출출처': '수출 매출 원본 미확보'},
]
ov_rev = amz_m + tw_rev_m
ov_pay = kr_blocks[0]['인건비'] + tw['총원가_KRW']
d['overseasRatio'] = {
    '행': rows,
    '합계': {'월매출': ov_rev, '월인건비': ov_pay, '인건비율': round(ov_pay / ov_rev, 4),
            '인원': kr_blocks[0]['인원'] + tw['인원']},
    '국내비교': {'채널월매출': round(sum(v for v, m in CH26.values()) / 9),
              '전사월인건비': TOT_PAY,
              '전사인건비율': round(TOT_PAY / (sum(v for v, m in CH26.values()) / 9), 4)},
    '한계': [
        '해외B2B(수출) 매출 원본이 없어 4명이 분모에 반영되지 않았습니다. 실제 해외 인건비율은 이 값보다 낮습니다.',
        '대만은 SHOPEE 채널만 집계된 매출이라 분모가 과소합니다. 다른 채널 매출이 들어오면 비율이 내려갑니다.',
        '분자는 해당 조직의 직접 인건비만 담았습니다. 물류·생산·경영지원이 나눠 지는 몫은 들어 있지 않습니다.',
        '전사 인건비율(전 채널 기준)은 같은 방식으로 계산한 비교용 수치입니다.',
    ],
}
json.dump(d, open('hrdata.json', 'w'), ensure_ascii=False)

# ── 검산 ────────────────────────────────────────────────────────────
print('직군 트리')
for n in tree:
    print(f"  {n['구분']:5s} {n['인원']:3d}명 {n['인건비']:>12,} ({n['인건비비중']:.1%})")
    for s in n['하위']:
        print(f"     └ {s['구분']:5s} {s['인원']:3d}명 {s['인건비']:>12,} 연장 {s['연장비중']:.1%}")
print('\n영업 파트', len(parts), '| 직접', d['salesSummary']['직접영업']['인원'],
      '| 지원', d['salesSummary']['영업지원']['인원'])
print('센터 파트', len(cparts), '| 사업장', [(x['구분'], x['인원']) for x in d['centerBySite']])
print('관리 파트', len(d['adminParts']))
print('\n해외 인력', d['overseas']['합계'])
print('해외 매출대비', d['overseasRatio']['합계'], '| 전사', d['overseasRatio']['국내비교'])
