# Pythonの公式イメージをベースにする
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピーしてインストール
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポートを公開（docker-compose.ymlで指定したポートと合わせる）
EXPOSE 8000

# アプリケーションを実行（docker-compose.ymlのcommandで上書きされるが、デフォルトとして定義）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
