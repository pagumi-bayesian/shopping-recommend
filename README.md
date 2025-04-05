# 買い物提案アプリ

## 概要

このプロジェクトは、家族向けの買い物提案アプリケーションです。LLM を活用し、過去の購入履歴や季節性に基づいて、スーパーマーケットやコンビニエンスストアで購入すべき品物を提案します。ユーザーは実際に購入した商品を記録でき、そのデータは次回の提案に反映されます。

**主な機能:**

*   LLM による買い物リスト提案
*   購入履歴の登録・表示
*   ユーザー管理（任意ユーザーでの履歴登録が可能）
*   季節性を考慮した提案
*   新規登録機能のオン/オフ設定

## 技術スタック

*   **フロントエンド:** Vue.js (Vite), Firebase Authentication, Firebase Hosting
*   **バックエンド:** Python (FastAPI), Uvicorn
*   **データベース:** PostgreSQL (Cloud SQL)
*   **コンテナ:** Docker, Docker Compose
*   **LLM:** OpenAI API (または互換 API)
*   **インフラ (GCP):** Cloud Run, Cloud SQL, Artifact Registry, Cloud Build, Secret Manager
*   **CI/CD:** Cloud Build

## ディレクトリ構成

```
.
├── backend/         # FastAPI バックエンドコード
│   ├── alembic/     # Alembic マイグレーションファイル
│   ├── __init__.py
│   ├── crud.py      # DB操作関数
│   ├── database.py  # DB接続設定
│   ├── Dockerfile   # バックエンド用Dockerfile
│   ├── llm_interface.py # LLM連携
│   ├── main.py      # FastAPI アプリケーションエントリーポイント
│   ├── models.py    # SQLAlchemy モデル定義
│   ├── requirements.txt # Python 依存関係
│   └── schemas.py   # Pydantic スキーマ定義
├── frontend/        # Vue.js フロントエンドコード
│   ├── public/
│   ├── src/
│   │   ├── App.vue    # メインコンポーネント
│   │   ├── main.js    # Vue アプリケーションエントリーポイント
│   │   └── firebaseConfig.js # Firebase 設定
│   ├── .env         # ローカル開発用環境変数 (Git管理外)
│   ├── Dockerfile   # (開発用) フロントエンド用Dockerfile
│   ├── firebase.json # Firebase Hosting 設定
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── docs/            # ドキュメント
│   ├── gcp_deployment_guide.md # GCPデプロイ手順
|   └── shopping_recommendation_app_plan.md # 初期設計ドキュメント
├── .env             # Docker Compose 用環境変数 (Git管理外)
├── .gitignore
├── cloudbuild.yaml  # Cloud Build 設定ファイル
├── docker-compose.yml # Docker Compose 設定ファイル
└── README.md        # このファイル
```

## ローカル開発環境セットアップ

### 前提条件

*   Docker & Docker Compose
*   Node.js (v18 推奨) & npm
*   Python (v3.9 推奨) & pip
*   Google Cloud SDK (gcloud CLI) - Cloud SQL Auth Proxy 使用時
*   Git

### 手順

1.  **リポジトリのクローン:**
    ```bash
    git clone <repository_url>
    cd shopping_app
    ```

2.  **環境変数ファイルの設定:**
    *   プロジェクトルートに `.env` ファイルを作成し、Docker Compose で使用する変数を設定します。
        ```dotenv
        # .env (プロジェクトルート)
        POSTGRES_USER=your_db_user
        POSTGRES_PASSWORD=your_db_password
        POSTGRES_DB=shopping_app_db
        DATABASE_URL=postgresql+psycopg2://your_db_user:your_db_password@db:5432/shopping_app_db # Docker Compose内のDBサービス名'db'を指定
        OPENAI_API_KEY=your_openai_api_key
        ```
    *   `frontend` ディレクトリに `.env` ファイルを作成し、フロントエンド用の変数を設定します。
        ```dotenv
        # frontend/.env
        VITE_API_BASE_URL=http://localhost:8000 # ローカルバックエンドAPIのURL
        VITE_ALLOW_SIGNUP=true # ローカルでは新規登録を許可
        ```
    *   `backend` ディレクトリに `.env` ファイルを作成し、バックエンド用の変数を設定します（`docker-compose.yml` で直接設定する場合は不要なこともあります）。
        ```dotenv
        # backend/.env (必要に応じて)
        # DATABASE_URL=... # Docker Composeから渡される場合は不要
        OPENAI_API_KEY=your_openai_api_key
        ```
    *   **重要:** これらの `.env` ファイルは `.gitignore` に追加し、Git で管理しないでください。

3.  **Docker コンテナの起動:**
    *   **Docker Compose を使用する場合 (推奨):**
        ```bash
        docker-compose up -d --build
        ```
        これにより、バックエンドコンテナと PostgreSQL データベースコンテナが起動します。
    *   **バックエンドのみ Docker で起動する場合:**
        ```bash
        # backend ディレクトリでビルド & 起動
        docker build -t shopping-app-backend ./backend
        docker run -d -p 8000:8000 --env-file backend/.env shopping-app-backend
        # この場合、別途 PostgreSQL データベースを用意する必要があります。
        ```

4.  **データベースマイグレーション (初回またはモデル変更時):**
    *   バックエンドコンテナ内で Alembic を実行します。
    ```bash
    docker-compose exec backend alembic upgrade head
    # または docker exec <backend_container_id> alembic upgrade head
    ```

5.  **フロントエンド開発サーバーの起動:**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    通常 `http://localhost:5173` でアクセス可能になります。

6.  **(オプション) Cloud SQL Auth Proxy の使用:**
    *   ローカルから GCP 上の Cloud SQL に直接接続したい場合に使用します。
    *   [Cloud SQL Auth Proxy のドキュメント](https://cloud.google.com/sql/docs/postgres/connect-auth-proxy) を参照してインストール・設定してください。
    *   起動コマンド例:
        ```bash
        ./cloud-sql-proxy --private-ip INSTANCE_CONNECTION_NAME
        # または TCP ポートを使用する場合
        # ./cloud-sql-proxy INSTANCE_CONNECTION_NAME -p 5433 # ローカルDBとポートを分ける
        ```
    *   この場合、バックエンドの `DATABASE_URL` はプロキシ経由のアドレス (例: `postgresql+psycopg2://USER:PASSWORD@127.0.0.1:5433/DB_NAME`) に設定する必要があります。

## デプロイ

GCP へのデプロイ手順は以下のドキュメントを参照してください。

*   [GCP デプロイガイド](./docs/gcp_deployment_guide.md)

## 使い方

1.  フロントエンド (`http://localhost:5173` またはデプロイ先の URL) にアクセスします。
2.  初回アクセス時はログイン/新規登録画面が表示されます。
    *   管理者が新規登録を許可している場合 (`VITE_ALLOW_SIGNUP=true`) は、メールアドレスとパスワードで新規登録またはログインが可能です。
    *   新規登録が無効な場合 (`VITE_ALLOW_SIGNUP=false`) は、既存のアカウントでログインします。
3.  ログイン後、以下の操作が可能です。
    *   **購入履歴登録:** ユーザー名（既存ユーザー検索または新規作成）と商品名（既存商品検索または新規作成）、購入日を入力して履歴を登録します。
    *   **購入履歴表示:** ユーザー名を入力して検索し、選択したユーザーの購入履歴を表示します。
    *   **AIからの提案:** 履歴表示中のユーザーを選択した状態で「最新の提案を取得」ボタンをクリックすると、LLM による買い物提案が表示されます。
