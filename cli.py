from queue import Queue
import queue
import threading
from typing import cast
from pydantic import ValidationError
import typer
import asyncio
from websockets import WebSocketClientProtocol
import websockets
from websockets.client import connect
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn

from client import User
from client.authentication import authenticate_user
from shared.projecttypes import (
  ChatMessage,
  Message,
  ConnectMessage,
  MessageType,
  Reasons,
  UserJoin,
  UserLeft,
)


def main(host: str | None = None):
  if host is None:
    host = typer.prompt(text="Server Addres")

  print("You can always quit with [bold]Ctrl + C[/]")

  user = authenticate_user(str(host))

  if not isinstance(user, User):
    exit(1)

  asyncio.run(start(cast(str, host), user))


async def handle_message(websocket: WebSocketClientProtocol, username: str):
  try:
    data = await asyncio.wait_for(websocket.recv(), 0.1)
    try:
      message = Message.model_validate_json(data)

      if message.messageType == MessageType.chatmessage:
        chat_message = ChatMessage.model_validate(message.data)

        if chat_message.sender == username:
          print(f"[gray50]{chat_message.sender}[/]: {chat_message.message}")
        else:
          print(f"[bold green]{chat_message.sender}[/]: {chat_message.message}")

      elif message.messageType == MessageType.userjoin:
        userJoin = UserJoin.model_validate(message.data)

        print(f"[bold green]User {userJoin.username} joined.[/]")

      elif message.messageType == MessageType.userleft:
        user_left = UserLeft.model_validate(message.data)

        print(f"[bold red]User {user_left.username} has left.[/]")
    except ValidationError as e:
      print(f"Got validation error: {e.errors()}")
  except asyncio.TimeoutError:
    pass


async def wait_for_join_message(websocket: WebSocketClientProtocol, username: str):
  got_message = False
  while not got_message:
    try:
      data = Message.model_validate_json(await websocket.recv())

      if data.messageType != MessageType.userjoin:
        continue

      userjoin = UserJoin.model_validate(data.data)
      if userjoin.username == username:
        got_message = True
    except ValidationError:
      pass

  print("[bold green]Successfully joined the Server[/]")


def user_input(message_queue: Queue, username: str):
  while True:
    message = input("")
    message_queue.put(
      Message(
        messageType=MessageType.chatmessage,
        data=ChatMessage(sender=username, message=message),
      )
    )


async def start(host: str, user: User):
  print(f"[bold gray50]Connecting to server host: {host}[/]")
  with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    transient=True,
  ) as progress:
    progress.add_task("Connecting...")
    async with connect(
      f"ws://{host}/ws",
      extra_headers={"Authorization": "Bearer " + user.jwt},
    ) as websocket:
      try:
        await websocket.send(
          Message(
            messageType=MessageType.connect,
            data=ConnectMessage(username=user.username),
          ).model_dump_json()
        )
        print("[bold gray50]Sucessfully connected[/]")

        await wait_for_join_message(websocket, user.username)
        progress.stop()

        message_queue = queue.Queue()

        user_input_thread = threading.Thread(
          target=user_input,
          args=(
            message_queue,
            user.username,
          ),
        )
        user_input_thread.daemon = True
        user_input_thread.start()

        stop = False
        while not stop:
          await handle_message(websocket, user.username)

          if not message_queue.empty():
            await websocket.send(message_queue.get().model_dump_json())
      except websockets.ConnectionClosed as c:
        if c.code == 1008 and c.reason == Reasons.already_logged_in:
          print("[bold red]You are already logged in![/]")
        else:
          print(f"[bold red]An unknown Error occured: {c}[/]")

        print("Quiting program")


if __name__ == "__main__":
  typer.run(main)
