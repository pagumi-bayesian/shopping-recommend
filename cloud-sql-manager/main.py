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
