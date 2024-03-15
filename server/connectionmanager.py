from fastapi import WebSocket

from shared.projecttypes import Message, MessageType, User, UserJoin, UserLeft


class Connection:
  websocket: WebSocket
  user: User

  def __init__(self, user: User, websocket: WebSocket) -> None:
    self.websocket = websocket
    self.user = user


class Connectionmanager:
  def __init__(self) -> None:
    self.active_connections: list[WebSocket] = []
    self.connections: list[Connection] = []

  async def connect(self, websocket: WebSocket):
    await websocket.accept()
    self.active_connections.append(websocket)

  async def disconnect(self, websocket: WebSocket):
    self.active_connections.remove(websocket)
    for connection in self.connections:
      if connection.websocket == websocket:
        message = Message(
          messageType=MessageType.userleft,
          data=UserLeft(username=connection.user.username),
        )
        self.connections.remove(connection)
        await self.broadcast(message=message.model_dump_json())

  async def send_personal_message(self, message: str, websocket: WebSocket):
    await websocket.send_text(message)

  async def broadcast(self, message: str):
    for connection in self.active_connections:
      await connection.send_text(message)

  async def new_user(self, user: User, websocket: WebSocket):
    for conn in self.connections:
      if conn.user.username == user.username:
        return False

    await self.broadcast(
      Message(
        messageType=MessageType.userjoin, data=UserJoin(username=user.username)
      ).model_dump_json()
    )

    self.connections.append(Connection(user, websocket))

    return True
