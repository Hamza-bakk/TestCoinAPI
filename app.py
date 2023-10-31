from flask import Flask, request, Response, render_template
 
app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return Response('', status=200)

@app.route("/") 
def accueil():
    return render_template("index.html")



