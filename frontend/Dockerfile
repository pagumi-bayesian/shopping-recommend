# Node.jsの公式イメージをベースにする (LTSバージョン推奨)
FROM node:18-alpine

# 作業ディレクトリを設定
WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# 依存関係をインストール
RUN npm install

# アプリケーションコードをコピー
COPY . .

# Viteの開発サーバーが使用するポートを公開
EXPOSE 5173

# アプリケーションを実行（開発モード）
CMD ["npm", "run", "dev", "--", "--host"]
