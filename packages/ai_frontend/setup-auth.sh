#!/bin/bash

# Supabase 인증 시스템 설정 스크립트

echo "🔐 Supabase 인증 시스템 설정"
echo "================================"
echo ""

# .env.local 파일 확인
if [ -f .env.local ]; then
    echo "✅ .env.local 파일이 이미 존재합니다."
    read -p "덮어쓰시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "설정을 취소합니다."
        exit 0
    fi
fi

echo ""
echo "Supabase 프로젝트 정보를 입력해주세요:"
echo "(Supabase Dashboard > Settings > API에서 확인 가능)"
echo ""

# Supabase URL 입력
read -p "KIM_BYUN_SUPABASE_URL: " SUPABASE_URL

# Supabase Anon Key 입력
read -p "KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY: " SUPABASE_ANON_KEY

# Site URL 입력 (선택사항)
read -p "NEXT_PUBLIC_SITE_URL (기본값: http://localhost:3000): " SITE_URL
SITE_URL=${SITE_URL:-http://localhost:3000}

# .env.local 파일 생성
cat > .env.local << EOF
# OpenAI (기존)
OPENAI_API_KEY=${OPENAI_API_KEY:-sk-proj-...}
NEXT_PUBLIC_CHATKIT_WORKFLOW_ID=${NEXT_PUBLIC_CHATKIT_WORKFLOW_ID:-wf_...}

# Supabase
KIM_BYUN_SUPABASE_URL=$SUPABASE_URL
KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY

# Site URL
NEXT_PUBLIC_SITE_URL=$SITE_URL
EOF

echo ""
echo "✅ .env.local 파일이 생성되었습니다!"
echo ""
echo "다음 단계:"
echo "1. Supabase Dashboard에서 Authentication > Providers에서 Email 활성화"
echo "2. Supabase Dashboard에서 Authentication > URL Configuration에 다음 추가:"
echo "   - $SITE_URL/api/auth/callback"
echo "   - $SITE_URL/auth/callback"
echo "3. npm run dev 실행"
echo "4. $SITE_URL/auth/signup 접속하여 테스트"
echo ""
echo "📚 자세한 내용은 AUTH_README.md를 참고하세요."
