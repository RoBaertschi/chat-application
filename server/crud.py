from sqlalchemy.orm import Session

from . import models
from shared import projecttypes


def get_user(db: Session, user_id: int):
  return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
  return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: projecttypes.UserCreate):
  db_user = models.User(**user.model_dump())
  db.add(db_user)
  db.commit()
  db.refresh(db_user)
  return db_user
