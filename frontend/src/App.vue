<template>
  <header>
    <h1>買い物提案アプリ</h1>
  </header>

  <main>
    <h2>購入履歴登録</h2>
    <form @submit.prevent="addPurchase">
      <div class="autocomplete-container"> <!-- コンテナ追加 -->
        <label for="userName">ユーザー名:</label>
        <input type="text" id="userName" v-model="userNameInput" @input="searchUsersForPurchase" placeholder="名前を入力..." required autocomplete="off"> <!-- 関数名を変更 -->
        <ul v-if="userSuggestions.length > 0" class="suggestions-list"> <!-- 候補リスト追加 -->
          <li v-for="user in userSuggestions" :key="user.id" @click="selectUserForPurchase(user)"> <!-- 関数名を変更 -->
            {{ user.name }}
          </li>
        </ul>
        <!-- 新規作成ボタン -->
        <button type="button" v-if="showCreateUserButton" @click="createUser">
          「{{ userNameInput }}」を新規作成
        </button>
      </div>
      <div class="autocomplete-container"> <!-- コンテナ追加 -->
        <label for="productName">商品名:</label>
        <input type="text" id="productName" v-model="productNameInput" @input="searchProducts" placeholder="商品名を入力..." required autocomplete="off"> <!-- @input追加, autocomplete="off"追加 -->
        <ul v-if="productSuggestions.length > 0" class="suggestions-list"> <!-- 候補リスト追加 -->
          <li v-for="product in productSuggestions" :key="product.id" @click="selectProduct(product)">
            {{ product.name }}
          </li>
        </ul>
        <!-- 新規作成ボタン -->
        <button type="button" v-if="showCreateProductButton" @click="createProduct">
          「{{ productNameInput }}」を新規作成
        </button>
      </div>
      <div>
        <label for="purchaseDate">購入日:</label>
        <input type="date" id="purchaseDate" v-model="newPurchase.purchaseDate" required>
      </div>
      <!-- 数量入力欄を削除 -->
      <!--
      <div>
        <label for="quantity">数量:</label>
        <input type="number" id="quantity" v-model.number="newPurchase.quantity" min="1" required>
      </div>
      -->
      <button type="submit">登録</button>
    </form>

    <h2>購入履歴</h2> <!-- 見出し変更 -->
    <div class="autocomplete-container"> <!-- コンテナ追加 -->
        <label for="displayUserName">ユーザー名:</label> <!-- ラベル変更 -->
        <input type="text" id="displayUserName" v-model="displayUserNameInput" @input="searchUsersForDisplay" placeholder="履歴を表示するユーザー名..." autocomplete="off"> <!-- type, v-model, @input変更 -->
        <ul v-if="displayUserSuggestions.length > 0" class="suggestions-list"> <!-- 候補リスト追加 -->
          <li v-for="user in displayUserSuggestions" :key="user.id" @click="selectUserForDisplay(user)">
            {{ user.name }}
          </li>
        </ul>
        <!-- 履歴更新ボタンは削除 (選択時に自動更新) -->
    </div>
    <ul v-if="historyList.length > 0">
      <li v-for="item in historyList" :key="item.id">
        <!-- 商品IDの代わりに商品名 (item.product.name) を表示 -->
        {{ item.purchase_date }} - {{ item.product?.name || '商品名不明' }} <!-- 数量表示を削除 -->
      </li>
    </ul>
    <p v-else>購入履歴はありません。</p>

    <hr>

    <h2>AIからの提案 (ユーザー: {{ displayUserNameInput || '未選択' }})</h2> <!-- ユーザー名表示に変更 -->
    <button @click="fetchSuggestions" :disabled="loadingSuggestions || !displayUserId"> <!-- ID未選択時はボタン無効化 -->
      {{ loadingSuggestions ? '提案を取得中...' : '最新の提案を取得' }}
    </button>
    <!-- v-htmlを使ってレンダリングされたHTMLを表示 -->
    <div v-if="suggestionsText" class="suggestions" v-html="renderedSuggestions"></div>
    <p v-else>まだ提案はありません。「最新の提案を取得」ボタンを押してください。</p>

  </main>
</template>

<script setup>
import { ref, onMounted, reactive, computed, watch } from 'vue'; // watch を追加
import { marked } from 'marked'; // marked をインポート

// APIのエンドポイントURL (docker-compose環境なのでコンテナ名ではなくlocalhost)
const API_BASE_URL = 'http://localhost:8000'; // バックエンドAPIのURL

// 新規購入履歴フォームのデータ (IDは別途管理)
const newPurchase = reactive({
  // userId: 1, // 削除
  // productId: null, // 削除
  purchaseDate: new Date().toISOString().split('T')[0], // 今日の日付をデフォルトに
  // quantity: 1 // 削除
});
// オートコンプリート用入力テキスト
const userNameInput = ref('');
const productNameInput = ref('');
// 選択されたID
const selectedUserId = ref(null);
const selectedProductId = ref(null);
// 検索候補リスト
const userSuggestions = ref([]);
const productSuggestions = ref([]);
// 新規作成ボタン表示制御用フラグ (購入履歴登録用)
const showCreateUserButton = ref(false);
const showCreateProductButton = ref(false);
// 履歴表示用オートコンプリート
const displayUserNameInput = ref(''); // 履歴表示用のユーザー名入力
const displayUserSuggestions = ref([]); // 履歴表示用の候補リスト

// 表示する購入履歴リスト
const historyList = ref([]);
// 表示対象のユーザーID
const displayUserId = ref(1); // デフォルトでユーザーID 1 の履歴を表示
// AIからの提案テキスト
const suggestionsText = ref('');
// 提案取得中のローディング状態
const loadingSuggestions = ref(false);

// suggestionsTextの内容をMarkdownとして解釈しHTMLに変換する算出プロパティ
const renderedSuggestions = computed(() => {
  if (suggestionsText.value) {
    // 注意: markedはデフォルトでサニタイズを行わないため、
    // 信頼できないソースからのMarkdownを表示する場合はサニタイズ処理を追加する必要がある。
    // 今回は信頼できるLLMからの応答を想定しているため、そのまま変換する。
    return marked(suggestionsText.value);
  }
  return '';
});

// 購入履歴を登録する関数
async function addPurchase() {
  // バリデーション: ユーザーと商品が選択されているか確認
  if (selectedUserId.value === null || selectedProductId.value === null) {
      alert('ユーザー名と商品名を候補から選択してください。');
      return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/purchase/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          user_id: selectedUserId.value, // 変更
          product_id: selectedProductId.value, // 変更
          purchase_date: newPurchase.purchaseDate,
          // quantity: newPurchase.quantity // 削除
      }),
    });
    if (!response.ok) {
      let errorDetail = response.statusText; // デフォルトのエラーメッセージ
      try {
          const errorData = await response.json();
          // FastAPIのHTTPExceptionのdetailを取得しようと試みる
          if (errorData && errorData.detail) {
              // detailがオブジェクトや配列の場合もあるため、文字列化する
              errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
          }
      } catch (jsonError) {
          // JSONパースに失敗した場合 (バックエンドがJSONを返さなかった場合など)
          console.error("Failed to parse error response as JSON:", jsonError);
      }
      // 詳細なエラーメッセージを投げる
      throw new Error(errorDetail);
    }
    // 登録成功したらフォームをリセット（任意）
    newPurchase.productId = null;
    // newPurchase.purchaseDate = new Date().toISOString().split('T')[0];
    newPurchase.quantity = 1;
    // 履歴を再取得して表示を更新
    fetchHistory();
    alert('購入履歴を登録しました。');
  } catch (error) {
    console.error('購入履歴登録エラー:', error);
    // catchしたエラーメッセージ (throw new Error(errorDetail) で投げたもの) を表示
    alert(`購入履歴の登録に失敗しました: ${error.message}`);
  }
}

// 購入履歴を取得する関数
async function fetchHistory() {
    if (!displayUserId.value) {
        historyList.value = []; // ユーザーIDがなければ空にする
        return;
    }
  try {
    const response = await fetch(`${API_BASE_URL}/history/${displayUserId.value}`);
    if (!response.ok) {
      const errorData = await response.json();
      // ユーザーが見つからない場合はエラーメッセージを表示してリストを空にする
      if (response.status === 404) {
          console.warn(`ユーザーID ${displayUserId.value} の履歴は見つかりませんでした。`);
          historyList.value = [];
          return; // ここで処理を終了
      }
      throw new Error(`購入履歴の取得に失敗しました: ${errorData.detail || response.statusText}`);
    }
    historyList.value = await response.json();
  } catch (error) {
    console.error('購入履歴取得エラー:', error);
    historyList.value = []; // エラー時はリストを空にする
    alert(`履歴の取得中にエラーが発生しました: ${error.message}`);
  }
}

// AIからの提案を取得する関数
async function fetchSuggestions() {
  if (!displayUserId.value) {
    suggestionsText.value = '';
    return;
  }
  loadingSuggestions.value = true; // ローディング開始
  suggestionsText.value = ''; // 前回の提案をクリア
  try {
    const response = await fetch(`${API_BASE_URL}/suggest/${displayUserId.value}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`提案の取得に失敗しました: ${errorData.detail || response.statusText}`);
    }
    const data = await response.json();
    suggestionsText.value = data.suggestions_text;
  } catch (error) {
    console.error('提案取得エラー:', error);
    alert(`提案の取得中にエラーが発生しました: ${error.message}`);
    suggestionsText.value = '提案の取得に失敗しました。';
  } finally {
    loadingSuggestions.value = false; // ローディング終了
  }
}

// コンポーネントがマウントされたときに最初の履歴を取得
onMounted(() => {
  fetchHistory();
  // 最初の提案も取得する場合はコメント解除
  // fetchSuggestions();
  // テスト用にユーザーと商品を作成 (初回のみ or 必要に応じて)
  // createTestData(); // 必要であればこの関数を実装
});

// --- オートコンプリート用関数 ---

// ユーザー名検索 (購入履歴登録用)
async function searchUsersForPurchase() {
  // 履歴表示用の候補もクリアしておく
  displayUserSuggestions.value = [];

  if (userNameInput.value.length < 1) { // 1文字以上入力されたら検索
    userSuggestions.value = [];
    // 以前選択したIDは保持する（入力クリアしても選択状態は維持）
    // selectedUserId.value = null;
    showCreateUserButton.value = false; // 候補がないので新規作成ボタンも非表示
    return;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/users/search?q=${encodeURIComponent(userNameInput.value)}`);
    if (!response.ok) {
      throw new Error('ユーザー検索APIの呼び出しに失敗しました。');
    }
    userSuggestions.value = await response.json();
    // 検索結果が空で入力がある場合、新規作成ボタンを表示
    showCreateUserButton.value = userNameInput.value.length > 0 && userSuggestions.value.length === 0;
  } catch (error) {
    console.error("ユーザー検索エラー:", error);
    userSuggestions.value = []; // エラー時は候補をクリア
    showCreateUserButton.value = userNameInput.value.length > 0; // エラー時も入力があれば表示
  }
}

// ユーザー名検索 (履歴表示用)
async function searchUsersForDisplay() {
  // 購入履歴登録用の候補もクリアしておく
  userSuggestions.value = [];
  showCreateUserButton.value = false; // こちらでは新規作成はしない

  if (displayUserNameInput.value.length < 1) {
    displayUserSuggestions.value = [];
    // 以前選択したIDは保持する
    // displayUserId.value = null;
    return;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/users/search?q=${encodeURIComponent(displayUserNameInput.value)}`);
    if (!response.ok) {
      throw new Error('ユーザー検索APIの呼び出しに失敗しました。');
    }
    displayUserSuggestions.value = await response.json();
  } catch (error) {
    console.error("ユーザー検索エラー:", error);
    displayUserSuggestions.value = [];
  }
}


// 商品名検索
async function searchProducts() {
  if (productNameInput.value.length < 1) { // 1文字以上入力されたら検索
    productSuggestions.value = [];
    selectedProductId.value = null; // 入力が空になったら選択も解除
    return;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/products/search?q=${encodeURIComponent(productNameInput.value)}`);
    if (!response.ok) {
      throw new Error('商品検索APIの呼び出しに失敗しました。');
    }
    productSuggestions.value = await response.json();
    // 検索結果が空で入力がある場合、新規作成ボタンを表示
    showCreateProductButton.value = productNameInput.value.length > 0 && productSuggestions.value.length === 0;
  } catch (error) {
    console.error("商品検索エラー:", error);
    productSuggestions.value = []; // エラー時は候補をクリア
    showCreateProductButton.value = productNameInput.value.length > 0; // エラー時も入力があれば表示
  }
}

// ユーザー候補選択 (購入履歴登録用)
function selectUserForPurchase(user) {
  userNameInput.value = user.name;
  selectedUserId.value = user.id;
  userSuggestions.value = []; // 候補リストを閉じる
  showCreateUserButton.value = false; // 選択したら新規作成ボタンは非表示
}

// ユーザー候補選択 (履歴表示用)
function selectUserForDisplay(user) {
    displayUserNameInput.value = user.name;
    displayUserId.value = user.id; // 表示対象のIDを更新
    displayUserSuggestions.value = []; // 候補リストを閉じる
    // fetchHistory(); // watch に移動
    // fetchSuggestions(); // watch に移動
}

// displayUserIdが変更されたら履歴を再取得
watch(displayUserId, (newUserId, oldUserId) => {
    // IDが実際に変更され、nullでない場合に実行
    if (newUserId !== oldUserId && newUserId !== null) {
        fetchHistory();
        // fetchSuggestions(); // ボタンクリック時のみ実行するため削除
    } else if (newUserId === null) {
        // IDがnullになったら表示をクリア (手動で入力欄を空にした場合など)
        historyList.value = [];
        suggestionsText.value = '';
    }
});

// 商品候補選択
function selectProduct(product) {
  productNameInput.value = product.name;
  selectedProductId.value = product.id;
  productSuggestions.value = []; // 候補リストを閉じる
  showCreateProductButton.value = false; // 選択したら新規作成ボタンは非表示
}

// 新規ユーザー作成
async function createUser() {
  if (!userNameInput.value) return;
  try {
    const response = await fetch(`${API_BASE_URL}/users/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: userNameInput.value })
    });
    if (!response.ok) {
      const errorData = await response.json();
      // 既に登録されている場合などはエラーメッセージを表示
      throw new Error(errorData.detail || response.statusText);
    }
    const newUser = await response.json();
    alert(`ユーザー「${newUser.name}」を新規作成しました。`);
    selectUserForPurchase(newUser); // 作成したユーザーを選択状態にする // 関数名を変更
    showCreateUserButton.value = false; // ボタンを非表示に
  } catch (error) {
    console.error("ユーザー作成エラー:", error);
    alert(`ユーザーの作成に失敗しました: ${error.message}`);
  }
}

// 新規商品作成
async function createProduct() {
    if (!productNameInput.value) return;
    // 簡単のためカテゴリなどは空で登録（必要なら入力欄を追加）
    const newProductData = { name: productNameInput.value };
    try {
        const response = await fetch(`${API_BASE_URL}/products/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newProductData)
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || response.statusText);
        }
        const newProduct = await response.json();
        alert(`商品「${newProduct.name}」を新規作成しました。`);
        selectProduct(newProduct); // 作成した商品を選択状態にする
        showCreateProductButton.value = false; // ボタンを非表示に
    } catch (error) {
        console.error("商品作成エラー:", error);
        alert(`商品の作成に失敗しました: ${error.message}`);
    }
}


// (任意) テストデータ作成関数
async function createTestData() {
    try {
        // ユーザー1を作成 (存在しない場合のみ)
        await fetch(`${API_BASE_URL}/users/`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: "テストユーザー1" })
        });
        // 商品1を作成 (存在しない場合のみ)
        await fetch(`${API_BASE_URL}/products/`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: "テスト商品A", category: "食品", seasonality: "通年" })
        });
        await fetch(`${API_BASE_URL}/products/`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: "テスト商品B", category: "飲料", seasonality: "夏" })
        });
    } catch(e) {
        // 既に存在する場合などのエラーは無視
        console.warn("テストデータの作成中にエラーが発生しましたが、無視します:", e);
    }
}

</script>

<style scoped>
/* スタイルを追加 */
.autocomplete-container {
  position: relative; /* 候補リストの位置基準 */
  margin-bottom: 1rem; /* 下の要素との間隔 */
}
.suggestions-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
  border: 1px solid #ccc;
  border-top: none;
  position: absolute; /* 入力欄の下に表示 */
  width: calc(100% - 2px); /* ボーダー分引く */
  background-color: white;
  z-index: 10; /* 他の要素より手前に表示 */
  max-height: 150px; /* スクロール表示 */
  overflow-y: auto;
}
.suggestions-list li {
  padding: 0.5rem;
  cursor: pointer;
}
.suggestions-list li:hover {
  background-color: #f0f0f0;
}

hr {
  margin: 2rem 0;
}
.suggestions {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 4px;
  white-space: pre-wrap; /* 改行をそのまま表示 */
  word-wrap: break-word; /* 長い単語で折り返し */
}
/* 提案エリア内の要素の余白を調整 */
.suggestions :deep(p),
.suggestions :deep(ul),
.suggestions :deep(li) {
  margin-top: 0.2em;
  margin-bottom: 0.2em;
  line-height: 1.0; /* 行の高さを少し詰める */
}
.suggestions :deep(ul) {
    padding-left: 1.5em; /* リストのインデント調整 */
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

header {
  line-height: 1.5;
  background-color: #f0f0f0;
  padding: 1rem;
  text-align: center;
}

main {
  padding: 1rem;
}

h1 {
  font-size: 1.5rem;
  font-weight: bold;
}
</style>
