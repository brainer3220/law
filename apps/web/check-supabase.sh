#!/bin/bash

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        🔐 Supabase 인증 시스템 설정이 필요합니다          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo -e "${RED}❌ .env.local 파일이 없습니다!${NC}"
    exit 1
fi

# Check if Supabase variables are set
if grep -q "your-project-url-here" .env.local || grep -q "your-anon-key-here" .env.local; then
    echo -e "${YELLOW}⚠️  Supabase 환경 변수가 설정되지 않았습니다!${NC}"
    echo ""
    echo -e "${BLUE}다음 단계를 따라주세요:${NC}"
    echo ""
    echo "1️⃣  Supabase 계정 만들기"
    echo "   https://supabase.com/dashboard"
    echo ""
    echo "2️⃣  새 프로젝트 생성"
    echo ""
    echo "3️⃣  Settings > API에서 다음 값 복사:"
    echo "   • Project URL"
    echo "   • anon/public key"
    echo ""
    echo "4️⃣  .env.local 파일 업데이트:"
    echo -e "   ${GREEN}KIM_BYUN_SUPABASE_URL=your-actual-url${NC}"
    echo -e "   ${GREEN}KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY=your-actual-key${NC}"
    echo ""
    echo "5️⃣  Authentication > Providers에서 Email 활성화"
    echo ""
    echo "6️⃣  Authentication > URL Configuration에 추가:"
    echo "   • http://localhost:3000/api/auth/callback"
    echo "   • http://localhost:3000/auth/callback"
    echo ""
    echo "7️⃣  개발 서버 재시작:"
    echo -e "   ${GREEN}npm run dev${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}💡 자세한 가이드는 AUTH_README.md를 참고하세요${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Supabase 환경 변수가 설정되어 있습니다!${NC}"
    echo ""
    echo "다음을 확인하세요:"
    echo "• Supabase Dashboard에서 Email Provider 활성화"
    echo "• Redirect URLs 설정"
    echo ""
    echo "테스트 페이지:"
    echo "• http://localhost:3000/auth/signup"
    echo "• http://localhost:3000/auth/login"
    echo ""
fi
