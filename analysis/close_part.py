# -*- coding: utf-8 -*-
"""월간 인사 마감 — 달을 고르면 그 달에 일어난 인사 일이 한 장에 나온다.

   3-1은 숫자를 월 축에 늘어놓은 표이고, 이것은 한 달을 세로로 펼친 마감장이다.
   같은 달에 대해 입사자·퇴사자·휴직자·산재·퇴직금·근태 접수·인건비·원천세를
   한 곳에 모은다. 없는 칸은 비워 두고 왜 없는지 적는다.

   출력: hrdata.json['closeDesk']
"""
import json, datetime, calendar, collections

d = json.load(open('hrdata.json', encoding='utf-8'))
H = d['hrMaster']
E = d['employees']
M = d['monthDesk']
SV = d.get('sevDesk') or {}
DL = d.get('dailyLedger') or {}
TX = (d.get('taxDesk') or {}).get('원천세') or {}

def dp(s):
    try: return datetime.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError): return None

def ym(x):
    dt = dp(x)
    return dt.isoformat()[:7] if dt else None

TODAY = datetime.date(2026, 10, 10)

# ── 월 축 ─────────────────────────────────────────────────────
MROWS = {r['월']: r for r in M['월별']}
months = sorted(MROWS) + ['2026-10']          # 명부는 9월까지, 10월은 진행 중
months = sorted(set(months))

def span(m):
    y, mm = int(m[:4]), int(m[5:])
    return datetime.date(y, mm, 1), datetime.date(y, mm, calendar.monthrange(y, mm)[1])

# ── 입사자 · 퇴사자 ────────────────────────────────────────────
가입 = collections.defaultdict(list)
퇴 = collections.defaultdict(list)
cost = {s['성명']: s.get('경비구분') for s in (SV.get('사람') or [])}
corp = {s['성명']: s.get('법인') for s in (SV.get('사람') or [])}

seen = set()
for x in H['leavers']:
    j, q = dp(x.get('입사일')), dp(x.get('퇴직일'))
    if not j or not q: continue
    seen.add(x['성명'])
    base = {'성명': x['성명'], '소속': x.get('소속') or '미지정',
            '직위': x.get('직위') or '-', '구분': x.get('직원구분') or '미기재',
            '법인': corp.get(x['성명']) or '-', '경비': cost.get(x['성명']) or '미기재'}
    if j.isoformat()[:7] in MROWS or j >= datetime.date(2022, 1, 1):
        가입[j.isoformat()[:7]].append(dict(base, 입사일=j.isoformat()))
    퇴[q.isoformat()[:7]].append(dict(base, 입사일=j.isoformat(), 퇴직일=q.isoformat(),
                                     근속년=x.get('근속년수'), 사유=x.get('퇴직사유') or '미기재'))

for e in E:
    if e['성명'] in seen: continue
    j = dp(e.get('입사일'))
    if not j: continue
    seen.add(e['성명'])
    base = {'성명': e['성명'], '소속': e.get('소속') or '미지정',
            '직위': e.get('직책') or '-', '구분': '미기재',
            '법인': e.get('법인') or '-', '경비': cost.get(e['성명']) or '미기재'}
    가입[j.isoformat()[:7]].append(dict(base, 입사일=j.isoformat()))
    q = dp(e.get('퇴사일'))
    if q: 퇴[q.isoformat()[:7]].append(dict(base, 입사일=j.isoformat(), 퇴직일=q.isoformat(),
                                           근속년=e.get('근속년수'), 사유='미기재'))

for x in (SV.get('사람') or []):
    if x['성명'] in seen: continue
    j = dp(x.get('입사일'))
    if not j: continue
    seen.add(x['성명'])
    base = {'성명': x['성명'], '소속': x.get('법인') or '미지정', '직위': '-',
            '구분': '미기재', '법인': x.get('법인') or '-', '경비': x.get('경비구분') or '미기재'}
    가입[j.isoformat()[:7]].append(dict(base, 입사일=j.isoformat()))

# ── 휴직 · 산재 ───────────────────────────────────────────────
사유 = {x['성명']: x.get('사유') for x in (d.get('leave') or [])}
leaves = []
for x in H.get('leave', []):
    st = dp(x.get('휴직시작'))
    if not st: continue
    leaves.append({'성명': x['성명'], '법인': x.get('법인'), '소속': x.get('소속'),
                   '직위': x.get('직위') or '-', '시작': st,
                   '복직': None if x.get('복직미정') else dp(x.get('복직예정')),
                   '미정': bool(x.get('복직미정')),
                   '사유': 사유.get(x['성명']) or '미기재',
                   '입사일': x.get('입사일'), '근속년수': x.get('근속년수')})
injs = []
for x in H.get('injury', []):
    st = dp(x.get('요양시작'))
    if not st: continue
    injs.append({'성명': x['성명'], '재해일자': x.get('재해일자'), '시작': st,
                 '종료': dp(x.get('요양종료')), '요양일수': x.get('요양일수'),
                 '재해형태': x.get('재해형태'), '의료기관': x.get('의료기관'),
                 '관할지사': x.get('관할지사')})

# ── 월 단위로 붙는 금액 ────────────────────────────────────────
PAY = {}
for y, rows in d['monthly'].items():
    for r in rows:
        if r.get('인건비') is not None: PAY[r['월']] = r['인건비']
PAY_R = (min(PAY), max(PAY)) if PAY else (None, None)
CAT_R = None
CAT = {r['월']: r for r in d.get('categoryMonthly') or []}
CAT_LIST = ', '.join(sorted(CAT))
WHT = {r['월']: r for r in (TX.get('월별') or [])}
LED = {r['월']: r for r in (DL.get('월별') or [])}

# 퇴직연금 월 불입 (임원 제외)
불입 = collections.defaultdict(lambda: {'인원': 0, '금액': 0})
for s in (SV.get('사람') or []):
    for k, v in (s.get('월별') or {}).items():
        g = 불입[k]; g['인원'] += 1; g['금액'] += v
# 퇴직금 지급 (퇴사월 기준)
지급 = collections.defaultdict(list)
for x in (SV.get('퇴직지급') or []):
    k = ym(x.get('퇴사일'))
    if k: 지급[k].append(x)

ATT_DAY = ((d.get('daily') or {}).get('근태') or {}).get('일자')

rows = []
for m in months:
    a, b = span(m)
    mv = MROWS.get(m) or {}
    hj = [x for x in leaves if x['시작'] <= b and (x['복직'] or TODAY) >= a]
    ij = [x for x in injs if x['시작'] <= b and (x['종료'] or TODAY) >= a]
    led = LED.get(m) or {}
    pay = PAY.get(m)
    bi = 불입.get(m) or {}
    pj = 지급.get(m) or []

    확보 = []
    def chk(name, ok, 비고, 해당없음=False):
        # 「없음」은 자료를 못 받은 것이고 「해당 없음」은 그 달에 그 일이 없었던 것이다.
        # 둘을 섞으면 마감률이 거짓이 된다.
        확보.append({'항목': name, '상태': '확보' if ok else ('해당 없음' if 해당없음 else '없음'),
                    '비고': 비고})
    chk('입사·퇴사 명단', bool(가입.get(m) or 퇴.get(m) or mv),
        '인사명부 기준입니다. 재직자 입사일이 일부 빠져 입사 인원이 실제보다 적을 수 있습니다.')
    chk('휴직자 명단', bool(hj),
        '휴직 기간이 이 달과 겹치는 사람 %d명입니다.' % len(hj) if hj else '이 달에 휴직자가 없습니다.',
        해당없음=not hj)
    chk('산재 요양', bool(ij),
        '요양 기간이 이 달과 겹치는 사람 %d명입니다.' % len(ij) if ij else '이 달에 산재 요양이 없습니다. 다행한 일이고 빠진 자료가 아닙니다.',
        해당없음=not ij)
    chk('월 인건비', pay is not None,
        '손익계산서 기준입니다.' if pay is not None
        else '손익 월별 인건비는 %s ~ %s만 있습니다.' % PAY_R)
    chk('급여 항목 상세', m in CAT,
        '기본급·수당별로 나뉘어 있습니다.' if m in CAT
        else '이 달 급여대장을 받지 못했습니다. 지금 가진 달은 %s입니다.' % CAT_LIST)
    chk('원천세 납부', m in WHT,
        '신고·납부액입니다.' if m in WHT else '원천세 신고 파일은 2025-12 ~ 2026-08만 있습니다.')
    chk('퇴직연금 불입', bool(bi.get('인원')),
        '개인별 월납 대장 %d명분입니다.' % bi['인원'] if bi.get('인원')
        else '이 달 월납 대장이 없습니다. 2024년부터만 있고 2023년과 그 이전이 비어 있습니다.')
    chk('일일 근태 보고', bool(led.get('접수')),
        '근무일 %s일 중 %s일 접수했습니다.' % (led.get('근무일'), led.get('접수')) if led.get('접수')
        else ('근무일 %s일 중 한 건도 못 받았습니다.' % led.get('근무일') if led
              else '일일보고를 모으기 시작한 2026-07 이전입니다.'))
    chk('개인별 근태·연차', ATT_DAY and ATT_DAY[:7] == m,
        '%s 하루치만 있습니다.' % ATT_DAY if (ATT_DAY and ATT_DAY[:7] == m) else '근태 원본이 없습니다. 5240을 붙여야 들어옵니다.')
    확보수 = sum(1 for c in 확보 if c['상태'] == '확보')
    해당없음수 = sum(1 for c in 확보 if c['상태'] == '해당 없음')
    분모 = len(확보) - 해당없음수

    rows.append({
        '월': m,
        '인원': {k: mv.get(k) for k in ('기초', '입사', '퇴사', '기말', '순증', '이직률',
                                       '휴직', '산재', '정규직', '계약직', '구분미기재',
                                       '제조', '판관', '경비미기재', '인건비', '1인인건비')},
        '입사자': sorted(가입.get(m) or [], key=lambda x: (x['소속'], x['성명'])),
        '퇴사자': sorted(퇴.get(m) or [], key=lambda x: (x['퇴직일'], x['성명'])),
        '휴직자': [{'성명': x['성명'], '법인': x['법인'], '소속': x['소속'], '직위': x['직위'],
                   '사유': x['사유'], '휴직시작': x['시작'].isoformat(),
                   '복직예정': '미정' if x['미정'] else (x['복직'].isoformat() if x['복직'] else '-'),
                   '이달경과월': round(((b - x['시작']).days) / 30.44, 1),
                   '입사일': x['입사일'], '근속년수': x['근속년수']} for x in hj],
        '산재': [{'성명': x['성명'], '재해일자': x['재해일자'],
                 '요양시작': x['시작'].isoformat(),
                 '요양종료': x['종료'].isoformat() if x['종료'] else '진행',
                 '요양일수': x['요양일수'], '재해형태': x['재해형태'],
                 '의료기관': x['의료기관'], '관할지사': x['관할지사']} for x in ij],
        '퇴직금': [{'성명': x['성명'], '법인': x['법인'], '입사일': x['입사일'],
                   '퇴사일': x['퇴사일'], '지급기한': x.get('지급기한'),
                   '근속년': x.get('근속년'), '총지급': x['총지급'],
                   '지연이자': x.get('지연이자')} for x in pj],
        '돈': {
            '인건비': pay,
            '급여상세': CAT.get(m),
            '원천세': WHT.get(m),
            '불입인원': bi.get('인원') or 0, '불입액': round(bi.get('금액') or 0),
            '퇴직금건': len(pj), '퇴직금액': sum(x['총지급'] for x in pj),
            '연장근무비': led.get('연장근무비'), '출장비': led.get('출장비'),
            '외주용역비': led.get('외주용역비'),
            '보고접수': led.get('접수'), '보고근무일': led.get('근무일'),
        },
        '체크': 확보, '확보수': 확보수, '해당없음': 해당없음수, '분모': 분모,
        '미확보': [c['항목'] for c in 확보 if c['상태'] == '없음'],
        '마감률': round(확보수 / max(분모, 1), 4),
    })

rows.sort(key=lambda r: r['월'], reverse=True)

ITEMS = ['입사·퇴사 명단', '휴직자 명단', '산재 요양', '월 인건비', '급여 항목 상세',
         '원천세 납부', '퇴직연금 불입', '일일 근태 보고', '개인별 근태·연차']

d['closeDesk'] = {
    '기준일': TODAY.isoformat(),
    '출처': '5240 인사명부 · 급여대장 · 퇴직연금 월납 대장 · 손익 월 인건비 · 원천세 신고 · 일일보고',
    '범위': '%s ~ %s (%d개월)' % (rows[-1]['월'], rows[0]['월'], len(rows)),
    '항목': ITEMS,
    '월별': rows,
    '집계': {
        '개월': len(rows), '첫월': rows[-1]['월'], '끝월': rows[0]['월'],
        '항목수': len(ITEMS),
        '평균마감률': round(sum(r['마감률'] for r in rows) / len(rows), 4),
        '최근마감률': rows[0]['마감률'],
        '완전한달': sum(1 for r in rows if not r['미확보']),
        '총입사': sum(r['인원'].get('입사') or 0 for r in rows),
        '총퇴사': sum(r['인원'].get('퇴사') or 0 for r in rows),
        '사유기재': sum(1 for r in rows for x in r['퇴사자'] if x['사유'] != '미기재'),
    },
    '항목별': [{'항목': it,
               '확보': sum(1 for r in rows for c in r['체크'] if c['항목'] == it and c['상태'] == '확보'),
               '없음': sum(1 for r in rows for c in r['체크'] if c['항목'] == it and c['상태'] == '없음'),
               '해당없음': sum(1 for r in rows for c in r['체크'] if c['항목'] == it and c['상태'] == '해당 없음')}
              for it in ITEMS],
    '쓰는법': [
        '달을 고르면 그 달에 들어온 사람, 나간 사람, 휴직한 사람, 다친 사람, 나간 돈이 한 장에 나옵니다.',
        '맨 아래 「마감 점검」이 그 달에 무엇이 확보됐고 무엇이 비었는지 보여 줍니다. 9개 항목이 기준입니다.',
        '매달 이 화면을 열어 「없음」이 줄어드는지 보시면 됩니다. 「해당 없음」은 그 달에 그 일이 없었던 것이라 마감률에서 빼고 셉니다.',
        '퇴사자의 퇴직사유 칸이 거의 비어 있습니다. 이 칸만 채워도 이탈 원인을 말할 수 있습니다.',
    ],
    '한계': [
        '입사 인원은 실제보다 적습니다. 퇴사자는 인사명부로 다 받았는데 재직자 명부를 사람 단위로 받지 못해, 급여대장·퇴직연금 대장에 이름이 없는 재직자가 빠집니다.',
        '개인별 근태와 연차 사용일수는 %s 하루치뿐입니다. 월별로 채우려면 5240 근태를 붙여야 합니다.' % ATT_DAY,
        '급여 항목 상세는 받은 급여대장이 있는 달만 있습니다.',
        '일일보고는 2026년 7월부터만 모았고, 9월만 접수됐습니다.',
        '2026년 10월은 진행 중입니다. 인원 숫자가 비어 있습니다.',
    ],
}

json.dump(d, open('hrdata.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
open('/home/user/coco/hr-dashboard/data.js', 'w', encoding='utf-8').write(
    'window.HR_DATA=' + json.dumps(d, ensure_ascii=False, default=str, separators=(',', ':')) + ';')

import re, os
blob = json.dumps(d['closeDesk'], ensure_ascii=False)
assert not re.search(r'\d{6}\s*-\s*\d{7}', blob), '주민등록번호 패턴'
assert not re.search(r'01[016-9]-?\d{3,4}-?\d{4}', blob), '휴대폰 패턴'

G = d['closeDesk']['집계']
print('%s ~ %s (%d개월) · 항목 %d개 · 평균 마감률 %.0f%% · 완전한 달 %d개'
      % (G['첫월'], G['끝월'], G['개월'], G['항목수'], G['평균마감률']*100, G['완전한달']))
print('퇴사자 사유 기재 %d건 / 총 퇴사 %d명' % (G['사유기재'], G['총퇴사']))
print()
print('%-9s %4s %4s %4s %4s %4s %4s %6s %5s' % ('월','기초','입사','퇴사','기말','휴직','산재','마감률','퇴직금'))
for r in rows[:14]:
    p=r['인원']
    print('%-9s %4s %4s %4s %4s %4d %4d %5.0f%% %5d건'
          % (r['월'], p.get('기초'), p.get('입사'), p.get('퇴사'), p.get('기말'),
             len(r['휴직자']), len(r['산재']), r['마감률']*100, r['돈']['퇴직금건']))
print()
print('2026-07 상세')
x=[r for r in rows if r['월']=='2026-07'][0]
print(' 입사', [p['성명'] for p in x['입사자']])
print(' 퇴사', [(p['성명'],p['소속'],p['근속년']) for p in x['퇴사자']])
print(' 휴직', [(p['성명'],p['사유'],p['복직예정']) for p in x['휴직자']])
print(' 돈  ', json.dumps({k:v for k,v in x['돈'].items() if k not in ('급여상세','원천세')},ensure_ascii=False))
for c in x['체크']: print('  %-16s %-4s %s' % (c['항목'], c['상태'], c['비고'][:58]))
print()
print('data.js', os.path.getsize('/home/user/coco/hr-dashboard/data.js'))
