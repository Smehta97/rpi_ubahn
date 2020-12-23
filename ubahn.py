import time
from datetime import datetime
from signal import pause
import pytz

import dateutil.parser
import requests

from gpiozero import Button
import lcddriver

TRIGGER_PIN = 25


class BVG:
    def __init__(self, station):
        self.base_url = "https://v5.bvg.transport.rest/"
        self.station_id = self.get_station_id(station)
        # self.display = lcddriver.lcd()

    def get_station_id(self, station):
        response = requests.get(
            self.base_url + f"locations/?query={station}&results=1"
        ).json()
        return response[0].get("id")

    def get_departures(self):
        departures = f"stops/{self.station_id}/departures"

        response = requests.get(self.base_url + departures)

        try:
            response.raise_for_status()
        except:
            self.display(str(response.json()))

        deps_ubahn_verbose = list(
            filter(lambda x: x["line"]["mode"] == "train", response.json())
        )
        deps_ubahn = [
            dict(
                direction=x["direction"],
                when=x["when"],
                # minutes=(datetime.strptime(x["when"][:-6], "%Y-%m-%dT%H:%M:%S") - now).seconds/60,
            )
            for x in deps_ubahn_verbose
        ]

        return deps_ubahn

    def display_departures(self):
        deps = self.get_departures()
        for dep in deps:
            timeout = time.time() + 3
            self.display.lcd_display_string(dep.get("direction"))
            while True:
                now = datetime.now()
                minutes = (
                    (
                        datetime.strptime(dep["when"][:-6], "%Y-%m-%dT%H:%M:%S") - now
                    ).seconds
                    / 60,
                )
                self.display.lcd_display_string(minutes)
                if time.time() > timeout:
                    break


if __name__ == "__main__":
    trigger_button = Button(TRIGGER_PIN)

    bvg_agent = BVG("amrummerstrasse")

    trigger_button.when_pressed = bvg_agent.display_departures

    pause()
