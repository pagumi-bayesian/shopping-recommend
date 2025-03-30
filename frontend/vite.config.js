import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // Dockerコンテナ内で外部からのアクセスを受け付けるために必要
    host: '0.0.0.0',
    port: 5173, // docker-compose.ymlで公開したポート
    // ホットリロードが効かない場合に追加する設定 (オプション)
    // watch: {
    //  usePolling: true,
    // }
  }
})
