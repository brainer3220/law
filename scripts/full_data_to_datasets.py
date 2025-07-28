import json
import os
from pathlib import Path
from datasets import Dataset, DatasetDict
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from tqdm.auto import tqdm
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import partial
import multiprocessing as mp

def load_single_json_file(json_file_path: Path) -> Dict[str, Any]:
    """
    단일 JSON 파일을 로드합니다.
    
    Args:
        json_file_path: JSON 파일 경로
    
    Returns:
        로드된 JSON 데이터 또는 None (에러 시)
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 파일 경로 정보도 추가
            data['source_file'] = str(json_file_path)
            return data
    except Exception as e:
        print(f"Error loading {json_file_path}: {e}")
        return None

def load_json_files(data_dir: str, max_workers: int = None) -> List[Dict[str, Any]]:
    """
    지정된 디렉토리에서 모든 JSON 파일을 병렬로 로드합니다.
    
    Args:
        data_dir: JSON 파일들이 있는 디렉토리 경로
        max_workers: 최대 워커 수 (None이면 CPU 코어 수)
    
    Returns:
        로드된 JSON 데이터의 리스트
    """
    data_path = Path(data_dir)
    
    # 먼저 JSON 파일 목록을 수집
    json_file_paths = list(data_path.rglob("*.json"))
    print(f"  발견된 JSON 파일 수: {len(json_file_paths)}개")
    
    if not json_file_paths:
        return []
    
    # 병렬로 JSON 파일들 로딩
    json_files = []
    if max_workers is None:
        max_workers = min(len(json_file_paths), mp.cpu_count())
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 파일에 대해 작업 제출
        future_to_file = {executor.submit(load_single_json_file, json_file): json_file 
                         for json_file in json_file_paths}
        
        # 진행률 표시와 함께 결과 수집
        for future in tqdm(as_completed(future_to_file), 
                          total=len(json_file_paths), 
                          desc=f"JSON 로딩 ({data_path.name})"):
            result = future.result()
            if result is not None:
                json_files.append(result)
    
    return json_files

def preprocess_single_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    단일 JSON 아이템을 전처리합니다.
    
    Args:
        item: 원본 JSON 데이터 아이템
    
    Returns:
        전처리된 데이터 아이템
    """
    # 데이터 타입 구분 (판결문: "1", 법령: "2", 심결례: "3", 유권해석: "4")
    doc_class = str(item.get('doc_class', item.get('data_class', '')))
    
    # 공통 기본 구조
    processed_item = {
        'doc_class': doc_class,
        'full_text': ' '.join(item.get('sentences', [])),
        'sentences': item.get('sentences', []),
        'num_sentences': len(item.get('sentences', [])),
        'text_length': len(' '.join(item.get('sentences', []))),
        'source_file': item.get('source_file', ''),
    }
    
    # 판결문 데이터 (doc_class == "1" 또는 casenames가 있는 경우)
    if doc_class == "1" or 'casenames' in item:
        processed_item.update({
            'document_type': 'court_decision',
            'doc_id': item.get('doc_id', ''),
            'casenames': item.get('casenames', ''),
            'normalized_court': item.get('normalized_court', ''),
            'casetype': item.get('casetype', ''),
            'announce_date': item.get('announce_date', ''),
            'announce_year': None,
            # 다른 필드들은 None으로 설정
            'statute_name': None,
            'statute_abbrv': None,
            'statute_type': None,
            'statute_category': None,
            'effective_date': None,
            'proclamation_date': None,
            'effective_year': None,
            'proclamation_year': None,
            'response_date': None,
            'response_institute': None,
            'title': None,
            'response_year': None,
            'decision_date': None,
            'decision_institute': None,
            'decision_number': None,
            'decision_year': None,
        })
        
        # 발표 연도 추출
        if item.get('announce_date'):
            try:
                announce_date = datetime.fromisoformat(item['announce_date'].replace('Z', '+00:00'))
                processed_item['announce_year'] = announce_date.year
            except:
                processed_item['announce_year'] = None
    
    # 법령 데이터 (doc_class == "2" 또는 statute_name이 있는 경우)
    elif doc_class == "2" or 'statute_name' in item:
        processed_item.update({
            'document_type': 'statute',
            'statute_name': item.get('statute_name', ''),
            'statute_abbrv': item.get('statute_abbrv', ''),
            'statute_type': item.get('statute_type', ''),
            'statute_category': item.get('statute_category', ''),
            'effective_date': item.get('effective_date', ''),
            'proclamation_date': item.get('proclamation_date', ''),
            'effective_year': None,
            'proclamation_year': None,
            # 다른 필드들은 None으로 설정
            'doc_id': None,
            'casenames': None,
            'normalized_court': None,
            'casetype': None,
            'announce_date': None,
            'announce_year': None,
            'response_date': None,
            'response_institute': None,
            'title': None,
            'response_year': None,
        })
        
        # 시행 연도 추출
        if item.get('effective_date'):
            try:
                effective_date = datetime.fromisoformat(item['effective_date'].replace('Z', '+00:00'))
                processed_item['effective_year'] = effective_date.year
            except:
                processed_item['effective_year'] = None
        
        # 공포 연도 추출
        if item.get('proclamation_date'):
            try:
                proclamation_date = datetime.fromisoformat(item['proclamation_date'].replace('Z', '+00:00'))
                processed_item['proclamation_year'] = proclamation_date.year
            except:
                processed_item['proclamation_year'] = None
    
    # 심결례 데이터 (doc_class == "3" 또는 decision_institute가 있는 경우)
    elif doc_class == "3" or 'decision_institute' in item or 'decision_number' in item:
        processed_item.update({
            'document_type': 'administrative_decision',
            'doc_id': item.get('doc_id', ''),
            'title': item.get('title', ''),
            'decision_date': item.get('decision_date', ''),
            'decision_institute': item.get('decision_institute', ''),
            'decision_number': item.get('decision_number', ''),
            'decision_year': None,
            # 다른 필드들은 None으로 설정
            'casenames': None,
            'normalized_court': None,
            'casetype': None,
            'announce_date': None,
            'announce_year': None,
            'statute_name': None,
            'statute_abbrv': None,
            'statute_type': None,
            'statute_category': None,
            'effective_date': None,
            'proclamation_date': None,
            'effective_year': None,
            'proclamation_year': None,
            'response_date': None,
            'response_institute': None,
            'response_year': None,
        })
        
        # 심결 연도 추출
        if item.get('decision_date'):
            try:
                # "2002. 09. 10" 형식 처리
                decision_date_str = item['decision_date'].strip()
                # 점으로 구분된 날짜 형식 처리
                if '.' in decision_date_str:
                    year_part = decision_date_str.split('.')[0].strip()
                    processed_item['decision_year'] = int(year_part)
                else:
                    # ISO 형식인 경우
                    decision_date = datetime.fromisoformat(decision_date_str.replace('Z', '+00:00'))
                    processed_item['decision_year'] = decision_date.year
            except:
                processed_item['decision_year'] = None
    
    # 유권해석 데이터 (doc_class == "4" 또는 response_institute가 있는 경우)
    elif doc_class == "4" or 'response_institute' in item:
        processed_item.update({
            'document_type': 'legal_interpretation',
            'doc_id': item.get('doc_id', ''),
            'title': item.get('title', ''),
            'response_date': item.get('response_date', ''),
            'response_institute': item.get('response_institute', ''),
            'response_year': None,
            # 다른 필드들은 None으로 설정
            'casenames': None,
            'normalized_court': None,
            'casetype': None,
            'announce_date': None,
            'announce_year': None,
            'statute_name': None,
            'statute_abbrv': None,
            'statute_type': None,
            'statute_category': None,
            'effective_date': None,
            'proclamation_date': None,
            'effective_year': None,
            'proclamation_year': None,
        })
        
        # 회신 연도 추출
        if item.get('response_date'):
            try:
                # "2002. 09. 10" 형식 처리
                response_date_str = item['response_date'].strip()
                # 점으로 구분된 날짜 형식 처리
                if '.' in response_date_str:
                    year_part = response_date_str.split('.')[0].strip()
                    processed_item['response_year'] = int(year_part)
                else:
                    # ISO 형식인 경우
                    response_date = datetime.fromisoformat(response_date_str.replace('Z', '+00:00'))
                    processed_item['response_year'] = response_date.year
            except:
                processed_item['response_year'] = None
    
    # 알 수 없는 타입
    else:
        processed_item.update({
            'document_type': 'unknown',
            # 모든 필드를 None으로 설정
            'doc_id': item.get('doc_id', None),
            'casenames': None,
            'normalized_court': None,
            'casetype': None,
            'announce_date': None,
            'announce_year': None,
            'statute_name': None,
            'statute_abbrv': None,
            'statute_type': None,
            'statute_category': None,
            'effective_date': None,
            'proclamation_date': None,
            'effective_year': None,
            'proclamation_year': None,
            'response_date': None,
            'response_institute': None,
            'title': None,
            'response_year': None,
        })
    
    return processed_item

def preprocess_legal_data(json_data: List[Dict[str, Any]], max_workers: int = None) -> List[Dict[str, Any]]:
    """
    판결문, 법령, 심결례, 유권해석 JSON 데이터를 병렬로 전처리합니다.
    
    Args:
        json_data: 원본 JSON 데이터 리스트
        max_workers: 최대 워커 수 (None이면 CPU 코어 수)
    
    Returns:
        전처리된 데이터 리스트
    """
    if not json_data:
        return []
    
    if max_workers is None:
        max_workers = min(len(json_data), mp.cpu_count())
    
    # 병렬 처리 (ThreadPoolExecutor 사용으로 pickle 문제 방지)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 아이템에 대해 작업 제출
        futures = [executor.submit(preprocess_single_item, item) for item in json_data]
        
        # 진행률 표시와 함께 결과 수집
        processed_data = []
        for future in tqdm(as_completed(futures), total=len(futures), desc="데이터 전처리"):
            result = future.result()
            processed_data.append(result)
    
    return processed_data

def create_huggingface_dataset(data_dirs: List[str], output_dir: str = None, push_to_hub: bool = False, hub_name: str = None, max_workers: int = None):
    """
    JSON 법률 데이터(판결문 + 법령 + 심결례 + 유권해석)를 HuggingFace Dataset으로 변환합니다.
    
    Args:
        data_dirs: JSON 파일들이 있는 디렉토리 경로 리스트
        output_dir: 데이터셋을 저장할 로컬 디렉토리 (선택사항)
        push_to_hub: HuggingFace Hub에 업로드할지 여부
        hub_name: Hub에서 사용할 데이터셋 이름
        max_workers: 최대 워커 수 (None이면 CPU 코어 수)
    
    Returns:
        생성된 HuggingFace Dataset
    """
    all_json_data = []
    
    # 각 디렉토리에서 JSON 파일들을 병렬로 로딩 (최적화된 워커 수)
    optimal_workers = min(len(data_dirs), max_workers or mp.cpu_count())
    with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
        # 모든 디렉토리에 대해 작업 제출
        future_to_dir = {executor.submit(load_json_files, data_dir, max_workers): data_dir 
                        for data_dir in data_dirs}
        
        # 진행률 표시와 함께 결과 수집
        for future in tqdm(as_completed(future_to_dir), total=len(data_dirs), desc="디렉토리 처리"):
            data_dir = future_to_dir[future]
            print(f"JSON 파일들을 로딩 중: {data_dir}")
            json_data = future.result()
            print(f"  - {len(json_data)}개의 JSON 파일을 로드했습니다.")
            all_json_data.extend(json_data)
    
    print(f"총 {len(all_json_data)}개의 JSON 파일을 로드했습니다.")
    
    print("데이터 전처리 중...")
    processed_data = preprocess_legal_data(all_json_data, max_workers)
    
    # DataFrame으로 변환 후 Dataset 생성
    df = pd.DataFrame(processed_data)
    print(f"전처리된 데이터: {len(df)}개 문서")
    
    # 데이터 타입 정리 (PyArrow 호환성을 위해)
    print("데이터 타입 정리 중...")
    
    # doc_class를 문자열로 통일
    df['doc_class'] = df['doc_class'].astype(str)
    
    # 리스트 컬럼들을 문자열로 변환 (PyArrow 호환성)
    if 'sentences' in df.columns:
        df['sentences'] = df['sentences'].apply(lambda x: x if isinstance(x, list) else [])
    
    # None 값들을 적절한 기본값으로 변경
    string_columns = [
        'doc_id', 'casenames', 'normalized_court', 'casetype', 'announce_date',
        'statute_name', 'statute_abbrv', 'statute_type', 'statute_category',
        'effective_date', 'proclamation_date', 'response_date', 'response_institute',
        'title', 'decision_date', 'decision_institute', 'decision_number', 'source_file'
    ]
    
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].fillna('')
    
    # 정수 컬럼들의 None 값을 -1로 변경
    int_columns = [
        'announce_year', 'effective_year', 'proclamation_year', 
        'response_year', 'decision_year', 'num_sentences', 'text_length'
    ]
    
    for col in int_columns:
        if col in df.columns:
            df[col] = df[col].fillna(-1).astype(int)
    
    # Dataset 생성
    dataset = Dataset.from_pandas(df)
    
    # 데이터셋 정보 출력
    print("\n=== 데이터셋 정보 ===")
    print(f"- 총 샘플 수: {len(dataset)}")
    print(f"- 컬럼: {list(dataset.column_names)}")
    print(f"- 평균 텍스트 길이: {df['text_length'].mean():.0f} 문자")
    print(f"- 평균 문장 수: {df['num_sentences'].mean():.1f} 문장")
    
    # 문서 타입별 분포
    if 'document_type' in df.columns:
        type_counts = df['document_type'].value_counts()
        print(f"\n=== 문서 타입별 분포 ===")
        for doc_type, count in type_counts.items():
            print(f"  {doc_type}: {count}개")
    
    # doc_class별 분포
    if 'doc_class' in df.columns:
        class_counts = df['doc_class'].value_counts()
        print(f"\n=== doc_class별 분포 ===")
        class_mapping = {
            "1": "판결문",
            "2": "법령", 
            "3": "심결례",
            "4": "유권해석"
        }
        for doc_class, count in class_counts.items():
            class_name = class_mapping.get(doc_class, f"기타({doc_class})")
            print(f"  {doc_class} ({class_name}): {count}개")
    
    # 통계 생성을 병렬로 처리
    def generate_court_statistics(df):
        """판결문 통계 생성"""
        court_data = df[df['document_type'] == 'court_decision']
        if len(court_data) == 0:
            return None
            
        stats = {
            'type': '판결문',
            'count': len(court_data),
            'court_counts': None,
            'year_counts': None
        }
        
        # 법원별 분포
        if 'normalized_court' in court_data.columns:
            stats['court_counts'] = court_data['normalized_court'].value_counts().head(10)
        
        # 연도별 분포
        if 'announce_year' in court_data.columns:
            stats['year_counts'] = court_data['announce_year'].value_counts().sort_index().head(10)
        
        return stats
    
    def generate_statute_statistics(df):
        """법령 통계 생성"""
        statute_data = df[df['document_type'] == 'statute']
        if len(statute_data) == 0:
            return None
            
        stats = {
            'type': '법령',
            'count': len(statute_data),
            'type_counts': None,
            'category_counts': None,
            'year_counts': None
        }
        
        # 법령 유형별 분포
        if 'statute_type' in statute_data.columns:
            stats['type_counts'] = statute_data['statute_type'].value_counts()
        
        # 법령 분야별 분포
        if 'statute_category' in statute_data.columns:
            stats['category_counts'] = statute_data['statute_category'].value_counts()
        
        # 시행 연도별 분포
        if 'effective_year' in statute_data.columns:
            stats['year_counts'] = statute_data['effective_year'].value_counts().sort_index().head(10)
        
        return stats
    
    def generate_decision_statistics(df):
        """심결례 통계 생성"""
        decision_data = df[df['document_type'] == 'administrative_decision']
        if len(decision_data) == 0:
            return None
            
        stats = {
            'type': '심결례',
            'count': len(decision_data),
            'institute_counts': None,
            'year_counts': None
        }
        
        # 심결기관별 분포
        if 'decision_institute' in decision_data.columns:
            stats['institute_counts'] = decision_data['decision_institute'].value_counts()
        
        # 심결 연도별 분포
        if 'decision_year' in decision_data.columns:
            stats['year_counts'] = decision_data['decision_year'].value_counts().sort_index().head(10)
        
        return stats
    
    def generate_interpretation_statistics(df):
        """유권해석 통계 생성"""
        interpretation_data = df[df['document_type'] == 'legal_interpretation']
        if len(interpretation_data) == 0:
            return None
            
        stats = {
            'type': '유권해석',
            'count': len(interpretation_data),
            'institute_counts': None,
            'year_counts': None
        }
        
        # 회신기관별 분포
        if 'response_institute' in interpretation_data.columns:
            stats['institute_counts'] = interpretation_data['response_institute'].value_counts()
        
        # 회신 연도별 분포
        if 'response_year' in interpretation_data.columns:
            stats['year_counts'] = interpretation_data['response_year'].value_counts().sort_index().head(10)
        
        return stats
    
    # 통계를 병렬로 생성
    with ThreadPoolExecutor(max_workers=4) as executor:
        court_future = executor.submit(generate_court_statistics, df)
        statute_future = executor.submit(generate_statute_statistics, df)
        decision_future = executor.submit(generate_decision_statistics, df)
        interpretation_future = executor.submit(generate_interpretation_statistics, df)
        
        # 결과 수집 및 출력
        court_stats = court_future.result()
        statute_stats = statute_future.result()
        decision_stats = decision_future.result()
        interpretation_stats = interpretation_future.result()
    
    # 통계 출력
    if court_stats:
        print(f"\n=== {court_stats['type']} 통계 ===")
        print(f"- {court_stats['type']} 수: {court_stats['count']}개")
        
        if court_stats['court_counts'] is not None:
            print(f"- 법원별 분포 (상위 10개):")
            for court, count in court_stats['court_counts'].items():
                if court:
                    print(f"    {court}: {count}개")
        
        if court_stats['year_counts'] is not None:
            print(f"- 연도별 분포 (상위 10개):")
            for year, count in court_stats['year_counts'].items():
                if year is not None:
                    print(f"    {year}: {count}개")
    
    if statute_stats:
        print(f"\n=== {statute_stats['type']} 통계 ===")
        print(f"- {statute_stats['type']} 수: {statute_stats['count']}개")
        
        if statute_stats['type_counts'] is not None:
            print(f"- 법령 유형별 분포:")
            for statute_type, count in statute_stats['type_counts'].items():
                if statute_type:
                    print(f"    {statute_type}: {count}개")
        
        if statute_stats['category_counts'] is not None:
            print(f"- 법령 분야별 분포:")
            for category, count in statute_stats['category_counts'].items():
                if category:
                    print(f"    {category}: {count}개")
        
        if statute_stats['year_counts'] is not None:
            print(f"- 시행 연도별 분포 (상위 10개):")
            for year, count in statute_stats['year_counts'].items():
                if year is not None:
                    print(f"    {year}: {count}개")
    
    if decision_stats:
        print(f"\n=== {decision_stats['type']} 통계 ===")
        print(f"- {decision_stats['type']} 수: {decision_stats['count']}개")
        
        if decision_stats['institute_counts'] is not None:
            print(f"- 심결기관별 분포:")
            for institute, count in decision_stats['institute_counts'].items():
                if institute:
                    print(f"    {institute}: {count}개")
        
        if decision_stats['year_counts'] is not None:
            print(f"- 심결 연도별 분포 (상위 10개):")
            for year, count in decision_stats['year_counts'].items():
                if year is not None:
                    print(f"    {year}: {count}개")
    
    if interpretation_stats:
        print(f"\n=== {interpretation_stats['type']} 통계 ===")
        print(f"- {interpretation_stats['type']} 수: {interpretation_stats['count']}개")
        
        if interpretation_stats['institute_counts'] is not None:
            print(f"- 회신기관별 분포:")
            for institute, count in interpretation_stats['institute_counts'].items():
                if institute:
                    print(f"    {institute}: {count}개")
        
        if interpretation_stats['year_counts'] is not None:
            print(f"- 회신 연도별 분포 (상위 10개):")
            for year, count in interpretation_stats['year_counts'].items():
                if year is not None:
                    print(f"    {year}: {count}개")
    
    # 로컬에 저장
    if output_dir:
        print(f"\n데이터셋을 {output_dir}에 저장 중...")
        dataset.save_to_disk(output_dir)
        print("저장 완료!")
    
    # HuggingFace Hub에 업로드
    if push_to_hub and hub_name:
        print(f"\nHuggingFace Hub ({hub_name})에 업로드 중...")
        dataset.push_to_hub(hub_name)
        print("업로드 완료!")
    
    return dataset

def create_dataset_splits(dataset: Dataset, train_ratio: float = 0.8, val_ratio: float = 0.1, test_ratio: float = 0.1):
    """
    데이터셋을 train/validation/test로 분할합니다.
    
    Args:
        dataset: 분할할 Dataset
        train_ratio: 훈련 세트 비율
        val_ratio: 검증 세트 비율
        test_ratio: 테스트 비율
    
    Returns:
        DatasetDict with train/validation/test splits
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "비율의 합이 1이 되어야 합니다."
    
    print("데이터셋 분할 중...")
    
    # 전체 데이터 섞기
    print("데이터 셔플링 중...")
    dataset = dataset.shuffle(seed=42)
    
    # 분할 지점 계산
    total_size = len(dataset)
    train_size = int(total_size * train_ratio)
    val_size = int(total_size * val_ratio)
    
    print("데이터셋 분할 진행 중...")
    # 분할 - 병렬로 처리
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 각 분할을 병렬로 생성
        train_future = executor.submit(dataset.select, range(train_size))
        val_future = executor.submit(dataset.select, range(train_size, train_size + val_size))
        test_future = executor.submit(dataset.select, range(train_size + val_size, total_size))
        
        # 결과 수집
        train_dataset = train_future.result()
        val_dataset = val_future.result()
        test_dataset = test_future.result()
    
    dataset_dict = DatasetDict({
        'train': train_dataset,
        'validation': val_dataset,
        'test': test_dataset
    })
    
    print(f"\n데이터셋 분할 완료:")
    print(f"- Train: {len(train_dataset)} 샘플")
    print(f"- Validation: {len(val_dataset)} 샘플") 
    print(f"- Test: {len(test_dataset)} 샘플")
    
    return dataset_dict

# 사용 예시
if __name__ == "__main__":
    # 데이터 디렉토리 경로 설정 (심결례 추가)
    data_directories = [
        "full_data/Training/01.원천데이터/TS_01. 민사법_001. 판결문/",
        "full_data/Training/01.원천데이터/TS_01. 민사법_002. 법령/",
        "full_data/Training/01.원천데이터/TS_01. 민사법_003. 심결례/",
        "full_data/Training/01.원천데이터/TS_01. 민사법_004. 유권해석/"
    ]
    
    # 기본 데이터셋 생성 (판결문 + 법령 + 심결례 + 유권해석)
    dataset = create_huggingface_dataset(
        data_dirs=data_directories,
        output_dir="korean_legal_dataset",  # 로컬 저장
        push_to_hub=False,  # True로 설정하면 Hub에 업로드
        hub_name="your-username/korean-legal-dataset"  # Hub 이름
    )
    
    # 데이터셋 분할 (선택사항)
    dataset_splits = create_dataset_splits(dataset)
    
    # 분할된 데이터셋과 간단한 버전을 병렬로 저장
    print("분할된 데이터셋과 간단한 버전 생성 중...")
    
    # 간단한 버전 생성과 저장을 병렬로 처리
    def save_dataset_splits(dataset_splits):
        """분할된 데이터셋 저장"""
        print("분할된 데이터셋 저장 중...")
        dataset_splits.save_to_disk("datasets/korean_legal_dataset_splits")
        return "korean_legal_dataset_splits"
    
    def create_and_save_simple_dataset(dataset):
        """간단한 버전 데이터셋 생성 및 저장"""
        print("간단한 버전 데이터셋 생성 중...")
        simple_columns = [
            'document_type', 'doc_class', 'full_text', 'text_length', 'num_sentences',
            'doc_id', 'casenames', 'normalized_court',  # 판결문 관련
            'statute_name', 'statute_type', 'statute_category',  # 법령 관련
            'decision_institute', 'decision_date', 'decision_number',  # 심결례 관련
            'title', 'response_institute', 'response_date'  # 유권해석 관련
        ]
        simple_dataset = dataset.select_columns([col for col in simple_columns if col in dataset.column_names])
        print("간단한 버전 데이터셋 저장 중...")
        simple_dataset.save_to_disk("datasets/korean_legal_dataset_simple")
        return simple_dataset
    
    # 병렬로 저장 작업 수행
    with ThreadPoolExecutor(max_workers=2) as executor:
        splits_future = executor.submit(save_dataset_splits, dataset_splits)
        simple_future = executor.submit(create_and_save_simple_dataset, dataset)
        
        # 결과 대기
        splits_path = splits_future.result()
        simple_dataset = simple_future.result()
    
    # 샘플 데이터 확인 - 병렬 처리
    print("\n=== 샘플 데이터 ===")
    
    def get_sample_info(dataset, doc_type, type_name):
        """특정 문서 타입의 샘플 정보를 가져오는 함수"""
        samples = dataset.filter(lambda x: x['document_type'] == doc_type)
        if len(samples) == 0:
            return None
        
        sample = samples[0]
        return {
            'type_name': type_name,
            'sample': sample
        }
    
    # 병렬로 샘플 데이터 수집
    with ThreadPoolExecutor(max_workers=4) as executor:
        court_future = executor.submit(get_sample_info, dataset, 'court_decision', '판결문')
        statute_future = executor.submit(get_sample_info, dataset, 'statute', '법령')
        decision_future = executor.submit(get_sample_info, dataset, 'administrative_decision', '심결례')
        interpretation_future = executor.submit(get_sample_info, dataset, 'legal_interpretation', '유권해석')
        
        # 결과 수집
        court_sample_info = court_future.result()
        statute_sample_info = statute_future.result()
        decision_sample_info = decision_future.result()
        interpretation_sample_info = interpretation_future.result()
    
    # 샘플 정보 출력
    if court_sample_info:
        sample = court_sample_info['sample']
        print(f"{court_sample_info['type_name']} 샘플:")
        print(f"- 문서 ID: {sample['doc_id']}")
        print(f"- 사건명: {sample['casenames']}")
        print(f"- 법원: {sample['normalized_court']}")
        print(f"- 텍스트 길이: {sample['text_length']} 문자")
        print(f"- 첫 문장: {sample['sentences'][0][:100] if sample['sentences'] else 'N/A'}...")
    
    if statute_sample_info:
        sample = statute_sample_info['sample']
        print(f"\n{statute_sample_info['type_name']} 샘플:")
        print(f"- 법령명: {sample['statute_name']}")
        print(f"- 법령 유형: {sample['statute_type']}")
        print(f"- 법령 분야: {sample['statute_category']}")
        print(f"- 시행일: {sample['effective_date']}")
        print(f"- 텍스트 길이: {sample['text_length']} 문자")
        print(f"- 첫 문장: {sample['sentences'][0][:100] if sample['sentences'] else 'N/A'}...")
    
    if decision_sample_info:
        sample = decision_sample_info['sample']
        print(f"\n{decision_sample_info['type_name']} 샘플:")
        print(f"- 문서 ID: {sample['doc_id']}")
        print(f"- 제목: {sample['title']}")
        print(f"- 심결기관: {sample['decision_institute']}")
        print(f"- 심결일: {sample['decision_date']}")
        print(f"- 심결번호: {sample['decision_number']}")
        print(f"- 텍스트 길이: {sample['text_length']} 문자")
        print(f"- 첫 문장: {sample['sentences'][0][:100] if sample['sentences'] else 'N/A'}...")
    
    if interpretation_sample_info:
        sample = interpretation_sample_info['sample']
        print(f"\n{interpretation_sample_info['type_name']} 샘플:")
        print(f"- 문서 ID: {sample['doc_id']}")
        print(f"- 제목: {sample['title']}")
        print(f"- 회신기관: {sample['response_institute']}")
        print(f"- 회신일: {sample['response_date']}")
        print(f"- 텍스트 길이: {sample['text_length']} 문자")
        print(f"- 첫 문장: {sample['sentences'][0][:100] if sample['sentences'] else 'N/A'}...")
    
    # 문서 타입별 데이터셋 생성 (선택사항) - 병렬 처리
    print("\n문서 타입별 데이터셋 생성 중...")
    
    # 필터링과 저장을 병렬로 처리
    def filter_and_save_dataset(dataset, filter_func, output_path, description):
        """데이터셋 필터링과 저장을 수행하는 헬퍼 함수"""
        print(f"{description} 데이터셋 필터링 중...")
        filtered_dataset = dataset.filter(filter_func)
        if len(filtered_dataset) > 0:
            print(f"{description} 데이터셋 저장 중...")
            filtered_dataset.save_to_disk(output_path)
            print(f"{description}만 따로 저장: {len(filtered_dataset)}개 문서")
            return filtered_dataset
        return None
    
    # 병렬로 각 문서 타입별 데이터셋 생성
    with ThreadPoolExecutor(max_workers=4) as executor:
        # 각 문서 타입에 대해 작업 제출
        court_future = executor.submit(
            filter_and_save_dataset, 
            dataset, 
            lambda x: x['document_type'] == 'court_decision',
            "datasets/korean_court_decisions_only",
            "판결문"
        )
        
        statute_future = executor.submit(
            filter_and_save_dataset,
            dataset,
            lambda x: x['document_type'] == 'statute',
            "korean_statutes_only", 
            "법령"
        )
        
        decision_future = executor.submit(
            filter_and_save_dataset,
            dataset,
            lambda x: x['document_type'] == 'administrative_decision',
            "korean_administrative_decisions_only",
            "심결례"
        )
        
        interpretation_future = executor.submit(
            filter_and_save_dataset,
            dataset,
            lambda x: x['document_type'] == 'legal_interpretation',
            "korean_legal_interpretations_only",
            "유권해석"
        )
        
        # 결과 수집
        court_dataset = court_future.result()
        statute_dataset = statute_future.result()
        decision_dataset = decision_future.result()
        interpretation_dataset = interpretation_future.result()
    
    # 간단한 버전 데이터셋 생성
    print("간단한 버전 데이터셋 생성 중...")
    simple_columns = [
        'document_type', 'doc_class', 'full_text', 'text_length', 'num_sentences',
        'doc_id', 'casenames', 'normalized_court',  # 판결문 관련
        'statute_name', 'statute_type', 'statute_category',  # 법령 관련
        'decision_institute', 'decision_date', 'decision_number',  # 심결례 관련
        'title', 'response_institute', 'response_date'  # 유권해석 관련
    ]
    simple_dataset = dataset.select_columns([col for col in simple_columns if col in dataset.column_names])
    print("간단한 버전 데이터셋 저장 중...")
    simple_dataset.save_to_disk("datasets/korean_legal_dataset_simple")
    
    print(f"\n=== 데이터셋 생성 완료 ===")
    print(f"- 전체 법률 데이터셋: korean_legal_dataset/ ({len(dataset)}개 문서)")
    print(f"- 분할된 데이터셋: korean_legal_dataset_splits/")
    print(f"- 판결문 전용: korean_court_decisions_only/ ({len(court_dataset) if 'court_dataset' in locals() else 0}개)")
    print(f"- 법령 전용: korean_statutes_only/ ({len(statute_dataset) if 'statute_dataset' in locals() else 0}개)")
    print(f"- 심결례 전용: korean_administrative_decisions_only/ ({len(decision_dataset) if 'decision_dataset' in locals() else 0}개)")
    print(f"- 유권해석 전용: korean_legal_interpretations_only/ ({len(interpretation_dataset) if 'interpretation_dataset' in locals() else 0}개)")
    print(f"- 간단한 버전: korean_legal_dataset_simple/")
    
    # 데이터셋 로드 예시
    print(f"\n=== 데이터셋 로드 예시 ===")
    print("from datasets import load_from_disk")
    print("dataset = load_from_disk('korean_legal_dataset')")
    print("court_only = load_from_disk('korean_court_decisions_only')")
    print("statute_only = load_from_disk('korean_statutes_only')")
    print("decision_only = load_from_disk('korean_administrative_decisions_only')")
    print("interpretation_only = load_from_disk('korean_legal_interpretations_only')")
    print("splits = load_from_disk('korean_legal_dataset_splits')")
    print("train_data = splits['train']")
    print("val_data = splits['validation']")
    print("test_data = splits['test']")
