from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def landing_page():
    return "Welcome to our landing page!"

if __name__ == "__main__":
    app.run()