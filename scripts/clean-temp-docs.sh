#!/bin/bash
# 임시 문서 정리 스크립트
# 용도: 개발 중 생성된 임시 문서를 검증 후 백업하고 정리

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 백업 디렉토리 생성
BACKUP_DIR=".backup/temp-docs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}🔍 임시 문서 검색 중...${NC}"

# 임시 문서 패턴 정의
TEMP_PATTERNS=(
  "IMPLEMENTATION_*.md"
  "TEMP_*.md"
  "TODO_*.md"
  "DRAFT_*.md"
  "WIP_*.md"
  "DECISION_*.md"
  "ANALYSIS_*.md"
  "DEBUG_*.md"
  "*_TEMP.md"
  "*_WIP.md"
  "*_DRAFT.md"
)

# 제외할 디렉토리
EXCLUDE_DIRS=(
  "node_modules"
  ".git"
  "dist"
  "build"
  ".next"
  "langflow"
  "flowise"
  "autogen-studio"
  "autogen-api"
  "perplexica"
  "open-notebook"
  "litellm"
  "external"
)

# 임시 문서 찾기
TEMP_FILES=()
for pattern in "${TEMP_PATTERNS[@]}"; do
  # 제외 디렉토리 빌드
  exclude_args=""
  for dir in "${EXCLUDE_DIRS[@]}"; do
    exclude_args="$exclude_args -path './$dir' -prune -o"
  done
  
  # 파일 검색
  while IFS= read -r file; do
    if [ -f "$file" ]; then
      TEMP_FILES+=("$file")
    fi
  done < <(eval "find . $exclude_args -type f -name '$pattern' -print")
done

# 중복 제거
TEMP_FILES=($(printf '%s\n' "${TEMP_FILES[@]}" | sort -u))

if [ ${#TEMP_FILES[@]} -eq 0 ]; then
  echo -e "${GREEN}✅ 임시 문서 없음${NC}"
  exit 0
fi

echo -e "${YELLOW}발견된 임시 문서: ${#TEMP_FILES[@]}개${NC}"
echo ""

# 각 파일 검증 및 처리
BACKED_UP=0
KEPT=0
ERRORS=0

for file in "${TEMP_FILES[@]}"; do
  echo -e "${BLUE}📄 파일: ${file}${NC}"
  
  # 파일 정보 표시
  file_size=$(wc -c < "$file" 2>/dev/null || echo "0")
  file_lines=$(wc -l < "$file" 2>/dev/null || echo "0")
  file_modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$file" 2>/dev/null || echo "Unknown")
  
  echo "  크기: ${file_size} bytes"
  echo "  줄 수: ${file_lines}"
  echo "  수정일: ${file_modified}"
  
  # 파일 내용 미리보기 (첫 5줄)
  echo "  미리보기:"
  head -n 5 "$file" | sed 's/^/    /'
  if [ $file_lines -gt 5 ]; then
    echo "    ..."
  fi
  echo ""
  
  # 중요 키워드 검사 (보존 필요 여부 판단)
  IMPORTANT_KEYWORDS=(
    "CRITICAL"
    "IMPORTANT"
    "DO NOT DELETE"
    "KEEP THIS"
    "PRODUCTION"
    "LICENSE"
  )
  
  is_important=false
  for keyword in "${IMPORTANT_KEYWORDS[@]}"; do
    if grep -qi "$keyword" "$file"; then
      is_important=true
      echo -e "  ${RED}⚠️  중요 키워드 발견: $keyword${NC}"
      break
    fi
  done
  
  # 최근 수정 여부 확인 (7일 이내)
  if [ "$(uname)" = "Darwin" ]; then
    file_age_seconds=$(( $(date +%s) - $(stat -f "%m" "$file") ))
  else
    file_age_seconds=$(( $(date +%s) - $(stat -c "%Y" "$file") ))
  fi
  file_age_days=$(( file_age_seconds / 86400 ))
  
  if [ $file_age_days -lt 7 ]; then
    echo -e "  ${YELLOW}⏰ 최근 수정됨 (${file_age_days}일 전)${NC}"
  fi
  
  # 사용자 확인 (인터랙티브 모드)
  if [ "${1:-}" != "--auto" ]; then
    if [ "$is_important" = true ]; then
      echo -e "  ${RED}❗ 중요 문서일 수 있습니다. 백업만 권장합니다.${NC}"
      read -p "  처리 방법 [k=보존, b=백업만, s=건너뛰기] (기본: k): " action
      action=${action:-k}
    else
      read -p "  처리 방법 [k=보존, b=백업+삭제, s=건너뛰기] (기본: b): " action
      action=${action:-b}
    fi
  else
    # 자동 모드: 중요 문서는 보존, 나머지는 백업
    if [ "$is_important" = true ] || [ $file_age_days -lt 7 ]; then
      action="k"
    else
      action="b"
    fi
  fi
  
  case $action in
    k|K)
      echo -e "  ${GREEN}✓ 보존${NC}"
      ((KEPT++))
      ;;
    b|B)
      # 백업 디렉토리 구조 생성
      file_dir=$(dirname "$file")
      backup_path="$BACKUP_DIR/$file"
      backup_dir=$(dirname "$backup_path")
      mkdir -p "$backup_dir"
      
      # 백업
      if mv "$file" "$backup_path"; then
        echo -e "  ${GREEN}✓ 백업 완료: $backup_path${NC}"
        ((BACKED_UP++))
      else
        echo -e "  ${RED}✗ 백업 실패${NC}"
        ((ERRORS++))
      fi
      ;;
    s|S)
      echo -e "  ${BLUE}⊘ 건너뛰기${NC}"
      ;;
    *)
      echo -e "  ${YELLOW}⊘ 알 수 없는 선택, 건너뛰기${NC}"
      ;;
  esac
  
  echo ""
done

# 결과 요약
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 완료${NC}"
echo "  보존: $KEPT"
echo "  백업+삭제: $BACKED_UP"
echo "  오류: $ERRORS"

if [ $BACKED_UP -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}백업 위치: $BACKUP_DIR${NC}"
  echo "  복원 방법: mv $BACKUP_DIR/<파일경로> ./"
fi

# 백업 디렉토리가 비어있으면 삭제
if [ -d "$BACKUP_DIR" ] && [ -z "$(ls -A "$BACKUP_DIR")" ]; then
  rmdir "$BACKUP_DIR"
  rmdir "$(dirname "$BACKUP_DIR")" 2>/dev/null || true
fi

echo ""
echo -e "${BLUE}📚 백업 보관 정책:${NC}"
echo "  - 백업 파일은 .backup/temp-docs/ 디렉토리에 보관"
echo "  - 30일 이상 된 백업은 수동으로 삭제 권장"
echo "  - 복원 필요 시: mv .backup/temp-docs/<날짜>/<파일경로> ./"

