# FOODFROM Design System

푸드프롬 브랜드 디자인 시스템. 마크다운 4개 문서가 원본이고, 정적 사이트는 빌드 결과물입니다.

## 문서

| 문서 | 다루는 것 |
|---|---|
| [`docs/Brand.md`](docs/Brand.md) | **眼** 어떻게 생겼는가 — 로고 · 컬러 · 타이포 · 그래픽 요소 · 사진 |
| [`docs/BX.md`](docs/BX.md) | **言** 뭐라고 말하는가 — 컨셉 · 슬로건 · 톤 · 카피 · 타깃 |
| [`docs/Product.md`](docs/Product.md) | **物** 무엇을 파는가 — 라인업 · 패키지 · 스티커 · 표시사항 |
| [`docs/UX.md`](docs/UX.md) | **手** 어떻게 사는가 — 채널 · 상세페이지 · 썸네일 |

## 빌드

```
python -m pip install markdown-it-py
python build.py
```

`docs/*.md` → `dist/` 에 정적 HTML 생성. **`dist/` 를 직접 고치지 마세요.** 마크다운을 고치고 다시 빌드합니다.

## 로컬 확인

```
python -m http.server 8000 --directory dist
```

## 구조

```
docs/          마크다운 원본 (유일한 진실)
src/style.css  공통 스타일
assets/        스티커 시안 · 패키지 사진
build.py       빌드 스크립트
dist/          빌드 결과물 (커밋됨 · Vercel 배포 대상)
PLAN.md        구축 계획
CHANGELOG.md   변경 이력
```

## 현재 상태

| 항목 | 상태 |
|---|---|
| 브랜드 컨셉 | '연결' → '편지' 개정 완료 |
| 컬러 | 확정 — 아이보리 `#FFFBEB` / 번트오렌지 `#D23A18` |
| 타이포그래피 | 미정 |
| 로고 | 재작업 예정 |
| UX PART B (자사몰) | 후순위 — 뼈대만 |
