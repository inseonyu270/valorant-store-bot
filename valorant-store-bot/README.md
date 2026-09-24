# 🎮 발로란트 일일 상점 디스코드 봇 (Valorant Store Discord Bot)

디스코드에서 `/상점` 커맨드로 라이엇 계정의 일일 4가지 총기 스킨 로테이션, 등급(셀렉트/디럭스/프리미엄/익스클루시브/울트라), VP 가격, 고화질 미리보기 이미지, 갱신 타이머 및 추천 세트(컬렉션) 패키지, 야시장 정보를 조회할 수 있는 디스코드 봇입니다.

---

## 🌟 주요 기능

- 🛒 **`/상점`**: 오늘의 일일 상점 4가지 무기 스킨 카드 조회 (전체 요약 & 개별 스킨 미리보기 슬라이드 버튼 지원)
- 📦 **`/컬렉션`**: 현재 판매 중인 메인 추천 세트 패키지(Bundle) 배너, 구성 및 총 가격 확인
- 🌙 **`/야시장`**: 야시장 진행 기간 중 할인율 및 할인가 스킨 목록 확인
- 🔑 **`/로그인`**: 안전한 디스코드 Modal 창을 통한 라이엇 계정 세션 인증
- 🚪 **`/로그아웃`**: 저장된 로그인 인증 세션 삭제

---

## 🛠️ 설치 및 설정 방법

### 1단계: 디스코드 봇 생성 및 토큰 발급
1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속하여 로그인합니다.
2. 우측 상단의 **`New Application`** 버튼을 누르고 봇 이름을 입력합니다 (예: `Valorant Store Bot`).
3. 좌측 메뉴에서 **`Bot`** 탭 선택 후 **`Reset Token`**을 클릭하여 **Bot Token**을 복사해 둡니다.
4. 아래로 스크롤하여 **Privileged Gateway Intents** 섹션에서 다음 항목들을 켜줍니다 (ON):
   - `PRESENCE INTENT`
   - `SERVER MEMBERS INTENT`
   - `MESSAGE CONTENT INTENT`
5. 좌측 메뉴 **`OAuth2` -> `URL Generator`** 이동:
   - **Scopes**: `bot`, `applications.commands` 체크
   - **Bot Permissions**: `Send Messages`, `Embed Links`, `Attach Files`, `Use External Emojis`, `Read Message History` 체크
   - 하단에 생성된 Invite URL을 복사하여 자신의 디스코드 서버에 봇을 초대합니다.

---

### 2단계: 환경 설정 및 패키지 설치

터미널 또는 프롬프트에서 프로젝트 폴더로 이동한 후 필수 패키지를 설치합니다:

```bash
cd /Users/youinseon/.gemini/antigravity/scratch/valorant-store-bot

# 라이브러리 설치
pip install -r requirements.txt
```

---

### 3단계: `.env` 파일 작성

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 1단계에서 복사한 디스코드 봇 토큰을 입력합니다:

```bash
cp .env.example .env
```

`.env` 파일 내용:
```env
DISCORD_BOT_TOKEN=복사한_디스코드_봇_토큰_입력
DEFAULT_REGION=kr
```

---

### 4단계: 봇 실행

```bash
python bot.py
```

실행 시 `valorant-api.com`에서 한국어 무기 스킨 메타데이터를 자동으로 동기화한 뒤 디스코드 슬래시 커맨드가 활성화됩니다.

---

## 🎯 사용 방법

1. 디스코드 채널에서 **`/로그인`** 입력 ➔ 모달 창에 라이엇 아이디와 비밀번호 입력.
2. **`/상점`** 입력 ➔ Embed 카드로 오늘의 일일 스킨 4개와 갱신 타이머 확인!
3. 하단의 **`◀ 이전`**, **`다음 ▶`** 버튼을 눌러 스킨별 고화질 이미지를 크게 확인하거나 **`📦 추천 컬렉션 보기`** 버튼 클릭.
4. **`/컬렉션`** 입력 ➔ 메인 컬렉션 세트 배너 확인.
5. **`/야시장`** 입력 ➔ 야시장 할인가 스킨 정보 확인.

---

## 🔒 보안 및 참고사항

- 라이엇 공식 개발자 포털 API는 개인의 상점 정보를 제공하지 않으므로, 이 봇은 인게임 클라이언트 인증 엔드포인트를 사용합니다.
- 로그인 비밀번호는 저장되지 않으며, 서버 통신을 위한 일회성 접근 토큰(Access Token & Entitlements Token)만 세션 메모리에 관리됩니다.
- 본 봇은 개인용 또는 친구 소수 서버용으로 호스팅하여 사용하시는 것을 권장합니다.
