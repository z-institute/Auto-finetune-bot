import os
import json
import time
import openai
import textwrap
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction

load_dotenv()

app = Flask(__name__)

# Replace with your Channel Access Token
line_bot_api = LineBotApi(os.environ['LINE_ACCESS_TOKEN'])

# Replace with your Channel Secret
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

# Dictionary to store user states and messages
user_states = {}
user_data = {}
user_message_save = None


@app.route("/callback", methods=['POST'])
def callback():
    # Get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    user_id = event.source.user_id

    # Initialize user state if not present
    if user_id not in user_states:
        user_states[user_id] = "start"
        user_data[user_id] = {'model':'gpt-3.5-turbo', 'api_key': None, 'instruction': None, 'conversation':{}, 'chat_model':['gpt-3.5-turbo', 'Back to main page'], 'chatting' : [False, None]}

    received_text = event.message.text
    response_text, quick_reply = process_user_message(user_id, received_text)

    # Send reply with quick replies if available
    text_message = TextSendMessage(text=response_text, quick_reply=quick_reply) if quick_reply else TextSendMessage(text=response_text)
    line_bot_api.reply_message(event.reply_token, text_message)


def process_user_message(user_id, received_text):
    state = user_states[user_id]

    # Respond based on user state
    if state == 'start' or received_text == 'Back to main page':
        response_text = textwrap.dedent("""
        歡迎使用 ✨GPT 自動 fine-tune 機器人！✨ 請更新 fine-tune 所需資料，以下為各個指令（按鍵）的功能 \n
        🌟Base Model🌟: fine-tune 的基礎模型，預設為 gpt-3.5-turbo ，可自行更新（必須是 OpenAI 的模型）\n
        🌟API Key🌟: OpenAI 的 api key ，請更新為自己的 api key  \n
        🌟Instruction🌟: 和模型說明你想要 fine-Tune 的方向，例如：你是一位國文老師，講話都用文言文 \n
        🌟Conversation data🌟: 更新用來 fine-Tune 模型的對話資料，對話須和 Instruction 的描述有關，才會有較好的效果 \n
        🌟Delete data🌟: 刪除先前所有的 Conversation data \n
        🌟Fine-Tune🌟: 以上資訊搜集完畢就能點擊進行 Fine-Tune 的工作 （對話資料須達 10 筆以上）， Fine-Tune 成功後會返回模型 id\n
        🌟Chat with model🌟: 選擇想要對話的模型，或是在 Fine-Tune 完畢後，輸入模型 id 與您的模型開始對話 \n
        🌟Check data🌟: 查看以上目前所有已輸入的資料
        """)
        quick_reply = create_quick_replies(['Base Model', 'API Key', 'Instruciton', 'Conversation data', 'Delete data', 'Fine-Tune', 'Chat with model', 'Check data'])
        user_states[user_id] = 'waiting_for_action'
        
        # update data if chatting canceled
        user_data[user_id]['chatting'][0], user_data[user_id]['chatting'][1] = False, None
    
    # Update base model    
    elif state == 'waiting_for_action' and received_text == 'Base Model':
        response_text = "請輸入模型名稱或是點擊 gpt-3.5-turbo 繼續使用 gpt-3.5-turbo"
        quick_reply = create_quick_replies(['gpt-3.5-turbo'])
        user_states[user_id] = 'waiting_for_model_name'
    elif state == 'waiting_for_model_name':
        response_text = "已更新 Base Model！ \n 點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'start'
        # update data
        model_name = received_text
        user_data[user_id]['model'] = model_name
    
    # Update api key
    elif state == 'waiting_for_action' and received_text == 'API Key':
        response_text = "請輸入 OpenAI api key \n 注意！請不要洩漏 api key \n 或點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'waiting_for_api_key'
    elif state == 'waiting_for_api_key':
        response_text = "已更新 api key！ \n 點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'start'
        # update data
        api_key = received_text
        user_data[user_id]['api_key'] = api_key

    # Update instruction
    elif state == 'waiting_for_action' and received_text == 'Instruciton':
        response_text = "請輸入你對於模型的描述，例：你是一位 ... ， 很擅長... \n 或點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'waiting_for_instruction'
    elif state == 'waiting_for_instruction':
        response_text = "已更新 Instruction！ \n 點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'start'
        # update data
        instruction = received_text
        user_data[user_id]['instruction'] = instruction

    # Update conversation data
    elif (state == 'waiting_for_action' and received_text == 'Conversation data') or (state == 'waiting_for_continue_or_not' and received_text == 'Yes'):
        response_text = "輸入對話資料 (使用者輸入) \n 或點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'waiting_for_conversation'
    elif state == 'waiting_for_conversation':
        response_text = "輸入對話資料 (建議模型怎麼回覆)"
        quick_reply = None
        user_states[user_id] = 'conversation_complete'
        # store user message
        global user_message_save
        user_message_save = received_text
    elif state == 'conversation_complete':
        response_text = "想要繼續輸入對話資料？ \n 或點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Yes', 'Back to main page'])
        user_states[user_id] = 'waiting_for_continue_or_not'
        # update data
        assistant_message = received_text
        user_data[user_id]['conversation'][user_message_save] = assistant_message
        
    # Delete conversation data
    elif state == 'waiting_for_action' and received_text == 'Delete data':
        response_text = "想要刪除已輸入的對話資料嗎？ \n 或點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Yes', 'Back to main page'])
        user_states[user_id] = 'waiting_for_delete_or_not'
    elif state == 'waiting_for_delete_or_not' and received_text == 'Yes':
        response_text = "已刪除先前對話資料 \n 點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'start'
        # delete data
        delete_data(user_id)

    # Fine-tune
    elif state == 'waiting_for_action' and received_text == 'Fine-Tune':
        response_text = "想要開始 Fine-Tune 嗎？ \n 或點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Yes', 'Back to main page'])
        user_states[user_id] = 'waiting_for_finetune_or_not'
    elif state == 'waiting_for_finetune_or_not'and received_text == 'Yes':
        # check data
        save_to_json(user_id)
        is_data_complete = check_data(user_id)
        if is_data_complete:
            # start fine tune process
            fine_tuning(user_id)
            response_text = "點擊 Back to main page 回到主頁"
        else:
            # data incomplete
            response_text = "資料不齊全，請繼續更新資料 \n 點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'start'

    # Chat with model
    elif state == 'waiting_for_action' and received_text == 'Chat with model':
        models = user_data[user_id]['chat_model']
        response_text = "請選擇你想要對話的模型，或是輸入想對話的模型 id \n 或點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(models)
        user_states[user_id] = 'waiting_for_chat_or_not'
    elif state == 'waiting_for_chat_or_not':
        response_text = "聊天模式已啟動，現在起，回覆你的是你的模型 \n 備註：與模型對話需要 Instruction，會自動設定為目前儲存的 Instruction \n 你可以隨時點擊 Back to main page 回到主頁，並關閉聊天模式"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'chatting_with_model'
        # update data and activate model
        model = received_text
        user_data[user_id]['chatting'][0], user_data[user_id]['chatting'][1] = True, model
    elif state == 'chatting_with_model' and user_data[user_id]['chatting'][0]:
        user_message = received_text
        response_text = chat_with_model(user_id, user_message)
        quick_reply = create_quick_replies(['Back to main page'])

    # Check data
    elif state == 'waiting_for_action' and received_text == 'Check data':
        check_data(user_id)
        response_text = "點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'start'

    # To avoid unseen instructions
    else:
        response_text = "不支援此指令，點擊 Back to main page 回到主頁"
        quick_reply = create_quick_replies(['Back to main page'])
        user_states[user_id] = 'start'

    return response_text, quick_reply


# Create quick reply buttons
def create_quick_replies(options):
    return QuickReply(items=[QuickReplyButton(action=MessageAction(label=option, text=option)) for option in options])

    
def delete_data(user_id):
    user_data[user_id]['conversation'] = {}
    try:
        os.remove(f"{user_id}_data.json")
    except FileNotFoundError:
        pass


# Save user messages to JSON file
def save_to_json(user_id):
    system_message = user_data[user_id]['instruction']
    conversation_data = user_data[user_id]['conversation']
    output_file = f"{user_id}_data.json"

    # Check if the file exists and if it contains data
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = f.readlines()
    else:
        existing_data = []
        
    # Prepare the new data to be added
    new_data = []
    for user_message, assistant_message in conversation_data.items():
        json_obj = {
                "messages":[
                    {"role":"system", "content":system_message},
                    {"role":"user", "content": user_message},
                    {"role":"assistant", "content": assistant_message}
                    ]
                }
        new_data.append(json.dumps(json_obj, ensure_ascii=False))
    
    # Combine the existing and new data
    all_data = existing_data + [entry + '\n' for entry in new_data]
    
    # Write all data back to the file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(all_data)

    user_data[user_id]['conversation'] = {}
    print(f" Data extraction completed. JSONL file saved to: {output_file}")


def check_data(user_id):
    save_to_json(user_id)
    pairs = extract_user_assistant_pairs(user_id)
    pairs_to_string = format_pairs_to_string(pairs)
    # Create check list for all require data
    check_list = textwrap.dedent(f"""
    🌟模型 (Base model)🌟: {user_data[user_id]['model']} {'✅ 已完成' if user_data[user_id]['model'] else '❌ 未完成'} \n
    🌟API Key🌟: {user_data[user_id]['api_key']} {'✅ 已完成' if user_data[user_id]['api_key'] else '❌ 未完成'} \n
    🌟給予模型的指示 (Instruciton)🌟:  {user_data[user_id]['instruction']} {'✅ 已完成' if user_data[user_id]['instruction'] else '❌ 未完成'} \n
    🌟已儲存對話筆數 (Conversation data)🌟: {len(pairs)} {'✅ 已完成' if len(pairs) >= 10 else '❌ 未完成'} \n
    """)
    conversations = f"目前已儲存的對話資料：\n\n{pairs_to_string}"
    line_bot_api.push_message(user_id, TextSendMessage(text=check_list))
    line_bot_api.push_message(user_id, TextSendMessage(text=conversations))
    return True if user_data[user_id]['model'] and user_data[user_id]['api_key'] and user_data[user_id]['instruction'] and len(pairs) >= 10 else False


def extract_user_assistant_pairs(user_id):
    user_assistant_pairs = []
    json_file = f'{user_id}_data.json'

    # Open the JSON file and read line by line
    with open(json_file, 'r', encoding='utf-8') as file:
        for line in file:
            # Parse the JSON object
            data = json.loads(line)
            messages = data.get('messages', [])
            
            user_message = None
            assistant_message = None
            
            # Extract user and assistant messages
            for message in messages:
                if message['role'] == 'user':
                    user_message = message['content']
                elif message['role'] == 'assistant':
                    assistant_message = message['content']
            
            # Append the pair if both are found
            if user_message and assistant_message:
                user_assistant_pairs.append((user_message, assistant_message))
    return user_assistant_pairs


def format_pairs_to_string(pairs):
    formatted_string = ""
    
    for user, assistant in pairs:
        formatted_string += f"使用者輸入: {user}\n建議模型回覆: {assistant}\n\n"
    return formatted_string.strip()


def fine_tuning(user_id):
    api = user_data[user_id]['api_key']
    client = OpenAI(api_key=api)
    model = user_data[user_id]['model']

    try:
        # Upload the training file
        response = client.files.create(
            file=open(f"{user_id}_data.json", "rb"),
            purpose='fine-tune'
            )
        training_file_id = response.id
        print(f"File uploaded successfully, file ID: {training_file_id}")

        # Start fine-tuning
        response = client.fine_tuning.jobs.create(
            training_file=training_file_id,
            model=model
            )
        fine_tune_id = response.id
        print(f"Fine-tuning started, fine-tune ID: {fine_tune_id}")
        # Send initial status to user
        fine_tune_message = f"開始 Fine-tune! Fine-tune ID:\n{fine_tune_id} \n 每分鐘會回傳 fine-tune 狀態，請耐心等待！"
        line_bot_api.push_message(user_id, TextSendMessage(text=fine_tune_message))

        # Monitor fine-tuning status
        while True:
            response = client.fine_tuning.jobs.retrieve(fine_tuning_job_id=fine_tune_id)
            status = response.status
            print(f"Fine-tuning status: {status}")
            # Send status update to user
            status_message = f"目前 Fine-tune 狀態: {status}"
            line_bot_api.push_message(user_id, TextSendMessage(text=status_message))
            # Fine tune succeeded
            if status == 'succeeded':
                print("Fine-tuning succeeded.")
                fine_tuned_model = response.fine_tuned_model
                user_data[user_id]['chat_model'].append(fine_tuned_model)
                status_message = f"Fine-tune 成功！ 你的 fine-tune 模型 id: {fine_tuned_model}"
                line_bot_api.push_message(user_id, TextSendMessage(text=status_message))
                break
            # Fine tune failed
            elif status == 'failed':
                print("Fine-tuning failed.")
                status_message = f"Fine-tune 失敗 QQ"
                line_bot_api.push_message(user_id, TextSendMessage(text=status_message))
                break
            time.sleep(60)  # Wait for 1 minute before checking the status again
    # error 
    except openai.OpenAIError as e:
        print(f"An error occurred: {e}")
        status_message = f"Fine-tune 錯誤！請確認資料是否有誤(模型名稱、API Key)"
        line_bot_api.push_message(user_id, TextSendMessage(text=status_message))


def chat_with_model(user_id, user_message):
    try:
        api = user_data[user_id]['api_key']
        client = OpenAI(api_key=api)
        
        model = user_data[user_id]['chatting'][1]
        system_message = user_data[user_id]['instruction']
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {'role':'system', 'content':system_message},
                {'role': 'user', 'content': user_message}
            ]
        )
        reply_message = completion.choices[0].message.content
        return reply_message
    except openai.APIError as e:
        reply_message = "對話出錯，請確認資料是否有誤(模型名稱、API Key) \n 點擊 Back to main page 回到主頁"
        return reply_message

if __name__ == "__main__":
    app.run(debug=True)
