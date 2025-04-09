# GCP デプロイガイド: 買い物提案アプリ

このドキュメントは、買い物提案アプリケーションを Google Cloud Platform (GCP) と Firebase にデプロイする手順をまとめたものです。

## 1. 概要

このアプリケーションは以下のコンポーネントで構成されます。

*   **バックエンド:** Python (FastAPI) 製。Cloud Run にコンテナとしてデプロイ。
*   **フロントエンド:** Vue.js 製。Firebase Hosting にデプロイ。
*   **データベース:** PostgreSQL。Cloud SQL でホスト。
*   **コンテナビルド:** Cloud Build を使用してバックエンドの Docker イメージをビルド。
*   **コンテナレジストリ:** Artifact Registry を使用してバックエンドのコンテナイメージを管理。
*   **シークレット管理:** Secret Manager を使用してデータベースパスワードや API キーを管理。

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
*   **ソースコードリポジトリ:** アプリケーションのソースコードが Git リポジトリで管理されていること。

## 3. GCP リソースの準備 (初回のみ)

以下のリソースがまだ準備されていない場合は、作成してください。

### 3.1. Cloud SQL (PostgreSQL)

1.  **インスタンスの作成:** GCP Console で PostgreSQL インスタンスを作成します。インスタンス ID、デフォルトユーザー (`postgres`) のパスワード、リージョン (`asia-northeast1` など) を設定します。
    *   **注意:** デフォルトユーザーのパスワードは安全な場所に記録し、後で Secret Manager に登録します。
    *   「接続」設定で「**プライベート IP**」を有効にし、ネットワーク (通常は `default`) を選択します。
2.  **データベースの作成:** 作成したインスタンス内に、アプリケーション用のデータベース (例: `shopping_app_db`) を作成します。
3.  **インスタンス接続名:** 作成したインスタンスの「概要」ページで**インスタンス接続名** (例: `YOUR_PROJECT_ID:asia-northeast1:your-instance-id`) を確認し、控えておきます。

### 3.2. Artifact Registry

1.  **リポジトリの作成:** GCP Console で Artifact Registry に Docker リポジトリを作成します (例: `shopping-app-repo`、リージョン: `asia-northeast1`)。

### 3.3. Secret Manager

1.  **シークレットの作成:** GCP Console で Secret Manager に以下のシークレットを作成します。
    *   `shopping-app-db-password`: Cloud SQL の `postgres` ユーザーのパスワード。
    *   `anthropic-api-key`: Anthropic API キー。
    *   (その他、アプリケーションが必要とする API キーなど)
2.  **Cloud Build/Run サービスアカウントへの権限付与:**
    *   Cloud Build サービスアカウント (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`) に、ビルド時に使用するシークレット (もしあれば) への「**Secret Manager のシークレット アクセサー**」ロールを付与します。
    *   Cloud Run サービスが使用するサービスアカウント (デフォルトまたは指定したもの) に、`shopping-app-db-password` と `anthropic-api-key` への「**Secret Manager のシークレット アクセサー**」ロールを付与します。

### 3.4. Firebase プロジェクト

1.  **Firebase プロジェクトの作成または選択:** Firebase Console で GCP プロジェクトに紐づく Firebase プロジェクトを作成または選択します。
2.  **Hosting の有効化:** Firebase プロジェクトで Hosting を有効にします。
3.  **Firebase CLI の設定:** ローカルの `frontend` ディレクトリで `firebase use --add` を実行し、対象の Firebase プロジェクトを選択します。`firebase init hosting` を実行し、Public directory を `dist`、single-page app を `Yes` に設定します。

## 4. デプロイ手順

バックエンドとフロントエンドは個別にデプロイします。

### 4.1. バックエンドの更新・デプロイ (Cloud Run)

バックエンドのコード (`backend/` ディレクトリ以下) を変更した場合、以下の手順でデプロイします。

1.  **Docker イメージのビルドとプッシュ:**
    プロジェクトのルートディレクトリ (`cloudbuild.yaml` がある場所) で以下のコマンドを実行します。これにより、Cloud Build が `cloudbuild.yaml` の設定に従って Docker イメージをビルドし、Artifact Registry にプッシュします。
    ```bash
    gcloud builds submit --config cloudbuild.yaml .
    ```
    *   **注意:** `cloudbuild.yaml` には、バックエンドの Docker イメージをビルドし、`asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/shopping-app-repo/shopping-app-backend:latest` のようなタグで Artifact Registry にプッシュするステップが含まれている必要があります。

2.  **Cloud Run サービスの更新:**
    ビルドが完了したら、以下のコマンドを実行して Cloud Run サービスを新しいイメージで更新します。**`YOUR_PROJECT_ID` と `YOUR_INSTANCE_CONNECTION_NAME` は実際の値に置き換えてください。**
    ```bash
    gcloud run deploy shopping-app-backend \
      --image asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/shopping-app-repo/shopping-app-backend:latest \
      --region asia-northeast1 \
      --platform managed \
      --allow-unauthenticated \
      --add-cloudsql-instances YOUR_INSTANCE_CONNECTION_NAME \
      --set-env-vars INSTANCE_CONNECTION_NAME=YOUR_INSTANCE_CONNECTION_NAME,DB_USER=postgres,DB_NAME=postgres \
      --set-secrets DB_PASSWORD=shopping-app-db-password:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest
    ```
    *   **コマンドの説明:**
        *   `gcloud run deploy shopping-app-backend`: `shopping-app-backend` サービスをデプロイ/更新します。
        *   `--image ...`: 使用する Docker イメージを指定します (Cloud Build でプッシュしたもの)。
        *   `--region ...`: デプロイ先のリージョン。
        *   `--platform managed`: マネージドプラットフォームを使用。
        *   `--allow-unauthenticated`: 認証なしアクセスを許可 (フロントエンドからのアクセス用)。
        *   `--add-cloudsql-instances ...`: Cloud SQL インスタンスへの接続を有効化。`YOUR_INSTANCE_CONNECTION_NAME` を置き換えてください。
        *   `--set-env-vars ...`: 環境変数を設定。`YOUR_INSTANCE_CONNECTION_NAME` を置き換えてください。
        *   `--set-secrets ...`: Secret Manager のシークレットを環境変数として設定。

### 4.2. フロントエンドの更新・デプロイ (Firebase Hosting)

フロントエンドのコード (`frontend/` ディレクトリ以下) を変更した場合、以下の手順でデプロイします。

1.  **フロントエンドのビルド:**
    `frontend` ディレクトリに移動し、本番用の静的ファイルをビルドします。
    ```bash
    cd frontend
    npm run build
    cd ..
    ```
    これにより `frontend/dist` ディレクトリにビルド成果物が生成されます。

2.  **Firebase Hosting へのデプロイ:**
    プロジェクトのルートディレクトリで以下のコマンドを実行し、ビルドされたファイルを Firebase Hosting にデプロイします。
    ```bash
    firebase deploy --only hosting
    ```
    *   **注意:** このコマンドは `frontend/firebase.json` の設定 (`"public": "dist"`) に基づいて `frontend/dist` ディレクトリの内容をデプロイします。

## 5. ローカル開発環境

ローカルでの開発・テストには以下のツールが役立ちます。

*   **Docker Compose (`docker-compose.yml`):** (オプション) ローカルで PostgreSQL コンテナなどを起動する場合に使用。
*   **Cloud SQL Auth Proxy:** ローカルマシンから Cloud SQL インスタンスへ安全に接続するためのプロキシ。
    ```bash
    # Cloud SQL Auth Proxy の起動例 (INSTANCE_CONNECTION_NAME を置き換える)
    ./cloud-sql-proxy YOUR_INSTANCE_CONNECTION_NAME -p 5432
    ```
*   **Python バックエンドサーバー:**
    ```bash
    # backend ディレクトリで実行
    # 必要な環境変数を設定 (例: .env ファイルまたは直接)
    # export DATABASE_URL="postgresql+psycopg2://postgres:YOUR_LOCAL_PROXY_PASSWORD@127.0.0.1:5432/shopping_app_db"
    # export ANTHROPIC_API_KEY="..."
    python backend/main.py
    ```
*   **Vite 開発サーバー:**
    ```bash
    # frontend ディレクトリで実行
    # .env ファイルで VITE_API_BASE_URL=http://localhost:8000 などを設定
    npm run dev
    ```

---

**以上が基本的なデプロイ手順です。実際の環境に合わせて設定値 (YOUR_PROJECT_ID, YOUR_INSTANCE_CONNECTION_NAME など) を変更してください。**
