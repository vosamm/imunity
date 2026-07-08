#!/usr/bin/env bash
# 전체 테스트 러너 — docs/TEST_PLAN.md의 자동화 가능 게이트를 한 번에 실행한다.
# 실 API/Mistral 호출 없음 (더미 키 사용).
set -uo pipefail

cd "$(dirname "$0")/.."
FAIL=0

section() { printf "\n\033[1m=== %s ===\033[0m\n" "$1"; }
check() {
  if [ "$1" -eq 0 ]; then echo "  -> PASS"; else echo "  -> FAIL"; FAIL=1; fi
}

section "1. Python 단위 테스트 (tests/)"
DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s tests -t . 2>&1 | tail -3
check "${PIPESTATUS[0]}"

section "2. 수락 테스트 (acceptance_tests/, 무수정 채점표)"
DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s acceptance_tests -t . 2>&1 | tail -3
check "${PIPESTATUS[0]}"

section "3. 웹 유닛/통합 (web/, vitest)"
(cd web && npm test --silent 2>&1 | tail -4)
check "${PIPESTATUS[0]}"

section "4-1. SEC-01 웹 빌드"
(cd web && npm run build 2>&1 | grep -E "✓ Compiled|Failed|Type error" | head -3)
check "${PIPESTATUS[0]}"

section "4-2. SEC-02 클라이언트 번들 비밀 스캔"
if grep -rlE "MISTRAL|DATA_GO_KR|serviceKey" web/.next/static 2>/dev/null; then
  echo "  비밀 패턴 검출!"; check 1
else
  echo "  비밀 패턴 없음"; check 0
fi

section "4-3. SEC-03 git 추적 파일 점검 (.env / data/ / node_modules / *.db)"
if git ls-files | grep -E "(^|/)\.env$|^data/|node_modules/|\.db$"; then
  echo "  금지 파일이 추적되고 있음!"; check 1
else
  echo "  금지 파일 추적 없음"; check 0
fi

section "4-4. SEC-04 npm audit (critical/high)"
AUDIT=$(cd web && npm audit --json 2>/dev/null)
CRIT=$(echo "$AUDIT" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const v=JSON.parse(d).metadata.vulnerabilities;console.log(v.critical+v.high)})")
echo "  critical+high: ${CRIT}"
[ "${CRIT}" = "0" ]; check $?

section "결과"
if [ "$FAIL" -eq 0 ]; then
  echo "ALL GREEN ✅ (E2E는 docs/TEST_PLAN.md 5장에 따라 브라우저로 별도 수행)"
else
  echo "FAILED ❌ — 위 실패 항목을 확인하세요"
fi
exit "$FAIL"
