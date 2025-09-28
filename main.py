from flask import Flask, request, render_template
from parse import get_general_summary, get_path, get_local_events, get_hotel_info
import asyncio
import json
import os

app = Flask(__name__)

'''async def get_info(location):
    summary = await get_general_summary(location)
    return summary'''

@app.route("/", methods = ["GET", "POST"])
def landing_page():
    if request.method == "POST":
        location = request.form.get("location")
        origin = request.form.get("origin")
        num_of_people = request.form.get("num_of_companions")
        stay_start = request.form.get("time_of_start_stay")
        stay_end = request.form.get("time_of_end_stay")
        num_of_rooms = request.form.get("num_of_rooms")
        trip_goal = request.form.get("purpose")

        # THERE HAS TO BE A BETTER WAY OF DOING THIS!! ITS 3:38 AM
        # It's 7:50 and i would figure out a better way but i dont want to idiots
        summary_result = asyncio.run(get_general_summary(location))
        formatted_summary = json.loads(summary_result)

        route_result = asyncio.run(get_path(location=location, origin=origin))
        formatted_routes = json.loads(route_result)

        event_result = asyncio.run(get_local_events(location=location, goal=trip_goal))
        formatted_events = json.loads(event_result)

        hotels_result = asyncio.run(get_hotel_info(location, stay_start, stay_end, num_of_people, num_of_rooms))
        formatted_hotels = json.loads(hotels_result)
        print(formatted_hotels)

        return render_template(
            "data.html", 
            summary = formatted_summary[0], #??? Yeah deal with it
            routes = formatted_routes,
            events = formatted_events,
            hotels = formatted_hotels
        )

    return render_template("index.html")

if __name__ == "__main__":
    app.run()