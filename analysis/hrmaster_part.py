# -*- coding: utf-8 -*-
"""인사 마스터(5240 HR 시스템, 2026-09-21 추출) 623명 이력 + 산재 + 근태 API 현황
   개인정보(생년월일·연락처·주소·이메일·주민번호)는 추출 단계에서 차단한다."""
import openpyxl, collections, datetime, json, statistics, re

U   = '/root/.claude/uploads/1c1085cf-e430-5f57-88e8-a8e9f2f98dee'
SRC = U + '/dc112193-_____260921___.xlsx'
INJ = U + '/ad6b13a9-____________11486200080.xlsx'
AS_OF = datetime.date(2026, 9, 21)
KR    = ('코코도르', '코코도르팜')          # 급여대장과 같은 범위

# ── 반출 금지 컬럼 ─────────────────────────────────────────────────
BLOCK = {'한자성명','영문성명','생년월일','사내전화','휴대전화','비상연락처',
         '사내메일','외부메일','현거주지','주민등록번호'}

wb   = openpyxl.load_workbook(SRC, data_only=True)
rows = list(wb['전체'].iter_rows(values_only=True))
HDR  = list(rows[0])
RAW  = [dict(zip(HDR, r)) for r in rows[1:] if r[1]]

def dd(v):
    return v.date() if isinstance(v, datetime.datetime) else None
def iso(v):
    x = dd(v)
    if not x: return None
    return '미정' if x.year >= 2999 else x.isoformat()
def yrs(a, b):
    return round((b - a).days / 365.25, 2) if (a and b and b >= a) else None
def age(v):
    x = dd(v)
    return int((AS_OF - x).days // 365.25) if x else None

# ── 1. 그룹 9개 법인 현황 ──────────────────────────────────────────
ent = collections.OrderedDict()
for x in RAW:
    co = x['회사'] or '(미지정)'
    e = ent.setdefault(co, {'법인': co, '명부': 0, '재직': 0, '휴직': 0, '퇴직': 0})
    e['명부'] += 1
    e[{'재직':'재직','휴직':'휴직','퇴직':'퇴직'}.get(x['재직상태'], '퇴직')] += 1
for e in ent.values():
    e['현원'] = e['재직'] + e['휴직']
    e['누적이탈률'] = round(e['퇴직'] / e['명부'], 4) if e['명부'] else 0
GROUP = sorted(ent.values(), key=lambda e: -e['현원'])

# ── 2. 이직률 (코코도르+코코도르팜 실측) ────────────────────────────
K = [x for x in RAW if x['회사'] in KR]
def hc_at(y):
    end = datetime.date(y, 12, 31)
    return sum(1 for x in K if dd(x['입사일']) and dd(x['입사일']) <= end
               and (not dd(x['퇴직일자']) or dd(x['퇴직일자']) > end))
TURN = []
for y in range(2022, 2027):
    ex = sum(1 for x in K if dd(x['퇴직일자']) and dd(x['퇴직일자']).year == y)
    hi = sum(1 for x in K if dd(x['입사일'])   and dd(x['입사일']).year   == y)
    s, e = hc_at(y - 1), hc_at(y)
    avg = (s + e) / 2
    part = (y == 2026)
    r = ex / avg if avg else None
    TURN.append({'연도': str(y), '기초': s, '기말': e, '평균인원': round(avg, 1),
                 '입사': hi, '퇴사': ex, '순증': hi - ex,
                 '이직률': round(r, 4) if r else None,
                 '연환산이직률': round(r * 12 / 9, 4) if (part and r) else (round(r, 4) if r else None),
                 '기간': '1~9월' if part else '12개월', '부분': part})

# ── 3. 퇴사자 근속 분포 ────────────────────────────────────────────
LV = []
for x in K:
    if x['재직상태'] != '퇴직': continue
    i, o = dd(x['입사일']), dd(x['퇴직일자'])
    t = yrs(i, o)
    LV.append({'성명': x['성명'], '소속': x['소속'], '직위': x['직위'],
               '입사일': iso(x['입사일']), '퇴직일': iso(x['퇴직일자']),
               '근속년수': t, '직원구분': x['직원구분'],
               '퇴직사유': x['퇴직사유'] or None, '국적': x['국적'] or None})
def band(t):
    if t is None: return '미상'
    return ('3개월 미만' if t < .25 else '3~6개월' if t < .5 else '6개월~1년' if t < 1
            else '1~2년' if t < 2 else '2~3년' if t < 3 else '3년 이상')
ORD = ['3개월 미만','3~6개월','6개월~1년','1~2년','2~3년','3년 이상','미상']
cb = collections.Counter(band(l['근속년수']) for l in LV)
LVB = [{'구간': k, '인원': cb[k], '비중': round(cb[k]/len(LV), 4)} for k in ORD if cb[k]]
tt = [l['근속년수'] for l in LV if l['근속년수'] is not None]
LVS = {'퇴사자': len(LV), '중위근속': round(statistics.median(tt), 2), '평균근속': round(sum(tt)/len(tt), 2),
       '1년내': sum(1 for t in tt if t < 1), '1년내비중': round(sum(1 for t in tt if t < 1)/len(tt), 4),
       '3개월내': sum(1 for t in tt if t < .25), '3개월내비중': round(sum(1 for t in tt if t < .25)/len(tt), 4),
       '사유기재': sum(1 for l in LV if l['퇴직사유'])}

# 최근 2년 부서별 퇴사
c2 = collections.Counter()
for x in K:
    o = dd(x['퇴직일자'])
    if o and o >= datetime.date(2025, 1, 1): c2[x['소속'] or '(미지정)'] += 1
LVD = [{'소속': k, '퇴사': v} for k, v in c2.most_common()]

# ── 4. 휴직자 (날짜 완비) ──────────────────────────────────────────
LEAVE = []
for x in RAW:
    if x['재직상태'] != '휴직': continue
    s, e = dd(x['휴직시작일자']), dd(x['휴직종료일자'])
    LEAVE.append({'성명': x['성명'], '법인': x['회사'], '소속': x['소속'], '직위': x['직위'],
                  '휴직시작': iso(x['휴직시작일자']), '복직예정': iso(x['휴직종료일자']),
                  '경과일': (AS_OF - s).days if s else None,
                  '예정기간(개월)': round((e - s).days / 30.44, 1) if (s and e and e.year < 2999) else None,
                  '복직미정': bool(e and e.year >= 2999),
                  '입사일': iso(x['입사일']), '근속년수': yrs(dd(x['입사일']), AS_OF), '성별': x['성별']})
LEAVE.sort(key=lambda r: r['휴직시작'] or '')

# ── 5. 재직자 인력 구성 ────────────────────────────────────────────
A = [x for x in RAW if x['재직상태'] in ('재직','휴직') and x['회사'] in KR]
def mix(key, src=None):
    c = collections.Counter(str((x.get(key) or '(미기재)')) for x in (src or A))
    n = sum(c.values())
    return [{'값': k, '인원': v, '비중': round(v/n, 4)} for k, v in c.most_common()]
ages = [age(x['생년월일']) for x in A]
ages = [a for a in ages if a]
ab = collections.Counter()
for a in ages:
    ab['20대 이하' if a < 30 else '30대' if a < 40 else '40대' if a < 50 else '50대' if a < 60 else '60대 이상'] += 1
AGE = {'구간': [{'구간': k, '인원': ab[k], '비중': round(ab[k]/len(ages), 4)}
                for k in ['20대 이하','30대','40대','50대','60대 이상'] if ab[k]],
       '평균': round(sum(ages)/len(ages), 1), '중위': round(statistics.median(ages), 1),
       '확인': len(ages), '전체': len(A)}
FOR = [x for x in A if x['외국인여부'] == 'Y']
COMP = {'현원': len(A), '고용형태': mix('직원구분'), '성별': mix('성별'),
        '근무유형': mix('근무유형'), '학력': mix('학력'),
        '외국인': {'인원': len(FOR), '비중': round(len(FOR)/len(A), 4),
                 '국적': mix('국적', FOR)},
        '연령': AGE}

# ── 6. 산재 요양 ───────────────────────────────────────────────────
iw = openpyxl.load_workbook(INJ, data_only=True)['sheet']
ir = list(iw.iter_rows(values_only=True)); ih = list(ir[0])
INJURY = []
for r in ir[1:]:
    if not r[0]: continue
    o = {h: v for h, v in zip(ih, r) if h and h not in BLOCK}
    s, e = o.get('요양시작일'), o.get('요양종료일')
    def p(v):
        if isinstance(v, datetime.datetime): return v.date()
        if isinstance(v, str): return datetime.date.fromisoformat(v[:10])
        return None
    ps, pe = p(s), p(e)
    INJURY.append({'성명': o.get('이름'), '재해일자': str(o.get('재해일자'))[:10],
                   '요양시작': str(s)[:10], '요양종료': str(e)[:10],
                   '요양일수': (pe - ps).days + 1 if (ps and pe) else None,
                   '의료기관': o.get('의료기관'), '재해형태': o.get('재해발생형태'),
                   '정밀진단': o.get('정밀진단'), '관할지사': o.get('요양관리지사')})
INJURY.sort(key=lambda r: r['재해일자'], reverse=True)
ic = collections.Counter(r['관할지사'] for r in INJURY)
INJ_SUM = {'건수': len(INJURY),
           '총요양일': sum(r['요양일수'] or 0 for r in INJURY),
           '평균요양일': round(sum(r['요양일수'] or 0 for r in INJURY)/len(INJURY)),
           '최장': max(INJURY, key=lambda r: r['요양일수'] or 0),
           '지사별': [{'지사': k, '건수': v} for k, v in ic.most_common()],
           '기간': INJURY[-1]['재해일자'][:4] + '~' + INJURY[0]['재해일자'][:4]}

# ── 7. 근태 API 연계 현황 ──────────────────────────────────────────
API = {
  '공급사': '5240 (인사시스템)', '담당': '박준영 이사',
  '요청자': '코코도르 인사파트 이윤정', '착수일': '2026-09-18', '가이드수령': '2026-09-23',
  'URL': 'https://api.5240.cloud/getBatchQueryApiCall.do',
  '방식': 'HTTPS/POST · JSON', 'interfaceId': 'BATCH_IF_WORK (근태정보 조회)',
  '인증': 'interfaceKey — 서비스영역ID와 조회일자(yyyymmdd)로 매 호출 생성',
  '조회단위': 'staYmd 1일 단위 (endYmd 미사용)',
  '응답항목': ['직원번호','성명','조직명','일자','출근시간','퇴근시간','체류시간','근무상태','특이사항'],
  '요청했으나_미확정': ['휴가현황(휴가명)','출장현황(출장지)','요일','근무특이사항 코드체계'],
  '메일상_공급사답변': '화면 단위 API는 제공 불가. 일자·사번·성명·구분(휴가/출장)·구분명·출근시간·퇴근시간까지 가능.',
  '미해결': ['인증키(API Key) 미수령 — 2026-09-23 기준 가이드만 전달됨',
             '월차·반차를 구분할 휴가명 코드가 응답 항목에 없음',
             '1일 단위 호출이라 1년치는 365회 호출 필요 — 배치 설계 필요'],
  '연결되면_가능해지는_것': ['개인별 발생·사용·잔여 연차', '부서별 연차 소진율',
                          '미사용 연차의 잠재 보상 부채', '역산이 아닌 실측 연장·휴일근무 시간',
                          '지각·조퇴·결근 현황'],
}

OUT = {'기준일': AS_OF.isoformat(), '출처': '5240 HR 인사기록 (2026-09-21 추출) 623명',
       '명부총원': len(RAW), '범위': '그룹 9개 법인 전체. 이직률·구성은 코코도르+코코도르팜만.',
       'group': GROUP, 'turnover': TURN, 'leavers': LV, 'leaverBands': LVB,
       'leaverSummary': LVS, 'leaverByDept': LVD, 'leave': LEAVE, 'composition': COMP,
       'injury': INJURY, 'injurySummary': INJ_SUM, 'api': API,
       '한계': [
         '퇴직사유가 기재된 건은 451명 중 %d건뿐입니다. 이탈 원인 분석은 아직 불가능합니다.' % LVS['사유기재'],
         '국적이 비어 있는 재직자가 있어 외국인 국적 분포는 기재된 인원만 집계했습니다.',
         '인사마스터 현원과 2026-02 급여대장 인원은 기준일이 7개월 달라 숫자가 다릅니다.',
         '생년월일·연락처·주소·이메일은 추출 단계에서 차단했고, 연령은 구간으로만 환산했습니다.',
       ]}

# ── PII 차단 검사 ──────────────────────────────────────────────────
blob = json.dumps(OUT, ensure_ascii=False, default=str)
assert not re.search(r'\d{6}-\d{7}', blob), 'PII 주민번호'
assert not re.search(r'\d{6}-[1-4]\*+', blob), 'PII 주민번호(마스킹)'
assert not re.search(r'01[016-9]-?\d{3,4}-?\d{4}', blob), 'PII 휴대폰'
assert not re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', blob.replace('api.5240.cloud','')), 'PII 이메일'

d = json.load(open('hrdata.json', encoding='utf-8'))
d['hrMaster'] = OUT
json.dump(d, open('hrdata.json', 'w'), ensure_ascii=False)

print('명부', len(RAW), '· 법인', len(GROUP), '· 퇴사자', len(LV), '· 휴직', len(LEAVE), '· 산재', len(INJURY))
print('이직률', [(t['연도'], t['이직률']) for t in TURN])
print('퇴사 근속', LVS)
print('외국인', COMP['외국인']['인원'], COMP['외국인']['국적'][:5])
print('PII 검사 통과')
