# -*- coding: utf-8 -*-
"""입사원서 조회 — 인사마스터의 입사 관련 항목 + 계약급여 3시점(과거 연봉).
   민감정보(보훈·장애·결혼·군필)는 개인별로 내보내지 않고 집계만 남긴다."""
import openpyxl, json, collections, datetime

U='/root/.claude/uploads/1c1085cf-e430-5f57-88e8-a8e9f2f98dee'
AS_OF=datetime.date(2026,9,21)
d=json.load(open('hrdata.json',encoding='utf-8'))
wb=openpyxl.load_workbook(U+'/dc112193-_____260921___.xlsx',data_only=True)
rows=list(wb['전체'].iter_rows(values_only=True)); H=list(rows[0])
RAW=[dict(zip(H,r)) for r in rows[1:] if r[1]]
A=[x for x in RAW if x['재직상태'] in ('재직','휴직') and x['회사'] in ('코코도르','코코도르팜')]

def dd(v): return v.date() if isinstance(v,datetime.datetime) else None
def iso(v):
    x=dd(v); return None if not x else ('미정' if x.year>=2999 else x.isoformat())
def txt(v):
    v=(v if v is not None else '')
    v=str(v).strip()
    return v or None

# 과거 연봉 — 계약급여 3시점
PY_ = {p['성명']: p for p in d['personYear']}
RS  = {r['성명']: r for r in d['raises']}

CODE = {'01':'공개채용','02':'추천','03':'경력·수시'}   # 원본에 코드표 없음 — 라벨은 추정
recs=[]
for x in A:
    nm=x['성명']; py=PY_.get(nm) or {}; rs=RS.get(nm) or {}
    recs.append({
        '성명': nm, '직원번호': txt(x['직원번호']), '법인': x['회사'], '소속': txt(x['소속']),
        '직위': txt(x['직위']), '직책': txt(x['직책']), '고용형태': txt(x['직원구분']),
        '급여유형': txt(x['급여유형']), '재직상태': x['재직상태'],
        '입사일': iso(x['입사일']), '그룹입사일': iso(x['그룹입사일']),
        '근속년수': round(((AS_OF-dd(x['입사일'])).days/365.25),2) if dd(x['입사일']) else None,
        '학력': txt(x['학력']), '학교': txt(x['학교']), '전공': txt(x['전공']),
        '채용구분': txt(x['채용구분명']),
        '채용구분명': CODE.get(txt(x['채용구분명']) or '', txt(x['채용구분명'])),
        '입사추천자': txt(x['입사추천자']),
        '승진일자': iso(x['승진일자']), '승진연수': txt(x['승진연수']),
        '근무유형': txt(x['근무유형']), '국적': txt(x['국적']),
        '연봉_2024_09': py.get('계약_2024_09'), '연봉_2025_07': py.get('계약_2025_07'),
        '연봉_2026_02': py.get('계약_2026_02') or rs.get('T2_2026_02'),
        '누적인상률': py.get('누적인상률'), '연환산인상률': py.get('연환산인상률'), '등급': py.get('등급'),
    })
recs.sort(key=lambda r: (r['입사일'] or '9999'))

FIELDS=[('학력','학력'),('학교','학교'),('전공','전공'),('채용구분','채용구분'),
        ('입사추천자','입사추천자'),('직위','직위'),('승진일자','승진일자'),
        ('입사일','입사일'),('국적','국적')]
fill=[]
for k,lab in FIELDS:
    n=sum(1 for r in recs if r.get(k))
    fill.append({'항목':lab,'기재':n,'미기재':len(recs)-n,'기재율':round(n/len(recs),4)})
fill.sort(key=lambda r:-r['기재율'])

def dist(key, src=None):
    c=collections.Counter((r.get(key) or '(미기재)') for r in (src or recs))
    n=sum(c.values())
    return [{'값':k,'인원':v,'비중':round(v/n,4)} for k,v in c.most_common()]

# 민감정보는 집계만
SENS={}
for k in ['군필여부','보훈여부','장애여부','결혼여부']:
    c=collections.Counter(txt(x.get(k)) or '(미기재)' for x in A)
    SENS[k]=[{'값':v,'인원':n} for v,n in c.most_common()]

edu=[r for r in recs if r['학력']]
d['applyDesk']={
    '기준일': AS_OF.isoformat(),
    '출처': '5240 인사마스터(2026-09-21) 입사 관련 항목 + 계약급여 3시점',
    '대상': len(recs),
    'records': recs,
    'fill': fill,
    '학력분포': dist('학력'), '채용구분분포': dist('채용구분명'),
    '전공분포': dist('전공', edu)[:15],
    '학교분포': dist('학교', edu)[:15],
    '민감집계': SENS,
    '코드주의': '채용구분은 원본이 01/02/03 코드이고 코드표가 없습니다. 화면의 이름표는 추정이니 인사파트 확인이 필요합니다.',
    '미보유': [
        {'자료':'입사지원서 원본','상태':'미확보','설명':'스캔본 또는 원본 파일이 전달되지 않았습니다. 인사시스템에도 첨부 항목이 없습니다.'},
        {'자료':'이력서·자기소개서','상태':'미확보','설명':'채용 당시 제출본입니다. 보관 위치와 보존기한을 먼저 정해야 합니다.'},
        {'자료':'적성검사 결과','상태':'미확보','설명':'실시 여부 자체가 확인되지 않았습니다. 실시했다면 검사기관·시행일·결과지가 필요합니다.'},
        {'자료':'입사구비서류 체크리스트','상태':'미확보','설명':'주민등록등본·통장사본·자격증·건강진단서 등 제출 여부 기록입니다.'},
        {'자료':'근로계약서 스캔','상태':'부분','설명':'계약 마스터에 조건은 있으나 서명본 이미지는 없습니다.'},
    ],
    '한계': [
        '학력·학교·전공이 %d%%만 채워져 있어 개인별 조회 시 대부분 빈칸입니다.' % round(fill[0]['기재율']*100) if False else
        '학력 기재율이 %s로 낮아 개인별 조회에서 3분의 2는 빈칸입니다.' % ('%.0f%%' % ([f for f in fill if f['항목']=='학력'][0]['기재율']*100)),
        '보훈·장애·결혼 여부는 민감정보라 개인별로 내보내지 않고 집계만 표시합니다.',
        '과거 연봉은 계약급여 3시점(2024-09 / 2025-07 / 2026-02)뿐입니다. 입사 당시 연봉은 원본이 없습니다.',
        '입사지원서·이력서·적성검사 원본은 확보되지 않았습니다.',
    ],
}
json.dump(d,open('hrdata.json','w'),ensure_ascii=False)
print('대상',len(recs))
for f in fill: print(f"  {f['항목']:10s} {f['기재']:3d}/{len(recs)} {f['기재율']*100:5.1f}%")
print('민감집계', {k:[x['값'] for x in v] for k,v in SENS.items()})
