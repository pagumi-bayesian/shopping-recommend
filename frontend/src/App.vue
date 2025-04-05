<template>
  <header>
    <h1>買い物提案アプリ</h1>
    <!-- ログイン情報表示とログアウトボタン -->
    <div v-if="user" class="user-info">
      <span>{{ user.email }} でログイン中</span>
      <button @click="logOut">ログアウト</button>
    </div>
  </header>

  <main>
    <!-- ログイン/新規登録フォーム (未ログイン時) -->
    <div v-if="!user" class="auth-container">
      <h2>{{ isLoginMode ? 'ログイン' : '新規登録' }}</h2>
      <form @submit.prevent="isLoginMode ? signIn() : signUp()">
        <div>
          <label for="email">メールアドレス:</label>
          <input type="email" id="email" v-model="email" required>
        </div>
        <div>
          <label for="password">パスワード:</label>
          <input type="password" id="password" v-model="password" required>
        </div>
        <button type="submit">{{ isLoginMode ? 'ログイン' : '新規登録' }}</button>
        <p v-if="authError" class="error">{{ authError }}</p>
      </form>
      <button @click="isLoginMode = !isLoginMode" class="toggle-mode">
        {{ isLoginMode ? '新規登録はこちら' : 'ログインはこちら' }}
      </button>
    </div>

    <!-- メインコンテンツ (ログイン時) -->
    <div v-if="user">
      <h2>購入履歴登録</h2>
      <form @submit.prevent="addPurchase">
        <!-- ユーザー選択部分のコメントアウトを解除 -->
        <div class="autocomplete-container">
          <label for="userName">ユーザー名:</label>
          <input type="text" id="userName" v-model="userNameInput" @input="searchUsersForPurchase" placeholder="名前を入力..." required autocomplete="off">
          <ul v-if="userSuggestions.length > 0" class="suggestions-list">
            <li v-for="u in userSuggestions" :key="u.id" @click="selectUserForPurchase(u)"> <!-- u に変更 -->
              {{ u.name }}
            </li>
          </ul>
          <button type="button" v-if="showCreateUserButton" @click="createUser">
            「{{ userNameInput }}」を新規作成
          </button>
        </div>
        <!-- <p>ユーザー: {{ user.email }} (自動)</p> --> <!-- 削除 -->

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
        <button type="submit">登録</button>
      </form>

      <hr>

      <h2>購入履歴</h2> <!-- 見出し変更 -->
       <!-- 履歴表示のユーザー選択は一旦そのまま残す -->
      <div class="autocomplete-container">
          <label for="displayUserName">ユーザー名:</label>
          <input type="text" id="displayUserName" v-model="displayUserNameInput" @input="searchUsersForDisplay" placeholder="履歴を表示するユーザー名..." autocomplete="off">
          <ul v-if="displayUserSuggestions.length > 0" class="suggestions-list">
            <li v-for="u in displayUserSuggestions" :key="u.id" @click="selectUserForDisplay(u)">
              {{ u.name }}
            </li>
          </ul>
      </div>
      <ul v-if="historyList.length > 0">
        <li v-for="item in historyList" :key="item.id">
          {{ item.purchase_date }} - {{ item.product?.name || '商品名不明' }}
        </li>
      </ul>
      <p v-else>購入履歴はありません。</p>

      <hr>

      <h2>AIからの提案 (ユーザー: {{ displayUserNameInput || '未選択' }})</h2>
      <button @click="fetchSuggestions" :disabled="loadingSuggestions || !displayUserId">
        {{ loadingSuggestions ? '提案を取得中...' : '最新の提案を取得' }}
      </button>
      <div v-if="suggestionsText" class="suggestions" v-html="renderedSuggestions"></div>
      <p v-else>まだ提案はありません。「最新の提案を取得」ボタンを押してください。</p>
    </div>

  </main>
</template>

<script setup>
import { ref, onMounted, reactive, computed, watch } from 'vue';
import { marked } from 'marked';
// Firebase関連のインポート
import { auth } from './firebaseConfig'; // firebaseConfig.jsからauthをインポート
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from "firebase/auth";

// --- Firebase Auth State ---
const user = ref(null); // ログイン中のユーザー情報
const email = ref('');
const password = ref('');
const authError = ref('');
const isLoginMode = ref(true); // true: ログインモード, false: 新規登録モード

// --- Existing State ---
const API_BASE_URL = 'https://shopping-app-backend-981489163354.asia-northeast1.run.app';
const newPurchase = reactive({
  purchaseDate: new Date().toISOString().split('T')[0],
});
const userNameInput = ref(''); // コメントアウト解除
const selectedUserId = ref(null); // コメントアウト解除
const productNameInput = ref('');
const selectedProductId = ref(null);
const productSuggestions = ref([]);
const userSuggestions = ref([]); // コメントアウト解除
const showCreateUserButton = ref(false); // コメントアウト解除
const showCreateProductButton = ref(false);
const displayUserNameInput = ref(''); // 履歴表示用は残す
const displayUserSuggestions = ref([]); // 履歴表示用は残す
const historyList = ref([]);
const displayUserId = ref(null); // 初期値はnullに変更
const suggestionsText = ref('');
const loadingSuggestions = ref(false);

// --- Computed Properties ---
const renderedSuggestions = computed(() => {
  if (suggestionsText.value) {
    return marked(suggestionsText.value);
  }
  return '';
});

// --- Firebase Auth Functions ---
const signUp = async () => {
  authError.value = ''; // エラーをクリア
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email.value, password.value);
    console.log("Signed up:", userCredential.user);
    // user.value は onAuthStateChanged で更新される
    email.value = ''; // フォームクリア
    password.value = '';
  } catch (error) {
    console.error("Sign up error:", error.code, error.message);
    authError.value = `新規登録エラー: ${error.message}`;
  }
};

const signIn = async () => {
  authError.value = '';
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email.value, password.value);
    console.log("Signed in:", userCredential.user);
    // user.value は onAuthStateChanged で更新される
    email.value = '';
    password.value = '';
  } catch (error) {
    console.error("Sign in error:", error.code, error.message);
    authError.value = `ログインエラー: ${error.message}`;
  }
};

const logOut = async () => {
  try {
    await signOut(auth);
    console.log("Signed out");
    // user.value は onAuthStateChanged で更新される
    // ログアウト時に表示データもクリアする（任意）
    historyList.value = [];
    suggestionsText.value = '';
    displayUserNameInput.value = '';
    displayUserId.value = null;
  } catch (error) {
    console.error("Sign out error:", error);
    alert('ログアウト中にエラーが発生しました。');
  }
};

// --- Existing Functions (Modified) ---
async function addPurchase() {
  // ログインチェックは維持する
  const currentUser = auth.currentUser;
  if (!currentUser) {
      alert('ログインしていません。');
      return;
  }
  // ユーザーと商品が選択されているか確認 (元のバリデーションに戻す)
  if (selectedUserId.value === null || selectedProductId.value === null) {
      alert('ユーザー名と商品名を候補から選択してください。');
      return;
  }
  // const userIdToRegister = currentUser.email; // 削除

  try {
    // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
    // const idToken = await currentUser.getIdToken();
    const response = await fetch(`${API_BASE_URL}/purchase/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 'Authorization': `Bearer ${idToken}` // バックエンド保護時に追加
      },
      body: JSON.stringify({
          user_id: selectedUserId.value, // 選択されたユーザーIDに戻す
          product_id: selectedProductId.value,
          purchase_date: newPurchase.purchaseDate,
      }),
    });
    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
          const errorData = await response.json();
          if (errorData && errorData.detail) {
              errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
          }
      } catch (jsonError) {
          console.error("Failed to parse error response as JSON:", jsonError);
      }
      throw new Error(errorDetail);
    }
    // フォームリセット調整 (ユーザー関連も追加)
    userNameInput.value = '';
    selectedUserId.value = null;
    productNameInput.value = '';
    selectedProductId.value = null;
    // 履歴を再取得 (表示中のユーザーが変わらない限り不要かも)
    // fetchHistory();
    alert('購入履歴を登録しました。');
  } catch (error) {
    console.error('購入履歴登録エラー:', error);
    alert(`購入履歴の登録に失敗しました: ${error.message}`);
  }
}

async function fetchHistory() {
    // ログインしていない、または表示対象ユーザーが未選択なら何もしない
    if (!user.value || !displayUserId.value) {
        historyList.value = [];
        return;
    }
  try {
    // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
    const response = await fetch(`${API_BASE_URL}/history/${displayUserId.value}`);
    if (!response.ok) {
      const errorData = await response.json();
      if (response.status === 404) {
          console.warn(`ユーザーID ${displayUserId.value} の履歴は見つかりませんでした。`);
          historyList.value = [];
          return;
      }
      throw new Error(`購入履歴の取得に失敗しました: ${errorData.detail || response.statusText}`);
    }
    historyList.value = await response.json();
  } catch (error) {
    console.error('購入履歴取得エラー:', error);
    historyList.value = [];
    alert(`履歴の取得中にエラーが発生しました: ${error.message}`);
  }
}

async function fetchSuggestions() {
  // ログインしていない、または表示対象ユーザーが未選択なら何もしない
  if (!user.value || !displayUserId.value) {
    suggestionsText.value = '';
    return;
  }
  loadingSuggestions.value = true;
  suggestionsText.value = '';
  try {
    // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
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
    loadingSuggestions.value = false;
  }
}

// --- Autocomplete Functions ---
// ユーザー名検索 (購入履歴登録用) - コメントアウト解除
async function searchUsersForPurchase() {
  // ログインチェックは不要 (任意のユーザーとして登録するため)
  // if (!user.value) return;
  if (userNameInput.value.length < 1) {
    userSuggestions.value = [];
    showCreateUserButton.value = false;
    return;
  }
  try {
    // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
    const response = await fetch(`${API_BASE_URL}/users/search?q=${encodeURIComponent(userNameInput.value)}`);
    if (!response.ok) {
      throw new Error('ユーザー検索APIの呼び出しに失敗しました。');
    }
    userSuggestions.value = await response.json();
    showCreateUserButton.value = userNameInput.value.length > 0 && userSuggestions.value.length === 0;
  } catch (error) {
    console.error("ユーザー検索エラー:", error);
    userSuggestions.value = [];
    showCreateUserButton.value = userNameInput.value.length > 0;
  }
}
// ユーザー候補選択 (購入履歴登録用) - コメントアウト解除
function selectUserForPurchase(u) { // user -> u に変更
  userNameInput.value = u.name;
  selectedUserId.value = u.id;
  userSuggestions.value = [];
  showCreateUserButton.value = false;
}
// 新規ユーザー作成 (購入履歴登録用) - コメントアウト解除
async function createUser() {
  // ログインチェックは不要
  // if (!user.value) return;
  if (!userNameInput.value) return;
  try {
    // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
    const response = await fetch(`${API_BASE_URL}/users/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: userNameInput.value })
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || response.statusText);
    }
    const newUser = await response.json();
    alert(`ユーザー「${newUser.name}」を新規作成しました。`);
    selectUserForPurchase(newUser); // 作成したユーザーを選択状態にする
    showCreateUserButton.value = false;
  } catch (error) {
    console.error("ユーザー作成エラー:", error);
    alert(`ユーザーの作成に失敗しました: ${error.message}`);
  }
}

// ユーザー名検索 (履歴表示用)
async function searchUsersForDisplay() {
    if (!user.value) return; // ログイン時のみ検索
    if (displayUserNameInput.value.length < 1) {
      displayUserSuggestions.value = [];
      return;
    }
    try {
      // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
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
    if (!user.value) return; // ログイン時のみ検索
     if (productNameInput.value.length < 1) {
       productSuggestions.value = [];
       selectedProductId.value = null;
       showCreateProductButton.value = false; // ボタンも非表示に
       return;
     }
     try {
       // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
       const response = await fetch(`${API_BASE_URL}/products/search?q=${encodeURIComponent(productNameInput.value)}`);
       if (!response.ok) {
         throw new Error('商品検索APIの呼び出しに失敗しました。');
       }
       productSuggestions.value = await response.json();
       showCreateProductButton.value = productNameInput.value.length > 0 && productSuggestions.value.length === 0;
     } catch (error) {
       console.error("商品検索エラー:", error);
       productSuggestions.value = [];
       showCreateProductButton.value = productNameInput.value.length > 0;
     }
}
// 新規商品作成
async function createProduct() {
    if (!user.value) return; // ログイン時のみ
     if (!productNameInput.value) return;
     const newProductData = { name: productNameInput.value };
     try {
       // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
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
       selectProduct(newProduct);
       showCreateProductButton.value = false;
     } catch (error) {
       console.error("商品作成エラー:", error);
       alert(`商品の作成に失敗しました: ${error.message}`);
     }
}

// ユーザー候補選択 (履歴表示用)
function selectUserForDisplay(u) {
    displayUserNameInput.value = u.name;
    displayUserId.value = u.id;
    displayUserSuggestions.value = [];
    // fetchHistory(); // watch で実行される
}

// 商品候補選択
function selectProduct(product) {
  productNameInput.value = product.name;
  selectedProductId.value = product.id;
  productSuggestions.value = [];
  showCreateProductButton.value = false;
}


// --- Lifecycle Hooks ---
onMounted(() => {
  // ログイン状態の変化を監視
  onAuthStateChanged(auth, (currentUser) => {
    user.value = currentUser; // ユーザー状態を更新
    if (currentUser) {
      console.log("User is logged in:", currentUser.email);
      // ログインしたらエラーメッセージをクリア
      authError.value = '';
      // ログイン時にデフォルトの履歴を表示する (任意)
      // displayUserId.value = 1; // または currentUser.uid に対応するDBのIDなど
      // fetchHistory(); // watch で displayUserId 変更時に実行される
    } else {
      console.log("User is logged out");
      // ログアウトしたら関連データをクリア
      historyList.value = [];
      suggestionsText.value = '';
      displayUserId.value = null;
      displayUserNameInput.value = '';
      // フォームもクリア（任意）
      productNameInput.value = '';
      selectedProductId.value = null;
      userNameInput.value = ''; // ユーザー選択フォームもクリア
      selectedUserId.value = null;
      userSuggestions.value = [];
      showCreateUserButton.value = false;
      email.value = ''; // 認証フォームもクリア
      password.value = '';
      authError.value = '';
    }
  });
  // fetchHistory(); // 初期表示は onAuthStateChanged 内で行うか、ユーザー選択を待つ
});

// displayUserIdが変更されたら履歴を再取得 (ログイン時のみ)
watch(displayUserId, (newUserId, oldUserId) => {
    if (user.value && newUserId !== oldUserId && newUserId !== null) {
        fetchHistory();
        // 提案もクリアしておく（任意）
        suggestionsText.value = '';
    } else if (newUserId === null) {
        historyList.value = [];
        suggestionsText.value = '';
    }
});

</script>

<style scoped>
/* スタイルを追加 */
.auth-container {
  max-width: 400px;
  margin: 2rem auto;
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 8px;
}
.auth-container h2 {
  text-align: center;
  margin-bottom: 1rem;
}
.auth-container form div {
  margin-bottom: 0.5rem;
}
.auth-container label {
  display: block;
  margin-bottom: 0.2rem;
}
.auth-container input {
  width: 100%;
  padding: 0.5rem;
  box-sizing: border-box;
}
.auth-container button[type="submit"] {
  width: 100%;
  padding: 0.7rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 1rem;
}
.auth-container button[type="submit"]:hover {
  background-color: #0056b3;
}
.auth-container .toggle-mode {
  background: none;
  border: none;
  color: #007bff;
  text-decoration: underline;
  cursor: pointer;
  display: block;
  margin-top: 1rem;
  text-align: center;
}
.auth-container .error {
  color: red;
  margin-top: 1rem;
  text-align: center;
}

.user-info {
  text-align: right;
  padding: 0.5rem 1rem;
  background-color: #e9ecef;
}
.user-info span {
  margin-right: 1rem;
}

/* 既存のスタイル */
.autocomplete-container {
  position: relative;
  margin-bottom: 1rem;
}
.suggestions-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
  border: 1px solid #ccc;
  border-top: none;
  position: absolute;
  width: calc(100% - 2px);
  background-color: white;
  z-index: 10;
  max-height: 150px;
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
  white-space: pre-wrap;
  word-wrap: break-word;
}
.suggestions :deep(p),
.suggestions :deep(ul),
.suggestions :deep(li) {
  margin-top: 0.2em;
  margin-bottom: 0.2em;
  line-height: 1.0;
}
.suggestions :deep(ul) {
    padding-left: 1.5em;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
header {
  line-height: 1.5;
  background-color: #f0f0f0;
  padding: 0; /* user-infoのために調整 */
  /* text-align: center; */ /* 中央揃え解除 */
}
header h1 {
    padding: 1rem;
    text-align: center;
    margin: 0;
}
main {
  padding: 1rem;
}
h1 {
  font-size: 1.5rem;
  font-weight: bold;
}
</style>
