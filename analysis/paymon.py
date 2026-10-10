# -*- coding: utf-8 -*-
"""개인별 월별 급여 — 받을 수 있는 가장 먼 과거부터 현재까지.

   급여대장 월별 파일은 두 달치만 받았다. 그런데 퇴직연금 월납 대장 안에
   매달 「N월급여데이터」 시트가 들어 있고, 한 시트가 석 달치 급여를 들고 있다.
   시트를 전부 겹쳐 붙이면 사람별 월 급여가 길게 이어진다.

     · 코코도르   — ecount 「급여」(퇴직금 산정 임금총액). 2024-01 ~
     · 코코도르팜 — 월별 급여대장 그대로(지급액계·기본급·시간외). 2025-01 ~

   기준이 다르므로 섞지 않고 「기준」 칸에 적어 둔다.

   출력: paymon.json
"""
import openpyxl, glob, os, re, json, datetime, collections, statistics

CO_FILES = [
    'raw/2024년도_귀속_퇴직연금_부담금_월납__코코도르_최종_1_.xlsx',
    'raw/2025년도_귀속_퇴직연금_부담금_월납__코코도르_26.01.29_최종확정.xlsx',
    'raw/2026년도_귀속_퇴직연금_부담금_월납__코코도르_20260810.xlsx',
]
FARM_FILES = [
    'raw/2025년도_귀속_퇴직연금_부담금_월납__코코도르팜_260126.xlsx',
    'raw/2026년도_귀속_퇴직연금_부담금_월납__코코도르팜_202607.xlsx',
]
HIDE = {'정연재', '이민정', '정지원', '정윤교'}

def num(v):
    if isinstance(v, (int, float)): return float(v)
    if v is None: return None
    s = str(v).replace(',', '').strip()
    if not s: return None
    try: return float(s)
    except ValueError: return None

def txt(v):
    return str(v).replace('\n', ' ').strip() if v is not None else ''

def dt(v):
    if isinstance(v, datetime.datetime): return v.date().isoformat()
    if isinstance(v, datetime.date): return v.isoformat()
    m = re.match(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', txt(v))
    return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3))) if m else None

def mlabel(s):
    m = re.match(r'(\d{4})\s*년\s*(\d{1,2})\s*월', txt(s))
    return '%s-%02d' % (m.group(1), int(m.group(2))) if m else None

P = {}            # 성명 -> 레코드
def rec(name):
    return P.setdefault(name, {'성명': name, '법인': None, '소속': None, '직책': None,
                               '사업장': None, '직원번호': None, '입사일': None,
                               '월별': {}, '지표': {}, '상세': {}})

# ── 코코도르 ───────────────────────────────────────────────────
co_months = set()
for path in CO_FILES:
    if not os.path.exists(path): continue
    wb = openpyxl.load_workbook(path, data_only=True)
    for sn in wb.sheetnames:
        if '급여데이터' not in sn: continue
        ws = wb[sn]
        # 헤더 행을 찾는다 (「급여」가 있는 행)
        hr = None
        for r in range(1, 6):
            row = {txt(ws.cell(r, c).value): c for c in range(1, ws.max_column + 1) if txt(ws.cell(r, c).value)}
            if '급여' in row and '사원명' in row:
                hr, H = r, row; break
        if hr is None: continue
        c급 = H['급여']
        # 급여 칸 바로 위/아래 행에 월 라벨이 있다
        mcols = {}
        for lr in (hr + 1, hr - 1):
            if lr < 1: continue
            for c in range(c급, min(c급 + 3, ws.max_column + 1)):
                k = mlabel(ws.cell(lr, c).value)
                if k: mcols[c] = k
            if mcols: break
        if not mcols: continue
        for r in range(hr + 2, ws.max_row + 1):
            nm = txt(ws.cell(r, H['사원명']).value)
            if not nm or nm in ('사원명', '합계', '소계'): continue
            p = rec(nm)
            p['법인'] = '코코도르'
            if H.get('사원코드'):
                sid = txt(ws.cell(r, H['사원코드']).value)
                if re.match(r'^[A-Z]\d{4}$', sid): p['직원번호'] = sid
            for k, col in (('사업장', '사업장명'), ('소속', '부서명'), ('직책', '직책명')):
                if H.get(col):
                    v = txt(ws.cell(r, H[col]).value)
                    if v: p[k] = v
            j = dt(ws.cell(r, H['입사일']).value) if H.get('입사일') else None
            if j: p['입사일'] = j
            for c, mk in mcols.items():
                v = num(ws.cell(r, c).value)
                if v is not None and v > 0:
                    p['월별'][mk] = round(v); co_months.add(mk)
            for k in ('상여(1년)', '연차(1년)', '근무일수', '근속년수', '평균임금', '퇴직추계액'):
                if H.get(k):
                    v = ws.cell(r, H[k]).value
                    if v not in (None, '', 0):
                        p['지표'][k] = num(v) if k not in ('근무일수', '근속년수') else txt(v)
    wb.close()

# ── 코코도르팜 ─────────────────────────────────────────────────
# 팜 시트는 달마다 머리글 모양이 다르다. 사원 칸과 항목 칸이 다른 행에 있고
# 금액 칸 이름도 지급액계·임금총액·총급여액으로 바뀐다. 네 행을 훑어 합친다.
FARM_AMT = ['지급액계', '임금총액', '총급여액']
FARM_ITEM = ['기본급', '상여', '시간외수당', '추가야근수당', '휴일특근수당', '야간수당',
             '연월차보상', '직책수당', '급여소급', '야근교통비', '무급휴가차감',
             '출장비', '기타수당', '식대', '장거리유류비']

def farm_header(ws):
    H = {}
    for r in range(1, 6):
        for c in range(1, ws.max_column + 1):
            lab = txt(ws.cell(r, c).value)
            if not lab or lab in ('수당', '공제') or lab in H:
                continue
            H[lab] = c
    if '사원명' not in H:
        return None, None
    # 데이터 시작 행 — 사원코드가 숫자나 영문+숫자인 첫 행
    c0 = H.get('사원코드', 1)
    for r in range(1, min(ws.max_row, 12) + 1):
        v = txt(ws.cell(r, c0).value)
        if re.match(r'^(\d{3,4}|[A-Z]\d{4})$', v):
            return H, r
    return None, None

farm_months = set()
farm_basis = {}
for path in FARM_FILES:
    if not os.path.exists(path): continue
    y = '2025' if '팜_260126' in path else '2026'
    wb = openpyxl.load_workbook(path, data_only=True)
    for sn in wb.sheetnames:
        m2 = re.match(r'^(\d{2})년(\d{1,2})월$', sn)
        m1 = re.match(r'^(\d{1,2})월급여데이터$', sn)
        if m2:   mk = '20%s-%02d' % (m2.group(1), int(m2.group(2)))
        elif m1: mk = '%s-%02d' % (y, int(m1.group(1)))
        else:    continue
        ws = wb[sn]
        H, r0 = farm_header(ws)
        if not H: continue
        amt = next((k for k in FARM_AMT if k in H), None)
        if not amt: continue
        farm_basis[mk] = amt
        for r in range(r0, ws.max_row + 1):
            nm = txt(ws.cell(r, H['사원명']).value)
            if not nm or nm in ('사원명', '합계', '소계'): continue
            tot = num(ws.cell(r, H[amt]).value)
            if tot is None or tot <= 0: continue
            p = rec(nm)
            if p['법인'] is None: p['법인'] = '코코도르팜'
            for k, col in (('소속', '부서'), ('직책', '직급')):
                if H.get(col):
                    v = txt(ws.cell(r, H[col]).value)
                    if v and v != '직급없음': p[k] = v
            p['월별'][mk] = round(tot); farm_months.add(mk)
            dd = p['상세'].setdefault(mk, {})
            for k in FARM_ITEM:
                if H.get(k):
                    v = num(ws.cell(r, H[k]).value)
                    if v: dd[k] = round(v)
    wb.close()

# ── 사람별 정리 ────────────────────────────────────────────────
people = []
for nm, p in P.items():
    ms = {k: v for k, v in sorted(p['월별'].items())}
    if not ms: continue
    vals = list(ms.values()); keys = list(ms)
    # 입사월·퇴사월·무급 달은 금액이 반 토막이다. 중위값의 60% 미만을 부분월로 본다.
    med = statistics.median(vals)
    부분 = [k for k in keys if ms[k] < med * 0.6]
    full = [k for k in keys if k not in 부분]
    people.append({
        '성명': nm, '직원번호': p['직원번호'], '법인': p['법인'] or '-',
        '소속': p['소속'] or '-', '직책': p['직책'] or '-', '사업장': p['사업장'] or '-',
        '입사일': p['입사일'],
        '기준': '퇴직금 산정 임금총액 (ecount)' if p['법인'] == '코코도르' else '급여대장 지급 합계',
        '월별': ms,
        '상세': p['상세'] or None,
        '개월수': len(ms), '첫월': keys[0], '끝월': keys[-1],
        '최초': vals[0], '최근': vals[-1],
        '부분월': 부분,
        '온전첫월': full[0] if full else None, '온전끝월': full[-1] if full else None,
        '온전최초': ms[full[0]] if full else None, '온전최근': ms[full[-1]] if full else None,
        '최저': min(vals), '최고': max(vals),
        '평균': round(sum(vals) / len(vals)),
        '중위': round(statistics.median(vals)),
        '변화율': (round((ms[full[-1]] - ms[full[0]]) / ms[full[0]], 4)
                  if len(full) >= 2 and ms[full[0]] else None),
        '연환산최근': round((ms[full[-1]] if full else vals[-1]) * 12),
        '지표': p['지표'] or None,
        '임원': nm in HIDE,
    })
people.sort(key=lambda x: (x['법인'], -x['최근']))

MONTHS = sorted(set(co_months) | set(farm_months))
전사 = []
for mk in MONTHS:
    vs = [p['월별'][mk] for p in people if mk in p['월별'] and not p['임원']]
    if not vs: continue
    전사.append({'월': mk, '인원': len(vs), '급여계': sum(vs),
                '1인평균': round(sum(vs) / len(vs)), '중위': round(statistics.median(vs)),
                '최저': min(vs), '최고': max(vs)})

pub = [p for p in people if not p['임원']]
out = {
    '기준일': datetime.date.today().isoformat(),
    '출처': '퇴직연금 월납 대장 안의 「N월급여데이터」 시트 전부 (파일 %d개). 한 시트가 석 달치를 들고 있어 겹쳐 붙였습니다.' % (len(CO_FILES) + len(FARM_FILES)),
    '범위': {
        '코코도르': '%s ~ %s (%d개월)' % (min(co_months), max(co_months), len(co_months)) if co_months else '없음',
        '코코도르팜': '%s ~ %s (%d개월)' % (min(farm_months), max(farm_months), len(farm_months)) if farm_months else '없음',
    },
    '기준설명': [
        '코코도르 수치는 ecount의 「급여」 칸입니다. 퇴직금을 산정하는 임금총액 기준이라 그 달 실제 지급액과 완전히 같지는 않습니다.',
        '코코도르팜 수치는 월별 급여대장의 지급 합계입니다. 달마다 칸 이름이 지급액계·임금총액·총급여액으로 바뀌어, 어느 칸을 읽었는지 「팜 금액 칸」에 월별로 적어 두었습니다. 기본급·시간외·야근 같은 항목별 금액도 함께 담았습니다.',
        '두 기준을 더해 그룹 합계로 쓰지 마십시오. 사람별 추이를 보는 데 쓰는 자료입니다.',
    ],
    '사람': pub,
    '전사월별': 전사,
    '월축': MONTHS,
    '팜금액칸': [{'월': k, '칸': v} for k, v in sorted(farm_basis.items())],
    '집계': {
        '사람수': len(pub), '개월수': len(MONTHS),
        '첫월': MONTHS[0], '끝월': MONTHS[-1],
        '총칸수': sum(p['개월수'] for p in pub),
        '평균개월': round(sum(p['개월수'] for p in pub) / len(pub), 1),
        '24개월이상': sum(1 for p in pub if p['개월수'] >= 24),
        '입사전부터': sum(1 for p in pub if p['입사일'] and p['입사일'][:7] >= MONTHS[0]),
        '팜상세': sum(1 for p in pub if p['상세']),
        '부분월있음': sum(1 for p in pub if p['부분월']),
    },
    '한계': [
        '급여 칸이 0인 달은 넣지 않았습니다. 입사 전, 퇴사 후, 휴직으로 무급인 달입니다.',
        '%s 이전 급여는 없습니다. 그 전 월납 대장을 찾지 못했습니다. 그래서 %s 이전 입사자는 「입사 때부터」가 아니라 %s부터 보입니다.' % (MONTHS[0], MONTHS[0], MONTHS[0]),
        '코코도르팜은 2025-01부터입니다. 2024년 팜 파일을 찾지 못했습니다.',
        '임원 4명은 뺐습니다.',
        '입사월과 퇴사월, 무급 휴직이 섞인 달은 금액이 반 토막입니다. 중위값의 60% 미만이면 「부분월」로 표시하고 변화율 계산에서 뺐습니다.',
        '코코도르는 항목별 내역이 없습니다. 월 총액만 있습니다. 항목별은 급여대장을 받은 달(2025-01~06, 2026-02)에만 있고 그것은 7-1 메뉴에 있습니다.',
    ],
}
json.dump(out, open('paymon.json', 'w', encoding='utf-8'), ensure_ascii=False)

G = out['집계']
print('사람 %d명 · %s ~ %s (%d개월) · 칸 %s개 · 1인 평균 %.1f개월'
      % (G['사람수'], G['첫월'], G['끝월'], G['개월수'], '{:,}'.format(G['총칸수']), G['평균개월']))
print('24개월 이상 이어지는 사람 %d명 · 팜 항목별 상세 %d명' % (G['24개월이상'], G['팜상세']))
print('범위:', json.dumps(out['범위'], ensure_ascii=False))
print()
print('%-9s %5s %14s %12s %12s' % ('월','인원','급여계','1인평균','중위'))
for r in 전사[::3]:
    print('%-9s %5d %14s %12s %12s' % (r['월'], r['인원'], '{:,}'.format(r['급여계']),
          '{:,}'.format(r['1인평균']), '{:,}'.format(r['중위'])))
print()
print('%-10s %-7s %-10s %4s %-9s %-9s %10s %10s %7s %4s' % ('성명','법인','소속','개월','첫월','끝월','최초','최근','변화','부분'))
for p in pub[:12]:
    print('%-10s %-7s %-10s %4d %-9s %-9s %10s %10s %6.1f%% %4d'
          % (p['성명'][:10], p['법인'], (p['소속'] or '-')[:10], p['개월수'], p['첫월'], p['끝월'],
             '{:,}'.format(p['온전최초'] or p['최초']), '{:,}'.format(p['온전최근'] or p['최근']),
             (p['변화율'] or 0)*100, len(p['부분월'])))
print()
print('팜 금액 칸:', ', '.join('%s=%s' % (x['월'], x['칸']) for x in out['팜금액칸']))
