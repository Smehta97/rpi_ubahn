import json
import pprint
import time
from datetime import datetime
from itertools import groupby
from signal import pause

import dateutil.parser
import requests

from colorzero import Color
from gpiozero import RGBLED, Button

R_pin, G_pin, B_pin = 17, 27, 22
oslo_pin, steglitz_pin = 24, 25


class BVG:
    def __init__(self, base_url, led):
        self.base_url = base_url
        self.led = led

    def check_status_code(self, response, query):
        if str(response.status_code)[:1] != 2:
            while response.status_code != 200:
                print(response.status_code)
                time.sleep(2)
                response = requests.get(self.base_url + query)

        return response.json()

    def get_closest_station(self, lat_long):
        latitude, longitude = lat_long
        stops_q = f"stops/nearby?latitude={latitude}&longitude={longitude}"

        response = requests.get(self.base_url + stops_q)
        data = self.check_status_code(response, stops_q)

        return sorted(data, key=lambda station: station["distance"])[0]

    def get_departures(self, station_id, direction=None):
        time_q = f"stations/{station_id}/departures"
        response = requests.get(self.base_url + time_q)
        data = self.check_status_code(response, time_q)

        return data

    def get_time(self, departures):
        subway_only = list(
            filter(lambda d: d["line"]["product"] == "subway", departures)
        )

        u_osloer_str = list(
            filter(lambda d: d["direction"] == "U Osloer Str.", subway_only)
        )
        earliest_o = sorted(u_osloer_str, key=lambda t: t["when"])[0]

        u_rathaus_steglitz = list(
            filter(lambda d: d["direction"] == "S+U Rathaus Steglitz", subway_only)
        )
        earliest_rs = sorted(u_rathaus_steglitz, key=lambda t: t["when"])[0]

        departure_times = {
            "U Osloer Str.": {"when": earliest_o["when"], "delay": earliest_o["delay"]},
            "S+U Rathaus Steglitz": {
                "when": earliest_rs["when"],
                "delay": earliest_rs["delay"],
            },
        }

        return departure_times

    def should_i_leave_now(self, times, where_to):
        assert where_to in times.keys()
        # print(times)

        seconds_in_day = 24 * 60 * 60

        to_date = dateutil.parser.parse(times[where_to]["when"]).replace(tzinfo=None)
        difference = to_date - datetime.now()
        print(datetime.now())
        timedelta = divmod(difference.days * seconds_in_day + difference.seconds, 60)

        minutes_until = timedelta[0]
        if timedelta[1] >= 35:
            minutes_until += 1

        print(minutes_until)
        if minutes_until >= 5:
            return 0
        elif minutes_until == 4:
            return 1
        elif minutes_until == 0:
            return 0
        elif minutes_until == -1:
            return 1
        else:
            return 2

    def set_led_color(self, ans):
        if ans == 0:
            self.led.color = Color("green")
        elif ans == 1:
            self.led.color = Color("yellow")
        else:
            self.led.color = Color("red")

        time.sleep(2)
        self.led.off()

    def display_oslo(self):
        self.led.color = Color("cyan")
        self.led.blink()

        my_station = self.get_closest_station((52.541839, 13.349102))
        departures = self.get_departures(my_station["id"])
        times = self.get_time(departures)
        ans = self.should_i_leave_now(times, "U Osloer Str.")

        self.set_led_color(ans)

    def display_steglitz(self):
        self.led.color = Color("cyan")
        self.led.blink()

        my_station = self.get_closest_station((52.541839, 13.349102))
        departures = self.get_departures(my_station["id"])
        times = self.get_time(departures)
        ans = self.should_i_leave_now(times, "S+U Rathaus Steglitz")

        self.set_led_color(ans)


if __name__ == "__main__":
    led = RGBLED(R_pin, G_pin, B_pin)
    base_url = "https://2.bvg.transport.rest/"
    oslo_button = Button(oslo_pin)
    steglitz_button = Button(steglitz_pin)

    bvg_agent = BVG(base_url, led)

    oslo_button.when_pressed = bvg_agent.display_oslo
    steglitz_button.when_pressed = bvg_agent.display_steglitz

    pause()

    # while True:
    #     if oslo_button.is_pressed:
    #         display_oslo(bvg_agent, led)
    #     elif steglitz_button.is_pressed:
    #         display_steglitz(bvg_agent, led)
