import requests

# Fonction pour récupérer les données de CoinAPI
def get_coin_data(api_key):
    url = 'https://rest.coinapi.io/v1/assets'
    params = {
        'apikey': api_key,
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None
