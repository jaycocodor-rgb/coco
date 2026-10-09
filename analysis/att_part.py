# -*- coding: utf-8 -*-
"""근태 조회 — 사람 단위로 모은다.

   일 단위 보고를 사람 단위로 뒤집는다. 부서·개인·근태유형으로 찾는 화면용이다.
   지금 가진 개인별 근태 기록은 셋뿐이다.
     ① 2026-09-23 하루 전원 근태유형 (일일보고)
     ② 휴직·산재 요양 기간 (인사마스터) — 유일하게 여러 해에 걸친 기록
     ③ 연차수당·무급휴가 금액 (2026-02 급여대장)
   5240 API가 붙으면 ①이 매일로 바뀐다. 그 전까지는 하루치다.

   출력: hrdata.json['attDesk']
"""
import json, collections, datetime

d = json.load(open('hrdata.json', encoding='utf-8'))
E = d['employees']
AP = {r['성명']: r for r in d['applyDesk']['records']}
DL = d['daily']
H = d['hrMaster']
TODAY = datetime.date(2026, 10, 9)

def num(v):
    try: return float(v or 0)
    except (TypeError, ValueError): return 0.0

def dparse(s):
    try: return datetime.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError): return None

# ── ① 2026-09-23 하루 근태유형 ─────────────────────────────────────
DAY = DL['근태']['일자']
day_type = {}
for r in DL['근태']['rows']:
    for nm in (r.get('코코도르명단') or []) + (r.get('코팜명단') or []):
        day_type[nm] = r['유형']
day_note = {r['유형']: (r.get('비고') or '') for r in DL['근태']['rows']}

# ── ② 휴직 · 요양 ────────────────────────────────────────────────
leave = {r['성명']: r for r in H.get('leave', [])}
injury = collections.defaultdict(list)
for r in H.get('injury', []):
    injury[r['성명']].append(r)

# ── 사람별 행 ─────────────────────────────────────────────────────
people = []
for e in E:
    nm = e['성명']
    ap = AP.get(nm) or {}
    lv = leave.get(nm)
    inj = injury.get(nm) or []
    근태 = day_type.get(nm)

    휴직일수 = None
    if lv:
        st = dparse(lv.get('휴직시작'))
        en = None if lv.get('복직미정') else dparse(lv.get('복직예정'))
        휴직일수 = ((en or TODAY) - st).days if st else None

    요양일수 = sum(int(x.get('요양일수') or 0) for x in inj)

    people.append({
        '직원번호': str(e.get('직원번호') or ''), '성명': nm,
        '법인': e.get('법인'), '소속': e.get('소속'), '직책': e.get('직책'),
        '직위': ap.get('직위'), '직군': e.get('직군세부'), '사업장': e.get('사업장'),
        '입사일': e.get('입사일'), '근속년수': e.get('근속년수'),
        '재직상태': e.get('재직상태'),
        '당일근태': 근태 or '기록없음',
        '휴직': bool(lv),
        '휴직시작': (lv or {}).get('휴직시작'),
        '복직예정': ('미정' if (lv or {}).get('복직미정') else (lv or {}).get('복직예정')) if lv else None,
        '휴직일수': 휴직일수,
        '요양건수': len(inj), '요양일수': 요양일수,
        '요양기간': [{'시작': x.get('요양시작'), '종료': x.get('요양종료'),
                     '일수': x.get('요양일수'), '재해형태': x.get('재해형태')} for x in inj],
        '연차수당': round(num(e.get('연차수당'))),
        '연가보상비': round(num(e.get('연가보상비'))),
        '무급휴가': round(num(e.get('무급휴가'))),
        '무급휴가차감': round(num(e.get('무급휴가차감'))),
    })

people.sort(key=lambda p: (p['소속'] or '', p['성명']))

# ── 집계 ─────────────────────────────────────────────────────────
유형별 = collections.Counter(p['당일근태'] for p in people if p['당일근태'])
REAL = lambda p: p['당일근태'] not in (None, '', '기록없음')
TYPE_ORDER = [r['유형'] for r in DL['근태']['rows']]
유형rows = [{'유형': t, '인원': 유형별.get(t, 0), '비고': day_note.get(t, ''),
            '비중': round(유형별.get(t, 0) / max(sum(유형별.values()), 1), 4)}
           for t in TYPE_ORDER if 유형별.get(t, 0)]
유형rows.insert(0, {'유형': '기록없음(정상 근무로 봄)', '인원': 유형별.get('기록없음', 0),
                   '비고': '일일보고에 이름이 오르지 않은 사람입니다.',
                   '비중': round(유형별.get('기록없음', 0) / max(len(people), 1), 4)})

부서 = collections.defaultdict(lambda: {'인원': 0, '출근': 0, '연차': 0, '휴직': 0,
                                       '연차수당': 0, '무급휴가차감': 0})
for p in people:
    g = 부서[p['소속'] or '미지정']
    g['인원'] += 1
    t = p['당일근태'] or ''
    if t in ('정상출근', '기록없음'): g['출근'] += 1
    if t.startswith('연차'): g['연차'] += 1
    if p['휴직']: g['휴직'] += 1
    g['연차수당'] += p['연차수당']
    g['무급휴가차감'] += p['무급휴가차감']
부서rows = [dict(소속=k, **v, 출근율=round(v['출근'] / v['인원'], 4) if v['인원'] else 0)
           for k, v in 부서.items()]
부서rows.sort(key=lambda x: -x['인원'])

매칭 = sum(1 for p in people if REAL(p))

d['attDesk'] = {
    '기준일': DAY,
    '출처': '일일보고 %s 근태표 + 인사마스터 휴직·산재 + %s 급여대장' % (DAY, d['asOf']),
    '상태': '개인별 근태 기록은 %s 하루치입니다. 휴직·요양만 여러 해에 걸쳐 있습니다.' % DAY,
    '사람': people,
    '유형별': 유형rows,
    '부서별': 부서rows,
    '집계': {
        '대상': len(people), '당일매칭': 매칭, '미매칭': len(people) - 매칭,
        '정원': DL['근태']['정원']['합계'],
        '유형수': len(유형rows),
        '부서수': len(부서rows),
        '휴직': sum(1 for p in people if p['휴직']),
        '요양': sum(1 for p in people if p['요양건수']),
        '연차수당계': sum(p['연차수당'] for p in people),
        '무급휴가차감계': sum(p['무급휴가차감'] for p in people),
    },
    '보유범위': [
        {'자료': '개인별 일별 근태유형', '범위': DAY + ' 하루', '건수': 매칭,
         '상태': '1일', '설명': '일일보고에 실린 근태표입니다. 5240이 붙으면 매일로 바뀝니다.'},
        {'자료': '휴직 기간', '범위': '2024-04 ~ 현재', '건수': len(leave),
         '상태': '기간 보유', '설명': '시작일과 복직예정일이 있어 날짜축으로 펼칠 수 있습니다.'},
        {'자료': '산재 요양', '범위': '2026-01 ~ 2026-03', '건수': len(H.get('injury', [])),
         '상태': '기간 보유', '설명': '재해일자·요양 시작·종료가 있습니다.'},
        {'자료': '연차수당·무급휴가', '범위': d['asOf'] + ' 한 달', '건수': sum(1 for p in people if p['연차수당'] or p['무급휴가차감']),
         '상태': '금액만', '설명': '사용일수가 아니라 지급·공제 금액입니다. 며칠 썼는지는 모릅니다.'},
        {'자료': '일별 연차 사용·잔여', '범위': '-', '건수': 0,
         '상태': '없음', '설명': '5240 연결 전까지는 개인별 연차 잔여를 알 수 없습니다.'},
    ],
    '한계': [
        '「기록된 것부터 현재까지」를 채우려면 5240 소급 수집이 필요합니다. 지금 화면은 하루치입니다.',
        '5240 접속이 이 서버에서 막혀 있어(방화벽) 회사 PC에서 받아야 합니다. 받는 명령은 9-1 ⑥ 탭에 적어 두었습니다.',
        '연차수당과 무급휴가차감은 금액이라 일수로 환산하려면 개인별 통상임금이 필요합니다.',
        '%s 근태표에 이름이 오른 사람은 %d명뿐입니다. 일일보고가 연차·출장·휴무처럼 예외만 적는 문서여서, 나머지 %d명은 「기록없음」으로 두고 정상 근무로 해석했습니다. 실제 출퇴근 시각은 5240을 붙여야 들어옵니다.'
        % (DAY, 매칭, len(people) - 매칭),
    ],
}

blob = json.dumps(d['attDesk'], ensure_ascii=False)
import re
assert not re.search(r'\d{6}\s*-\s*\d{7}', blob), '주민등록번호 패턴'
assert not re.search(r'01[016-9]-?\d{3,4}-?\d{4}', blob), '휴대폰 패턴'

json.dump(d, open('hrdata.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)

G = d['attDesk']['집계']
print('대상 %d명 · 당일 근태 매칭 %d명 · 미매칭 %d명' % (G['대상'], G['당일매칭'], G['미매칭']))
print('유형 %d · 부서 %d · 휴직 %d · 요양 %d' % (G['유형수'], G['부서수'], G['휴직'], G['요양']))
print()
for r in 유형rows:
    print('  %-14s %4d명  %5.1f%%  %s' % (r['유형'], r['인원'], r['비중'] * 100, r['비고'][:40]))
print()
print('%-14s %4s %4s %4s %4s' % ('소속', '인원', '출근', '연차', '휴직'))
for r in 부서rows[:10]:
    print('%-14s %4d %4d %4d %4d' % (r['소속'], r['인원'], r['출근'], r['연차'], r['휴직']))
