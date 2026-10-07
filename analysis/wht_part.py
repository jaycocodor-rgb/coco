# -*- coding: utf-8 -*-
"""원천세 지급내역 — 법인 × 월 × 소득구분 집계.

   원본은 법인마다 시트가 하나씩이고, 한 시트 안에 귀속월이 다른 블록이 여럿 들어 있다.
   세부 행은 합이 소계와 맞지 않는 곳이 있어 믿지 않는다. 「가감계」와 「총계」 행만 읽는다.

   출력: wht.json
"""
import xlrd, glob, os, re, json, collections

COL = {'인원': 5, '금액': 6, '소득세': 7, '소득세계': 10, '지방세': 11, '지방세계': 14}

def num(v):
    if isinstance(v, (int, float)):
        return 0 if v == '' else float(v)
    try:
        return float(str(v).replace(',', '').strip() or 0)
    except ValueError:
        return 0.0

def txt(v):
    return str(v).strip().replace('\n', ' ')

rows = []
버린시트 = []
files = sorted(glob.glob('raw/wht_*.xls'))
for path in files:
    ym = os.path.basename(path)[4:8]          # 2608
    지급월 = '20%s-%s' % (ym[:2], ym[2:])
    wb = xlrd.open_workbook(path)
    for sn in wb.sheet_names():
        m = re.search(r'\((.+?)\)', sn)
        법인 = m.group(1) if m else sn
        # 시트 이름의 「N월지급」이 파일의 달과 다르면 갱신 안 된 과거 시트다. 버린다.
        mo = re.match(r'(\d{1,2})월지급', sn)
        if not mo or int(mo.group(1)) != int(ym[2:]):
            버린시트.append({'파일': 지급월, '시트': sn}); continue
        sh = wb.sheet_by_name(sn)
        블록 = None
        for r in range(sh.nrows):
            a = txt(sh.cell_value(r, 1)) if sh.ncols > 1 else ''
            b = txt(sh.cell_value(r, 2)) if sh.ncols > 2 else ''
            # 귀속·지급 블록 머리
            mm = re.match(r'(\d{1,2})월귀속\s*(\d{1,2})월지급', a)
            if mm:
                블록 = {'귀속월': int(mm.group(1)), '지급월': int(mm.group(2))}
                continue
            if a in ('총계', '가감계') or b == '가감계':
                구분 = a if a in ('총계', '가감계') else '가감계'
                # 가감계는 바로 위 소득구분을 따른다
                소득 = None
                if 구분 == '가감계':
                    for back in range(r, max(r - 12, 0), -1):
                        v = txt(sh.cell_value(back, 1))
                        if v in ('근로소득', '퇴직소득', '사업소득', '기타소득'):
                            소득 = v
                            break
                    if 소득 is None:
                        continue
                vals = {k: num(sh.cell_value(r, c)) for k, c in COL.items() if c < sh.ncols}
                if not any(vals.values()):
                    continue
                rows.append({
                    '파일': 지급월, '법인': 법인, '시트': sn,
                    '귀속월': (블록 or {}).get('귀속월'),
                    '지급월': (블록 or {}).get('지급월'),
                    '구분': 구분, '소득구분': 소득 or '전체',
                    '인원': int(vals.get('인원', 0)),
                    '지급액': vals.get('금액', 0),
                    '소득세': vals.get('소득세', 0),
                    '소득세_가산포함': vals.get('소득세계', 0),
                    '지방소득세': vals.get('지방세', 0),
                    '지방소득세_가산포함': vals.get('지방세계', 0),
                })

tot = [r for r in rows if r['구분'] == '총계']
seg = [r for r in rows if r['구분'] == '가감계']

def pay(r):
    """실제 납부액 = 소득세(가산세 포함) + 지방소득세(가산세 포함).
       가산세 포함 칸이 비면 본세를 쓴다."""
    s = r['소득세_가산포함'] or r['소득세']
    j = r['지방소득세_가산포함'] or r['지방소득세']
    return s + j

for r in rows:
    r["납부액"] = pay(r)

# 월별(파일 기준) 집계
월별 = collections.defaultdict(lambda: {'인원': 0, '지급액': 0, '소득세': 0, '지방소득세': 0, '납부액': 0, '법인': set()})
for r in tot:
    g = 월별[r['파일']]
    g['인원'] += r['인원']; g['지급액'] += r['지급액']
    g['소득세'] += r['소득세_가산포함'] or r['소득세']
    g['지방소득세'] += r['지방소득세_가산포함'] or r['지방소득세']
    g['납부액'] += r['납부액']
    if r['인원'] or r['지급액']: g['법인'].add(r['법인'])
월별rows = [{'월': k, '인원': v['인원'], '지급액': v['지급액'], '소득세': v['소득세'],
            '지방소득세': v['지방소득세'], '납부액': v['납부액'], '법인수': len(v['법인'])}
           for k, v in sorted(월별.items())]

# 법인별 집계
법인별 = collections.defaultdict(lambda: {'월': set(), '지급액': 0, '소득세': 0, '지방소득세': 0, '납부액': 0, '인원최대': 0})
for r in tot:
    g = 법인별[r['법인']]
    g['지급액'] += r['지급액']
    g['소득세'] += r['소득세_가산포함'] or r['소득세']
    g['지방소득세'] += r['지방소득세_가산포함'] or r['지방소득세']
    g['납부액'] += r['납부액']
    g['인원최대'] = max(g['인원최대'], r['인원'])
    if r['지급액']: g['월'].add(r['파일'])
법인rows = [{'법인': k, '지급액': v['지급액'], '소득세': v['소득세'], '지방소득세': v['지방소득세'],
            '납부액': v['납부액'], '인원최대': v['인원최대'], '신고월수': len(v['월'])}
           for k, v in 법인별.items()]
법인rows.sort(key=lambda x: -x['납부액'])

# 소득구분별
소득별 = collections.defaultdict(lambda: {'지급액': 0, '납부액': 0, '인원': 0})
for r in seg:
    g = 소득별[r['소득구분']]
    g['지급액'] += r['지급액']; g['납부액'] += r['납부액']; g['인원'] += r['인원']
소득rows = [{'소득구분': k, '지급액': v['지급액'], '납부액': v['납부액'], '인원': v['인원']}
           for k, v in 소득별.items()]
소득rows.sort(key=lambda x: -x['지급액'])

out = {
    '기준': '원천세지급내역 월별 파일 %d개 (%s ~ %s)' % (len(files), 월별rows[0]['월'], 월별rows[-1]['월']),
    '출처': 'G:\\공유 드라이브 · 재무 · 원천세신고파일',
    '월별': 월별rows, '법인별': 법인rows, '소득구분별': 소득rows,
    '상세': tot,
    '합계': {
        '월수': len(월별rows),
        '지급액': sum(x['지급액'] for x in 월별rows),
        '소득세': sum(x['소득세'] for x in 월별rows),
        '지방소득세': sum(x['지방소득세'] for x in 월별rows),
        '납부액': sum(x['납부액'] for x in 월별rows),
        '법인수': len(법인rows),
    },
    '제외시트': 버린시트,
    '주의': [
        '시트 이름의 지급월이 파일의 달과 다른 시트 %d개는 갱신되지 않은 과거 시트라 뺐습니다. 넣으면 같은 금액이 여러 달에 중복으로 더해집니다.' % len(버린시트),
        '한 파일 안에 귀속월이 다른 블록이 여럿 들어 있어, 「총계」 행을 모두 더했습니다. 파일 이름의 달에 실제로 신고·납부한 금액입니다.',
        '세부 행은 합이 소계와 맞지 않는 곳이 있어 쓰지 않았습니다. 가감계와 총계만 읽었습니다.',
        '납부액은 가산세를 포함한 소득세와 지방소득세의 합입니다. 가산세 칸이 비면 본세를 썼습니다.',
        '그룹 전체(7개 법인) 기준입니다. 코코도르 단독 수치가 필요하면 법인별 표를 보십시오.',
    ],
}
json.dump(out, open('wht.json', 'w', encoding='utf-8'), ensure_ascii=False)

S = out['합계']
print('파일 %d개 · 법인 %d개 · 총계행 %d건' % (len(files), S['법인수'], len(tot)))
print('지급액 %s · 소득세 %s · 지방소득세 %s · 납부 %s'
      % tuple('{:,.0f}'.format(S[k]) for k in ('지급액', '소득세', '지방소득세', '납부액')))
print()
print('%-9s %6s %16s %14s %13s' % ('월', '인원', '지급액', '소득세', '납부액'))
for x in 월별rows:
    print('%-9s %6d %16s %14s %13s' % (x['월'], x['인원'],
          '{:,.0f}'.format(x['지급액']), '{:,.0f}'.format(x['소득세']), '{:,.0f}'.format(x['납부액'])))
print()
print('%-14s %16s %13s %6s' % ('법인', '지급액', '납부액', '최대인원'))
for x in 법인rows:
    print('%-14s %16s %13s %6d' % (x['법인'], '{:,.0f}'.format(x['지급액']),
          '{:,.0f}'.format(x['납부액']), x['인원최대']))
print()
for x in 소득rows:
    print('  %-8s 지급 %16s · 납부 %12s' % (x['소득구분'], '{:,.0f}'.format(x['지급액']), '{:,.0f}'.format(x['납부액'])))
