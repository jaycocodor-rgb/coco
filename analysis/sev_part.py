# -*- coding: utf-8 -*-
"""퇴직연금 불입 · 퇴직금 지급 — 개인별 × 연도별.

   원본은 「YYYY년도 귀속 퇴직연금 부담금(월납)」 파일이다. 암호가 걸려 있어 풀고 읽는다.
   한 파일에 두 가지가 들어 있다.
     · 부담금 총괄 — 재직자 개인별 월별 불입액 (DC형이라 불입액이 곧 그 해 적립액이다)
     · 퇴사자      — 퇴직 시 최종 정산액 (총 부담금 = 그 사람에게 나간 퇴직금)
   주민등록번호 칸은 읽지 않는다.

   출력: sev.json
"""
import openpyxl, glob, os, re, json, datetime, collections

FILES = [
    ('2024', '코코도르',   'raw/2024년도_귀속_퇴직연금_부담금_월납__코코도르_최종_1_.xlsx'),
    ('2025', '코코도르',   'raw/2025년도_귀속_퇴직연금_부담금_월납__코코도르_26.01.29_최종확정.xlsx'),
    ('2025', '코코도르팜', 'raw/2025년도_귀속_퇴직연금_부담금_월납__코코도르팜_260126.xlsx'),
    ('2026', '코코도르',   'raw/2026년도_귀속_퇴직연금_부담금_월납__코코도르_20260810.xlsx'),
    ('2026', '코코도르팜', 'raw/2026년도_귀속_퇴직연금_부담금_월납__코코도르팜_202607.xlsx'),
]
HIDE = {'정연재', '이민정', '정지원', '정윤교'}      # 개인별 화면 비표기 (임원)
BANK = {'하나은행', '국민은행', '산업은행', '신한은행', '우리은행', '기업은행', '농협'}

def bank(v):
    """운용사 칸에는 수식 오류(#REF!)와 '-', '퇴직금' 같은 값이 섞여 있다.
       은행명이 아니면 전부 「계좌 없음」으로 묶는다. 뜻이 다른 값을 같은 칸에 두면 집계가 거짓이 된다."""
    v = (v or '').strip()
    return v if v in BANK else ('미가입' if v in ('미가입', '', '-') else '확인필요')

# 2023년 퇴사자 — 연간 월납 대장이 없고 개별 계산서만 남아 있다. 파일명에서 사람과 시점만 확보했다.
PAY2023 = [('2023-03', '박선택'), ('2023-04', '권소현'), ('2023-04', '원인준'),
           ('2023-05', '최창민'), ('2023-07', '김창수'), ('2023-07', '박성호'),
           ('2023-07', '백종식'), ('2023-08', '이현재'), ('2023-09', '한완수'),
           ('2023-09', '이학진'), ('2023-10', '이규남'), ('2023-10', '이선희'),
           ('2023-11', '정보라'), ('2023-12', '김세연')]

def num(v):
    if isinstance(v, (int, float)): return float(v)
    if v is None: return None
    s = str(v).replace(',', '').strip()
    if not s or s in ('-', '임원'): return None
    try: return float(s)
    except ValueError: return None

def dt(v):
    if isinstance(v, datetime.datetime): return v.date().isoformat()
    if isinstance(v, datetime.date): return v.isoformat()
    if v is None: return None
    s = str(v).strip()
    m = re.match(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', s)
    return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3))) if m else None

def txt(v):
    return str(v).replace('\n', ' ').strip() if v is not None else ''

def hdr(ws, key, upto=12):
    """헤더 행을 찾아 {라벨: 열번호}로 돌려준다. 같은 라벨이 두 번 나오면 뒤쪽을 쓴다."""
    for r in range(1, upto + 1):
        row = {txt(ws.cell(r, c).value): c for c in range(1, ws.max_column + 1)
               if txt(ws.cell(r, c).value)}
        if key in row:
            return r, row
    return None, {}

people = {}            # (법인, 성명, 입사일) -> row
pays   = []            # 퇴직금 지급
노트    = []

for year, co, path in FILES:
    if not os.path.exists(path):
        노트.append({'연도': year, '법인': co, '내용': '파일 없음: ' + path}); continue
    wb = openpyxl.load_workbook(path, data_only=True)

    # ── 부담금 총괄 ────────────────────────────────────────────
    ws = wb['부담금 총괄']
    hr, H = hdr(ws, 'Seq')
    mcols = {}                                     # 'YYYY.MM' -> 열
    for lab, c in H.items():
        m = re.match(r'^(\d{4})\.(\d{1,2})$', lab)
        if m and m.group(1) == year:
            mcols['%s-%02d' % (m.group(1), int(m.group(2)))] = c
    prevcol = next((c for lab, c in H.items() if re.match(r'^~\s*\d{4}년 귀속$', lab)), None)
    C = {k: H.get(k) for k in ('직원번호', '성명', '퇴직연금 운용사', '입사일', '그룹입사일',
                               '경비 구분', '퇴직일자')}
    if C['성명'] is None: C['성명'] = H.get('성명')
    for r in range(hr + 1, ws.max_row + 1):
        nm = txt(ws.cell(r, C['성명']).value) if C['성명'] else ''
        sid = txt(ws.cell(r, C['직원번호']).value) if C['직원번호'] else ''
        if not nm or not re.match(r'^[A-Z]\d{4}$', sid): continue
        joined = dt(ws.cell(r, C['입사일']).value) if C['입사일'] else None
        key = (co, sid)
        p = people.setdefault(key, {
            '법인': co, '직원번호': sid, '성명': nm,
            '운용사': txt(ws.cell(r, C['퇴직연금 운용사']).value) if C['퇴직연금 운용사'] else '',
            '입사일': joined,
            '그룹입사일': dt(ws.cell(r, C['그룹입사일']).value) if C['그룹입사일'] else None,
            '경비구분': txt(ws.cell(r, C['경비 구분']).value) if C['경비 구분'] else '',
            '퇴직일자': None, '연도별': {}, '월별': {}, '이전적립': None, '임원': nm in HIDE,
        })
        p['성명'] = nm
        q = dt(ws.cell(r, C['퇴직일자']).value) if C['퇴직일자'] else None
        if q: p['퇴직일자'] = q
        if prevcol and p['이전적립'] is None:
            v = num(ws.cell(r, prevcol).value)
            if v: p['이전적립'] = round(v)
        tot = 0.0; got = False
        for ym, c in sorted(mcols.items()):
            v = num(ws.cell(r, c).value)
            if v is not None:
                p['월별'][ym] = round(v); tot += v; got = True
        if got: p['연도별'][year] = round(tot)

    # ── 퇴사자 ────────────────────────────────────────────────
    ws = wb['퇴사자']
    hr, H = hdr(ws, '퇴사일')
    cs  = H.get('직원번호'); cn = H.get('성명')
    cin = H.get('입사일');   cou = H.get('퇴사일'); cdl = H.get('지급기한')
    cpd = next((H[k] for k in (' 추가부담금 산정기간', '추가부담금 산정기간',
                               '부담금 산정기간') if k in H), None)
    cadd = next((H[k] for k in ('추가납입부담금', '기간별 부담금') if k in H), None)
    cpre = H.get('기 납입부담금'); ctot = H.get('총 부담금'); cop = H.get('운용사')
    cur = None
    for r in range(hr + 1, ws.max_row + 1):
        nm = txt(ws.cell(r, cn).value) if cn else ''
        add = num(ws.cell(r, cadd).value) if cadd else None
        per = txt(ws.cell(r, cpd).value) if cpd else ''
        if nm:
            cur = {
                '연도': year, '법인': co,
                '직원번호': txt(ws.cell(r, cs).value) if cs else '',
                '성명': nm,
                '입사일': dt(ws.cell(r, cin).value) if cin else None,
                '퇴사일': dt(ws.cell(r, cou).value) if cou else None,
                '지급기한': dt(ws.cell(r, cdl).value) if cdl else None,
                '추가납입': round(add) if add else 0,
                '기납입': round(num(ws.cell(r, cpre).value) or 0) if cpre else 0,
                '총지급': round(num(ws.cell(r, ctot).value) or 0) if ctot else 0,
                '운용사': bank(txt(ws.cell(r, cop).value) if cop else ''),
                '산정기간': [per] if per else [],
                '임원': nm in HIDE,
            }
            pays.append(cur)
        elif cur is not None and (add or per):
            # 이름이 빈 줄은 바로 위 사람의 추가 산정기간이다
            cur['추가납입'] += round(add) if add else 0
            if per: cur['산정기간'].append(per)
    wb.close()

# 총지급이 빈 사람은 추가+기납입으로 채운다
for x in pays:
    if not x['총지급']:
        x['총지급'] = x['추가납입'] + x['기납입']
    if x['입사일'] and x['퇴사일']:
        a = datetime.date.fromisoformat(x['입사일']); b = datetime.date.fromisoformat(x['퇴사일'])
        x['근속일'] = (b - a).days
        x['근속년'] = round((b - a).days / 365.25, 1)
    else:
        x['근속일'] = None; x['근속년'] = None
    x['지연이자'] = any(('지연이자' in s) for s in x['산정기간'])

# 중복 제거 (같은 사람이 같은 해에 두 줄)
seen = {}
for x in pays:
    k = (x['법인'], x['성명'], x['퇴사일'])
    if k in seen:
        seen[k]['총지급'] = max(seen[k]['총지급'], x['총지급'])
        seen[k]['산정기간'] += x['산정기간']
    else:
        seen[k] = x
pays = sorted(seen.values(), key=lambda x: (x['퇴사일'] or '', x['성명']))

PER = sorted(people.values(), key=lambda p: (p['법인'], -(sum(p['연도별'].values()) or 0)))
YEARS = sorted({y for p in PER for y in p['연도별']} | {x['연도'] for x in pays})

def esum(rows, f):
    return round(sum(f(r) or 0 for r in rows))

연도rows = []
for y in YEARS:
    for co in ('코코도르', '코코도르팜'):
        ps = [p for p in PER if p['법인'] == co and y in p['연도별'] and not p['임원']]
        qs = [x for x in pays if x['연도'] == y and x['법인'] == co and not x['임원']]
        if not ps and not qs: continue
        연도rows.append({
            '연도': y, '법인': co,
            '불입인원': len(ps), '불입액': esum(ps, lambda p: p['연도별'][y]),
            '퇴직인원': len(qs), '퇴직지급': esum(qs, lambda x: x['총지급']),
            '지연이자건': sum(1 for x in qs if x['지연이자']),
            '월평균불입': round(esum(ps, lambda p: p['연도별'][y]) / max(len(ps), 1) / 12),
        })

# 사람별 (임원 제외)
사람 = []
for p in PER:
    if p['임원']: continue
    tot = sum(p['연도별'].values())
    사람.append({
        '법인': p['법인'], '직원번호': p['직원번호'], '성명': p['성명'],
        '운용사': bank(p['운용사']), '입사일': p['입사일'], '그룹입사일': p['그룹입사일'],
        '경비구분': p['경비구분'], '퇴직일자': p['퇴직일자'],
        '연도별': {k: v for k, v in sorted(p['연도별'].items())},
        '월별': {k: v for k, v in sorted(p['월별'].items())},
        '이전적립': p['이전적립'],
        '관측기간불입': round(tot),
        '누적적립추정': round(tot + (p['이전적립'] or 0)) if p['이전적립'] is not None else None,
        '연수': len(p['연도별']),
    })
TODAY = datetime.date.today()
for s_ in 사람:
    s_['계좌없음'] = s_['운용사'] in ('미가입', '확인필요')
    s_['미가입경과월'] = None
    if s_['계좌없음'] and s_['입사일']:
        end = datetime.date.fromisoformat(s_['퇴직일자']) if s_['퇴직일자'] else TODAY
        s_['미가입경과월'] = round((end - datetime.date.fromisoformat(s_['입사일'])).days / 30.44, 1)
    s_['1년초과미가입'] = bool(s_['계좌없음'] and (s_['미가입경과월'] or 0) >= 12 and not s_['퇴직일자'])
사람.sort(key=lambda x: (x['법인'], -x['관측기간불입']))

# 운용사별
운용사 = collections.defaultdict(lambda: {'인원': 0, '불입': 0})
for s in 사람:
    g = 운용사[s['운용사']]; g['인원'] += 1; g['불입'] += s['관측기간불입']
운용사rows = sorted([{'운용사': k, **v} for k, v in 운용사.items()], key=lambda x: -x['불입'])

퇴직 = [x for x in pays if not x['임원']]
구간 = collections.Counter()
for x in 퇴직:
    n = x['근속년']
    구간['미상' if n is None else ('1년 미만' if n < 1 else '1~3년' if n < 3 else '3~5년' if n < 5 else '5년 이상')] += 1

미가입1년 = sorted([s_ for s_ in 사람 if s_['1년초과미가입']],
                   key=lambda x: -(x['미가입경과월'] or 0))
지연 = [x for x in 퇴직 if x['지연이자']]

점검 = [
    {'항목': 'DC 계좌 미개설 상태로 1년 초과',
     '근거': '근로자퇴직급여보장법 제20조 제1항·제3항 — 확정기여형은 가입자별 계좌에 연 1회 이상 부담금을 납입해야 하고, 늦으면 지연이자가 붙습니다.',
     '대상': len(미가입1년),
     '판정': '위반 소지' if 미가입1년 else '해당 없음',
     '설명': '대장에는 매월 적립액이 잡혀 있는데 운용사 칸이 비어 있습니다. 적립만 하고 계좌에 넣지 않았다는 뜻이면 납입 의무를 넘긴 것입니다. 사내 적립으로 두기로 한 결정이라면 규약과 맞는지 확인해야 합니다.',
     '명단': [{'성명': x['성명'], '법인': x['법인'], '입사일': x['입사일'],
               '경과월': x['미가입경과월'], '적립액': x['관측기간불입']} for x in 미가입1년]},
    {'항목': '부담금 납입 지연이자 발생',
     '근거': '근로자퇴직급여보장법 제20조 제3항 — 정해진 날까지 부담금을 내지 않으면 다음 날부터 지연이자를 더해 내야 합니다. 퇴직 후 14일을 넘기면 제9조의 지급 지연도 함께 걸립니다.',
     '대장': len(지연),
     '대상': len(지연),
     '판정': '지연 이력 있음' if 지연 else '해당 없음',
     '설명': '정산 내역에 「23년귀속 지연이자」「24년귀속 지연이자」가 붙은 건입니다. 퇴직할 때 늦게 준 것이 아니라, 재직 중 그 해 부담금을 제때 넣지 않아 퇴직정산에서 이자를 얹어 메운 것입니다. 위 「계좌 미개설」과 원인이 같습니다. 모두 2025년에 몰려 있습니다.',
     '명단': [{'성명': x['성명'], '법인': x['법인'], '퇴사일': x['퇴사일'],
               '지급기한': x['지급기한'], '총지급': x['총지급'],
               '사유': ' / '.join(x['산정기간'])} for x in 지연]},
    {'항목': '2023년 개인별 불입 대장 없음',
     '근거': '-',
     '대상': len(PAY2023),
     '판정': '자료 없음',
     '설명': '2023년은 1분기 부담금 파일과 퇴사자 개별 계산서만 있습니다. 연간 월납 대장이 없어 개인별 불입액을 연도축에 올릴 수 없습니다. 퇴사자 %d명은 이름과 시점만 확인했습니다.' % len(PAY2023),
     '명단': [{'성명': n, '퇴사월': m} for m, n in PAY2023]},
    {'항목': '2022년 이전 자료',
     '근거': '-',
     '대상': 0,
     '판정': '자료 없음',
     '설명': '2022년 그룹 통합 보고와 수시부담금(DC) 파일이 드라이브에 있으나 이번 판독에서 열지 못했습니다. 2021년은 퇴직급여산정 파일이 있어 법정퇴직금 시절 자료로 보입니다.',
     '명단': []},
]

out = {
    '기준일': datetime.date.today().isoformat(),
    '출처': 'G:\\공유 드라이브 · 재무_대외비 · 「YYYY년도 귀속 퇴직연금 부담금(월납)」 파일 %d개 (암호 해제 후 판독)' % len(FILES),
    '제도': '확정기여형(DC). 회사가 매월 불입하면 그 달로 책임이 끝나고, 운용 손익은 근로자 몫입니다. 따라서 「불입액」이 회사가 실제 부담한 금액입니다.',
    '연도별': 연도rows,
    '사람': 사람,
    '퇴직지급': 퇴직,
    '운용사별': 운용사rows,
    '근속구간': [{'구간': k, '인원': v} for k, v in sorted(구간.items())],
    '점검': 점검,
    '미가입1년': 미가입1년,
    '지연': 지연,
    '2023퇴사자': [{'성명': n, '퇴사월': m} for m, n in PAY2023],
    '집계': {
        '연도수': len(YEARS), '연도': YEARS,
        '사람수': len(사람),
        '불입총계': esum(사람, lambda s: s['관측기간불입']),
        '퇴직건수': len(퇴직),
        '퇴직지급총계': esum(퇴직, lambda x: x['총지급']),
        '계좌없음': sum(1 for s in 사람 if s['계좌없음']),
        '미가입1년': len(미가입1년),
        '지연이자': len(지연),
        '법인수': len({s['법인'] for s in 사람}),
    },
    '주의': [
        '2024·2025·2026년 세 해만 개인별로 잡힙니다. 2023년은 1분기 파일과 퇴사자 개별 계산서만 있고 연간 월납 대장이 없습니다. 2022년은 별도 rawdata 파일이 있으나 이번 판독에서 열지 못했습니다.',
        '2026년은 코코도르 8월분, 코코도르팜 7월분까지입니다. 연간 합계가 아니라 진행 중 금액입니다.',
        '코코도르팜은 2025·2026만 있습니다. 2024년 팜 파일을 찾지 못했습니다.',
        '임원(대표이사 등) 4명은 개인별 표와 합계에서 모두 뺐습니다. 금액이 크고 민감해 전체 추세를 왜곡합니다.',
        '「누적적립추정」은 파일의 「~ 이전 귀속」 칸에 관측기간 불입액을 더한 값입니다. 운용 손익은 빠져 있어 실제 계좌 잔액과 다릅니다.',
        '퇴직지급액은 DC 최종 정산액(기 납입 + 추가 납입)입니다. 근로자가 중도인출했다면 계좌 수령액과 다릅니다.',
        '주민등록번호 칸은 읽지 않았습니다.',
    ],
}
json.dump(out, open('sev.json', 'w', encoding='utf-8'), ensure_ascii=False)

blob = json.dumps(out, ensure_ascii=False)
assert not re.search(r'\d{6}\s*-\s*\d{7}', blob), '주민등록번호 패턴'
assert not re.search(r'\d{3}-\d{6}-\d{2}', blob), '계좌번호 패턴'
for n in HIDE: assert n not in blob, '임원 성명 노출: ' + n

G = out['집계']
print('연도 %s · 사람 %d명 · 불입 %s원' % ('/'.join(G['연도']), G['사람수'], '{:,}'.format(G['불입총계'])))
print('퇴직 %d건 · 지급 %s원 · 지연이자 %d건 · 계좌없음 %d명 (1년초과 %d명)'
      % (G['퇴직건수'], '{:,}'.format(G['퇴직지급총계']), G['지연이자'], G['계좌없음'], G['미가입1년']))
print()
print('%-6s %-10s %6s %16s %6s %16s %5s' % ('연도','법인','불입인원','불입액','퇴직','퇴직지급','지연'))
for r in 연도rows:
    print('%-6s %-10s %6d %16s %6d %16s %5d'
          % (r['연도'], r['법인'], r['불입인원'], '{:,}'.format(r['불입액']),
             r['퇴직인원'], '{:,}'.format(r['퇴직지급']), r['지연이자건']))
print()
for r in 운용사rows:
    print('  %-10s %4d명  %16s' % (r['운용사'], r['인원'], '{:,}'.format(r['불입'])))
print()
print('상위 불입자 (임원 제외)')
for s in 사람[:8]:
    print('  %-10s %-6s %-9s %14s  %s' % (s['성명'], s['법인'], s['운용사'],
          '{:,}'.format(s['관측기간불입']), '/'.join(s['연도별'])))
print()
print('1년 넘게 DC 계좌 없는 재직자')
for x in 미가입1년:
    print('  %-9s %-7s 입사 %s  경과 %5.1f개월  적립 %10s' % (x['성명'], x['법인'], x['입사일'], x['미가입경과월'], '{:,}'.format(x['관측기간불입'])))
print()
print('지연이자 발생 건')
for x in 지연:
    print('  %-9s %-7s 퇴사 %s  %12s  %s' % (x['성명'], x['법인'], x['퇴사일'], '{:,}'.format(x['총지급']), ' / '.join(x['산정기간'])[:50]))
print()
print('퇴직 지급 최근 8건')
for x in 퇴직[-8:]:
    print('  %-10s %-6s %s → %s  %12s  근속 %s년%s'
          % (x['성명'], x['법인'], x['입사일'], x['퇴사일'], '{:,}'.format(x['총지급']),
             x['근속년'], ' (지연이자)' if x['지연이자'] else ''))
