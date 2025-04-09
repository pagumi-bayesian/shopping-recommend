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
      <!-- 新規登録モードのタイトルは環境変数で制御しない（ログイン/新規登録の表示は維持） -->
      <h2>{{ isLoginMode ? 'ログイン' : '新規登録' }}</h2>
      <!-- フォームはログインモード、または新規登録許可時のみ表示 -->
      <form v-if="isLoginMode || allowSignup" @submit.prevent="isLoginMode ? signIn() : signUp()">
        <div>
          <label for="email">メールアドレス:</label>
          <input type="email" id="email" v-model="email" required>
        </div>
        <div>
          <label for="password">パスワード:</label>
          <input type="password" id="password" v-model="password" required>
        </div>
        <!-- 送信ボタンのテキストはモードに応じて変更 -->
        <button type="submit">{{ isLoginMode ? 'ログイン' : '新規登録' }}</button>
        <p v-if="authError" class="error">{{ authError }}</p>
      </form>
      <!-- 新規登録が許可されていない場合、ログインフォームのみ表示 -->
      <p v-if="!isLoginMode && !allowSignup" class="info">
        現在、新規ユーザー登録は受け付けていません。
      </p>
      <!-- モード切り替えボタンは新規登録許可時のみ表示 -->
      <button v-if="allowSignup" @click="isLoginMode = !isLoginMode" class="toggle-mode">
        {{ isLoginMode ? '新規登録はこちら' : 'ログインはこちら' }}
      </button>
      <!-- デバッグ用: allowSignup と isLoginMode の値を表示 -->
      <!-- <p>Debug: allowSignup={{ allowSignup }}, isLoginMode={{ isLoginMode }}</p> -->
    </div>

    <!-- メインコンテンツ (ログイン時) -->
    <div v-if="user">
      <!-- アプリケーション全体で使用するユーザー選択 -->
      <div class="app-user-select autocomplete-container">
        <h2>対象ユーザー選択</h2>
        <label for="appUserName">ユーザー名:</label>
        <input type="text" id="appUserName" v-model="appUserNameInput" @input="searchUsersForApp" placeholder="操作対象のユーザー名..." autocomplete="off">
        <ul v-if="appUserSuggestions.length > 0" class="suggestions-list">
          <li v-for="u in appUserSuggestions" :key="u.id" @click="selectUserForApp(u)">
            {{ u.name }}
          </li>
        </ul>
         <button type="button" v-if="showCreateAppUserButton" @click="createAppUser">
            「{{ appUserNameInput }}」を新規作成
         </button>
         <p v-if="appSelectedUserId">選択中のユーザー: {{ appUserNameInput }} (ID: {{ appSelectedUserId }})</p>
         <p v-else>ユーザーを選択してください。</p>
      </div>

      <hr>

      <!-- 購入履歴登録 (ユーザー選択を削除) -->
      <h2>購入履歴登録</h2>
      <form @submit.prevent="addPurchase">
        <!-- ユーザー選択部分は削除 -->
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

      <h2>購入履歴 (ユーザー: {{ appUserNameInput || '未選択' }})</h2>
      <!-- ユーザー選択部分は削除 -->
      <table v-if="paginatedHistory.length > 0" class="history-table">
        <thead>
          <tr>
            <th>購入日</th>
            <th>商品名</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in paginatedHistory" :key="item.id">
            <td>{{ item.purchase_date }}</td>
            <td>{{ item.product?.name || '商品名不明' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else>購入履歴はありません。</p>

      <!-- ページネーションコントロール -->
      <div class="pagination" v-if="totalPages > 1">
        <button @click="prevPage" :disabled="currentPage === 1">前へ</button>
        <span>ページ {{ currentPage }} / {{ totalPages }}</span>
        <button @click="nextPage" :disabled="currentPage === totalPages">次へ</button>
      </div>

      <hr>

      <h2>AIからの提案 (ユーザー: {{ appUserNameInput || '未選択' }})</h2>
      <button @click="fetchSuggestions" :disabled="loadingSuggestions || !appSelectedUserId">
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
// 環境変数から新規登録の許可フラグを取得 (文字列 'true' と比較)
const allowSignup = computed(() => import.meta.env.VITE_ALLOW_SIGNUP === 'true');

// --- Existing State ---
const API_BASE_URL = 'https://shopping-app-backend-981489163354.asia-northeast1.run.app';
const newPurchase = reactive({
  purchaseDate: new Date().toISOString().split('T')[0],
});
// const userNameInput = ref(''); // 削除 -> appUserNameInput へ統合
// const selectedUserId = ref(null); // 削除 -> appSelectedUserId へ統合
const appUserNameInput = ref(''); // アプリ全体で使用するユーザー名入力
const appSelectedUserId = ref(null); // アプリ全体で選択されたユーザーID
const appUserSuggestions = ref([]); // アプリ全体のユーザー候補
const showCreateAppUserButton = ref(false); // アプリ全体の新規ユーザー作成ボタン表示フラグ
const productNameInput = ref('');
const selectedProductId = ref(null);
const productSuggestions = ref([]);
// const userSuggestions = ref([]); // 削除 -> appUserSuggestions へ統合
// const showCreateUserButton = ref(false); // 削除 -> showCreateAppUserButton へ統合
const showCreateProductButton = ref(false);
// const displayUserNameInput = ref(''); // 削除 -> appUserNameInput へ統合
// const displayUserSuggestions = ref([]); // 削除 -> appUserSuggestions へ統合
const historyList = ref([]);
// const displayUserId = ref(null); // 削除 -> appSelectedUserId へ統合
const suggestionsText = ref('');
const loadingSuggestions = ref(false);
const currentPage = ref(1); // ページネーション用: 現在のページ
const itemsPerPage = ref(10); // ページネーション用: 1ページあたりのアイテム数

// --- Computed Properties ---
// allowSignup を computed に移動
const renderedSuggestions = computed(() => {
  if (suggestionsText.value) {
    return marked(suggestionsText.value);
  }
  return '';
});

// ページネーションされた履歴リスト
const paginatedHistory = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  // historyList を日付で降順ソートしてからスライスする
  return historyList.value
    .slice() // 元の配列を変更しないようにコピー
    .sort((a, b) => new Date(b.purchase_date) - new Date(a.purchase_date)) // 日付で降順ソート
    .slice(start, end);
});

// 総ページ数
const totalPages = computed(() => {
  return Math.ceil(historyList.value.length / itemsPerPage.value);
});

// --- Firebase Auth Functions ---
const signUp = async () => {
  // 新規登録が許可されていない場合は処理を中断
  if (!allowSignup.value) {
      authError.value = '現在、新規ユーザー登録は受け付けていません。';
      return;
  }
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
    // displayUserNameInput.value = ''; // 削除
    // displayUserId.value = null; // 削除
    appUserNameInput.value = ''; // アプリユーザー選択もリセット
    appSelectedUserId.value = null;
    appUserSuggestions.value = [];
    showCreateAppUserButton.value = false;
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
  // アプリ全体でユーザーが選択されているか確認
  if (appSelectedUserId.value === null) {
      alert('操作対象のユーザーを選択してください。');
      return;
  }
  // 商品が選択されているか確認
  if (selectedProductId.value === null) {
      alert('商品名を候補から選択してください。');
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
          user_id: appSelectedUserId.value, // アプリで選択されたユーザーIDを使用
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
    // userNameInput.value = ''; // ユーザー入力はリセットしない
    // selectedUserId.value = null; // ユーザー選択はリセットしない
    productNameInput.value = '';
    selectedProductId.value = null;
    // 履歴を再取得
    fetchHistory();
    alert('購入履歴を登録しました。');
  } catch (error) {
    console.error('購入履歴登録エラー:', error);
    alert(`購入履歴の登録に失敗しました: ${error.message}`);
  }
}

async function fetchHistory() {
    // ログインしていない、または表示対象ユーザーが未選択なら何もしない
    // ログインしていない、またはアプリ全体でユーザーが未選択なら何もしない
    if (!user.value || !appSelectedUserId.value) {
        historyList.value = [];
        currentPage.value = 1; // ユーザー未選択時はページもリセット
        return;
    }
  try {
    // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
    const response = await fetch(`${API_BASE_URL}/history/${appSelectedUserId.value}`);
    if (!response.ok) {
      const errorData = await response.json();
      if (response.status === 404) {
          console.warn(`ユーザーID ${appSelectedUserId.value} の履歴は見つかりませんでした。`);
          historyList.value = [];
          currentPage.value = 1; // 履歴がない場合もページをリセット
          return;
      }
      throw new Error(`購入履歴の取得に失敗しました: ${errorData.detail || response.statusText}`);
    }
    historyList.value = await response.json();
  } catch (error) {
    console.error('購入履歴取得エラー:', error);
    historyList.value = [];
    currentPage.value = 1; // エラー時もページをリセット
    alert(`履歴の取得中にエラーが発生しました: ${error.message}`);
  }
}

async function fetchSuggestions() {
  // ログインしていない、または表示対象ユーザーが未選択なら何もしない
  // ログインしていない、またはアプリ全体でユーザーが未選択なら何もしない
  if (!user.value || !appSelectedUserId.value) {
    suggestionsText.value = '';
    return;
  }
  loadingSuggestions.value = true;
  suggestionsText.value = '';
  try {
    // TODO: APIリクエストにIDトークンを含める改修 (バックエンド保護時)
    const response = await fetch(`${API_BASE_URL}/suggest/${appSelectedUserId.value}`);
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

// --- Autocomplete Functions (Refactored for App-wide User Selection) ---

// アプリ全体で使用するユーザー名検索
async function searchUsersForApp() {
  if (!user.value) return; // ログイン時のみ
  if (appUserNameInput.value.length < 1) {
    appUserSuggestions.value = [];
    showCreateAppUserButton.value = false;
    // ユーザー名がクリアされたら選択も解除
    // appSelectedUserId.value = null; // 意図しない解除を防ぐためコメントアウト
    return;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/users/search?q=${encodeURIComponent(appUserNameInput.value)}`);
    if (!response.ok) {
      throw new Error('ユーザー検索APIの呼び出しに失敗しました。');
    }
    appUserSuggestions.value = await response.json();
    showCreateAppUserButton.value = appUserNameInput.value.length > 0 && appUserSuggestions.value.length === 0;
  } catch (error) {
    console.error("ユーザー検索エラー:", error);
    appUserSuggestions.value = [];
    showCreateAppUserButton.value = appUserNameInput.value.length > 0; // 検索失敗時も作成ボタンは表示
  }
}

// アプリ全体で使用するユーザー候補選択
function selectUserForApp(u) {
  appUserNameInput.value = u.name;
  appSelectedUserId.value = u.id;
  appUserSuggestions.value = [];
  showCreateAppUserButton.value = false;
  // ユーザー選択時に履歴と提案を更新 (watchでも実行されるが、即時反映のためここでも呼ぶ)
  // fetchHistory();
  // fetchSuggestions();
}

// アプリ全体で使用する新規ユーザー作成
async function createAppUser() {
  if (!user.value) return; // ログイン時のみ
  if (!appUserNameInput.value) return;
  try {
    const response = await fetch(`${API_BASE_URL}/users/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: appUserNameInput.value })
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || response.statusText);
    }
    const newUser = await response.json();
    alert(`ユーザー「${newUser.name}」を新規作成しました。`);
    selectUserForApp(newUser); // 作成したユーザーを選択状態にする
    showCreateAppUserButton.value = false;
  } catch (error) {
    console.error("ユーザー作成エラー:", error);
    alert(`ユーザーの作成に失敗しました: ${error.message}`);
  }
}

// ユーザー名検索 (購入履歴登録用) - 削除
// async function searchUsersForPurchase() { ... }
// ユーザー候補選択 (購入履歴登録用) - 削除
// function selectUserForPurchase(u) { ... }
// 新規ユーザー作成 (購入履歴登録用) - 削除
// async function createUser() { ... }

// ユーザー名検索 (履歴表示用) - 削除 (searchUsersForApp に統合)
// async function searchUsersForDisplay() { ... }

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

// ユーザー候補選択 (履歴表示用) - 削除 (selectUserForApp に統合)
// function selectUserForDisplay(u) { ... }

// 商品候補選択
function selectProduct(product) {
  productNameInput.value = product.name;
  selectedProductId.value = product.id;
  productSuggestions.value = [];
  showCreateProductButton.value = false;
}

// --- Pagination Functions ---
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
  }
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
      // displayUserId.value = null; // 削除
      // displayUserNameInput.value = ''; // 削除
      appUserNameInput.value = ''; // アプリユーザー選択もリセット
      appSelectedUserId.value = null;
      appUserSuggestions.value = [];
      showCreateAppUserButton.value = false;
      currentPage.value = 1; // ページもリセット
      // フォームもクリア（任意）
      productNameInput.value = '';
      selectedProductId.value = null;
      // userNameInput.value = ''; // 削除
      // selectedUserId.value = null; // 削除
      // userSuggestions.value = []; // 削除
      // showCreateUserButton.value = false; // 削除
      // userNameInput.value = ''; // 削除
      // selectedUserId.value = null; // 削除
      // userSuggestions.value = []; // 削除
      // showCreateUserButton.value = false; // 削除
      email.value = ''; // 認証フォームもクリア
      password.value = '';
      authError.value = '';
      isLoginMode.value = true; // ログアウト時はログインモードに戻す
    }
  });
  // fetchHistory(); // 初期表示は onAuthStateChanged 内で行うか、ユーザー選択を待つ
});

// アプリ全体で選択されたユーザーIDが変更されたら履歴と提案を再取得 (ログイン時のみ)
watch(appSelectedUserId, (newUserId) => {
  if (user.value && newUserId) {
    currentPage.value = 1; // ユーザー変更時に最初のページに戻る
    fetchHistory();
    fetchSuggestions(); // 提案も更新
  } else if (!newUserId) {
      // ユーザー選択がクリアされた場合も履歴と提案をクリアし、ページをリセット
      historyList.value = [];
      suggestionsText.value = '';
      currentPage.value = 1;
  }
});
</script>

<style>
/* --- Table and Pagination Styles --- */
.history-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1em;
}

.history-table th,
.history-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.history-table th {
  background-color: #f2f2f2;
}

.pagination {
  margin-top: 1em;
  display: flex;
  justify-content: center;
  align-items: center;
}

.pagination button {
  margin: 0 5px;
  padding: 5px 10px;
  cursor: pointer;
}

.pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.pagination span {
  margin: 0 10px;
}

/* --- Autocomplete Styles --- */
.autocomplete-container {
  position: relative;
  margin-bottom: 1em; /* Add some space below */
}

.suggestions-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border: 1px solid #ccc;
  position: absolute;
  background-color: white;
  width: calc(100% - 2px); /* Adjust width to match input */
  max-height: 150px;
  overflow-y: auto;
  z-index: 10; /* Ensure suggestions appear above other elements */
  box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* Optional: add shadow */
}

.suggestions-list li {
  padding: 8px 12px;
  cursor: pointer;
}

.suggestions-list li:hover {
  background-color: #f0f0f0;
}

/* --- General Styles --- */
body {
  font-family: sans-serif;
  padding: 20px;
  background-color: #f9f9f9;
}

header {
  background-color: #4CAF50;
  color: white;
  padding: 10px 20px;
  display: flex; /* Use flexbox for layout */
  justify-content: space-between; /* Space out title and user info */
  align-items: center; /* Vertically align items */
  margin-bottom: 20px;
}

header h1 {
  margin: 0; /* Remove default margin */
}

.user-info {
  display: flex;
  align-items: center;
}

.user-info span {
  margin-right: 10px;
}

main {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h2 {
  color: #333;
  border-bottom: 2px solid #4CAF50;
  padding-bottom: 5px;
  margin-top: 30px; /* Add space above headings */
}

form div {
  margin-bottom: 15px; /* Increase spacing between form elements */
}

label {
  display: block; /* Make labels take full width */
  margin-bottom: 5px;
  font-weight: bold;
}

input[type="text"],
input[type="date"],
input[type="email"], /* Style email/password inputs */
input[type="password"] {
  width: calc(100% - 22px); /* Adjust width to account for padding/border */
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

button {
  background-color: #4CAF50;
  color: white;
  padding: 10px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

button:hover {
  background-color: #45a049;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button[type="button"] { /* Style for non-submit buttons like create */
  background-color: #007bff; /* Blue color */
  margin-left: 10px; /* Add space next to input */
}
button[type="button"]:hover {
  background-color: #0056b3;
}

hr {
  border: 0;
  height: 1px;
  background-color: #eee;
  margin: 30px 0; /* Increase spacing around horizontal rules */
}

ul {
  list-style: none; /* Remove default bullets */
  padding: 0;
}

li {
  background-color: #f9f9f9; /* Light background for list items */
  margin-bottom: 8px; /* Space between items */
  padding: 10px;
  border-radius: 4px;
  border-left: 3px solid #4CAF50; /* Add a left border */
}

.suggestions {
  margin-top: 15px;
  padding: 15px;
  background-color: #e9f5e9; /* Light green background */
  border: 1px solid #c8e6c9; /* Green border */
  border-radius: 4px;
}

.suggestions p { /* Style paragraphs within suggestions */
  margin-bottom: 0.5em;
}
.suggestions ul { /* Style lists within suggestions */
  margin-top: 0.5em;
  padding-left: 20px; /* Indent list */
  list-style: disc; /* Use standard bullets */
}
.suggestions li { /* Reset background/border for list items inside suggestions */
  background-color: transparent;
  border: none;
  padding: 0;
  margin-bottom: 0.3em;
}

.auth-container {
  max-width: 400px;
  margin: 20px auto; /* Center the auth container */
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: #fff;
}

.toggle-mode {
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  margin-top: 10px;
  display: block; /* Make it a block element */
}
.toggle-mode:hover {
  color: #0056b3;
  background: none; /* Ensure no background on hover */
}

.error {
  color: red;
  margin-top: 10px;
}

.info {
  color: #666;
  margin-top: 10px;
  font-style: italic;
}
</style>
