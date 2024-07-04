# Auto Fine-tune Bot

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
[Line Developer website](https://developers.line.biz/zh-hant/)
- You should update the URL everytime you run ngrok

## Run Line bot
- Access to the line bot folder
- Run the Line bot in terminal
`
python3 line_bot.py
`
- Now, open Line and Update your data with Line bot

## Update Fine Tuning Data in Line Bot
- Enter any message to initialize the Line bor
- Follow the Instruction on Line Bot, examples below
![img](/img/chat.png)
![img](/img/chat2.png)

- You can store the data first after entering any conversation data. If there are enough data (more than 10), you can fine tune your GPT by entering your Openai API Key. Get API Key in [Openai API](https://platform.openai.com/api-keys)
![img](/img/chat3.png)

- You can see the fine tuning process in [Openai platform](https://platform.openai.com/finetune/ftjob-wgRJDRzLhFy0jg3z1xopUBot?filter=all), and test your model by clicking "Playground" below
![img](/img/openai.png)