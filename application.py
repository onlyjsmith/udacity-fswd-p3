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
from dicttoxml import dicttoxml
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Categories&Items"

# Connect to Database and create database session
engine = create_engine('sqlite:///category.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#
# User Helper Functions
#


# Create User from given session
def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session[
                       'email'
                   ],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# Find User object by user_id
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Find user by email
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

#
# API endpoints
#


# All categories returned as JSON or XML, depending on parameter
@app.route('/category.<string:format>')
def categoriesJSON(format):
    categories = session.query(Category).all()
    serialized = [r.serialize for r in categories]
    if format == 'json':
        return jsonify(categories=serialized)
    elif format == 'xml':
        return app.response_class(dicttoxml(serialized),
                                  mimetype='application/xml')
    else:
        return 'Unknown format'


# All items for given category returned as JSON or XML, depending on parameter
@app.route('/category/<int:category_id>.<string:format>')
def itemsJSON(category_id, format):
    items = session.query(Item).filter_by(category_id=category_id).all()
    serialized = [i.serialize for i in items]
    if format == 'json':
        return jsonify(items=serialized)
    elif format == 'xml':
        return app.response_class(dicttoxml(serialized),
                                  mimetype='application/xml')
    else:
        return 'Unknown format'


# Single item returned as JSON or XML, depending on parameter
@app.route('/category/<int:category_id>/items/<int:item_id>.<string:format>')
def itemJSON(category_id, item_id, format):
    item = session.query(Item).filter_by(id=item_id).one()
    serialized = [item.serialize]
    if format == 'json':
        return jsonify(item=serialized)
    elif format == 'xml':
        return app.response_class(dicttoxml(serialized),
                                  mimetype='application/xml')
    else:
        return 'Unknown format'

#
# Category CRUD routes
#


# Root route, showing all categories
@app.route('/')
@app.route('/category/')
def showCategories():
    categories = session.query(Category).order_by(asc(Category.name)).all()
    if 'username' not in login_session:
        readonly = True
    else:
        readonly = False
    return render_template('showCategories.html', categories=categories, readonly=readonly)


# Create new category
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    # Redirect to login if not already logged-in
    if 'username' not in login_session:
        return redirect('/login')

    # If responding to form submission
    if request.method == 'POST':
        newCategory = Category(
            name=request.form['name'],
            user_id=login_session['user_id'])
        session.add(newCategory)
        flash('%s Category created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newCategory.html')


# Edit category
@app.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
def editCategory(category_id):
    editedCategory = session.query(Category).filter_by(id=category_id).one()
    if editedCategory.user_id != login_session['user_id']:
        flash('Not authorised to delete %s' % editedCategory.name)
        return redirect(url_for('showCategories'))
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            flash('Edited %s' % editedCategory.name)
            return redirect(url_for('showCategories'))
    else:
        return render_template('editCategory.html', category=editedCategory)


# Delete category
@app.route('/category/<int:category_id>/delete', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categoryToDelete = session.query(Category).filter_by(id=category_id).one()
    if categoryToDelete.user_id != login_session['user_id']:
        flash('Not authorised to delete %s' % categoryToDelete.name)
        return redirect(url_for('showCategories', category_id=category_id))
    if request.method == 'POST':
        if request.form['delete_token'] == login_session['delete_token']:
            session.query(Item).filter_by(category_id=category_id).delete()
            session.delete(categoryToDelete)
            flash('%s Successfully Deleted' % categoryToDelete.name)
            session.commit()
            return redirect(url_for('showCategories'))
        else:
            del login_session['delete_token']
            flash('Not authorised to delete %s' % categoryToDelete.name)
            return redirect(url_for('showCategories', category_id=category_id))
    else:
        login_session['delete_token'] = createRandomString(64)
        return render_template('deleteCategory.html',
                               category=categoryToDelete,
                               delete_token=login_session['delete_token'])
#
# Item CRUD routes
#


# Show all items for given category
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/items/')
def showItems(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    items = session.query(Item).filter_by(category_id=category_id).all()
    readonly = 'username' not in login_session or creator.id != login_session[
        'user_id'
    ]
    return render_template('showItems.html',
                           items=items,
                           category=category,
                           creator=creator,
                           readonly=readonly)


# Show single item
@app.route('/category/<int:category_id>/items/<int:item_id>/')
def showItem(category_id, item_id):
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    item = session.query(Item).filter_by(id=item_id).one()
    readonly = 'username' not in login_session or creator.id != login_session[
        'user_id'
    ]
    return render_template('showItem.html',
                           item=item,
                           category=category,
                           readonly=readonly)


# Create new item for given category
@app.route('/category/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    categories = session.query(Category).filter_by(
        user_id=login_session['user_id']).all()
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       user_id=category.user_id,
                       category_id=request.form['category_id'],
                       description=request.form[
                           'description'
                       ],
                       image_url=request.form['image_url'])
        session.add(newItem)
        session.commit()
        flash('%s Item created' % (newItem.name))
        return redirect(url_for('showItems',
                                category_id=request.form['category_id']))
    else:
        return render_template('newItem.html',
                               category_id=category_id,
                               categories=categories)


# Edit item
@app.route('/category/<int:category_id>/items/<int:item_id>/edit/',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    editedItem = session.query(Item).filter_by(id=item_id).one()
    category = session.query(Category).filter_by(id=category_id).one()
    categories = session.query(Category).filter_by(
        user_id=login_session['user_id']).all()
    if editedItem.user_id != login_session['user_id']:
        flash('Not authorised to edit %s' % editedItem.name)
        return redirect(url_for('showItems', category_id=category_id))

    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['category_id']:
            editedItem.category_id = request.form['category_id']
        if request.form['image_url']:
            editedItem.image_url = request.form['image_url']
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showItems',
                                category_id=editedItem.category_id))
    else:
        return render_template('editItem.html',
                               category_id=category_id,
                               categories=categories,
                               item_id=item_id,
                               item=editedItem)


# Delete item
@app.route('/category/<int:category_id>/items/<int:item_id>/delete/',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if category.user_id != login_session['user_id']:
        flash('Not authorised to delete %s from %s' % itemToDelete.name,
              category.name)
        return redirect(url_for('showItems', category_id=category.id))
    if request.method == 'POST':
        if request.form['delete_token'] == login_session['delete_token']:
            session.delete(itemToDelete)
            session.commit()
            flash('Item Successfully Deleted')
            return redirect(url_for('showItems', category_id=category.id))
        else:
            del login_session['delete_token']
            flash('Not authorised to delete %s from %s' %
                  (itemToDelete.name, category.name))
            return redirect(url_for('showItems', category_id=category.id))
    else:
        login_session['delete_token'] = createRandomString(64)
        return render_template('deleteItem.html',
                               category_id=category.id,
                               item=itemToDelete,
                               delete_token=login_session['delete_token'])

#
# Authentication and session management routes
#


# Create anti-forgery session token for login request
@app.route('/login')
def showLogin():
    state = createRandomString(32)
    login_session['state'] = state
    return render_template('login.html',
                           STATE=state,
                           GOOGLE_CLIENT_ID=CLIENT_ID)

# Callback for Google plus login
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %
           access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check if already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()

    # Create session variables to store user and details
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    # Create simple response to POST request
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += login_session['gplus_id']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("you are now logged in as %s" % login_session['email'])
    print "Done with auth!"
    return output  # `output` is returned to as the response to the POST request

# Disconnect Googple plus and delete session variables
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCategories'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCategories'))

# Disconnect a user from google plus
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')

    # Check if user not currently logged int
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials
    # Revoke token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response
#
# UTILITY
#

# Used in tokens to avoid CRSF
def createRandomString(length):
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for x in xrange(32))


# Launch!
if __name__ == '__main__':
    # In production, `secret_key` should not be kept in the repo, but is here to simplify testing and review of the application
    app.secret_key = '97249824iini34r90304r90we0f9j0w9ejf09j2340u039j90jfwef'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
