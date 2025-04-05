# GCP デプロイガイド: 買い物提案アプリ

このドキュメントは、買い物提案アプリケーションを Google Cloud Platform (GCP) にデプロイする手順をまとめたものです。

## 1. 概要

このアプリケーションは以下のコンポーネントで構成されます。

*   **バックエンド:** Python (FastAPI) 製。Cloud Run にコンテナとしてデプロイ。
*   **フロントエンド:** Vue.js 製。Firebase Hosting にデプロイ。
*   **データベース:** PostgreSQL。Cloud SQL でホスト。
*   **CI/CD:** Cloud Build を使用してビルドとデプロイを自動化。
*   **コンテナレジストリ:** Artifact Registry を使用してバックエンドのコンテナイメージを管理。
*   **シークレット管理:** Secret Manager を使用してデータベースパスワードやFirebaseトークンを管理。

## 2. 前提条件

デプロイを開始する前に、以下の準備が整っていることを確認してください。

*   **Google Cloud SDK (gcloud CLI):** インストールおよび認証済みであること (`gcloud auth login`, `gcloud config set project YOUR_PROJECT_ID`)。
*   **Docker:** ローカル環境にインストール済みであること（バックエンドコンテナのローカルビルド/テスト用）。
*   **Node.js & npm:** ローカル環境にインストール済みであること（フロントエンド開発/ビルド用）。
*   **Firebase CLI:** インストールおよび認証済みであること (`npm install -g firebase-tools`, `firebase login`)。
*   **GCP プロジェクト:** 課金が有効な GCP プロジェクトが存在すること。
*   **有効な API:** プロジェクトで以下の API が有効になっていること。
    *   Cloud Build API
    *   Cloud Run Admin API
    *   Cloud SQL Admin API
    *   Artifact Registry API
    *   Secret Manager API
    *   Identity and Access Management (IAM) API
*   **ソースコードリポジトリ:** アプリケーションのソースコードが Git リポジトリ (GitHub, Cloud Source Repositories など) で管理されていること。

## 3. GCP リソースの準備

### 3.1. Cloud SQL (PostgreSQL)

1.  **インスタンスの作成:**
    *   GCP Console で Cloud SQL に移動し、「インスタンスを作成」をクリック。
    *   「PostgreSQL を選択」。
    *   インスタンス ID、デフォルトユーザー (`postgres`) のパスワード、リージョン、マシンタイプなどを設定。
        *   **注意:** デフォルトユーザーのパスワードは安全な場所に記録し、後で Secret Manager に登録します。
    *   「接続」設定で「**プライベート IP**」を有効にし、ネットワーク (通常は `default`) を選択します。これにより、同じ VPC 内の Cloud Run から安全に接続できます。必要に応じて「パブリック IP」も有効にできますが、セキュリティリスクを考慮してください。
    *   「作成」をクリックします。作成には数分かかります。
2.  **データベースの作成:**
    *   作成されたインスタンスを選択し、「データベース」タブを開きます。
    *   「データベースを作成」をクリックし、データベース名 (例: `shopping_app_db`) を入力して作成します。
3.  **ユーザーの作成 (オプション):**
    *   デフォルトの `postgres` ユーザー以外を使用する場合は、「ユーザー」タブで新しいユーザーを作成し、パスワードを設定します。

### 3.2. Artifact Registry

1.  **リポジトリの作成:**
    *   GCP Console で Artifact Registry に移動し、「リポジトリを作成」をクリック。
    *   リポジトリ名 (例: `shopping-app-repo`) を入力。
    *   フォーマットとして「**Docker**」を選択。
    *   モードとして「標準」を選択。
    *   ロケーションタイプとリージョン (例: `asia-northeast1`) を選択。
    *   「作成」をクリックします。

### 3.3. Secret Manager

1.  **データベースパスワードの登録:**
    *   GCP Console で Secret Manager に移動し、「シークレットを作成」をクリック。
    *   名前 (例: `db-password`) を入力。
    *   「シークレットの値」に Cloud SQL で設定したデータベースユーザーのパスワードを入力。
    *   「シークレットを作成」をクリック。
    *   作成したシークレットの**リソース名**をコピーしておきます (Cloud Run の設定で使用)。
2.  **Firebase CI トークンの登録:**
    *   ローカルのターミナルで `firebase login:ci` を実行し、表示されるトークンをコピーします。
    *   Secret Manager で新しいシークレットを作成します。
    *   名前 (例: `firebase-ci-token`) を入力。
    *   「シークレットの値」にコピーした Firebase CI トークンを貼り付けます。
    *   「シークレットを作成」をクリック。
    *   作成したシークレットの**リソース名**をコピーしておきます (Cloud Build トリガーの設定で使用)。
3.  **Cloud Build サービスアカウントへの権限付与:**
    *   作成した各シークレット (`db-password`, `firebase-ci-token`) の詳細画面を開き、「権限」タブで Cloud Build サービスアカウント (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`) に「**Secret Manager のシークレット アクセサー**」ロールを付与します。

### 3.4. Firebase プロジェクト

1.  **Firebase プロジェクトの作成または選択:**
    *   Firebase Console ([https://console.firebase.google.com/](https://console.firebase.google.com/)) にアクセスします。
    *   既存の GCP プロジェクトを選択するか、新規に Firebase プロジェクトを作成します (既存の GCP プロジェクトに紐付けることを推奨)。
2.  **Hosting の有効化:**
    *   左側のメニューから「ビルド」>「Hosting」を選択します。
    *   「始める」をクリックし、画面の指示に従って Hosting を有効にします。
3.  **Firebase CLI の設定:**
    *   ローカルの `frontend` ディレクトリで `firebase use --add` を実行し、対象の Firebase プロジェクトを選択してエイリアス (例: `default`) を設定します。
    *   `firebase init hosting` を実行し、指示に従って設定します。
        *   Public directory: `dist` (Vite のビルド出力ディレクトリ)
        *   Configure as a single-page app: `Yes`
        *   Set up automatic builds and deploys with GitHub: `No` (Cloud Build で行うため)
    *   これにより `firebase.json` と `.firebaserc` が生成・更新されます。

## 4. バックエンド (Cloud Run) のデプロイ

### 4.1. Dockerfile の確認

`backend/Dockerfile` が存在し、FastAPI アプリケーションを適切にコンテナ化する内容になっていることを確認します。

```dockerfile
# backend/Dockerfile の例
FROM python:3.9-slim

WORKDIR /app

# Poetryのインストール (Poetryを使用している場合)
# RUN pip install poetry
# COPY poetry.lock pyproject.toml ./
# RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

# requirements.txtを使用している場合
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./backend /app/backend

# FastAPIがリッスンするポート
EXPOSE 8000

# アプリケーションの起動コマンド (例: uvicorn)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2. Cloud Build によるビルドとプッシュ

`cloudbuild.yaml` に以下のステップが含まれていることを確認します。

```yaml
# cloudbuild.yaml のバックエンド関連部分
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      [
        'build',
        '-t',
        '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}:latest',
        './backend', # Dockerfileのあるディレクトリ
        '-f',
        './backend/Dockerfile',
      ]
    id: Build Backend

  # Push the container image to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      [
        'push',
        '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}:latest',
      ]
    id: Push Backend
    waitFor: ['Build Backend']

# ... (他のステップ) ...

images:
  - '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}:latest'

substitutions:
  _LOCATION: asia-northeast1 # Artifact Registryのリージョン
  _REPOSITORY: shopping-app-repo # Artifact Registryのリポジトリ名
  _SERVICE_NAME: shopping-app-backend # イメージ名の一部
  # ... (他の置換変数) ...
```

### 4.3. Cloud Run サービスの作成/更新

Cloud Build でイメージがプッシュされた後、Cloud Run サービスを作成または更新します。これは初回は手動で行い、以降は `gcloud run deploy` コマンドや Cloud Build で自動化できます。

1.  **GCP Console で Cloud Run に移動し、「サービスを作成」をクリック (または既存サービスを選択して「新しいリビジョンを編集してデプロイ」)。**
2.  **コンテナイメージの選択:**
    *   「既存のコンテナ イメージから 1 つのリビジョンをデプロイする」を選択。
    *   「コンテナ イメージの URL」で「選択」をクリックし、Artifact Registry から先ほどプッシュしたイメージ (`${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}:latest`) を選択します。
3.  **サービス名、リージョンを設定。**
4.  **認証:** 「未認証の呼び出しを許可」または「認証が必要」を選択します (API の性質による)。
5.  **コンテナ、変数とシークレット、接続、セキュリティ の設定:**
    *   **コンテナポート:** Dockerfile で `EXPOSE` したポート (例: `8000`) を指定します。
    *   **環境変数:**
        *   `DATABASE_URL`: PostgreSQL の接続文字列を設定します。Cloud SQL のプライベート IP を使用する場合、通常は `postgresql+psycopg2://USER:PASSWORD@PRIVATE_IP:5432/DB_NAME` の形式になります。パスワード部分は直接入力せず、次の「シークレット」で設定します。
        *   `OPENAI_API_KEY` など、アプリケーションが必要とする他の環境変数も設定します。
    *   **シークレット:**
        *   「参照」>「シークレットとしてマウント」を選択。
        *   環境変数名 (例: `DB_PASSWORD`) を指定。
        *   「シークレット」で Secret Manager に登録したデータベースパスワード (`db-password`) を選択し、「バージョン」は `latest` を選択。
        *   「完了」をクリック。
        *   `DATABASE_URL` のパスワード部分を `${DB_PASSWORD}` のように参照するように修正します (例: `postgresql+psycopg2://USER:${DB_PASSWORD}@PRIVATE_IP:5432/DB_NAME`)。
    *   **接続:**
        *   「Cloud SQL 接続」で「接続を追加」をクリックし、作成した Cloud SQL インスタンスを選択します。これにより、コンテナから Cloud SQL への安全な接続が確立されます。
6.  **作成 (または デプロイ):** 設定を確認し、クリックします。

## 5. フロントエンド (Firebase Hosting) のデプロイ

### 5.1. Firebase 設定の確認

`frontend/firebase.json` と `frontend/.firebaserc` が正しく設定されていることを確認します。

```json
// frontend/firebase.json の例
{
  "hosting": {
    "public": "dist", // Viteのビルド出力ディレクトリ
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html" // シングルページアプリケーション用
      }
    ]
  }
}
```

```json
// frontend/.firebaserc の例
{
  "projects": {
    "default": "YOUR_FIREBASE_PROJECT_ID" // firebase use で設定される
  }
}
```

### 5.2. 環境変数

*   **ローカル開発:** `frontend/.env` ファイルで `VITE_API_BASE_URL` (バックエンドAPIのURL) や `VITE_ALLOW_SIGNUP` などを設定します。
*   **Cloud Build:** `cloudbuild.yaml` のフロントエンドビルドステップで、本番用の環境変数を設定します。
    *   `_VITE_API_BASE_URL`: デプロイされた Cloud Run サービスの URL。
    *   `_VITE_ALLOW_SIGNUP`: `'true'` または `'false'`。

### 5.3. Cloud Build によるビルドとデプロイ

`cloudbuild.yaml` に以下のステップが含まれていることを確認します。

```yaml
# cloudbuild.yaml のフロントエンド関連部分
steps:
# ... (バックエンドのステップ) ...

  # Frontend Build Step
  - name: 'node:18'
    entrypoint: 'npm'
    args: ['install']
    dir: 'frontend'
    id: Frontend Install Dependencies

  - name: 'node:18'
    entrypoint: 'npm'
    args: ['run', 'build']
    dir: 'frontend'
    env:
      # Cloud Buildでは _ プレフィックスが必要
      - '_VITE_API_BASE_URL=YOUR_CLOUD_RUN_SERVICE_URL' # Cloud RunのURLに置き換える
      - '_VITE_ALLOW_SIGNUP=false' # デフォルトは新規登録無効
    id: Frontend Build
    waitFor: ['Frontend Install Dependencies']

  # Firebase Deploy Step
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'firebase'
    args:
      [
        'deploy',
        '--only',
        'hosting',
        '--project',
        '${PROJECT_ID}', # GCPプロジェクトID
        '--non-interactive',
        '--token',
        '${_FIREBASE_TOKEN}', # Secret Managerから渡すトークン
      ]
    dir: 'frontend'
    id: Deploy to Firebase Hosting
    waitFor: ['Frontend Build']

# ... (他の設定) ...

substitutions:
  # ... (他の置換変数) ...
  _FIREBASE_TOKEN: '' # トリガーでSecret Managerから設定する
```

**注意:** `_VITE_API_BASE_URL` の値は、デプロイされた Cloud Run サービスの URL に置き換える必要があります。これは Cloud Run サービスの詳細画面で確認できます。

## 6. Cloud Build トリガーの設定

1.  **トリガー作成:** GCP Console で Cloud Build > トリガー に移動し、「トリガーを作成」。
2.  **イベント、ソース:** リポジトリとブランチ（例: `main`）を設定。
3.  **構成:** Cloud Build 構成ファイルとして `cloudbuild.yaml` を指定。
4.  **置換変数:**
    *   `_FIREBASE_TOKEN`: **値**の右にある**鍵アイコン**をクリックし、Secret Manager に保存した `firebase-ci-token` シークレットを選択。
    *   必要に応じて `_LOCATION`, `_REPOSITORY`, `_SERVICE_NAME` なども設定（`cloudbuild.yaml` で定義済みなら不要な場合あり）。
5.  **作成:** トリガーを保存。

これで、指定したブランチにコードがプッシュされると、自動的にバックエンドとフロントエンドのビルド＆デプロイが実行されます。

## 7. ローカル開発環境

ローカルでの開発・テストには以下のツールが役立ちます。

*   **Docker Compose (`docker-compose.yml`):** バックエンド、(オプションで)データベースコンテナなどをまとめて起動・管理。
*   **Cloud SQL Auth Proxy:** ローカルマシンから Cloud SQL インスタンスへ安全に接続するためのプロキシ。
    ```bash
    # Cloud SQL Auth Proxy の起動例
    ./cloud-sql-proxy --private-ip INSTANCE_CONNECTION_NAME
    # または TCP ポートを使用
    # ./cloud-sql-proxy INSTANCE_CONNECTION_NAME -p 5432
    ```
    `INSTANCE_CONNECTION_NAME` は Cloud SQL インスタンスの詳細画面で確認できます。
*   **Vite 開発サーバー (`npm run dev`):** フロントエンドの開発サーバーを起動。`.env` ファイルでローカル用 API URL (例: `http://localhost:8000`) を設定します。

---

**以上が基本的なデプロイ手順です。実際の環境に合わせて適宜設定値を変更してください。**
