# 한지만 — 검증하고, 고치고, 재는 사람

> QA 엔지니어로 입사해 3년 동안 릴리스 관리 → QA 리드 → 기획 → 백오피스 KR 오너로 역할을 넓혔다(공식 직무는 QA).
> 마지막 해에는 AI 에이전트 위에 규칙·검증·측정 구조를 세워 **FE·BE 개발, QA, 기획, 데이터 분석을 한 사람이 이어서 맡았다.**

| 운영자 만족도 | 프로덕션 커밋 | PRD·정책서 | 결함 유출률 지표 | 사례 |
|---|---|---|---|---|
| **7.29 → 8.82** · KR 오너 | **328건** · 6개 레포 · 비개발 직군 | **18건+** | **신설** · 미달도 공개 | **9건** · 원인 진단부터 |

---

> Notion에서 보기: https://brawny-alloy-73a.notion.site/415cb53ea276818585eac70cfd78efb8 (이 레포와 같은 내용, `tools/sync_notion.py`로 갱신)

## 이 레포에서 볼 수 있는 것

| | 질문 | 문서 |
|---|---|---|
| **1** | 다른 회사에 가도 이 방식대로 일할 수 있나? | [AI 에이전트 업무 환경 이식 가이드](1-ai-workflow-guide/README.md) — 규칙서·메모리·검증 에이전트·훅·측정 스크립트 템플릿 |
| **2** | 3년 동안 무엇을 했고 어떤 성과를 냈나? | [3년 성과 흐름](2-career-flow/README.md) — FE·BE·QA·기획·데이터·AI 하네스 6개 영역, 사례 9건, [경력기술서](2-career-flow/경력기술서.md) |
| **3** | 왜 이 사람이 필요한가? AI를 얼마나 쓰나? | [왜 이 사람이 필요한가](3-why-me/README.md) — AI 활용 5단계 중 L4·L5 근거, 측정 전후, RAG 평가 실험, 첫 90일 |

## 폴더 구조

```
.
├── 1-ai-workflow-guide/
│   ├── README.md                      이식 가이드
│   └── templates/
│       ├── CLAUDE.md.template         규칙서 뼈대
│       ├── memory/                    메모리 인덱스·파일 예시·버그 패턴 DB
│       ├── agents/independent-verifier.md
│       ├── hooks/                     push 차단 훅 + 28개 입력 테스트
│       └── scripts/session_metrics.py 세션 로그 기준선 측정
├── 2-career-flow/
│   ├── README.md                      3년 흐름 + 영역별 성과
│   ├── 경력기술서.md
│   └── cases/01~09                    문제 → 진단 → 조치 → 결과 → 원칙
├── 3-why-me/README.md
├── tools/check_sanitize.py            커밋 전 회사 정보 검사
├── tools/sync_notion.py               Notion 사본 갱신 (페이지 매핑: tools/notion_pages.json)
└── PRIVACY.md                         회사 정보 취급 원칙
```

## 읽는 법

- **[실측]** 원자료가 있는 값 · **[동료 측정]** 내가 관리했지만 측정은 동료가 한 값 · **[검증 중]** 기준을 못 넘어 인용을 보류한 값
- 이 레포에는 전 직장의 코드·문서·데이터·화면이 없다. 모든 글은 경험을 새로 서술한 것이다. → [PRIVACY.md](PRIVACY.md)
