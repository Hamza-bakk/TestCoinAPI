from flask import Flask
from flask import request, redirect, url_for, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import InputRequired, Length, Email, ValidationError
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
import requests
from flask import jsonify
import redis
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy()
db.init_app(app)

app.config['SECRET_KEY'] = 'thisisasecretkey'

# Créez une instance de connexion Redis
redis_client = redis.StrictRedis(host='localhost', port=5000, db=0)

log_filename = 'app_log.json'
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

login_manager = LoginManager(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)


session = Session()

login_manager.login_view = "login"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)  # Champ email ajouté
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


login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))  # Utilisez User.query au lieu de session.get
    return user


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    email = StringField(validators=[InputRequired(), Email(), Length(max=120)], render_kw={"placeholder": "Email"})  # Champ email ajouté
    
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

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
    
class EditAlertForm(FlaskForm):
    asset = StringField('Actif', validators=[InputRequired()])
    target_price = FloatField('Prix cible', validators=[InputRequired()])

    
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

@app.route('/about')
@login_required
def about():
    return render_template('about.html')


@app.route('/set_alert_page')
@login_required
def set_alert_page():
    # Afficher la page "set_alert.html"
    return render_template('set_alert.html')



# api_key = "AE1B809C-03C8-4342-B9D4-5378A137F868"
api_key = "9BDAF92C-3C94-4F06-B943-13B5D44A7EF6" 

assets = ['BTC', 'ETH', 'XRP']

@app.route('/erreur_assets.html')
def erreur_assets():
    return render_template('erreur_assets.html')

def get_current_price(asset):
    url = f"https://rest.coinapi.io/v1/exchangerate/{asset}/USD"
    headers = {
        "X-CoinAPI-Key": api_key
    }

    response = requests.get(url, headers=headers)
    data = response.json()
    print(data)

    if 'rate' in data:
        return data['rate']
    else:
        return None
    

@app.route('/set_alert', methods=['POST'])
@login_required
def set_alert():
    asset = request.form.get('asset')
    target_price = float(request.form.get('target_price'))
    is_open = True

    try:
        current_price = get_current_price(asset)
        if current_price is None:
            return redirect(url_for('erreur_assets'))

        new_alert = Alert(user_id=current_user.id, asset=asset, target_price=target_price, is_open=is_open)

        # Si le Prix cible est supérieur au current price
        if target_price > current_price:
            # Passez l'alerte en "close" si le current price est égal ou supérieur au Prix cible
            if current_price >= target_price:
                new_alert.is_open = False

        # Si le Prix cible est inférieur au current price
        if target_price < current_price:
            # Passez l'alerte en "close" si le current price est inférieur ou égal au Prix cible
            if current_price <= target_price:
                new_alert.is_open = False
                
        db.session.add(new_alert)
        db.session.commit()

        if not new_alert.is_open :
            # L'alerte est fermée, affichez un message en Python
            alert_message = f"Notification : Votre alerte {new_alert.id} a été exécutée )"
            print(alert_message)
            # Enregistrez le message dans un fichier journal si nécessaire
            with open('alerts.json', 'a') as log_file:
                log_file.write(alert_message + '\n')
        return redirect(url_for('mes_alertes'))
    except Exception as e:
        # Gérez l'exception liée à la limite de requêtes ici
        return redirect(url_for('erreur_assets'))


@app.route('/mes_alertes')
@login_required
def mes_alertes():
    user = current_user
    # Mettez à jour l'état de toutes les alertes en fonction du prix actuel
    alerts = Alert.query.filter_by(user_id=user.id).all()
    
    for alert in alerts:
        current_price = get_current_price(alert.asset)
        if current_price is not None:
            if alert.target_price >= current_price:
                alert.is_open = False
            else:
                alert.is_open = True

    db.session.commit()  # Mettez à jour la base de données
    open_alerts = [alert for alert in alerts if alert.is_open]
    closed_alerts = [alert for alert in alerts if not alert.is_open]
    return render_template('mes_alertes.html', open_alerts=open_alerts, closed_alerts=closed_alerts)


@app.route('/edit_alert/<int:alert_id>', methods=['GET', 'POST'])
@login_required
def edit_alert(alert_id):
    alert = Alert.query.get(alert_id)

    if not alert:
        return redirect(url_for('mes_alertes'))

    form = EditAlertForm()
    if form.validate_on_submit():
        alert.asset = form.asset.data
        alert.target_price = form.target_price.data
        db.session.commit()
        return redirect(url_for('mes_alertes'))

    form.asset.data = alert.asset
    form.target_price.data = alert.target_price
    return render_template('edit_alert.html', form=form, alert=alert)


@app.route('/delete_alert/<int:alert_id>', methods=['POST'])
@login_required
def delete_alert(alert_id):
    alert = Alert.query.get(alert_id)

    if alert:
        db.session.delete(alert)
        db.session.commit()
    return redirect(url_for('mes_alertes'))


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
