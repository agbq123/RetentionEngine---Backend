import os

class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///retention.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False