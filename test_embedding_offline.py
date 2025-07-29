#!/usr/bin/env python3
"""
오프라인 환경에서 Embedding 재사용 테스트
"""
import os
import time
import numpy as np
from typing import List

# 오프라인 모드 설정
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

from model_manager import ModelManager

def print_banner(text: str):
    """배너 출력"""
    print("=" * 60)
    print(f"🧪 {text}")
    print("=" * 60)

def print_step(step: int, text: str):
    """단계별 출력"""
    print(f"\n{step}️⃣ {text}")

def test_embedding_reuse_offline():
    """오프라인 환경에서 Embedding 재사용 테스트"""
    
    print_banner("Embedding 재사용 테스트 (오프라인 모드)")
    
    # 테스트 데이터
    test_texts = [
        "계약법에 관한 기본 원칙을 설명하시오.",
        "민법상 손해배상의 요건과 범위는 무엇인가?",
        "형법상 고의와 과실의 차이점을 서술하시오."
    ]
    
    print(f"📝 테스트 텍스트: {len(test_texts)}개")
    print(f"🤖 사용 모델: jhgan/ko-sroberta-multitask (오프라인)")
    
    try:
        # ModelManager 인스턴스 생성
        model_manager = ModelManager()
        
        print_step(1, "첫 번째 임베딩 생성 (모델 로딩 + 임베딩)...")
        start_time = time.time()
        
        embeddings1 = model_manager.get_embeddings(test_texts)
        first_time = time.time() - start_time
        
        print(f"✅ 첫 번째 임베딩 완료: {first_time:.2f}초")
        print(f"📊 임베딩 shape: {embeddings1.shape}")
        
        print_step(2, "두 번째 임베딩 생성 (캐시 사용)...")
        start_time = time.time()
        
        embeddings2 = model_manager.get_embeddings(test_texts)
        second_time = time.time() - start_time
        
        print(f"✅ 두 번째 임베딩 완료: {second_time:.2f}초")
        
        print_step(3, "결과 비교...")
        
        # 임베딩 동일성 확인
        if np.array_equal(embeddings1, embeddings2):
            print("✅ 임베딩이 정확히 동일합니다 (캐시 작동)")
        else:
            print("❌ 임베딩이 다릅니다 (캐시 미작동)")
            return False
        
        # 속도 개선 확인
        if second_time < first_time * 0.1:  # 90% 이상 빨라짐
            speedup = first_time / second_time
            print(f"🚀 속도 개선: {speedup:.1f}배 빨라짐")
        else:
            print(f"⚠️ 속도 개선 미미: {first_time:.2f}초 → {second_time:.2f}초")
        
        print_step(4, "메모리 사용량 확인...")
        memory_info = model_manager.get_memory_usage()
        print(f"📈 메모리 사용량: {memory_info}")
        
        print_step(5, "캐시 정보 확인...")
        cache_info = model_manager.get_cache_info()
        print(f"💾 캐시 정보: {cache_info}")
        
        print_step(6, "다른 텍스트로 추가 테스트...")
        new_texts = ["새로운 법률 질문입니다.", "추가 테스트용 텍스트"]
        
        start_time = time.time()
        new_embeddings = model_manager.get_embeddings(new_texts)
        new_time = time.time() - start_time
        
        print(f"✅ 새 텍스트 임베딩: {new_time:.2f}초")
        print(f"📊 새 임베딩 shape: {new_embeddings.shape}")
        
        # 최종 캐시 상태
        final_cache_info = model_manager.get_cache_info()
        print(f"💾 최종 캐시 정보: {final_cache_info}")
        
        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("✅ 임베딩 모델 재사용이 정상적으로 작동합니다")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n💥 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_embedding_reuse_offline()
