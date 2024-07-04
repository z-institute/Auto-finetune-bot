import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from openai import OpenAI
import time

app = Flask(__name__)

# Replace with your Channel Access Token
line_bot_api = LineBotApi(os.environ['LINE_ACCESS_TOKEN'])

# Replace with your Channel Secret
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

# Dictionary to store user states and messages
user_states = {}
user_messages = {}


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
        user_messages[user_id] = []

    # does not do lower when input is api key
    if user_states[user_id] == "waiting_for_api":
        received_text = event.message.text
    else:
        received_text = event.message.text.strip()

    # Respond based on user state
    if user_states[user_id] == "start":
        response_text = "請點擊「描述模型」來輸入你對想要訓練的模型的描述"
        quick_reply = create_quick_replies(["描述模型"])
        user_states[user_id] = "waiting_for_instruction"
    elif received_text == "描述模型" and user_states[user_id] == "waiting_for_instruction":
        response_text = "請輸入你對想要訓練的模型的描述"
        quick_reply = None
        user_states[user_id] = "instruction_complete"
    elif user_states[user_id] == "instruction_complete":
        user_messages[user_id].append(received_text)
        response_text = "點擊「更新對話資料」來輸入模型的訓練資料，或選擇「刪除資料」來重置訓練資料集！"
        quick_reply = create_quick_replies(["更新對話資料", "刪除資料"])
        user_states[user_id] = "waiting_for_train_model"
    elif received_text == "刪除資料" and user_states[user_id] == "waiting_for_train_model":
        response_text = "確定要刪除資料嗎？"
        quick_reply = create_quick_replies(["是", "否"])
        user_states[user_id] = "delete_or_not"
    elif received_text == "是" and user_states[user_id] == "delete_or_not":
        delete_data(user_id)
        response_text = "已刪除資料！請點擊「描述模型」來重新輸入你對想要訓練的模型的描述"
        quick_reply = create_quick_replies(["描述模型"])
        user_states[user_id] = "waiting_for_instruction"
    elif received_text == "否" and user_states[user_id] == "delete_or_not":
        response_text = "刪除資料取消！點擊「更新對話資料」來輸入模型的訓練資料"
        quick_reply = create_quick_replies(["更新對話資料"])
        user_states[user_id] = "waiting_for_train_model"
    # wait for fisrt input
    elif received_text == "更新對話資料" and user_states[user_id] == "waiting_for_train_model":
        response_text = "請輸入對話："
        quick_reply = None
        user_states[user_id] = "waiting_for_first_input"
    # complete first and wait for second input
    elif user_states[user_id] == "waiting_for_first_input":
        user_messages[user_id].append(received_text)
        response_text = "請輸入你想要模型怎麼回覆對話："
        quick_reply = None
        user_states[user_id] = "waiting_for_second_input"
    # complete second input and wait for next step (keep input or pass)
    elif user_states[user_id] == "waiting_for_second_input":
        user_messages[user_id].append(received_text)
        response_text = "你想要繼續輸入對話資料嗎?"
        quick_reply = create_quick_replies(["輸入另一筆對話資料", "停止輸入並儲存資料"])
        user_states[user_id] = "waiting_for_continue_or_stop"
    # keep input
    elif received_text == "輸入另一筆對話資料" and user_states[user_id] == "waiting_for_continue_or_stop":
        response_text = "請輸入對話:"
        quick_reply = None
        user_states[user_id] = "waiting_for_first_input"
    # stop input and save data
    elif received_text == "停止輸入並儲存資料" and user_states[user_id] == "waiting_for_continue_or_stop":
        #  Process the user_messages[user_id] dictionary as needed for training the model
        save_to_json(user_id)
        enough_data = check_data(user_id)
        if enough_data:
            response_text = "資料儲存完成！已達10筆，是否訓練模型？"
            quick_reply = create_quick_replies(["是", "否"])
            user_states[user_id] = "train_or_not"
        else:
            response_text = "好的，資料已儲存（10筆才能訓練模型），已輸入過的就不用再輸入一次囉！點擊「更新對話資料」來繼續輸入模型的訓練資料，或選擇「刪除資料」來重置訓練資料集～"
            quick_reply = create_quick_replies(["更新對話資料", "刪除資料"])
            user_states[user_id] = "waiting_for_train_model"
    # train model and get api
    elif received_text == "是" and user_states[user_id] == "train_or_not":
        response_text = "請輸入你的 openai api key~ 備註：在訓練時請勿輸入任何文字，否則訓練會中斷！請耐心等待模型訓練完成的回覆～"
        quick_reply = None
        user_states[user_id] = "waiting_for_api"
    # train model
    elif user_states[user_id] == "waiting_for_api":
        api = received_text
        result = fine_tuning(user_id, api)
        if result == 'success':
            response_text = "模型訓練完成! 點擊「更新對話資料」來繼續輸入模型的訓練資料，或選擇「刪除資料」來重置訓練資料集！"
            quick_reply = create_quick_replies(["更新對話資料", "刪除資料"])
            user_states[user_id] = "waiting_for_train_model"
        else:
            response_text = "api 錯誤! 請重新輸入 api"
            quick_reply = None
    # not to train model and back to the original status
    elif received_text == "否" and user_states[user_id] == "train_or_not":
        response_text = "好的，資料已儲存，以輸入過的就不用再輸入一次囉！點擊「更新對話資料」來繼續輸入模型的訓練資料，或選擇「刪除資料」來重置訓練資料集～"
        quick_reply = create_quick_replies(["更新對話資料", "刪除資料"])
        user_states[user_id] = "waiting_for_train_model"
    # to avoid illegel input when not collecting data
    else:
        response_text = "不支援此功能, 點擊「更新對話資料」來輸入模型的訓練資料，或選擇「刪除資料」來重置訓練資料集！"
        quick_reply = create_quick_replies(["更新對話資料", "刪除資料"])
        user_states[user_id] = "waiting_for_train_model"


    # Send reply with quick replies if available
    text_message = TextSendMessage(text=response_text, quick_reply=quick_reply) if quick_reply else TextSendMessage(text=response_text)
    line_bot_api.reply_message(event.reply_token, text_message)



# Create quick reply buttons
def create_quick_replies(options):
    quick_reply_items = [
        QuickReplyButton(action=MessageAction(label=option, text=option.lower()))
        for option in options
    ]
    return QuickReply(items=quick_reply_items)
    
def delete_data(user_id):
    user_messages[user_id] = []
    file_path = f"{user_id}_data.json"

    # Check if file exists
    if os.path.exists(file_path):
        # Read existing data
        os.remove(file_path)

# Save user messages to JSON file
def save_to_json(user_id):
    data = user_messages[user_id]
    output_file = f"{user_id}_data.json"
    system_message = data[0]

    # Check if the file exists and if it contains data
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = f.readlines()
    else:
        existing_data = []
        
    # Prepare the new data to be added
    new_data = []
    for i in range(1, len(data), 2):
        user_message = data[i]
        assistant_message = data[i+1]

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

    user_messages[user_id] = [system_message]
    print(f" Data extraction completed. JSONL file saved to: {output_file}")

def check_data(user_id):
    data_path = f'{user_id}_data.json'
    # Load the dataset
    with open(data_path, 'r', encoding='utf-8') as f:
        dataset = [json.loads(line) for line in f]
    if len(dataset) >= 10:
        return True
    return False

def fine_tuning(user_id, api):
    client = OpenAI(api_key=api)

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
        model="gpt-3.5-turbo"
        )
    fine_tune_id = response.id
    print(f"Fine-tuning started, fine-tune ID: {fine_tune_id}")

    # Monitor fine-tuning status
    while True:
        response = client.fine_tuning.jobs.retrieve(fine_tuning_job_id=fine_tune_id)
        status = response.status
        print(f"Fine-tuning status: {status}")
        if status == 'succeeded':
            return 'success'
        elif status == 'failed':
            print("Fine-tuning failed.")
            return 'failed'
        time.sleep(60)  # Wait for 1 minute before checking the status agai


if __name__ == "__main__":
    app.run(debug=True)
