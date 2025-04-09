# Cloud SQLインスタンス自動停止・起動ガイド

このドキュメントでは、GCPのCloud SQLインスタンスを夜間や使用しない時間帯に自動的に停止し、必要な時間に自動的に起動する方法について説明します。

## 目的

- 使用していない時間帯（夜間や週末）にCloud SQLインスタンスを自動的に停止することで、コストを削減する
- 業務時間内に自動的にインスタンスを起動し、開発作業に支障が出ないようにする

## アーキテクチャ

以下のGCPサービスを組み合わせて実装します：

1. **Cloud Run**: Cloud SQL Admin APIを呼び出すHTTPエンドポイントを提供
2. **Cloud Scheduler**: 定期的にCloud Runサービスを呼び出す
3. **Cloud SQL Admin API**: インスタンスの停止・起動を実行s

## 実装手順

### 1. Cloud Runサービスの作成

#### 1.1 必要なファイルの準備

プロジェクトディレクトリに `cloud-sql-manager` ディレクトリを作成し、以下のファイルを作成します。

**Dockerfile**:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Use gunicorn as the WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]
```

**requirements.txt**:
```
flask==2.3.3
gunicorn==20.1.0
google-api-python-client==2.15.0
google-auth==2.3.0
```

**main.py**:
```python
import os
from flask import Flask, request, jsonify
from googleapiclient import discovery
from google.oauth2 import service_account
import json

app = Flask(__name__)

def get_sql_service():
    """Cloud SQL Admin APIのサービスクライアントを取得"""
    return discovery.build('sqladmin', 'v1beta4')

@app.route('/manage-instance', methods=['POST'])
def manage_instance():
    """Cloud SQLインスタンスを管理するエンドポイント"""
    request_json = request.get_json(silent=True)
    
    if not request_json:
        return jsonify({"error": "リクエストボディがありません"}), 400
    
    project_id = request_json.get('project_id')
    instance_name = request_json.get('instance_name')
    action = request_json.get('action')  # 'start' または 'stop'
    
    if not all([project_id, instance_name, action]):
        return jsonify({"error": "必須パラメータが不足しています"}), 400
    
    if action not in ['start', 'stop']:
        return jsonify({"error": "アクションは 'start' または 'stop' である必要があります"}), 400
    
    service = get_sql_service()
    
    try:
        if action == 'start':
            # インスタンスを起動
            body = {
                "settings": {
                    "activationPolicy": "ALWAYS"
                }
            }
            api_request = service.instances().patch(
                project=project_id,
                instance=instance_name,
                body=body
            )
            response = api_request.execute()
            return jsonify({"message": f"インスタンス {instance_name} の起動を開始しました", "operation": response})
        else:
            # インスタンスを停止
            body = {
                "settings": {
                    "activationPolicy": "NEVER"
                }
            }
            api_request = service.instances().patch(
                project=project_id,
                instance=instance_name,
                body=body
            )
            response = api_request.execute()
            return jsonify({"message": f"インスタンス {instance_name} の停止を開始しました", "operation": response})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=PORT)
```

#### 1.2 Artifact Registryリポジトリの作成

```bash
gcloud artifacts repositories create cloud-sql-manager-repo \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Repository for Cloud SQL Manager"
```

#### 1.3 Dockerイメージのビルドとプッシュ

```bash
cd cloud-sql-manager
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/PROJECT_ID/cloud-sql-manager-repo/cloud-sql-manager
```

※ `PROJECT_ID` は実際のGCPプロジェクトIDに置き換えてください。

#### 1.4 Cloud Runサービスのデプロイ

```bash
gcloud run deploy cloud-sql-manager \
  --image asia-northeast1-docker.pkg.dev/PROJECT_ID/cloud-sql-manager-repo/cloud-sql-manager \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### 2. IAM権限の設定

Cloud Runサービスに、Cloud SQLインスタンスを管理するための権限を付与します。

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.admin"
```

※ `SERVICE_ACCOUNT_EMAIL` はCloud Runサービスのサービスアカウントのメールアドレスに置き換えてください。

### 3. Cloud Schedulerジョブの作成

#### 3.1 停止ジョブの作成

```bash
gcloud scheduler jobs create http stop-cloud-sql \
  --schedule="0 20 * * 0-6" \
  --location=asia-northeast1 \
  --uri="https://CLOUD_RUN_URL/manage-instance" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"project_id":"PROJECT_ID","instance_name":"INSTANCE_NAME","action":"stop"}' \
  --time-zone="Asia/Tokyo"
```

#### 3.2 起動ジョブの作成

```bash
gcloud scheduler jobs create http start-cloud-sql \
  --schedule="0 10 * * 0-6" \
  --location=asia-northeast1 \
  --uri="https://CLOUD_RUN_URL/manage-instance" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"project_id":"PROJECT_ID","instance_name":"INSTANCE_NAME","action":"start"}' \
  --time-zone="Asia/Tokyo"
```

※ 以下の値を実際の値に置き換えてください：
- `CLOUD_RUN_URL`: デプロイしたCloud RunサービスのURL
- `PROJECT_ID`: GCPプロジェクトID
- `INSTANCE_NAME`: Cloud SQLインスタンス名

## 動作確認

GCPコンソールでCloud Schedulerジョブを手動で実行して、Cloud SQLインスタンスが正しく停止・起動することを確認します。

1. GCPコンソールでCloud Schedulerに移動
2. 作成したジョブの横にある「今すぐ実行」ボタンをクリック
3. Cloud SQLインスタンスの状態が変わることを確認

## トラブルシューティング

### 一般的な問題と解決策

#### 1. Cloud Runサービスが起動しない

**症状**: Cloud Runサービスのデプロイは成功するが、アクセスするとエラーが発生する。

**解決策**:
- Cloud Runのログを確認する
- Dockerfileの `CMD` 命令が正しいか確認する
- 依存関係のバージョンの互換性を確認する

#### 2. Cloud SQLインスタンスの状態が変わらない

**症状**: Cloud Schedulerジョブは成功するが、Cloud SQLインスタンスの状態が変わらない。

**解決策**:
- Cloud RunサービスのIAM権限が正しく設定されているか確認する
- Cloud Runサービスのログでエラーメッセージを確認する
- リクエストのパラメータ（プロジェクトID、インスタンス名）が正しいか確認する

#### 3. 依存関係の問題

**症状**: `ImportError` や `ModuleNotFoundError` などのエラーが発生する。

**解決策**:
- `requirements.txt` の依存関係のバージョンを更新する
- 互換性のあるバージョンの組み合わせを使用する
- 変数名の衝突がないか確認する（例: `request` 変数と Flask の `request` オブジェクト）

## 注意点

1. **コスト**: Cloud Runは使用した分だけ課金されますが、リクエスト数が少ない場合はほぼ無料で利用できます
2. **セキュリティ**: 本番環境では `--allow-unauthenticated` を使用せず、適切な認証を設定することをお勧めします
3. **エラーハンドリング**: 実際の実装ではより堅牢なエラーハンドリングを追加することをお勧めします
4. **モニタリング**: Cloud Loggingを使用して操作のログを確認できます
