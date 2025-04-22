# GCP デプロイガイド: 買い物提案アプリ

このドキュメントは、買い物提案アプリケーションを Google Cloud Platform (GCP) と Firebase にデプロイする手順をまとめたものです。

## 1. 概要

このアプリケーションは以下のコンポーネントで構成されます。

*   **バックエンド:** Python (FastAPI) 製。Cloud Run にコンテナとしてデプロイ。
*   **フロントエンド:** Vue.js 製。Firebase Hosting にデプロイ。
*   **データベース:** SQLite。Cloud Storage にファイルを永続化。
*   **コンテナビルド:** Cloud Build を使用してバックエンドの Docker イメージをビルド。
*   **コンテナレジストリ:** Artifact Registry を使用してバックエンドのコンテナイメージを管理。
*   **シークレット管理:** Secret Manager を使用して API キーを管理 (DBパスワードは不要に)。
*   **ファイルストレージ:** Cloud Storage を使用して SQLite データベースファイルを保存。

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
    *   Cloud Storage API # 追加
    *   Artifact Registry API
    *   Secret Manager API
    *   Identity and Access Management (IAM) API
    # Cloud SQL Admin API は不要
*   **ソースコードリポジトリ:** アプリケーションのソースコードが Git リポジトリで管理されていること。

## 3. GCP リソースの準備 (初回のみ)

以下のリソースがまだ準備されていない場合は、作成してください。

### 3.1. Cloud Storage バケット

1.  **バケットの作成:** GCP Console または `gsutil` コマンドを使用して、SQLite データベースファイルを保存するための Cloud Storage バケットを作成します (例: `shopping-app-sqlite-db`、リージョン: `asia-northeast1`、標準ストレージクラス)。
    ```bash
    gsutil mb -l asia-northeast1 gs://shopping-app-sqlite-db
    ```
2.  **IAM権限:** Cloud Run サービスが使用するサービスアカウントに、このバケットへの読み取りおよび書き込み権限 (`roles/storage.objectAdmin` または `roles/storage.objectUser`) を付与します (後述のデプロイ手順で設定)。
# Cloud SQL (PostgreSQL) セクションは削除

### 3.2. Artifact Registry

1.  **リポジトリの作成:** GCP Console で Artifact Registry に Docker リポジトリを作成します (例: `shopping-app-repo`、リージョン: `asia-northeast1`)。

### 3.3. Secret Manager

1.  **シークレットの作成:** GCP Console で Secret Manager に以下のシークレットを作成します。
    *   `anthropic-api-key`: Anthropic API キー。
    *   `langchain-api-key`: LangSmith API キー (使用している場合)。
    *   (その他、アプリケーションが必要とする API キーなど)
    *   `shopping-app-db-password` は不要になりました。
2.  **Cloud Build/Run サービスアカウントへの権限付与:**
    *   Cloud Build サービスアカウント (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`) に、ビルド時に使用するシークレット (もしあれば) への「**Secret Manager のシークレット アクセサー**」ロールを付与します。
    *   Cloud Run サービスが使用するサービスアカウント (デフォルトまたは指定したもの) に、`anthropic-api-key` や `langchain-api-key` など、アプリケーションが使用するシークレットへの「**Secret Manager のシークレット アクセサー**」ロールを付与します。

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

2. **Cloud Run サービスの更新:**
    ビルドが完了したら、以下のコマンドを実行して Cloud Run サービスを新しいイメージで更新します。**`YOUR_PROJECT_ID`、`YOUR_STORAGE_BUCKET_NAME`、`YOUR_DB_FILE_NAME`、`YOUR_LANGSMITH_PROJECT_NAME` は実際の値に置き換えてください。**

    ```bash
    gcloud run deploy shopping-app-backend \
        --image asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/shopping-app-repo/shopping-app-backend:latest \
        --region asia-northeast1 \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars STORAGE_BUCKET=YOUR_STORAGE_BUCKET_NAME,DB_FILE_NAME=YOUR_DB_FILE_NAME,LANGCHAIN_TRACING_V2=true,LANGCHAIN_ENDPOINT=https://api.smith.langchain.com,LANGCHAIN_PROJECT=YOUR_LANGSMITH_PROJECT_NAME \
        --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest,LANGCHAIN_API_KEY=langchain_api_key:latest
        # --add-cloudsql-instances は削除
        # DB_USER, DB_NAME, INSTANCE_CONNECTION_NAME は削除
        # DB_PASSWORD シークレットは削除
    ```

    * **コマンドの説明:**
        * `gcloud run deploy shopping-app-backend`: `shopping-app-backend` サービスをデプロイ/更新します。
        * `--image ...`: 使用する Docker イメージを指定します (Cloud Build でプッシュしたもの)。
        * `--region ...`: デプロイ先のリージョン。
        * `--platform managed`: マネージドプラットフォームを使用。
        * `--allow-unauthenticated`: 認証なしアクセスを許可 (フロントエンドからのアクセス用)。
        * `--set-env-vars ...`: 環境変数を設定。SQLiteデータベースファイルを保存するCloud Storageバケット名 (`STORAGE_BUCKET`) とファイル名 (`DB_FILE_NAME`) を指定します。LangSmith関連も設定します。
        * `--set-secrets ...`: Secret Manager のシークレットを環境変数として設定 (APIキーなど)。
    * **重要:** Cloud Run サービスアカウントに、指定した Cloud Storage バケット (`YOUR_STORAGE_BUCKET_NAME`) への読み取り/書き込み権限 (`roles/storage.objectAdmin` など) が付与されている必要があります。付与されていない場合は、IAM設定で追加してください。
        ```bash
        # 例: デフォルトのCompute Engineサービスアカウントに権限を付与
        gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
            --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
            --role="roles/storage.objectAdmin"

        # または、Cloud Run用に作成したサービスアカウントに権限を付与
        gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
            --member="serviceAccount:YOUR_RUN_SERVICE_ACCOUNT_EMAIL" \
            --role="roles/storage.objectAdmin"
        ```
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
    `frontend` ディレクトリで以下のコマンドを実行し、ビルドされたファイルを Firebase Hosting にデプロイします。
    ```bash
    firebase deploy --only hosting
    ```
    *   **注意:** このコマンドは `frontend/firebase.json` の設定 (`"public": "dist"`) に基づいて `frontend/dist` ディレクトリの内容をデプロイします。

## 5. ローカル開発環境

ローカルでの開発・テストには以下のツールが役立ちます。

* **Cloud Storage バケット:** ローカル開発時も、テスト用の Cloud Storage バケットを用意し、`STORAGE_BUCKET` 環境変数を設定すると、デプロイ環境に近い動作を確認できます。または、ローカルファイルシステムのみでテストすることも可能です (`database.py` がローカルファイルを作成します)。

* **Python バックエンドサーバー:**

    ```bash
    # backend ディレクトリで実行
    # 必要な環境変数を設定 (例: .env ファイルまたは直接)
    # export STORAGE_BUCKET="your-dev-bucket" # オプション
    # export DB_FILE_NAME="dev_shopping_app.db" # オプション
    # export ANTHROPIC_API_KEY="..."
    # export LANGCHAIN_API_KEY="..." # オプション
    uvicorn main:app --reload # uvicorn を使用
    ```

* **Vite 開発サーバー:**

    ```bash
    # frontend ディレクトリで実行
    # .env ファイルで VITE_API_BASE_URL=http://localhost:8000 などを設定
    npm run dev
    ```

---

**以上が基本的なデプロイ手順です。実際の環境に合わせて設定値 (YOUR_PROJECT_ID, YOUR_INSTANCE_CONNECTION_NAME など) を変更してください。**
