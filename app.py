from flask import Flask, request, Response, render_template, redirect, url_for
import requests
 
app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return Response('', status=200)

@app.route("/")
def accueil():
    exchange_rates = crypto_portfolio()
    return render_template("index.html", exchange_rates=exchange_rates)


@app.route("/about")
def about():
    return render_template("about.html")

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

        if 'rate' in data:
            exchange_rates[asset] = data['rate']

    return exchange_rates

if __name__ == '__main__':
    app.run(debug=True)
