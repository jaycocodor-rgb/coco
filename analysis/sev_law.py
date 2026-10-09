# -*- coding: utf-8 -*-
"""퇴직급여 자료가 들어왔으니 법규 점검의 「퇴직급여 제도」 항목을 다시 판정한다.

   들어오기 전에는 「DB인지 DC인지도 모른다」였다. 지금은 안다.
   제도는 확인됐고, 그 대신 계좌 미개설이 드러났다. 판정을 확인불가에서 위험으로 내린다.
"""
import json

H = 'hrdata.json'
d = json.load(open(H, encoding='utf-8'))
S = d['sevDesk']; G = S['집계']
hit = 0
for c in d['lawCheck']['점검']:
    if c['항목'] != '퇴직급여 제도':
        continue
    hit += 1
    c['판정'] = '위험'
    c['심각도'] = '치명'
    c['근거'] = '근로자퇴직급여보장법 제4조 · 제9조 · 제20조'
    c['내용'] = ('제도는 확정기여형(DC)으로 확인했습니다(코코도르 DC 규약 2023.03 개정). '
                '%s년 개인별 월납 대장 %s명분을 읽었고 불입 총액은 %s원입니다. '
                '다만 운용사 칸이 빈 사람이 %d명이고, 그 가운데 %d명은 1년이 넘었습니다. '
                '2025년 퇴직자 %d명에게는 「23년귀속·24년귀속 지연이자」가 붙어 정산됐습니다. '
                '적립은 했는데 계좌에 넣지 않았다는 뜻이면 제20조 납입 의무를 넘긴 것입니다.'
                % ('·'.join(G['연도']), G['사람수'], '{:,}'.format(G['불입총계']),
                   G['계좌없음'], G['미가입1년'], G['지연이자']))
    c['조치'] = ('① 계좌 없는 %d명의 적립액이 실제로 금융기관에 들어갔는지 은행별로 확인합니다. '
                '② 안 들어갔으면 지연이자(시행령 제11조 — 납입 예정일 다음 날부터 연 10%%, '
                '퇴직 후 14일 경과분은 연 20%%)를 더해 납입합니다. '
                '③ 2023년 월납 대장을 찾아 연도축의 빈 해를 메웁니다. '
                '자세한 내역은 20번 「퇴직연금 불입 · 퇴직금」에 있습니다.' % G['미가입1년'])
    c['처벌'] = '제20조 위반은 시정지시 대상이고, 미납 부담금에는 지연이자가 붙습니다. 퇴직금 미지급(제9조)은 3년 이하 징역 또는 3천만원 이하 벌금입니다.'
assert hit == 1, '퇴직급여 제도 항목을 찾지 못했습니다'

# 집계 다시 센다
from collections import Counter
c = Counter(x['판정'] for x in d['lawCheck']['점검'])
s = Counter(x['심각도'] for x in d['lawCheck']['점검'])
d['lawCheck']['집계'] = {'항목수': len(d['lawCheck']['점검']), '위반': c['위반'], '위험': c['위험'],
                        '확인불가': c['확인불가'], '적합': c['적합'], '치명': s['치명']}
json.dump(d, open(H, 'w', encoding='utf-8'), ensure_ascii=False, default=str)
open('/home/user/coco/hr-dashboard/data.js', 'w', encoding='utf-8').write(
    'window.HR_DATA=' + json.dumps(d, ensure_ascii=False, default=str, separators=(',', ':')) + ';')
print(json.dumps(d['lawCheck']['집계'], ensure_ascii=False))
