# Docs Agent

## Scope
`docs/` 디렉토리만 담당.

## Responsibility
프로젝트 문서 작성, 관리, 변환.

## 문서 분류

| 유형 | 대상 독자 | 예시 |
|------|----------|------|
| **설계 문서** | 개발자 | manifest_schema.md, architecture 문서 |
| **설치/설정 가이드** | 사용자 | INSTALL.md, BLENDER_MCP_SETUP.md |
| **변경 이력** | 전체 | changelog.md |
| **매뉴얼** | 최종 사용자 (배포용) | 사용법 가이드, 튜토리얼 |

## 작성 규칙

1. **언어**: 한국어 기본, 코드/API 레퍼런스는 영문
2. **형식**: Markdown 기본 (GitHub-flavored)
3. **파일명**: 소문자 + 언더스코어 (예: `manifest_schema.md`), 설치 가이드 등 관례적 대문자는 허용
4. **이미지**: `docs/images/` 하위에 저장, 상대경로로 참조
5. **변경 이력**: 기능 추가/변경 시 `changelog.md` 업데이트 필수

## 배포용 문서 변환

완성된 매뉴얼은 `.md` 외에 배포 형식으로도 변환한다.

### 변환 대상 판단 기준
- 초안/WIP 문서: `.md`만 유지
- 완성된 매뉴얼: `.md` + `.docx` (Word) 생성

### 변환 방법
```bash
# pandoc 사용 (설치: https://pandoc.org/)
pandoc docs/<file>.md -o docs/exports/<file>.docx --reference-doc=docs/templates/reference.docx
```

### 디렉토리 구조
```
docs/
├── *.md                    # 원본 문서 (source of truth)
├── images/                 # 문서에 포함되는 이미지
├── templates/              # pandoc reference 템플릿 (.docx 등)
└── exports/                # 변환된 배포 파일 (.docx, .pdf)
```

### 규칙
- **원본은 항상 `.md`** — Word 파일은 자동 생성물이며 직접 편집하지 않음
- `exports/` 내 파일은 `.gitignore`에 추가 가능 (CI에서 생성하는 경우)
- 변환 시 목차, 스타일은 `templates/reference.docx`를 따름

## Constraints
- 코드 파일 수정 금지 (문서만 담당)
- 다른 모듈 CLAUDE.md의 API 설명과 일관성 유지
- manifest_schema.md 변경 시 root orchestrator에 알릴 것 (양쪽 패키지 영향)
