import json
import typer
import requests
from . import console, User


def authenticate_user(host: str):
  if typer.confirm("Do you want to create a new Account?"):
    if create_account(host):
      user = log_into_account(host)
  else:
    user = log_into_account(host)

  return user


def log_into_account(host: str):
  jwt = None
  while jwt is None:
    console.rule("[bold red]Login")
    username = typer.prompt("Username")
    password = typer.prompt(
      "Password",
      hide_input=True,
    )
    console.rule()

    r = requests.post(
      f"http://{host}/token",
      {"username": username, "password": password, "scope": "all"},
    )

    if r.ok:
      jwt = r.content
    else:
      print("Failed to login: ", str(r.content))
      if ask_register_account(host):
        create_account(host)

  json_text = json.loads(jwt)

  return User(username=username, jwt=json_text["access_token"])


def create_account(host: str):
  console.rule("Register")
  username = typer.prompt("Username")
  password = typer.prompt("Password", hide_input=True)
  confirm_password = typer.prompt("Confirm Password", hide_input=True)

  if password != confirm_password:
    print("Password does not match")

    while password != confirm_password:
      if typer.confirm("Try again?", default=True):
        password = typer.prompt("Password", hide_input=True)
        confirm_password = typer.prompt("Confirm Password", hide_input=True)

  r = requests.post(
    f"http://{host}/register-user", json={"username": username, "password": password}
  )
  console.rule()

  if not r.ok:
    print("[bold red]Error: ", str(r.content), "[/]")
    return False

  print("Successfully registered new account, please log into your new account.")

  return True


def ask_register_account(host: str):
  if typer.confirm("Do you want to register a account?"):
    return create_account(host)
  return False
