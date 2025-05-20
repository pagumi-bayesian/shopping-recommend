import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
# from langchain_core.messages import SystemMessage, HumanMessage # ChatPromptTemplateを使うので直接は不要かも

LLM_PROVIDER = "OPENAI"
MAX_TOKENS = 1000

# LLMの初期化
def get_llm():
    if LLM_PROVIDER.lower() == "anthropic":
        model_name = "claude-3-7-sonnet-20250219"
        api_key = os.getenv("ANTHROPIC_API_KEY")
        return ChatAnthropic(model=model_name, api_key=api_key, max_tokens=MAX_TOKENS)
    elif LLM_PROVIDER.lower() == "openai":
        model_name = "gpt-4o-2024-08-06"
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(model=model_name, api_key=api_key, max_tokens=MAX_TOKENS)

def generate_suggestions(
    user_prompt: str, max_tokens: int = 1000 # 引数名とモデル名を変更 (最新の推奨モデル名を確認)
) -> str:
    """
    指定されたプロンプトを使用して Anthropic Claude から提案を生成する。

    Args:
        user_prompt (str): LLMに渡すユーザー固有のプロンプト部分（例: 購入履歴）。
        max_tokens (int): 生成する最大トークン数。

    Returns:
        str: LLMによって生成された提案テキスト。エラー時は空文字列を返す。
    """
    llm = get_llm()  # LLMを初期化

    # システムプロンプトを定義 (Anthropic APIでは別パラメータで渡す)
    # --- LangChain プロンプトテンプレートの定義 ---
    system_template = """あなたは**食品スーパーで購入する商品をユーザーに提案するアシスタント**です。

ユーザーから過去に購入した食品の履歴を受け取ります。
あなたの役割は、ユーザーの購入履歴を分析して、次回の買い物で購入するとよい食品を推薦することです。

## 提案する際のポイント：
    - 週に1回の購入頻度に合った食品を提案してください。
    - 過去の購入傾向や購入履歴を考慮してください。
    - 季節や旬の食材なども考慮してください。
    - 提案する商品は15品ほどにしてください。
    - 献立（料理）として使いやすい商品を優先的に提案してください。
    - 健康的で栄養バランスを考えた食品を含めてください。
    - 提案する食品に基づいた簡単な献立（料理）を2〜3品併せて提案してください。

提案の形式は以下のようなマークダウン形式にしてください。
ただし、出力には前置きやMarkdownのコードブロックマーカー（例: ```markdown）は一切含めないでください。
```markdown
## 【提案商品】
- 商品名
- 商品名
- 商品名
（…商品を15個ほど列挙…）

## 【提案商品を使った献立例】

- **献立名1**
    - 使用する提案商品、簡単な調理方法や特徴
- **献立名2**
    - 使用する提案商品、簡単な調理方法や特徴
- **献立名3**
    - 使用する提案商品、簡単な調理方法や特徴
```
"""
    human_template = "{user_history_prompt}" # ユーザー履歴は変数として渡す

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    # -----------------------------------------

    # --- LangChain チェーンの定義と実行 ---
    output_parser = StrOutputParser()
    chain = chat_prompt | llm | output_parser

    try:
        # チェーンを実行し、ユーザープロンプトを渡す
        suggestion_text = chain.invoke({"user_history_prompt": user_prompt})
        return suggestion_text.strip()

    # except APIError as e: # LangChainは独自の例外を発生させる可能性がある
    #     print(f"Anthropic APIエラーが発生しました (LangChain経由): {e}") # エラーの詳細を確認
    #     return ""
    except Exception as e:
        # LangChain実行中の一般的なエラーを捕捉
        print(f"LangChain実行中に予期せぬエラーが発生しました: {e}")
        # エラーの詳細（トレースバックなど）を出力するとデバッグに役立つ
        import traceback
        traceback.print_exc()
        return ""
    # ------------------------------------


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

    recent_history = formatted_list

    return "最近の購入履歴:\n" + "\n".join(recent_history)

# --- テスト用コード削除 ---
# (必要であればAnthropic用に書き直す)
