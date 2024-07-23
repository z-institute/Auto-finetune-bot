# Auto Fine-tune Bot

## Add Line bot to your contact 

Line Bot ID: @368ivokx

## Update Fine Tuning Data in Line Bot
- Enter any message to initialize the Line bor
- Follow the Instruction on Line Bot
- Get API Key in [Openai API](https://platform.openai.com/api-keys)

## Here are some examples

- Enter any message at initial stage
![img](/img/chat1.png)

- Update your base model or use default model: gpt-3.5-turbo 
![img](/img/chat2.png)

- Update your OpenAI API key (required)
![img](/img/chat3.png)

- Update the instruction for the model (required)
![img](/img/chat4.png)

- Update the conversation data (at least 10 to fine-tune)
![img](/img/chat5.png)

- Delete the conversation data whenever you want
![img](/img/chat6.png)

- Check if all requirements have been completed with check data
![img](/img/chat7.png)

- After all requirements have been completed, you can fine-tune the model. 
The chatbot will check required data in advance to avoid error in fine-tuning.
![img](/img/chat8.png)

- If you passed the checking process, the model will start fine-tuning and return the status every minute.
The process usually takes 5-10 minutes with 10 coversation data and the time will increase with the amount of conversation data.
![img](/img/chat9.png)

- You can see the fine tuning process in [Openai platform](https://platform.openai.com/finetune/ftjob-wgRJDRzLhFy0jg3z1xopUBot?filter=all) as well.
![img](/img/openai.png)

- You can chat with the existing model or your own model (required data: API Key and Instruction)
  - Chat with gpt-3.5-turbo
    ![img](/img/chat10.png)
    ![img](/img/chat11.png)
  - Chat with your own model
    ![img](/img/chat12.png)
  - Press "Back to main page" whenever you want to stop chatting
    ![img](/img/chat13.png)


# You can also run your own bot 

## Clone the repository
`
git clone https://github.com/z-institute/Auto-finetune-bot.git
`

## Create a Line Bot 
- Register on the [Line Developer website](https://developers.line.biz/zh-hant/)
- Go to "Providers" and click "Create" to create a new provider
- Create a new channel for Line bot
- Find "Bot basic ID" in "Messageing API" Page, and add your Line bot to contact by this ID
- Go to [Line Official Account Manage Page](https://tw.linebiz.com/login/)
- Disable automatic response messages to avoid original auto messages

## set .env file
- create an empty .env file in your folder
- Back to [Line Developer website](https://developers.line.biz/zh-hant/)
- Go to "Basic Setting" in your Line bot, and you will see "channel secret"
- Put your channel secret in .env file, the variable nane: LINE_CHANNEL_SECRET 
- Go to "Messaging API" to get "Channel Access Token"
- Put your channel access token in .env file, the variable nane: LINE_ACCESS_TOKEN

## Get a public URL from ngrok
- Register on the [ngrok](https://ngrok.com/)
- Go to "Setup & Installation" and follow the instruction to download ngrok to local
- After this step, you can get a public URL by running 
`
ngrok http http://127.0.0.1:5000
`
in your terminal
- Update the "Webhook URL" in "Messaging API" from
[Line Developer website](https://developers.line.biz/zh-hant/), **remember to add /callback at the end of the URL**
- You should update the URL everytime you run ngrok

## Run Line bot
- Access to the line bot folder `cd bot`
- Run the Line bot in terminal
`
python3 line_bot.py
`
- Now, open Line and Update your data with Line bot