from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField, TelField, DateField
from wtforms.validators import DataRequired, Email, Length
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import os

TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
TMDB_ACCESS_TOKEN = os.environ.get("TMDB_ACCESS_TOKEN")
TMDB_MOVIE_SEARCH = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_DETAILS = "https://api.themoviedb.org/3/movie/"
TMDB_IMG_URL = "https://image.tmdb.org/t/p/w500"

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
Bootstrap5(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('NEW_DB_URI', 'sqlite:///Movie_DB.db')
db = SQLAlchemy()
db.init_app(app)

app.secret_key = "Reza123456789123456789"

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_load(user_id):
    return db.get_or_404(User, user_id)


class FindMovie(FlaskForm):
    title = StringField("Movie Title:", validators=[DataRequired()])
    submit = SubmitField("OK")





class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True)
    fname = db.Column(db.String(30), nullable=False)
    lname = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=False)


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    review = db.Column(db.String)
    ranking = db.Column(db.Integer)
    rating = db.Column(db.Float)
    year = db.Column(db.Integer, nullable=False)
    img_url = db.Column(db.String(255), nullable=False)


# url_maker = list(string.ascii_letters)
# url = []
# for i in range(0, 52):
#     url.append(random.choices(url_maker[i]))


with app.app_context():
    db.create_all()


@app.route("/")
def auth():
    return render_template("authenticate.html", logged_in=current_user.is_authenticated)



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        result = db.session.execute(db.select(User).where(User.username == username))
        user = result.scalar()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('The password is wrong. Please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("login.html")


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth'))


@app.route("/sign-up", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8)
        new_user = User(
            username=request.form.get('username'),
            fname=request.form.get('fname'),
            lname=request.form.get('lname'),
            phone=request.form.get('phone'),
            password=hash_and_salted_password,
            age=request.form.get('age')
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('login'))
    return render_template("signup.html")


@app.route("/home")
@login_required
def home():
    results = db.session.execute(db.select(Movie).order_by('rating'))
    all_movies = results.scalars().all()
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()
    return render_template("index.html", movies=all_movies)


@app.route("/find", methods=["GET", "POST"])
@login_required
def find():
    if request.method == 'POST':
        entry_title = request.form.get('title')
        response = requests.get(TMDB_MOVIE_SEARCH, params={'api_key': TMDB_API_KEY,
                                                           'query': entry_title})
        data = response.json()['results']
        return render_template('select.html', options=data)
    return render_template("add.html")


@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    movie_id = request.args.get('id')
    movie = db.get_or_404(Movie, movie_id)
    if request.method == "POST":
        movie_to_update = db.get_or_404(Movie, movie_id)
        movie_to_update.rating = request.form.get('rating')
        movie_to_update.review = request.form.get('review')
        db.session.commit()
        return redirect(url_for('home'))

    return render_template("edit.html", movie=movie)


@app.route("/add_movie", methods=["GET", "POST"])
@login_required
def add_movie():
    movie_id = request.args.get('id')
    URL = f"{TMDB_MOVIE_DETAILS}/{movie_id}"
    if movie_id:
        response = requests.get(URL, params={'api_key': TMDB_API_KEY})
        data = response.json()
        new_movie = Movie(
            title=data["title"],
            year=data["release_date"].split('-')[0],
            description=data["overview"],
            img_url=f"{TMDB_IMG_URL}{data['poster_path']}"
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for('edit', id=new_movie.id))


@app.route("/delete")
@login_required
def delete():
    movie_id = request.args.get('id')
    movie_to_delete = db.get_or_404(Movie, movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/select", methods=["GET", "POST"])
@login_required
def select():
    return render_template("select.html")


if __name__ == '__main__':
    app.run(debug=True)



