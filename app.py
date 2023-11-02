from flask import Flask, render_template, url_for, redirect, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import InputRequired, Length, Email, ValidationError
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
import requests
from flask import jsonify
import redis

app = Flask(__name__)



app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy()
db.init_app(app)

app.config['SECRET_KEY'] = 'thisisasecretkey'


# Créez une instance de connexion Redis
redis_client = redis.StrictRedis(host='localhost', port=5000, db=0)



login_manager = LoginManager(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)


login_manager.login_view = "login"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True) 
    password = db.Column(db.String(80), nullable=False)
    

class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    asset = db.Column(db.String(10), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    is_open = db.Column(db.Boolean, default=True)

    def __init__(self, user_id, asset, target_price, is_open=True):
        self.user_id = user_id
        self.asset = asset
        self.target_price = target_price
        self.is_open = is_open



login_manager = LoginManager(app)
login_manager.login_view = "login"
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], 
    render_kw={"placeholder": "Username"})
    
    email = StringField(validators=[InputRequired(), Email(), Length(max=120)], 
    render_kw={"placeholder": "Email"})  # Champ email ajouté

    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], 
    render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        existing_user_email = User.query.filter_by(email=email.data).first()
        if existing_user_email:
            raise ValidationError('That email address is already registered. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), 
    Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), 
    Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')
    
@app.route("/")
def accueil():
    exchange_rates = crypto_portfolio()
    return render_template("index.html", exchange_rates=exchange_rates)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)  # Ajout de l'email
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)



@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



@app.route('/set_alert_page')
@login_required
def set_alert_page():
    # Afficher la page "set_alert.html"
    return render_template('set_alert.html')



@app.route('/set_alert', methods=['POST'])
@login_required
def set_alert():
    asset = request.form.get('asset')
    target_price = float(request.form.get('target_price'))
    is_open = True

    # Créez une nouvelle instance d'alerte
    new_alert = Alert(user_id=current_user.id, asset=asset, target_price=target_price, is_open=is_open)


    # Ajoutez l'alerte à la base de données
    db.session.add(new_alert)
    db.session.commit()

    return redirect(url_for('mes_alertes'))


@app.route('/mes_alertes')
@login_required
def mes_alertes():
    user = current_user
    open_alerts = Alert.query.filter_by(user_id=user.id, is_open=True).all()
    closed_alerts = Alert.query.filter_by(user_id=user.id, is_open=False).all()
    return render_template('mes_alertes.html', open_alerts=open_alerts, closed_alerts=closed_alerts)


api_key = "CA89529B-FA3C-44B1-B65D-3BED3D6AAE70"

assets = ['BTC', 'ETH', 'XRP']


def crypto_portfolio():
    exchange_rates = {}

    # Récupérer les taux de change pour chaque crypto-monnaie
    for asset in assets:
        url = f"https://rest.coinapi.io/v1/exchangerate/{asset}/USD"
        headers = {
            "X-CoinAPI-Key": api_key
        }

        response = requests.get(url, headers=headers)
        data = response.json()
        print(data)

        if 'rate' in data:
            exchange_rates[asset] = data['rate']

    return exchange_rates

if __name__ == '__main__':
    app.run(debug=True)
