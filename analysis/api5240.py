#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""5240 근태 API 클라이언트 — 일일 인사 보고 자동화용.

인증 정보는 반드시 환경변수로 넘긴다. 파일에 적지 않는다.
    CO5240_SID        서비스영역ID (정수)         ← 5240에서 발급
    CO5240_SITE_ID    사이트ID (선택)
    CO5240_STAFF_NO   요청자 사번 (선택)

사용법
    python api5240.py key                              오늘자 interfaceKey 출력
    python api5240.py key --date 2026-09-18            특정일 키 (명세 예시 검증용)
    python api5240.py selftest                         키 공식을 명세 예시값으로 검증
    python api5240.py probe                            엔드포인트 도달 가능 여부만 확인
    python api5240.py fetch --date 2026-09-23          1일 조회 → out/work_YYYYMMDD.json
    python api5240.py fetch --date 2026-09-23 --dry-run 실제 호출 없이 요청 본문만 출력
    python api5240.py backfill --from 2026-01-01 --to 2026-09-23
                                                       일 단위 소급 수집 (중단 지점 재개)
    python api5240.py report --date 2026-09-23         수집분 → 일일 근태보고 표 생성
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = 'https://api.5240.cloud/getBatchQueryApiCall.do'
INTERFACE_ID = 'BATCH_IF_WORK'
OUT_DIR = Path(os.environ.get('CO5240_OUT', 'out'))
TIMEOUT = 30
RETRY = 4                 # 2s → 4s → 8s → 16s
RATE_SLEEP = 0.4          # 소급 수집 시 호출 간 간격

# 정규 종업시간 — 연장근무 판정 기준
REGULAR_END = dt.time(18, 0)
FULL_DAY_HOURS = 8.0


# ── 인증 ──────────────────────────────────────────────────────────────
def interface_key(sid: int, ymd: int) -> int:
    """5240 명세: (서비스영역ID × 조회일자) + (서비스영역ID²) + (조회일자²)

    >>> interface_key(1, 20260918)
    410504818463643
    """
    return sid * ymd + sid * sid + ymd * ymd


def require_sid() -> int:
    raw = os.environ.get('CO5240_SID')
    if not raw:
        sys.exit('CO5240_SID 가 설정되지 않았습니다. 5240에서 발급받은 서비스영역ID를 넣으십시오.\n'
                 '  예) export CO5240_SID=1')
    try:
        return int(raw)
    except ValueError:
        sys.exit(f'CO5240_SID 는 정수여야 합니다 (받은 값: {raw!r})')


def ymd_int(d: dt.date) -> int:
    return int(d.strftime('%Y%m%d'))


def parse_date(s: str) -> dt.date:
    return dt.datetime.strptime(s.strip(), '%Y-%m-%d').date()


# ── 호출 ──────────────────────────────────────────────────────────────
def build_payload(day: dt.date, sid: int) -> dict:
    """staYmd 1일 단위. endYmd 는 명세상 미지원이라 보내지 않는다."""
    ymd = ymd_int(day)
    body = {
        'interfaceId': INTERFACE_ID,
        'interfaceKey': str(interface_key(sid, ymd)),
        'staYmd': str(ymd),
    }
    for env, field in (('CO5240_SITE_ID', 'siteId'), ('CO5240_STAFF_NO', 'workStaffNo')):
        v = os.environ.get(env)
        if v:
            body[field] = v
    return body


def post(body: dict) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    last = None
    for attempt in range(RETRY):
        req = urllib.request.Request(
            URL, data=data, method='POST',
            headers={'Content-Type': 'application/json; charset=utf-8',
                     'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace')[:500]
            if e.code in (401, 403):        # 인증 문제는 재시도해도 같다
                raise RuntimeError(f'인증 거부 HTTP {e.code} — 서비스영역ID/키를 확인하십시오.\n{detail}') from e
            last = RuntimeError(f'HTTP {e.code}: {detail}')
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
        if attempt < RETRY - 1:
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f'{RETRY}회 재시도 실패: {last}')


def rows_of(resp: dict) -> list:
    """응답 래퍼 구조가 확정되지 않았으므로 흔한 키를 차례로 본다."""
    if isinstance(resp, list):
        return resp
    for k in ('data', 'resultList', 'list', 'rows', 'items', 'result'):
        v = resp.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for k2 in ('list', 'rows', 'data'):
                if isinstance(v.get(k2), list):
                    return v[k2]
    return []


def fetch_day(day: dt.date, sid: int, dry: bool = False) -> dict:
    body = build_payload(day, sid)
    if dry:
        return {'_dryRun': True, '_url': URL, '_request': body}
    resp = post(body)
    return {'_url': URL, '_request': body, '_fetchedAt': dt.datetime.now().isoformat(timespec='seconds'),
            '_rowCount': len(rows_of(resp)), 'response': resp}


def save(day: dt.date, payload: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f'work_{ymd_int(day)}.json'
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    return p


# ── 근태유형 판정 ─────────────────────────────────────────────────────
def pick(row: dict, *names):
    for n in names:
        if n in row and row[n] not in (None, ''):
            return row[n]
    return None


def hhmm(v) -> float | None:
    """'0900' / '09:00' / '9:00' → 9.0"""
    if v in (None, '', '/', '-'):
        return None
    s = str(v).strip().replace(':', '')
    if not s.isdigit():
        return None
    s = s.zfill(4)[:4]
    return int(s[:2]) + int(s[2:]) / 60.0


def classify(row: dict) -> dict:
    """응답 1행 → 일일보고 근태유형. 체류시간 8H 기준으로 연차 구분."""
    state = (pick(row, '근무상태', 'workStatus', 'wrkSttsNm') or '').strip()
    inn, out = hhmm(pick(row, '출근시간', 'inTime', 'atdTm')), hhmm(pick(row, '퇴근시간', 'outTime', 'lvTm'))
    stay = pick(row, '체류시간', 'stayTime', 'stayHr')
    try:
        stay = float(str(stay).replace(':', '.')) if stay not in (None, '') else None
    except ValueError:
        stay = None
    if stay is None and inn is not None and out is not None:
        stay = round(out - inn, 2)

    if '휴직' in state:
        kind, used = '휴직', None
    elif '출장' in state:
        kind, used = '출장', None
    elif '외근' in state:
        kind, used = '외근', None
    elif '무급' in state:
        kind, used = '무급휴가', None
    elif '휴무' in state:
        kind, used = '휴무', None
    elif '연차' in state or '휴가' in state:
        if stay is None or stay <= 0:
            kind, used = '연차(8H)', FULL_DAY_HOURS
        else:
            kind, used = '연차(8H미만)', round(FULL_DAY_HOURS - stay, 2)
    elif inn is None and out is None:
        kind, used = '출근기록누락', None
    else:
        kind, used = '정상출근', None

    ot = round(out - REGULAR_END.hour, 2) if (out is not None and out > REGULAR_END.hour) else 0.0
    return {'사번': pick(row, '직원번호', 'staffNo', 'empNo'),
            '성명': pick(row, '성명', 'staffNm', 'empNm'),
            '조직': pick(row, '조직명', 'deptNm', 'orgNm'),
            '일자': pick(row, '일자', 'workYmd', 'staYmd'),
            '출근': inn, '퇴근': out, '체류시간': stay,
            '근무상태': state, '근태유형': kind, '연차사용시간': used, '연장시간': ot,
            '특이사항': pick(row, '특이사항', 'remark', 'etcCntn')}


TYPE_ORDER = ['정상출근', '연차(8H)', '연차(8H미만)', '휴무', '출장', '외근',
              '무급휴가', '휴직', '출근기록누락', '입사자/퇴사자']


def build_report(day: dt.date) -> dict:
    p = OUT_DIR / f'work_{ymd_int(day)}.json'
    if not p.exists():
        sys.exit(f'{p} 가 없습니다. 먼저 fetch 로 수집하십시오.')
    payload = json.loads(p.read_text(encoding='utf-8'))
    recs = [classify(r) for r in rows_of(payload.get('response', payload))]

    by = {t: [] for t in TYPE_ORDER}
    for r in recs:
        by.setdefault(r['근태유형'], []).append(r)

    rows = [{'유형': t, '인원': len(by.get(t, [])),
             '명단': sorted(x['성명'] for x in by.get(t, []) if x['성명'])}
            for t in TYPE_ORDER if by.get(t)]

    partial = {}
    for r in by.get('연차(8H미만)', []):
        h = r['연차사용시간']
        if h:
            partial.setdefault(round(h), []).append(r['성명'])

    ot = [r for r in recs if r['연장시간'] and r['연장시간'] > 0]
    return {
        '일자': day.isoformat(),
        '응답행수': len(recs),
        '근태유형별': rows,
        '부분연차': [{'구간': f'{k}시간', '시간': float(k), '인원': len(v), '명단': sorted(v)}
                   for k, v in sorted(partial.items())],
        '연차시간합': round(sum(r['연차사용시간'] or 0 for r in recs), 2),
        '연장근무': [{'성명': r['성명'], '조직': r['조직'], '퇴근': r['퇴근'], '연장시간': r['연장시간']}
                   for r in sorted(ot, key=lambda x: -x['연장시간'])],
        '연장시간합': round(sum(r['연장시간'] for r in ot), 2),
        '출근기록누락': sorted(x['성명'] for x in by.get('출근기록누락', []) if x['성명']),
    }


# ── CLI ───────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description='5240 근태 API 클라이언트')
    sub = ap.add_subparsers(dest='cmd', required=True)

    k = sub.add_parser('key', help='interfaceKey 계산')
    k.add_argument('--date', default=None)
    k.add_argument('--sid', type=int, default=None)

    sub.add_parser('selftest', help='명세 예시값으로 키 공식 검증')
    sub.add_parser('probe', help='엔드포인트 도달 가능 여부 확인')

    f = sub.add_parser('fetch', help='1일 조회')
    f.add_argument('--date', required=True)
    f.add_argument('--dry-run', action='store_true')

    b = sub.add_parser('backfill', help='기간 소급 수집')
    b.add_argument('--from', dest='frm', required=True)
    b.add_argument('--to', dest='to', required=True)
    b.add_argument('--force', action='store_true', help='이미 받은 날도 다시 호출')

    r = sub.add_parser('report', help='수집분 → 근태보고 표')
    r.add_argument('--date', required=True)

    a = ap.parse_args()

    if a.cmd == 'selftest':
        got, want = interface_key(1, 20260918), 410504818463643
        print(f'서비스영역ID=1, 조회일자=20260918')
        print(f'  계산값  {got}')
        print(f'  명세예시 {want}')
        print('  결과: 일치' if got == want else '  결과: 불일치')
        sys.exit(0 if got == want else 1)

    if a.cmd == 'key':
        sid = a.sid if a.sid is not None else require_sid()
        day = parse_date(a.date) if a.date else dt.date.today()
        print(f'조회일자 {day} / 서비스영역ID {sid}')
        print(f'interfaceKey {interface_key(sid, ymd_int(day))}')
        return

    if a.cmd == 'probe':
        req = urllib.request.Request(URL, data=b'{}', method='POST',
                                    headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                print(f'도달 가능 — HTTP {r.status}')
        except urllib.error.HTTPError as e:
            print(f'도달 가능 — HTTP {e.code} (인증 없이 호출했으므로 오류 응답이 정상)')
        except urllib.error.URLError as e:
            print(f'도달 불가 — {e.reason}')
            print('배치를 이 환경이 아니라 사내망에서 돌려야 할 수 있습니다.')
            sys.exit(1)
        return

    if a.cmd == 'fetch':
        day = parse_date(a.date)
        sid = 0 if a.dry_run and not os.environ.get('CO5240_SID') else require_sid()
        payload = fetch_day(day, sid, dry=a.dry_run)
        if a.dry_run:
            if not os.environ.get('CO5240_SID'):
                payload['_경고'] = ('CO5240_SID 가 없어 서비스영역ID=0 으로 키를 계산했습니다. '
                                  '실제 발급값을 넣으면 interfaceKey 가 달라집니다.')
            print(json.dumps(payload, ensure_ascii=False, indent=1))
            return
        p = save(day, payload)
        print(f'{day} 수집 완료 — {payload["_rowCount"]}행 → {p}')
        return

    if a.cmd == 'backfill':
        sid = require_sid()
        frm, to = parse_date(a.frm), parse_date(a.to)
        if frm > to:
            sys.exit('--from 이 --to 보다 뒤입니다.')
        total = (to - frm).days + 1
        done = skipped = failed = 0
        print(f'{frm} ~ {to} — {total}일, 1일 1회 호출')
        day = frm
        while day <= to:
            p = OUT_DIR / f'work_{ymd_int(day)}.json'
            if p.exists() and not a.force:
                skipped += 1
            else:
                try:
                    save(day, fetch_day(day, sid))
                    done += 1
                except Exception as e:                      # 하루 실패가 전체를 멈추지 않게
                    failed += 1
                    print(f'  {day} 실패: {e}', file=sys.stderr)
                time.sleep(RATE_SLEEP)
            if (done + skipped + failed) % 20 == 0:
                print(f'  진행 {done + skipped + failed}/{total} (수집 {done} 건너뜀 {skipped} 실패 {failed})')
            day += dt.timedelta(days=1)
        print(f'완료 — 수집 {done} / 건너뜀 {skipped} / 실패 {failed}')
        print('실패분은 같은 명령을 다시 실행하면 받은 날은 건너뛰고 이어서 받습니다.')
        return

    if a.cmd == 'report':
        print(json.dumps(build_report(parse_date(a.date)), ensure_ascii=False, indent=1))
        return


if __name__ == '__main__':
    main()
