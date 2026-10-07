# -*- coding: utf-8 -*-
"""다면평가 — 사람별 DB.

   점수 원본은 없다. 있는 것은 조직이고, 조직에서 「누가 누구를 평가하는가」는 계산된다.
   그래서 이 스크립트가 만드는 것은 점수표가 아니라 배정표다.
   평가를 실시하면 같은 키(직원번호 × 평가자 × 문항)로 점수가 그대로 붙는다.

   출력: hrdata.json['rv360']
"""
import json, collections

d = json.load(open('hrdata.json', encoding='utf-8'))
E = d['employees']
R = d['review360']
AN = {str(r['직원번호']): r for r in d['annual']['rows']}
AP = {str(r['직원번호']): r for r in d['applyDesk']['records']}

PEER_CAP = R['동료상한']          # 동료평가 최대 배정 인원 (4)
UP_MIN   = 3                      # 상향평가 최소 인원 — 미만이면 익명성 보호로 미실시

MGR_TITLE = {'파트장', '반장'}       # 부서 단위 관리자
EXEC_TITLE = {'대표이사', '이사'}    # 임원 — 다면평가는 별도 체계라 대상에서 뺀다

def mgr(e):
    return (e.get('직책') or '').strip() in MGR_TITLE
def exec_(e):
    return (e.get('직책') or '').strip() in EXEC_TITLE

# ── 대상: 퇴사·휴직·임원을 뺀 재직자 ────────────────────────────
def active(e):
    st = str(e.get('재직상태') or '')
    if '퇴사' in st or '휴직' in st: return False
    return bool(e.get('소속')) and not exec_(e)

base = [e for e in E if active(e)]
by_dept = collections.defaultdict(list)
for e in base:
    by_dept[e['소속']].append(e)
for v in by_dept.values():
    v.sort(key=lambda x: str(x.get('직원번호') or ''))

# ── 사람별 배정 ────────────────────────────────────────────────
rows = []
for e in base:
    dept = e['소속']
    mates = by_dept[dept]
    me = str(e['직원번호'])
    peers_all = [x for x in mates if str(x['직원번호']) != me]
    mgrs  = [x for x in mates if mgr(x)]
    staff = [x for x in mates if not mgr(x)]
    나관리자 = mgr(e)

    # 동료평가 — 같은 부서에서 사번 순으로 돌려 최대 4명. 고정 배정이라 매번 같다.
    idx = [i for i, x in enumerate(mates) if str(x['직원번호']) == me][0]
    peers = [mates[(idx + k) % len(mates)] for k in range(1, min(PEER_CAP, len(mates) - 1) + 1)] if len(mates) > 1 else []

    # 나를 평가하는 사람
    받는 = []
    받는.append({'구분': '자기', '성명': e['성명'], '직책': e.get('직책'), '가중치': 0.1})
    for p in peers:
        받는.append({'구분': '동료', '성명': p['성명'], '직책': p.get('직책'), '가중치': 0.3})
    if not 나관리자:
        for m in mgrs:
            받는.append({'구분': '하향', '성명': m['성명'], '직책': m.get('직책'), '가중치': 0.4})
    if 나관리자 and len(staff) >= UP_MIN:
        for s in staff:
            받는.append({'구분': '상향', '성명': s['성명'], '직책': s.get('직책'), '가중치': 0.2})

    # 내가 평가하는 사람
    주는 = [{'구분': '자기', '성명': e['성명']}]
    for p in peers_all:
        pi = [i for i, x in enumerate(mates) if str(x['직원번호']) == str(p['직원번호'])][0]
        그의동료 = [mates[(pi + k) % len(mates)] for k in range(1, min(PEER_CAP, len(mates) - 1) + 1)]
        if any(str(x['직원번호']) == me for x in 그의동료):
            주는.append({'구분': '동료', '성명': p['성명']})
    if 나관리자:
        for s in staff:
            주는.append({'구분': '하향', '성명': s['성명']})
    if (not 나관리자) and len(staff) >= UP_MIN:
        for m in mgrs:
            주는.append({'구분': '상향', '성명': m['성명']})

    an = AN.get(me) or {}
    ap = AP.get(me) or {}
    jg = e.get('직군세부') or '미지정'
    문항수 = len(R['공통문항']) + len(R['직군문항'].get(jg, [])) + (len(R['관리자문항']) if 나관리자 else 0)

    rows.append({
        '직원번호': me, '성명': e['성명'], '법인': e.get('법인'), '소속': dept,
        '직책': e.get('직책'), '직위': ap.get('직위'),
        '관리자': 나관리자, '직군': e.get('직군'), '직군세부': jg,
        '사업장': e.get('사업장'),
        '입사일': e.get('입사일'), '근속년수': e.get('근속년수'),
        '계약연봉': an.get('현재_계약연봉'), '등급': an.get('등급') or ap.get('등급'),
        '부서인원': len(mates), '부서관리자수': len(mgrs), '부서원수': len(staff),
        '받는평가': 받는, '받는건수': len(받는),
        '주는평가': 주는, '주는건수': len(주는),
        '문항수': 문항수,
        '상향미실시': 나관리자 and len(staff) < UP_MIN,
        '관리자공석': len(mgrs) == 0,
        '상태': '미실시',
    })

rows.sort(key=lambda r: (r['소속'], str(r['직원번호'])))

# ── 집계 ───────────────────────────────────────────────────────
총받는 = sum(r['받는건수'] for r in rows)
총주는 = sum(r['주는건수'] for r in rows)
구성 = collections.Counter()
for r in rows:
    for a in r['받는평가']:
        구성[a['구분']] += 1

depts = collections.defaultdict(lambda: {'인원': 0, '관리자': 0, '받는': 0, '공석': False, '상향미실시': 0})
for r in rows:
    g = depts[r['소속']]
    g['인원'] += 1
    g['관리자'] += 1 if r['관리자'] else 0
    g['받는'] += r['받는건수']
    g['공석'] = r['관리자공석']
    g['상향미실시'] += 1 if r['상향미실시'] else 0
deptRows = [{'소속': k, '인원': v['인원'], '관리자': v['관리자'], '응답건수': v['받는'],
             '1인평균': round(v['받는'] / v['인원'], 1),
             '관리자공석': v['공석'], '상향미실시': v['상향미실시']}
            for k, v in depts.items()]
deptRows.sort(key=lambda x: -x['인원'])

관리자목록 = [{'직원번호': r['직원번호'], '성명': r['성명'], '소속': r['소속'],
             '직책': r['직책'], '부서원수': r['부서원수'],
             '상향미실시': r['상향미실시']}
            for r in rows if r['관리자']]
관리자목록.sort(key=lambda x: (-x['부서원수'], x['소속']))

d['rv360'] = {
    '기준일': d.get('asOf') or '2026-02',
    '출처': '2026-02 급여대장 소속·직책 실측 + 인사마스터 직위 + 연봉 히스토리 계약연봉',
    '상태': '배정표입니다. 평가를 실시한 적이 없어 점수는 한 건도 없습니다.',
    '사람': rows,
    '부서별': deptRows,
    '관리자': 관리자목록,
    '척도': R['scale'],
    '가중치': R['weight'],
    '공통문항': R['공통문항'],
    '직군문항': R['직군문항'],
    '관리자문항': R['관리자문항'],
    '집계': {
        '대상': len(rows),
        '관리자': len(관리자목록),
        '부서': len(deptRows),
        '총응답건': 총받는,
        '1인평균': round(총받는 / len(rows), 1) if rows else 0,
        '자기': 구성['자기'], '동료': 구성['동료'], '하향': 구성['하향'], '상향': 구성['상향'],
        '관리자공석부서': sum(1 for x in deptRows if x['관리자공석']),
        '상향미실시': sum(1 for r in rows if r['상향미실시']),
        '완료': 0,
        '동료상한': PEER_CAP,
        '상향최소': UP_MIN,
    },
    '규칙': [
        '자기평가는 전원 1건입니다.',
        '동료평가는 같은 부서에서 사번 순으로 돌려 최대 %d명을 고정 배정합니다. 무작위가 아니라 고정이라, 누가 누구를 평가하는지 매번 같습니다.' % PEER_CAP,
        '하향평가는 부서 직책 보유자가 부서원 전원을 평가합니다. 관리자 본인은 하향평가를 받지 않습니다.',
        '상향평가는 부서원이 %d명 이상인 부서에서만 합니다. 그 미만이면 누가 썼는지 드러나 익명성이 깨집니다.' % UP_MIN,
        '관리자가 없는 부서는 하향·상향이 모두 빠집니다. 본부장이 대행하거나 평가 단위를 본부로 올려야 합니다.',
    ],
    '한계': [
        '임원(대표이사·이사) %d명은 다면평가가 별도 체계라 대상에서 뺐습니다.' % sum(1 for e in E if exec_(e)),
        '점수가 없습니다. 이 화면은 「누가 누구를 평가하는가」까지만입니다.',
        '등급 A·B·C·D는 회사가 집행한 인상률을 네 구간으로 나눈 값이지 평가 결과가 아닙니다.',
        '직책 보유 여부로 관리자를 판정했습니다. 실제 보고 라인이 다르면 배정이 달라집니다.',
        '휴직자는 대상에서 뺐습니다. 복직하면 다시 들어옵니다.',
    ],
}

blob = json.dumps(d['rv360'], ensure_ascii=False)
import re
assert not re.search(r'\d{6}\s*-\s*\d{7}', blob), '주민등록번호 패턴'
assert not re.search(r'01[016-9]-?\d{3,4}-?\d{4}', blob), '휴대폰 패턴'

json.dump(d, open('hrdata.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)

G = d['rv360']['집계']
print('대상 %d명 · 관리자 %d명 · 부서 %d개' % (G['대상'], G['관리자'], G['부서']))
print('총 응답 %d건 (1인평균 %.1f) — 자기 %d · 동료 %d · 하향 %d · 상향 %d'
      % (G['총응답건'], G['1인평균'], G['자기'], G['동료'], G['하향'], G['상향']))
print('관리자 공석 부서 %d개 · 상향 미실시 관리자 %d명' % (G['관리자공석부서'], G['상향미실시']))
print()
print('%-14s %4s %4s %6s %7s %s' % ('소속', '인원', '관리', '응답', '1인평균', '비고'))
for x in deptRows[:12]:
    note = '관리자 공석' if x['관리자공석'] else ('상향 미실시 %d' % x['상향미실시'] if x['상향미실시'] else '')
    print('%-14s %4d %4d %6d %7.1f %s' % (x['소속'], x['인원'], x['관리자'], x['응답건수'], x['1인평균'], note))
print()
s = [r for r in rows if r['관리자']][:5]
for r in s:
    print('%s (%s %s) — 받는 %d건 / 주는 %d건 / 문항 %d개'
          % (r['성명'], r['소속'], r['직책'], r['받는건수'], r['주는건수'], r['문항수']))
