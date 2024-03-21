# Chat Application

This a small application written to learn FastAPI and Python. It uses FastAPI and Websockets to create a small Chat app.

## Security

Your passwords are hashed using bcrypt and passlib. The key is currently public so please replace the key if you really want to host a server.
Your Account is per Server. Do not trust any Server you do not know and DON'T use your NORMAL Password for servers that you don't own. Because you do not have control as the password is encrypted server side, if they actually just store the password or steal it.

## Usage

Install all the dependencies with:

```shell
pip install -r requirements.txt
```

Start the backend with the following command:

```shell
uvicorn server.server:app
```

Then you should run the cli.
On the first prompt, type "y" and press enter. Then create a user account. After that you can directly log into the new account.
To test the chat, you can open a second terminal with the command from below, create a second account and log into that.

Then just start writing. When you press enter, the message will be send.

```shell
python3 cli.py --host localhost:8000
```
