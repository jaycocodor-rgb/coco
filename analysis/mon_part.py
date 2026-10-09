# -*- coding: utf-8 -*-
"""월별 인원 변동표 — 가로축 월, 세로축 항목.

   5240 인사명부의 퇴사자 306명(입사일·퇴직일)과 급여대장 재직자를 합쳐
   월초·월말 재적을 다시 세운다. 연도 단위 이직률은 이미 있으니
   같은 모수로 월 단위까지 쪼개고, 연간 합이 기존 숫자와 맞는지 확인한다.

   출력: hrdata.json['monthDesk']
"""
import json, datetime, calendar, collections

d = json.load(open('hrdata.json', encoding='utf-8'))
H = d['hrMaster']
E = d['employees']
SV = d.get('sevDesk') or {}
MON = d['monthly']

def dp(s):
    try: return datetime.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError): return None

# ── 명부 합치기 ────────────────────────────────────────────────
# 퇴사자는 인사명부가 원본이다. 재직자는 급여대장에서 가져오되 이름이 겹치면 명부를 쓴다.
roster = []
seen = set()
for x in H['leavers']:
    j, q = dp(x.get('입사일')), dp(x.get('퇴직일'))
    if not j or not q: continue
    roster.append({'성명': x['성명'], '입사': j, '퇴직': q,
                   '구분': x.get('직원구분') or '미기재', '소속': x.get('소속') or '미지정'})
    seen.add(x['성명'])
for e in E:
    if e['성명'] in seen: continue
    j = dp(e.get('입사일'))
    if not j: continue
    roster.append({'성명': e['성명'], '입사': j, '퇴직': dp(e.get('퇴사일')),
                   '구분': '미기재', '소속': e.get('소속') or '미지정'})
    seen.add(e['성명'])
# 급여대장은 2026-02 기준이라 그 뒤 입사자가 빠진다. 퇴직연금 대장(2024~2026)으로 메운다.
for x in (SV.get('사람') or []):
    if x['성명'] in seen: continue
    j = dp(x.get('입사일'))
    if not j: continue
    roster.append({'성명': x['성명'], '입사': j, '퇴직': dp(x.get('퇴직일자')),
                   '구분': '미기재', '소속': x.get('법인') or '미지정'})
    seen.add(x['성명'])

# 경비구분(제조/판관)은 퇴직연금 대장에만 있다. 이름으로 붙인다.
cost = {s['성명']: s.get('경비구분') for s in (SV.get('사람') or [])}
for r in roster:
    r['경비'] = cost.get(r['성명']) or '미기재'

# ── 휴직 · 산재 기간 ──────────────────────────────────────────
TODAY = datetime.date(2026, 10, 9)
leaves = []
for x in H.get('leave', []):
    st = dp(x.get('휴직시작'))
    if not st: continue
    en = None if x.get('복직미정') else dp(x.get('복직예정'))
    leaves.append((st, en or TODAY))
injs = []
for x in H.get('injury', []):
    st, en = dp(x.get('요양시작')), dp(x.get('요양종료'))
    if st: injs.append((st, en or TODAY))

# ── 월 축 ────────────────────────────────────────────────────
Y0, Y1 = 2022, 2026
months = ['%d-%02d' % (y, m) for y in range(Y0, Y1 + 1) for m in range(1, 13)]
LAST = '2026-09'                      # 인사명부 추출 2026-09-21
months = [m for m in months if m <= LAST]

PAY = {}
for y, rows in MON.items():
    for r in rows:
        PAY[r['월']] = r.get('인건비')

def span(m):
    y, mm = int(m[:4]), int(m[5:])
    return datetime.date(y, mm, 1), datetime.date(y, mm, calendar.monthrange(y, mm)[1])

rows = []
for m in months:
    a, b = span(m)
    at = lambda day: [r for r in roster if r['입사'] <= day and (r['퇴직'] is None or r['퇴직'] >= day)]
    기초 = len([r for r in roster if r['입사'] < a and (r['퇴직'] is None or r['퇴직'] >= a)])
    입사 = len([r for r in roster if a <= r['입사'] <= b])
    퇴사 = len([r for r in roster if r['퇴직'] and a <= r['퇴직'] <= b])
    말 = at(b)
    기말 = len(말)
    cc = collections.Counter(r['구분'] for r in 말)
    ec = collections.Counter(r['경비'] for r in 말)
    rows.append({
        '월': m,
        '기초': 기초, '입사': 입사, '퇴사': 퇴사, '기말': 기말, '순증': 입사 - 퇴사,
        '평균인원': round((기초 + 기말) / 2, 1),
        '이직률': round(퇴사 / max((기초 + 기말) / 2, 1), 4),
        '휴직': sum(1 for st, en in leaves if st <= b and en >= a),
        '산재': sum(1 for st, en in injs if st <= b and en >= a),
        '정규직': cc.get('정규직', 0), '계약직': cc.get('계약직', 0),
        '구분미기재': 기말 - cc.get('정규직', 0) - cc.get('계약직', 0),
        '제조': ec.get('제조', 0), '판관': ec.get('판관', 0),
        '경비미기재': 기말 - ec.get('제조', 0) - ec.get('판관', 0),
        '인건비': PAY.get(m),
        '1인인건비': round(PAY[m] / 기말) if PAY.get(m) and 기말 else None,
    })

# ── 연도 요약 + 기존 숫자와 대조 ───────────────────────────────
TURN = {str(x['연도']): x for x in H['turnover']}
연도 = []
for y in range(Y0, Y1 + 1):
    ms = [r for r in rows if r['월'].startswith(str(y))]
    if not ms: continue
    t = TURN.get(str(y)) or {}
    입 = sum(r['입사'] for r in ms); 퇴 = sum(r['퇴사'] for r in ms)
    연도.append({
        '연도': str(y), '개월': len(ms),
        '기초': ms[0]['기초'], '기말': ms[-1]['기말'],
        '입사': 입, '퇴사': 퇴, '순증': 입 - 퇴,
        '명부입사': t.get('입사'), '명부퇴사': t.get('퇴사'),
        '입사차': (입 - t['입사']) if t.get('입사') is not None else None,
        '퇴사차': (퇴 - t['퇴사']) if t.get('퇴사') is not None else None,
        '이직률': round(퇴 / max((ms[0]['기초'] + ms[-1]['기말']) / 2, 1), 4),
        '명부기말': t.get('기말'),
        '기말차': (ms[-1]['기말'] - t['기말']) if t.get('기말') is not None else None,
        '인건비': sum(r['인건비'] or 0 for r in ms) or None,
    })

ITEMS = [
    {'키': '기초',      '이름': '기초 인원',   '단위': '명',  '설명': '그 달 1일 아침의 재적입니다.'},
    {'키': '입사',      '이름': '입사',        '단위': '명',  '설명': '입사일이 그 달에 있는 사람입니다.'},
    {'키': '퇴사',      '이름': '퇴사',        '단위': '명',  '설명': '퇴직일이 그 달에 있는 사람입니다.'},
    {'키': '순증',      '이름': '순증',        '단위': '명',  '설명': '입사에서 퇴사를 뺀 값입니다.'},
    {'키': '기말',      '이름': '기말 인원',   '단위': '명',  '설명': '그 달 말일의 재적입니다. 다음 달 기초와 같습니다.'},
    {'키': '이직률',    '이름': '월 이직률',   '단위': '%',   '설명': '퇴사 ÷ 평균인원입니다. 연율이 아니라 그 달 값입니다.'},
    {'키': '휴직',      '이름': '휴직 중',     '단위': '명',  '설명': '휴직 기간이 그 달과 겹치는 사람입니다. 기말 인원에 들어 있습니다.'},
    {'키': '산재',      '이름': '산재 요양 중', '단위': '명', '설명': '요양 기간이 그 달과 겹치는 사람입니다.'},
    {'키': '정규직',    '이름': '정규직',      '단위': '명',  '설명': '인사명부의 직원구분입니다.'},
    {'키': '계약직',    '이름': '계약직',      '단위': '명',  '설명': '계약직·기간제·촉탁직을 합쳤습니다.'},
    {'키': '구분미기재','이름': '구분 미기재', '단위': '명',  '설명': '재직자는 명부에 직원구분이 없어 대부분 여기 들어갑니다.'},
    {'키': '제조',      '이름': '제조 (직접)', '단위': '명',  '설명': '퇴직연금 대장의 경비구분입니다. 생산 원가로 가는 인원입니다.'},
    {'키': '판관',      '이름': '판관 (간접)', '단위': '명',  '설명': '판매비와 관리비로 가는 인원입니다.'},
    {'키': '경비미기재','이름': '경비 미기재', '단위': '명',  '설명': '2024년 이전 퇴사자는 퇴직연금 대장에 없어 구분이 붙지 않습니다.'},
    {'키': '인건비',    '이름': '월 인건비',   '단위': '원',  '설명': '손익계산서 기준 월 인건비입니다. 2023년부터 있습니다.'},
    {'키': '1인인건비', '이름': '1인 인건비',  '단위': '원',  '설명': '월 인건비 ÷ 기말 인원입니다.'},
]

d['monthDesk'] = {
    '기준일': '2026-09-21',
    '출처': '5240 인사명부 퇴사자 306명(입사일·퇴직일) + 2026-02 급여대장 재직자 + 손익 월 인건비',
    '범위': '%s ~ %s (%d개월). 코코도르 + 코코도르팜입니다. 대만법인과 다른 계열은 명부에 이직률 모수로 들어 있지 않습니다.' % (months[0], months[-1], len(months)),
    '월별': rows,
    '연도': 연도,
    '항목': ITEMS,
    '집계': {
        '개월': len(months), '첫월': months[0], '끝월': months[-1],
        '명부': len(roster),
        '현재기말': rows[-1]['기말'],
        '총입사': sum(r['입사'] for r in rows),
        '총퇴사': sum(r['퇴사'] for r in rows),
        '최대월퇴사': max(rows, key=lambda r: r['퇴사'])['월'],
        '최대월퇴사수': max(r['퇴사'] for r in rows),
        '최대월입사': max(rows, key=lambda r: r['입사'])['월'],
        '최대월입사수': max(r['입사'] for r in rows),
        '대조불일치': sum(1 for y in 연도 if (y['입사차'] or 0) or (y['퇴사차'] or 0)),
        '명부기말': (TURN.get('2026') or {}).get('기말'),
        '기말차': rows[-1]['기말'] - ((TURN.get('2026') or {}).get('기말') or 0),
    },
    '대조': {
        '설명': '퇴사는 인사명부가 원본이라 연간 합이 정확히 맞습니다. 입사와 기말은 모자랍니다. '
                '제가 사람 단위로 가진 명부는 퇴사자 306명과 급여대장·퇴직연금 대장에 이름이 있는 재직자뿐이어서, '
                '명부에만 있는 재직자가 월 축에 올라오지 않습니다. 그 차이를 아래에 그대로 적었습니다. 메우지 않았습니다.',
        '메우는법': '5240에서 재직자 전원의 입사일을 한 번 받으면 입사와 기말이 그 자리에서 맞습니다. '
                    '9-1의 연도별 이직률은 이미 그 모수로 계산된 값이라 그 표는 맞습니다.',
    },
    '없는항목': [
        {'항목': '휴가 사용일수', '왜': '월별 연차 사용 기록이 없습니다. 급여대장의 연차수당은 미사용분 보상 금액이고, 그것도 2026-02 한 달치입니다. 5240 근태를 붙이면 월별로 들어옵니다.'},
        {'항목': '지각 · 조퇴 · 결근', '왜': '같은 이유입니다. 근태 원본이 없습니다.'},
        {'항목': '월별 연장근로시간', '왜': '급여대장 한 달치만 있습니다. 월별 추이는 5240 연결 후입니다.'},
        {'항목': '재직자 고용형태', '왜': '인사명부의 직원구분이 퇴사자에만 채워져 있습니다. 그래서 「구분 미기재」가 현재 인원만큼 큽니다.'},
        {'항목': '2022년 월 인건비', '왜': '손익 월별 자료가 2023년부터입니다.'},
    ],
    '한계': [
        '인원은 인사명부의 입사일·퇴직일로 다시 센 값입니다. 명부에 날짜가 없는 사람은 빠집니다.',
        '연간 합을 기존 9-1 이직률 표와 대조했습니다. 차이가 있으면 「연도 대조」 칸에 그대로 표시했습니다.',
        '휴직자는 기말 인원에 포함돼 있습니다. 빼서 보려면 휴직 줄을 따로 읽으십시오.',
        '제조·판관 구분은 퇴직연금 대장에 이름이 있는 162명만 붙습니다. 그 전 퇴사자는 미기재입니다.',
        '2026-09까지입니다. 명부를 다시 뽑으면 그 뒤가 채워집니다.',
    ],
}

json.dump(d, open('hrdata.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
open('/home/user/coco/hr-dashboard/data.js', 'w', encoding='utf-8').write(
    'window.HR_DATA=' + json.dumps(d, ensure_ascii=False, default=str, separators=(',', ':')) + ';')

G = d['monthDesk']['집계']
print('%s ~ %s (%d개월) · 명부 %d명 · 현재 기말 %d명' % (G['첫월'], G['끝월'], G['개월'], G['명부'], G['현재기말']))
print('총 입사 %d · 총 퇴사 %d · 불일치 연도 %d개' % (G['총입사'], G['총퇴사'], G['대조불일치']))
print('최대 입사월 %s (%d명) · 최대 퇴사월 %s (%d명)' % (G['최대월입사'], G['최대월입사수'], G['최대월퇴사'], G['최대월퇴사수']))
print()
print('%-6s %4s %4s %4s %4s %4s %6s %5s %4s %5s %4s %5s %4s' %
      ('연도','개월','기초','기말','입사','퇴사','이직률','명부입','차','명부퇴','차','명부말','차'))
for y in 연도:
    print('%-6s %4d %4d %4d %4d %4d %5.1f%% %5s %4s %5s %4s %5s %4s' %
          (y['연도'], y['개월'], y['기초'], y['기말'], y['입사'], y['퇴사'], y['이직률']*100,
           y['명부입사'], y['입사차'], y['명부퇴사'], y['퇴사차'], y['명부기말'], y['기말차']))
print()
print('%-9s %5s %4s %4s %5s %5s %4s %4s %5s %5s %5s' %
      ('월','기초','입사','퇴사','기말','순증','휴직','산재','정규','계약','제조'))
for r in rows[-14:]:
    print('%-9s %5d %4d %4d %5d %5d %4d %4d %5d %5d %5d' %
          (r['월'], r['기초'], r['입사'], r['퇴사'], r['기말'], r['순증'],
           r['휴직'], r['산재'], r['정규직'], r['계약직'], r['제조']))
