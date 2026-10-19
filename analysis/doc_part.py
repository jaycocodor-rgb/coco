# -*- coding: utf-8 -*-
"""인사 문서함 — 필수·중요 문서를 분류별로 등록하고 계속 추가한다.
   각 문서: 제목·날짜·중요도·상태·드라이브 링크. 판독 가능한 핵심 규정은 요약을 방 안에 넣는다.
   새 문서가 생기면 docs 리스트에 한 줄 추가하면 된다(지속 업그레이드).
   출력: hrdata.json['docHub']
"""
import json, datetime
U = 'https://drive.google.com/file/d/%s/view'
def doc(제목, 날짜, 중요도, 상태, fid=None, 비고=''):
    return {'제목': 제목, '날짜': 날짜, '중요도': 중요도, '상태': 상태,
            '링크': (U % fid) if fid else None, '비고': 비고}

분류 = [
    {'군': '규정·제도', '설명': '회사가 지켜야 할 인사 규칙. 가장 먼저 최신화해야 할 묶음.', 'docs': [
        doc('확정기여형 퇴직연금 규약 (2023.03 개정)', '2023-03', '필수', '방에 반영', '1RYnbl6YT0lsM6DevFIY_2UrFQwtdO_xM', '하나·산업은행. 부담금·미납 지연이자·중도인출 요건 수록'),
        doc('복리후생규정', '2022-05', '필수', '링크(hwp)', '1QDOX4I4sxiozT5EhMH56Q_Vth2CleSiD', 'hwp라 자동 판독 불가. 현행 유효 여부 확인 필요'),
        doc('경조사비 지급 규정', '2022-05', '필수', '방에 반영', '1KcZF9JjL5fGzoeBwD7GeIURI-AK0ky8w', '초안 PDF로 판독해 0-3 ⑥에 표로 수록'),
        doc('집행임원 인사규정 (안내)', '-', '중요', '링크(ppt)', '1sJ692zkD1UJMY4kOC3TVLeqiGf_jBSd0', '임원 인사 규정'),
        doc('야근비 변경 및 야근교통비 재안내', '2022-07', '중요', '링크(hwp)', '1NPspDXnFmUuKVXsg9kpLmgQgRXLOUz-4', ''),
        doc('입퇴사 프로세스 및 근로계약내용 (센터직)', '2022-05', '필수', '링크(hwp)', '1g8tXzz2f7_mtgV3Vd3EkedPvPxOqGuaZ', ''),
        doc('채용 프로세스 및 근로계약 안내 (센터직)', '2022-05', '중요', '링크(hwp)', '1blnfGJTtUegL5nij7hYnRftCdPU1exvu', ''),
    ]},
    {'군': '전략·계획', '설명': '인사 방향을 정한 문서. 실행 점검의 기준.', 'docs': [
        doc('인사 혁신 Master Plan · 10대 과제', '2020-02', '필수', '방에 반영', '1iMnGyRteIdZoZCMnK_l5DsakHawnYps7', '0-3 ⑦에 2026 실측과 대조 수록'),
    ]},
    {'군': '매뉴얼·양식', '설명': '실무가 반복해 쓰는 절차·양식.', 'docs': [
        doc('업무 매뉴얼 (인사채용파트)', '2018-08', '중요', '방에 반영', '1WQZeSunBC5N4sXfRqi1lzcSxJeIKNamo', '채용 프로세스 요약 아래 수록'),
        doc('급여지급확인원 (예스폼 양식)', '2022-05', '참고', '링크(docx)', '1lUS8Yu1Q-NdntADFc4eCcP4LlQ0iZskH', ''),
        doc('JADE 인사시스템 평가모듈 견적서', '2020-06', '참고', '링크(pdf)', '1oVG7ltJTYZiq3x9hof7wPUt04WijHBnX', '평가 제도 재가동 시 참고'),
    ]},
    {'군': '명부·인사 DB', '설명': '사람 데이터의 원본. 방의 숫자가 여기서 나온다.', 'docs': [
        doc('직원명부_입퇴사자전체 (53필드)', '2026-09-16', '필수', '방에 반영', '1ECOOTrHzUl6wFyPOXtusEXIh-4lfOYlR', '최신 인사 마스터. 0-3 ⑧에 비식별 집계'),
        doc('03. 근로자명부', '2026-09-16', '필수', '링크(zip)', '1dNJjRWShxAIj_WZi6P1Mm8rRWW8-Uz10', '법정 근로자명부(근기법 제41조)'),
        doc('퇴직연금 가입자명부', '2026-10', '중요', '링크(xlsx)', '1AWHxx4oTR5nQTgx_bdhYkpH43eMIwJWQ', ''),
        doc('부서별 인원명부', '2022-05', '참고', '링크(xlsx)', '1aLYT_zjZmTkSXOhZLw8-Tw9QRPV8RPGK', '현재 데이터로 대체됨'),
    ]},
    {'군': '급여·세무·퇴직급여', '설명': '돈이 나간 기록. 금액 검증의 근거.', 'docs': [
        doc('2026 귀속 퇴직연금 부담금(월납)_코코도르', '2026-08', '필수', '방에 반영', '1nvnHxtA1kIoTKgYAxVjA41_oZA_LwU_X', '5-3·20번의 원본. 암호 1235'),
        doc('2025 귀속 퇴직연금 부담금(월납)_코코도르', '2026-01', '필수', '방에 반영', '134LTz78wPG0OeLL9skceBq5WQXkZ4LY_', ''),
        doc('2024 귀속 퇴직연금 부담금(월납)_코코도르', '2025-01', '필수', '방에 반영', '10IAm4kk53MilJ8WZ4Wfb_yxdmkUzbwgd', ''),
        doc('퇴직급여 충당부채 계산내역', '2026-03', '중요', '링크(xlsx)', '1JLQlgyxmYibsRnqQE5Mj-tjBSYBCOU9w', ''),
    ]},
    {'군': '해외·대만', '설명': '해외 법인 보상 설계 참고.', 'docs': [
        doc('대만법인 대표이사 급여 제안', '2022-06', '중요', '링크(pptx)', '1WnqJU-fADMQDHo4g-SUgG7zWurqVbZnB', ''),
        doc('대만법인 인센티브 제안', '2022-05', '중요', '링크(pptx)', '1_EBlbDaBO8sYFAw4Al0mEAbcmgEghgsP', ''),
        doc('대만법인 연봉현황', '2022-05', '참고', '링크(xlsx)', '1OVQXv9pqRIBu3ntAGL9rQIVt3nXFoTU0', ''),
    ]},
    {'군': '성과·면담', '설명': '2022년에 있던 성과·면담 자료. 재가동 대상.', 'docs': [
        doc('22년도 PI 평가표', '2022-05', '중요', '링크(xlsx)', '1O7f70jT-d88utwz3gFazaZk1HlSc3VRW', '성과급 평가표'),
        doc('PI 지급안', '2022-04', '중요', '링크(xlsx)', '1RjOfiHnkwVjAFNoZgh4fAnua3m8xK0vZ', ''),
        doc('면담일지 (2022)', '2022-06', '참고', '링크(docx)', '1iZ0r7wVnJJkG25F39dA7haRFmKDIfCBp', 'Stay 면담 복원 시 양식 참고'),
    ]},
    {'군': '주주 명부', '설명': '지분 관련 민감 문서. 열람 제한 권장.', 'docs': [
        doc('제이스퍼퓸 주주명부 (6월말)', '2026-06', '중요', '링크(xlsx)', '1G01phVJ33oFltMu0z7EEtJzaUv4cZKNO', '민감'),
        doc('코코도르팜 주주명부 (6월말)', '2026-06', '중요', '링크(xlsx)', '12495D_AA4FLzB6hhZLi8xYQtAWfpSwdY', '민감'),
        doc('헬스투데이 주주명부 (6월말)', '2026-06', '중요', '링크(xlsx)', '1HG_SbiIrlLbo25tO98onWVmqBLfaFZIi', '민감'),
    ]},
]

핵심요약 = [
    {'문서': '확정기여형 퇴직연금 규약 (2023.03)', '항목': [
        '제도: 확정기여형(DC). 운용·자산관리기관은 하나은행·산업은행.',
        '부담금: 가입자 연간 임금총액의 1/12을 매년 말일까지 계정에 납입(제13·14조).',
        '미납 시: 정기납입일부터 60일 연장, 그 뒤 지연이자 — 퇴직 14일 전까지 연 10%, 이후 연 20%(제15조).',
        '가입대상: 소정근로 주 15시간 이상·근속 1년 이상. 임원 포함 가능(제10조).',
        '중도인출: 무주택 주택구입·전세, 6개월 이상 요양 의료비, 파산·개인회생, 대학등록금·혼례·장례 등(제26조).',
        '→ 20번에서 드러난 「계좌 미개설 11명·지연이자 9건」이 바로 이 제15·18조 위반 소지.',
    ]},
    {'문서': '채용 프로세스 (업무 매뉴얼, 2018)', '항목': [
        '① 채용요청(전자결재 인력채용요청서) → ② 공고·서칭·헤드헌팅 → ③ 서류전형 → ④ 인·적성(사람인 휴노) → ⑤ 면접(1차 실무+요청자, 2차 대표·이사, 3차 급여) → ⑥ 합·불 통보 → ⑦ 입사.',
        '입사 제출서류: 신분증·통장사본·어학성적표·졸업(재학)증명서.',
        '참고자료: 사무직·현장직 면접 체크리스트, 면접 평가표.',
        '→ 0-3 ①유치 단계의 「채용 기준서·면접위원 교육」이 이 매뉴얼을 되살리는 일.',
    ]},
]

d = json.load(open('hrdata.json', encoding='utf-8'))
tot = sum(len(c['docs']) for c in 분류)
반영 = sum(1 for c in 분류 for x in c['docs'] if x['상태'] == '방에 반영')
필수 = sum(1 for c in 분류 for x in c['docs'] if x['중요도'] == '필수')
d['docHub'] = {
    '기준일': datetime.date.today().isoformat(),
    '출처': '구글 드라이브 인사 관련 폴더(인사파트·재무_대외비·최근 업로드)에서 추린 핵심 문서',
    '안내': [
        '인사에서 꼭 챙겨야 할 문서를 분류별로 모았습니다. 「링크」를 누르면 드라이브 원본이 열립니다.',
        '「방에 반영」은 내용을 읽어 이 방 메뉴 안에 이미 넣은 문서입니다(규약·10대 과제·명부·퇴직연금 대장 등).',
        '「링크(hwp/zip)」는 자동 판독이 안 되는 형식이라 원본 링크만 걸어 둔 문서입니다.',
        '새 문서가 생기면 이 목록에 계속 추가됩니다. 추가할 문서가 있으면 알려 주세요.',
    ],
    '분류': 분류,
    '핵심요약': 핵심요약,
    '집계': {'문서수': tot, '분류수': len(분류), '필수': 필수, '방반영': 반영,
            '링크만': tot - 반영},
    '한계': [
        'hwp·zip·ppt는 커넥터가 자동 판독하지 못해 원본 링크만 걸었습니다. 내용 확인은 사람이 열어야 합니다.',
        '링크는 드라이브 공유 설정을 따릅니다. 권한이 없는 사람은 열리지 않습니다.',
        '주주명부 등 민감 문서는 열람 범위를 좁히는 것을 권합니다.',
    ],
}
json.dump(d, open('hrdata.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
open('/home/user/coco/hr-dashboard/data.js', 'w', encoding='utf-8').write(
    'window.HR_DATA=' + json.dumps(d, ensure_ascii=False, default=str, separators=(',', ':')) + ';')
import os
print('문서', tot, '· 분류', len(분류), '· 필수', 필수, '· 방반영', 반영)
print('data.js', os.path.getsize('/home/user/coco/hr-dashboard/data.js'))
