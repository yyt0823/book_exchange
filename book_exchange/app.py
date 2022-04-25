import os
import sqlite3
import urllib.parse
import requests
import json
import pprint
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from functools import wraps


#############################       CONFIGURATION       ###################################################

# Configure application
app = Flask(__name__)

#key
app.secret_key = "test"

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#link db
con = sqlite3.connect('book_exchange.db', check_same_thread=False)
db = con.cursor()

#Configure apology and login_required
def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/showcase")
        return f(*args, **kwargs)
    return decorated_function












#####################################          MAIN        ################################################
# routing non-user index
@app.route("/showcase")
def showcase():
    return render_template("index.html")

# routing index
@app.route("/")
@login_required
def index():
    return render_template("index_user.html")

# routing login
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        #check database
        username = request.form.get("username")
        password = request.form.get("password")
        rows = db.execute("SELECT count(*) FROM users where username = ? and password = ?;", (username, password))
        validation = rows.fetchone()[0]

        if validation == 1:
            user_id = db.execute("SELECT id FROM users where username = ? and password = ?;", (username, password)).fetchone()[0]
            session["user_name"] = username
            session["user_id"] = user_id

            return redirect("/")
        else:
            return apology("Sorry, username or password is incorrect")
    else:
        return render_template("login.html")
    

# routing register
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        try:
            username = request.form.get("username")
            password = request.form.get("password")
            re_enter = request.form.get("re_enter") 
            if username == "" or password == "":
                return apology("username or password must not be none")
            if re_enter != password:
                return apology("passwords do not match")
            db.execute("INSERT INTO users(username, password) VALUES (?, ?);", (username, password))
        except sqlite3.IntegrityError:
            return apology("sorry, username have been taken", 400)
        db.execute("INSERT INTO people(id_user) SELECT id FROM users WHERE username = (?);", (username,)) 
        con.commit()
        return redirect("/login")
    else:
        return render_template("register.html")

    

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/login")


################################## REQUEST ########################################

book_list = []
book_select = {}
#####   SEARCH  #####
@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
    url = 'https://www.googleapis.com/books/v1/volumes'
    pp = pprint.PrettyPrinter(indent=4)
    if request.method == "POST":
        book_list.clear()
        book_name = request.form.get("book_name")
        author = request.form.get("author")
        if author != "":
            query_author = "+inauthor:" + author
        else:
            query_author = ""
        payload = {"q": "intitle:" + book_name + query_author}
        r = requests.get(url, params=payload)
        data = r.json()["items"]
        for books in data:
            if "title" in books["volumeInfo"]:
                book_select["name"] = books['volumeInfo']["title"]
                if "authors" in books["volumeInfo"]:
                    book_select["authors"] = books['volumeInfo']["authors"]
                else:
                    book_select["authors"] = None
                book_list.append(book_select.copy())       
        return render_template("result.html", book_list = book_list)
    else:
        return render_template("search.html")



##### READ #####
@app.route("/result", methods=['GET', 'POST'])
@login_required
def read():
    if request.method == "POST":
        index = int(request.form.get("index"))
        name = str(book_list[index]["name"])
        authors = str(book_list[index]["authors"])
        db.execute("INSERT OR IGNORE INTO books(title, authors) VALUES(?, ?);", (name, authors))
        id_book = db.execute("SELECT id FROM books WHERE title = ? and authors = ?;", (name, authors)).fetchone()[0]
        id_user = db.execute("SELECT id FROM users WHERE username = ?;", (session["user_name"],)).fetchone()[0]
        id_people = db.execute("SELECT id FROM people WHERE id_user = ?;", (id_user,)).fetchone()[0]
        db.execute("INSERT or IGNORE INTO possession(id_book, id_people) VALUES(?,?);", (id_book, id_people))
        con.commit()
        return redirect('/possession')
#########  SHOW DATA TABLE  ##########
@app.route("/possession", methods=['GET', 'POST'])
@login_required
def possession():
    ###### SHOW POSSESSION #######
    id_user = db.execute("SELECT id FROM users WHERE username = ?;", (session["user_name"],)).fetchone()[0]
    id_people = db.execute("SELECT id FROM people WHERE id_user = ?;", (id_user,)).fetchone()[0]
    if request.method == "GET":
        possession_list = []
        books_id = db.execute("SELECT id_book FROM possession WHERE id_people = ?;", (id_people,)).fetchall()
        for items in books_id:
            book_info = db.execute("SELECT title, authors FROM books WHERE id = ?", (items)).fetchall()
            possession_list.append(book_info.copy())
        return render_template("possession.html", possession_list = possession_list)
    ###### DELETE ######
    if request.method == "POST":
        book_name = request.form.get("name")
        book_authors = request.form.get("authors")
        id_book = db.execute("SELECT id  FROM books WHERE title = ? and authors = ?;", (book_name, book_authors)).fetchone()[0]
        db.execute("DELETE FROM possession WHERE id_book = ? and id_people = ?;", (id_book, id_people))
        return redirect("/possession")
    



###############################  EXCHANGE  ################################
@app.route("/exchange_search", methods=['GET', 'POST'])
@login_required
def exchange():
    if request.method == "POST":
        search_result_list = []
        name = request.form.get("name")
        authors = request.form.get("authors")
        print(name, authors)
        #########  sql search like book  ##############
        id_book_list = db.execute("SELECT id FROM books WHERE title LIKE ? and authors LIKE ?;", ("%" + name + "%", "%" + authors + "%")).fetchall()
        print(id_book_list)
        for items in id_book_list:
            book_list = db.execute("SELECT title, authors, id FROM books WHERE id = ?;", (items[0],)).fetchall()
            search_result_list.append(book_list.copy())
        return render_template("exchange_result.html", search_result_list = search_result_list)

    else:
        return render_template("exchange_search.html")


################  MATCH  ########################
@app.route("/match", methods=['GET', 'POST'])
@login_required
def match():
    username_list = []
    id_book = request.form.get("id")
    id_people = db.execute("SELECT id_people FROM possession WHERE id_book = ?;", (id_book,)).fetchall()
    for people in id_people:
        id_user = db.execute("SELECT id_user FROM people where id = ?;", (people[0],)).fetchone()[0]
        username = db.execute("SELECT username FROM users WHERE id = ?;", (id_user,)).fetchone()[0]
        tuple_id_username = (people, username)
        username_list.append(tuple_id_username)
    return render_template("match.html", username_list = username_list, id_book = id_book)

##############  REQUEST  #################
@app.route("/match_request", methods=['GET', 'POST'])
@login_required
def match_request():
    owner = request.form.get("owner")
    requestor = session["user_id"]
    id_book = request.form.get("id_book")
    print(owner, requestor, id_book)
    db.execute("INSERT INTO match_request (owner, requestor, id_book) VALUES(?, ?, ?);", (owner, requestor, id_book))
    con.commit()
    return redirect("/message")

##############  MESSAGE  #################
@app.route("/message", methods=['GET', 'POST'])
@login_required
def message():
    list_return = []
    list_return2 = []
    if request.method == "POST":
        items = request.form.get("items")[1: -1].split(", ")
        owner = session["user_id"]
        id_book = int(items[2])
        requestor = int(items[3])
        if request.form.get("submit_button") == "Accept":
            db.execute("INSERT INTO possession(id_book, id_people) VALUES(?, ?);", (id_book, requestor))
            db.execute("DELETE FROM possession WHERE id_book = ? and id_people = ?;", (id_book, owner))
            db.execute("DELETE FROM match_request WHERE requestor = ? and owner = ? and id_book = ?;", (requestor, owner, id_book) )
        elif request.form.get("submit_button") == "Decline":
            db.execute("DELETE FROM match_request WHERE requestor = ? and owner = ? and id_book = ?;", (requestor, owner, id_book) )
        con.commit()
        return redirect("/message")  
    else:
        owner = session["user_id"]
        request_list = db.execute("SELECT * FROM match_request WHERE owner = ?;", (owner,)).fetchall()
        for items in request_list:
            id_requestor = items[1]
            id_book = items[2]
            requestor = db.execute("SELECT username FROM users WHERE id = ?;", (id_requestor,)).fetchone()[0]
            book = db.execute("SELECT title FROM books WHERE id = ?;", (id_book,)).fetchone()[0]
            list_group = [requestor, book, id_book, id_requestor]
            list_return.append(list_group)
        print(list_return)
        requestor = session["user_id"]
        con.row_factory = sqlite3.Row
        requestor_list =  db.execute("SELECT * FROM match_request WHERE requestor = ?;", (requestor,)).fetchall()
        for items in requestor_list:
            id_owner = items[0]
            id_book = items[2]
            owner = db.execute("SELECT username FROM users WHERE id = ?;", (id_owner,)).fetchone()[0]
            book = db.execute("SELECT title FROM books WHERE id = ?;", (id_book,)).fetchone()[0]
            list_group2 = [owner, book, id_book, id_owner]
            list_return2.append(list_group2)
        print(list_return2)
        return render_template("message.html", list_return = list_return, list_return2 = list_return2)


##############  My profile  #################
@app.route("/create_profile", methods=['GET', 'POST'])
@login_required
def create_profile():
    if request.method == "POST":
        fn = request.form.get("fn")
        ln = request.form.get("ln")
        bd = request.form.get("bd")
        city = request.form.get("city")
        state = request.form.get("state")
        country = request.form.get("country")
        id = session["user_id"]
        db.execute("UPDATE people SET first_name = ?, last_name = ?, birthday = ?, city = ?, state = ?, country = ? WHERE id = ?;", (fn, ln, bd, city, state,country, id))
        con.commit()
        return redirect('/profile')
    else:
        return render_template('create_profile.html')

@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    info = []
    id = session["user_id"]
    Info = db.execute("SELECT first_name, last_name, birthday, city, state, country FROM people where id =?;", (id,)).fetchall()
    for items in Info[0]:
        if items == "":
            items = "no data"
        info.append(items)
        print(items)
    print(info)
    print(Info)
    return render_template('profile.html', info = info)