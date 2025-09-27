from flask import Flask, render_template
import os

dir_path = os.path.dirname(__file__)
folder_path = os.path.join(dir_path, "html")

app = Flask(__name__, template_folder = folder_path)

@app.route("/")
def landing_page():
    return render_template("index.html")

@app.route("/itinerary")
def show_iternary():
    return render_template("itinerary.html")

if __name__ == "__main__":
    app.run()