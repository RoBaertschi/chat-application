from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, cast
from fastapi import (
  Depends,
  FastAPI,
  HTTPException,
  Request,
  Response,
  WebSocket,
  WebSocketDisconnect,
  status,
)
from fastapi.requests import HTTPConnection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError
from server.connectionmanager import Connectionmanager
from shared.projecttypes import (
  ChatMessage,
  ConnectMessage,
  Message,
  MessageType,
  Reasons,
  User,
  UserCreate,
)
from passlib.context import CryptContext
from .database import SessionLocal, engine
from . import crud, models
from sqlalchemy.orm import Session

# REALLY SECRET CODE, DO NOT SHARE
SECRET_KEY = "6a18c5421ebc4923199c8148b61663f4dc2ed93c0182b8d6b831985f0d130611"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
  access_token: str
  token_type: str


class TokenData(BaseModel):
  username: str | None = None


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Workaround for websockets because OAuth2PasswordBearer has no websocket support
class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
  async def __call__(
    self,
    request: Request = None,  # type: ignore
    websocket: WebSocket = None,  # type: ignore
  ) -> str | None:
    connection: HTTPConnection = request or websocket

    print(connection.headers)

    authorization = connection.headers.get("Authorization") or connection.headers.get(
      "authorization"
    )
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
      if self.auto_error:
        raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Not authenticated",
          headers={"WWW-Authenticate": "Bearer"},
        )
      else:
        return None
    return param


oauth2_scheme = CustomOAuth2PasswordBearer(tokenUrl="token", auto_error=False)

manager = Connectionmanager()


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


def verify_password(plain_password, hashed_password):
  return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str):
  return pwd_context.hash(password)


def authenticate_user(
  username: str, password: str, db: Session
) -> Literal[False] | models.User:
  user = crud.get_user_by_username(db, username)

  if not user:
    print("Could not find uesr")
    return False

  if not verify_password(password, user.password):
    print("User password do not match")
    return False

  return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.now(timezone.utc) + expires_delta
  else:
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)

  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  return encoded_jwt


async def get_current_user(
  token: Annotated[str | None, Depends(oauth2_scheme)],
  db: Annotated[Session, Depends(get_db)],
) -> models.User | None:
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )

  if not token:
    return None

  try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    if username is None:
      raise credentials_exception
    token_data = TokenData(username=username)
  except JWTError:
    raise credentials_exception

  user = crud.get_user_by_username(db, username=cast(str, token_data.username))
  if user is None:
    raise credentials_exception
  return user


@app.get("/test")
def test(user: Annotated[User, Depends(get_current_user)]):
  pass


@app.post("/token")
async def login_for_access_token(
  form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
  db: Annotated[Session, Depends(get_db)],
) -> Token:
  user = authenticate_user(form_data.username, form_data.password, db)
  if not user:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Incorrect username or password",
      headers={"WWW-Authenticate": "Bearer"},
    )

  access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  access_token = create_access_token(
    data={"sub": user.username}, expires_delta=access_token_expires
  )
  return Token(access_token=access_token, token_type="bearer")


@app.post("/register-user")
def register_user(user_create: UserCreate, db: Annotated[Session, Depends(get_db)]):
  user = crud.get_user_by_username(db, user_create.username)
  if user:
    raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Already exsits")

  user_create.password = get_password_hash(user_create.password)

  created_user = crud.create_user(db, user_create)

  if not created_user:
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)

  return User(username=created_user.username, id=created_user.id)


@app.websocket("/ws")
async def ws(
  websocket: WebSocket, user: Annotated[User | None, Depends(get_current_user)]
):
  if not user:
    await websocket.accept()
    await websocket.close(status.WS_1008_POLICY_VIOLATION)
    return Response(status_code=401)

  await manager.connect(websocket)
  try:
    while True:
      data = await websocket.receive_text()
      try:
        message = Message.model_validate_json(data)

        if message.messageType == MessageType.connect:
          ConnectMessage.model_validate(message.data)

          if not await manager.new_user(user, websocket):
            await websocket.close(
              status.WS_1008_POLICY_VIOLATION, reason=Reasons.already_logged_in
            )
            return Response(status_code=401)

        elif message.messageType == MessageType.chatmessage:
          ChatMessage.model_validate(message.data)
          await manager.broadcast(data)

        print(f"Received message: {message}")
      except ValidationError as e:
        print(f"Error while reading websocket message: {e.errors()}")

  except WebSocketDisconnect:
    await manager.disconnect(websocket)
