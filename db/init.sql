--CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT);

-- db/init.sql

-- 데이터베이스 생성 (Terraform/Kubernetes 설정에서 지정될 수 있으므로 여기서는 생략 가능)
-- CREATE DATABASE personal_data_assistant_db;

-- 데이터베이스 선택 (만약 위에서 생성했다면)
-- \c personal_data_assistant_db;

-- 필요한 확장 기능 설치 (예: JSONB 사용 시)
-- CREATE EXTENSION IF NOT EXISTS plpgsql;
-- CREATE EXTENSION IF NOT EXISTS jsonb_ops; -- JSONB 인덱싱 등에 필요할 수 있음

-- 테이블 생성

-- 사용자 테이블 (선택 사항 - 사용자 인증 구현 시 필요)
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY, -- 자동 증가하는 고유 ID
    email VARCHAR(255) UNIQUE NOT NULL, -- 사용자 이메일 (로그인 ID)
    hashed_password VARCHAR(255) NOT NULL, -- 비밀번호 해시 값
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- 생성 시간
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 업데이트 시간
    -- 기타 사용자 관련 정보 추가
);

-- 작업 테이블 (각 파일 업로드 및 처리 요청 기록)
CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(255) PRIMARY KEY, -- 워커에서 사용될 고유 작업 ID (UUID 사용)
    user_id INTEGER NULL REFERENCES users(user_id), -- 요청한 사용자 (users 테이블과 연결, NULL 허용)
    original_file_location JSONB NOT NULL, -- 원본 파일 위치 정보 (JSONB 형식 - {type, bucket, key 등})
    requested_output_format VARCHAR(50) NOT NULL, -- 요청된 출력 형식 (예: 'midi', 'mp3')
    request_shakespearean_translation BOOLEAN NOT NULL DEFAULT FALSE, -- 셰익스피어 번역 요청 여부
    status VARCHAR(50) NOT NULL DEFAULT 'queued', -- 작업 상태 (예: 'queued', 'processing', 'completed', 'failed', 'completed_with_errors')
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- 작업 요청 시간
    started_at TIMESTAMP WITH TIME ZONE NULL, -- 워커가 작업 시작한 시간
    completed_at TIMESTAMP WITH TIME ZONE NULL, -- 작업 완료 시간
    processing_time_seconds REAL NULL, -- 총 처리 시간 (초)
    error_message TEXT NULL, -- 작업 실패 시 오류 메시지 저장
    -- 기타 작업 관련 메타데이터 (원본파일명 등)는 metadata 필드에 JSONB로 저장 가능
    metadata JSONB NULL
);

-- 작업 결과 테이블 (각 작업의 상세 결과 및 단계별 상태)
-- Task와 1:1 관계 또는 1:N 관계로 설계 가능 (예: 각 단계별 결과를 별도 레코드로 저장)
-- 여기서는 Task 테이블에 결과 요약을 JSONB로 저장하거나, 별도 결과 테이블에 최종 결과만 연결
-- Task 테이블에 결과 요약을 저장하는 방식이 간단할 수 있음.
-- Task 테이블에 결과 필드 추가 예시:
-- result_data JSONB NULL; -- 워커의 processed_results 전체를 JSONB로 저장
-- generated_music_file_location JSONB NULL; -- 최종 음악 파일 위치 (S3 키 등)
-- shakespearean_translation_result JSONB NULL; -- 번역 결과 요약

-- 또는 별도의 결과 테이블을 만든다면 (Task와 1:1 또는 1:N)
/*
CREATE TABLE IF NOT EXISTS task_results (
    result_id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL REFERENCES tasks(task_id), -- tasks 테이블과 1:1 연결
    final_status VARCHAR(50) NOT NULL, -- 최종 결과 상태 (성공/실패 등)
    generated_music_file_location JSONB NULL, -- 생성된 음악 파일 위치
    shakespearean_translation_result JSONB NULL, -- 번역 결과
    analysis_summary JSONB NULL, -- 음악 분석 결과 요약
    processed_results_detail JSONB NULL -- 워커의 processed_results 전체를 JSONB로 저장 (상세 로깅/디버깅용)
    -- 기타 결과 관련 정보 추가
);
*/

-- 인덱스 추가 (조회 성능 향상을 위해 필요)
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status); -- 상태별 작업 조회 시 유용
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks (created_at); -- 시간별 작업 조회 시 유용
-- 사용자별 작업 조회가 많다면 users 테이블의 user_id에 기반한 인덱스도 유용

-- 필요한 경우 데이터베이스 접근 권한 설정
-- GRANT ALL PRIVILEGES ON DATABASE personal_data_assistant_db TO myuser;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO myuser;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO myuser;
