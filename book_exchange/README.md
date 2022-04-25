# book exchange
#### Video Demo:  https://youtu.be/wJsNKkcryZY
#### Description:
a website that helps people exchange books.
tools used:
html, css, bootstrap, javescript, python, flask, sqlite3, font-awesome, api


## HOME
a nicely design home page with random pictures when refresh
a collapse nav bar with animation and display of username
![showcase 1](/readme_source/1.png)
![showcase 2](/readme_source/2.png)


## login/register 
user first need to register for an account in order to access the
search and exchange function.
![navbar 1](/readme_source/5.png)
![navbar 2](/readme_source/3.png)
![navbar 3](/readme_source/4.png) 
client-side session were used to track
user login status, when click sign out, session were cleared.
```python 
    session["user_name"] = username
    session["user_id"] = user_id
```
```python
@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/login")
```
When register, 2 password needs to match or will direct user to apology
page. When successfully registered, username and password were store in 
the book_exhcnage.db database. When login, if username and password match 
database query will return exactly one line of dictionary and authenticate
user to login
```python
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
```
and create 2 session: username, userid. Now user have been
succussfully loged in.


## SEARCH
user search for the book they own by typing the book name and/or author.
a request was made using google books api
`url = 'https://www.googleapis.com/books/v1/volumes'`
to retrieve 10 books which contain
the book name.
```python 
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
```





 When select the book user owned, redirect to 
possession page where shows all books user owned.


## Profile 
user can fill out the form in profile page to help locate themselves.
![profile](/readme_source/6.png)
user can click edit to change their personal info


## EXCHANGE, MATCH 
user search database of everyother users' possession. If the book he want
was found owning by other user, a request can be send by clicking send 
request. 
```python
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
```

![exchange](/readme_source/7.png)
Owner of the book will get a message of this request,
![exchange](/readme_source/9.png)and
requestor will also have a message that record this ongoing request.
![exchange](/readme_source/8.png)
If the owner see the message and click accept, the book will be transfer
from the owner's possession to the requestor's possession. If decline was 
click, nothing happen.
```python
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
```
 Both the owner and the requestors' message will be
deleted when owner click any of these two buttons.





## DOCUMENTS

book_exchange folder:
main project folder

static folder:
css, pictures, font-awesome css(icon)

templates folder:
all html page with two layout template

readme_source foler:
all img from  readme.md


















