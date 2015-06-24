from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, Item
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

# CLIENT_ID = json.loads(
#     open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Categories and Items"

# Connect to Database and create database session
engine = create_engine('sqlite:///category.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
@app.route('/categories')
def show_categories():
    categories = session.query(Category).order_by(asc(Category.name)).all()
    print(categories)
    return render_template('show_categories.html', categories=categories)

if __name__ == '__main__':
    app.secret_key = '97249824iini34r90304r90we0f9j0w9ejf09j2340u039j90jfwef'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
