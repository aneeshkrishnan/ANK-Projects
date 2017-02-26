from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

# define for IIS module registration.
wsgi_app = app.wsgi_app

if __name__ == "__main__":
    app.run(host='0.0.0.0')
