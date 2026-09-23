# -*- coding: utf-8 -*-
"""휴직자 관리 — 인사마스터(2026-09-21) 현재 휴직 15명에 급여대장 사유를 붙이고,
   2026-02 당시 휴직자 19명의 그 후 행방(복직/퇴사)을 추적한다."""
import json, openpyxl, datetime, collections

U='/root/.claude/uploads/1c1085cf-e430-5f57-88e8-a8e9f2f98dee'
AS_OF = datetime.date(2026, 9, 21)
d = json.load(open('hrdata.json', encoding='utf-8'))

# 인사마스터 원본에서 상태를 다시 읽어 행방 추적
wb = openpyxl.load_workbook(U+'/dc112193-_____260921___.xlsx', data_only=True)
rows = list(wb['전체'].iter_rows(values_only=True)); HDR=list(rows[0])
RAW = [dict(zip(HDR, r)) for r in rows[1:] if r[1]]
def dd(v): return v.date() if isinstance(v, datetime.datetime) else None
def iso(v):
    x = dd(v)
    return None if not x else ('미정' if x.year >= 2999 else x.isoformat())
ST = {}
for x in RAW:
    ST.setdefault(x['성명'], []).append(x)

REASON = {x['성명']: x for x in d['leave']}          # 2026-02 급여대장 (사유 있음)
CUR    = d['hrMaster']['leave']                      # 2026-09-21 현재 휴직 (날짜 있음)

def bucket(r):
    if r['복직미정']: return '복직 미정'
    n = r.get('복직까지')
    if n is None: return '기타'
    if n < 0:  return '복직일 경과'
    if n <= 90: return '90일 내 복직'
    if n <= 365: return '1년 내 복직'
    return '1년 초과'

cur = []
for r in CUR:
    o = dict(r)
    src = REASON.get(r['성명'])
    o['사유'] = src['사유'] if src else None
    o['사유출처'] = '2026-02 급여대장 참고칸' if src else None
    if r['복직예정'] and r['복직예정'] != '미정':
        e = datetime.date.fromisoformat(r['복직예정'])
        o['복직까지'] = (e - AS_OF).days
        o['복직월'] = r['복직예정'][:7]
    else:
        o['복직까지'] = None; o['복직월'] = '미정'
    o['구분'] = bucket(o)
    cur.append(o)
cur.sort(key=lambda r: r['휴직시작'] or '')

# 2026-02 휴직자 19명의 그 후
trace = []
for r in d['leave']:
    nm = r['성명']
    rec = ST.get(nm, [])
    still = any(x['재직상태'] == '휴직' for x in rec)
    quit_ = [x for x in rec if x['재직상태'] == '퇴직']
    back  = any(x['재직상태'] == '재직' for x in rec)
    stat = '휴직 유지' if still else ('퇴사' if quit_ and not back else ('복직' if back else '명부 밖'))
    trace.append({'성명': nm, '소속': r['소속'], '법인': r['법인'], '사유': r['사유'],
                  '근속년수': r['근속년수'], '이후': stat,
                  '퇴직일': iso(quit_[0]['퇴직일자']) if (stat == '퇴사' and quit_) else None})
ORD = {'휴직 유지': 0, '복직': 1, '퇴사': 2, '명부 밖': 3}
trace.sort(key=lambda r: (ORD.get(r['이후'], 9), r['성명']))
tc = collections.Counter(t['이후'] for t in trace)

# 복직 예정 월별
mon = collections.Counter(r['복직월'] for r in cur)
MON = [{'월': m, '인원': mon[m]} for m in sorted(mon, key=lambda m: (m == '미정', m))]

bc = collections.Counter(r['구분'] for r in cur)
BORD = ['복직일 경과', '90일 내 복직', '1년 내 복직', '1년 초과', '복직 미정', '기타']
rc = collections.Counter(r['사유'] or '미기재' for r in cur)
dc = collections.Counter(r['소속'] for r in cur)

d['leaveDesk'] = {
    '기준일': AS_OF.isoformat(),
    '현재휴직': cur, '인원': len(cur),
    '복직미정': sum(1 for r in cur if r['복직미정']),
    '90일내복직': bc['90일 내 복직'],
    '복직일경과': bc['복직일 경과'],
    '사유확인': sum(1 for r in cur if r['사유']),
    '최장경과': max(r['경과일'] or 0 for r in cur),
    '평균경과': round(sum(r['경과일'] or 0 for r in cur) / len(cur)),
    '구간': [{'구분': k, '인원': bc[k]} for k in BORD if bc[k]],
    '사유별': [{'사유': k, '인원': v} for k, v in rc.most_common()],
    '부서별': [{'소속': k, '인원': v} for k, v in dc.most_common()],
    '복직월별': MON,
    'trace': trace,
    'traceSummary': [{'이후': k, '인원': tc[k]} for k in ['휴직 유지', '복직', '퇴사', '명부 밖'] if tc[k]],
    '한계': [
        '사유는 2026-02 급여대장 「참고」 칸에서 왔습니다. 그 뒤 새로 휴직한 인원은 사유가 비어 있습니다.',
        '복직 예정일이 2999-12-31로 입력된 건은 「미정」으로 표시했습니다.',
        '2026-02 당시 휴직자 19명과 현재 휴직 15명은 7개월 차이라 8명만 겹칩니다.',
    ],
}
json.dump(d, open('hrdata.json', 'w'), ensure_ascii=False)
print('현재휴직', len(cur), '· 사유확인', d['leaveDesk']['사유확인'], '· 미정', d['leaveDesk']['복직미정'])
print('구간', dict(bc)); print('사유', dict(rc))
print('2026-02 휴직자 이후:', dict(tc))
for t in trace:
    if t['이후'] == '퇴사': print('   퇴사 →', t['성명'], t['소속'], t['사유'], t['퇴직일'])
