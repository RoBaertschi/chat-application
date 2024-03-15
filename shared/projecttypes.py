from enum import Enum
from pydantic import BaseModel


class UserBase(BaseModel):
  username: str


class UserCreate(UserBase):
  password: str


class User(UserBase):
  id: int


class ChatMessage(BaseModel):
  message: str
  sender: str


class ConnectMessage(BaseModel):
  username: str


class UserJoin(BaseModel):
  username: str


class UserLeft(BaseModel):
  username: str


class MessageType(str, Enum):
  connect = "connect"
  chatmessage = "chat"
  userjoin = "userjoin"
  userleft = "userleft"


class Message(BaseModel):
  messageType: MessageType
  data: object


class Reasons(str, Enum):
  already_logged_in = "Alread Logged in"
