import os
# from openai import OpenAI # 不要
from anthropic import Anthropic, APIError # Anthropicをインポート
from typing import List, Dict, Any

# APIキーを環境変数から読み込む (Anthropic用に変更)
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print(
        "警告: 環境変数 ANTHROPIC_API_KEY が設定されていません。LLM連携機能は動作しません。"
    )
    # client = None # clientの初期化は後で行う
else:
    # client = OpenAI(api_key=api_key) # OpenAIクライアントは不要になる
    pass # キーが存在することを確認

# Anthropicクライアントを初期化
if api_key:
    client = Anthropic(api_key=api_key)
else:
    client = None


def generate_suggestions(
    prompt: str, model: str = "claude-3-7-sonnet-20250219", max_tokens: int = 1000 # モデル名を変更
) -> str:
    """
    指定されたプロンプトを使用して Anthropic Claude から提案を生成する。

    Args:
        prompt (str): LLMに渡すプロンプト文字列。
        model (str): 使用するLLMモデル。
        max_tokens (int): 生成する最大トークン数。

    Returns:
        str: LLMによって生成された提案テキスト。エラー時は空文字列を返す。
    """
    if not client:
        print("エラー: Anthropicクライアントが初期化されていません。ANTHROPIC_API_KEYを確認してください。")
        return ""

    # システムプロンプトを定義 (Anthropic APIでは別パラメータで渡す)
    system_prompt = """あなたは買い物アドバイザーです。ユーザーの購入履歴と季節に基づいて、スーパーマーケットで購入すべき商品を提案してください。
頻繁に購入される商品、たまに買われる商品、普段買わない新しい発見があるような商品を、大体7:2:1の割合で含めてください。
提案は商品名を箇条書きで15個ほど列挙してください。それらを提案した理由は不要です。
ユーザーに季節を指定された場合は、季節にちなんだ商品を1~2個含めてください。
また最後に、提案した商品を使用した献立を2~3個ほど出力してください。
出力はマークダウン形式にしてください。
"""

    try:
        # Anthropic API呼び出しに変更
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.7,
            system=system_prompt, # systemプロンプトを指定
            messages=[
                {
                    "role": "user",
                    "content": prompt # ユーザープロンプトのみをmessagesに渡す
                }
            ]
        )
        # レスポンスからテキストを取得 (構造が異なる)
        suggestion_text = ""
        if message.content and isinstance(message.content, list) and len(message.content) > 0:
            # contentがブロックのリストになっている場合があるため最初のtextブロックを取得
            first_text_block = next((block.text for block in message.content if hasattr(block, 'text')), None)
            if first_text_block:
                suggestion_text = first_text_block.strip()

        # suggestion_text = message.content[0].text.strip() # よりシンプルな想定の場合
        return suggestion_text
    except APIError as e:
        # AnthropicのAPIエラーを捕捉
        print(f"Anthropic APIエラーが発生しました: {e.status_code} - {e.message}")
        return ""
    except Exception as e:
        print(f"Anthropic API呼び出し中に予期せぬエラーが発生しました: {e}")
        return ""


def format_purchase_history_for_prompt(history: List[Dict[str, Any]]) -> str:
    """
    購入履歴リストをLLMプロンプト用の文字列に整形する。
    (この関数は改善の余地あり。より詳細な情報を含めるなど)
    """
    if not history:
        return "購入履歴はありません。"

    formatted_list = []
    for item in history:
        # product情報が必要な場合は、history取得時にJOINするなどして追加する必要がある -> 済
        # 商品IDの代わりに商品名を使用
        # 辞書アクセスに変更: item.key -> item['key']
        product_name = item.get("product", {}).get(
            "name", "不明な商品"
        )  # productキーやnameキーが存在しない場合に備える
        formatted_list.append(
            f"- {product_name}, 購入日: {item['purchase_date']}"
        )  # 商品IDを商品名に変更、数量は削除済み

    # 直近の履歴に絞るなどの工夫も可能
    recent_history = formatted_list[:20]  # 例: 直近20件

    return "最近の購入履歴:\n" + "\n".join(recent_history)

# --- テスト用コード削除 ---
# (必要であればAnthropic用に書き直す)
