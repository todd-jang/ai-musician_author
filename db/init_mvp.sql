-- db/init.sql

-- PostgreSQL 데이터베이스 스키마 정의

-- 필요한 확장 기능 설치 (JSONB 타입 사용을 위해 필요)
CREATE EXTENSION IF NOT EXISTS plpgsql;

-- 사용자 테이블 (선택 사항 - 사용자 인증 구현 시 필요)
-- 사용자를 관리하지 않는다면 이 테이블은 제거하거나 비활성화
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY, -- 사용자 고유 ID (자동 증가)
    email VARCHAR(255) UNIQUE NOT NULL, -- 사용자 이메일 (로그인 ID, 중복 불가)
    hashed_password VARCHAR(255) NOT NULL, -- 비밀번호 해시
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- 레코드 생성 시간
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 레코드 업데이트 시간
    -- 기타 사용자 관련 정보 (예: 이름, 설정 등) 추가 가능
);

-- 사용자 테이블의 updated_at 자동 업데이트 트리거 (선택 사항)
-- CREATE OR REPLACE FUNCTION update_timestamp()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     NEW.updated_at = CURRENT_TIMESTAMP;
--     RETURN NEW;
-- END;
-- $$ language 'plpgsql';
--
-- CREATE TRIGGER update_users_updated_at
-- BEFORE UPDATE ON users
-- FOR EACH ROW
-- EXECUTE PROCEDURE update_timestamp();


-- 업로드된 원본 파일 정보 테이블
CREATE TABLE IF NOT EXISTS files (
    file_id VARCHAR(255) PRIMARY KEY, -- 파일 고유 ID (UUID 사용 권장)
    user_id INTEGER NULL REFERENCES users(user_id), -- 파일 업로드 사용자 (users 테이블의 user_id 참조, NULL 허용)
    original_filename VARCHAR(255) NOT NULL, -- 업로드 시 원본 파일 이름
    file_extension VARCHAR(50) NOT NULL, -- 파일 확장자 (예: '.pdf', '.musicxml')
    file_size_bytes BIGINT NULL, -- 파일 크기 (바이트 단위, 없을 수 있음)
    -- 파일이 저장된 위치 정보 (JSONB 형식으로 유연하게 저장: {type: 's3', bucket: '...', key: '...'} 또는 {type: 'oci', ...}, {type: 'onprem', path: '...'})
    storage_location JSONB NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 파일 업로드 시간
    -- 기타 파일 관련 메타데이터 추가 가능
);

-- 파일 테이블의 인덱스 추가 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_files_uploaded_at ON files (uploaded_at); -- 시간별 파일 조회
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files (user_id); -- 사용자별 파일 조회


-- 작업 요청 정보 테이블
CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(255) PRIMARY KEY, -- 작업 고유 ID (워커가 사용, UUID 사용)
    user_id INTEGER NULL REFERENCES users(user_id), -- 작업 요청 사용자 (users 테이블의 user_id 참조, NULL 허용)
    file_id VARCHAR(255) NOT NULL REFERENCES files(file_id), -- 이 작업이 처리할 원본 파일 (files 테이블의 file_id 참조)
    requested_output_format VARCHAR(50) NOT NULL, -- 요청된 출력 형식 (예: 'midi', 'mp3')
    request_shakespearean_translation BOOLEAN NOT NULL DEFAULT FALSE, -- 셰익스피어 번역 요청 여부
    -- 요청된 음악 분석 작업 목록 (JSONB 형식: 예: [{"type": "analyze_harmony"}, {"type": "analyze_form"}])
    requested_analysis_tasks JSONB NULL,
    -- 작업 현재 상태 (워커에 의해 업데이트됨)
    status VARCHAR(50) NOT NULL DEFAULT 'queued', -- 'queued', 'processing', 'completed', 'failed', 'completed_with_errors' 등
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- 작업 요청 시간
    started_at TIMESTAMP WITH TIME ZONE NULL, -- 워커가 작업 시작한 시간
    completed_at TIMESTAMP WITH TIME ZONE NULL, -- 작업 완료 시간
    error_message TEXT NULL -- 작업 실패 시 저장될 간략한 오류 메시지
    -- 기타 작업 관련 설정 또는 요청 메타데이터 추가 가능
);

-- 작업 테이블의 인덱스 추가 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status); -- 상태별 작업 조회
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks (created_at); -- 시간별 작업 조회
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks (user_id); -- 사용자별 작업 조회
CREATE INDEX IF NOT EXISTS idx_tasks_file_id ON tasks (file_id); -- 파일별 작업 조회


-- 작업 결과 상세 정보 테이블 (Tasks 테이블과 1:1 관계)
-- Task가 완료(성공/실패)될 때 워커에 의해 결과가 저장됩니다.
CREATE TABLE IF NOT EXISTS task_results (
    task_id VARCHAR(255) PRIMARY KEY REFERENCES tasks(task_id) ON DELETE CASCADE, -- tasks 테이블의 task_id를 참조하며 기본 키 역할 (1:1 관계)
    -- Task가 삭제되면 연결된 작업 결과도 자동으로 삭제 (ON DELETE CASCADE)
    final_status VARCHAR(50) NOT NULL, -- 워커가 보고한 최종 상태 ('completed', 'failed', 'completed_with_errors')
    processing_time_seconds REAL NULL, -- 워커가 보고한 총 처리 시간 (초)
    -- 워커의 processed_results 딕셔너리 전체 내용을 JSONB로 저장.
    -- 각 단계별 결과, 오류 상세, 생성된 파일 위치, 번역 결과 내용, 분석 결과 요약 등 모든 상세 정보 포함.
    detailed_results JSONB NULL,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 결과가 데이터베이스에 기록된 시간 (워커 작업 완료 시간과 유사)
    -- 필요한 경우 특정 핵심 결과 필드를 여기에 별도 컬럼으로 추가 가능 (예: final_music_file_s3_key VARCHAR, final_translated_text TEXT 등)
);

-- task_results 테이블은 task_id가 이미 기본 키이자 외래 키이므로 별도의 인덱스 추가는 일반적으로 불필요합니다.
