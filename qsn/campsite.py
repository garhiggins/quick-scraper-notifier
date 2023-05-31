import argparse
import collections
import datetime
import dateutil.parser
import os
import signal
import threading
import time
import requests
import urllib.parse

from twilio.rest import Client

parser = argparse.ArgumentParser(description="Scrape a url for a value.")
parser.add_argument("campground_ids")  # 232447
parser.add_argument("--dry_run", action="store_true")
parser.add_argument("--start_date")  # 2023-05-01T00%3A00%3A00.000Z
parser.add_argument("--nights", type=int, default=1)
# parser.add_argument("--site_name")

parser.add_argument("--twilio_sid")
parser.add_argument("--twilio_token")
parser.add_argument("--twilio_phone_to")
parser.add_argument("--twilio_phone_from")

parser.add_argument("--iterations", type=int, default=1)

args = parser.parse_args()

CAMPGROUND_NAMES = {
    "232451": "Hodgdon Meadow",
    "232450": "Lower Pines",
    "232447": "Upper Pines",
    "232452": "Crane Flat",
}


def make_twilio_client():
    twilio_sid = args.twilio_sid or os.environ.get("TWILIO_SID")
    twilio_token = args.twilio_token or os.environ.get("TWILIO_TOKEN")
    return Client(twilio_sid, twilio_token)


twilio_phone_to = args.twilio_phone_to or os.environ.get("TWILIO_PHONE_TO")
twilio_phone_from = args.twilio_phone_from or os.environ.get("TWILIO_PHONE_FROM")


def process_response(availabilities):
    open_campgrounds = collections.defaultdict(lambda: collections.defaultdict(int))
    for campground_id, availability in availabilities.items():
        for campsite in availability["campsites"].values():
            for i in range(args.nights):
                day = (start_date + datetime.timedelta(days=i)).strftime(
                    "%Y-%m-%dT00:00:00Z"
                )
                availability = campsite["availabilities"].get(day)
                if availability == "Available":
                    open_campgrounds[campground_id][campsite["site"]] += 1

    if open_campgrounds:
        messages = []
        for campground_id, campsites in open_campgrounds.items():
            max_stay = max(campsites.values())
            campground_name = (
                CAMPGROUND_NAMES[campground_id]
                if campground_id in CAMPGROUND_NAMES
                else campground_id
            )
            messages.append(
                f"{campground_name} has {len(campsites)} sites available on {start_date.strftime('%Y-%m-%d')} for a max stay of {max_stay}."
            )
        message = "\n".join(messages)
        print(message)
        if not args.dry_run:
            client = make_twilio_client()
            client.messages.create(
                to=twilio_phone_to,
                from_=twilio_phone_from,
                body=message,
            )


def fetch_availability(start_date):
    availability = {}
    for campground_id in args.campground_ids.split(","):
        for i in range(5):
            if not args.start_date:
                raise Exception("--start_date is required")
            start_of_month = start_date.replace(day=1)

            url = f"https://www.recreation.gov/api/camps/availability/campground/{campground_id}/month"
            params = {
                "start_date": start_of_month.strftime("%Y-%m-%dT00:00:00.000Z"),
            }
            url = f"{url}?{urllib.parse.urlencode(params)}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                availability[campground_id] = response.json()
                break
            else:
                time.sleep(3)
        else:
            raise Exception(f"Received [{response.status_code}] from recreation.gov")
        if not args.dry_run:
            time.sleep(3)
    return availability


kill_signal = threading.Event()


# Watch for kill signal and gracefully shutdown
def kill_watcher(signal, frame):
    print("Received signal %s" % signal)
    kill_signal.set()


for sig in [signal.SIGINT, signal.SIGTERM]:
    signal.signal(sig, kill_watcher)


start_date = dateutil.parser.parse(args.start_date)
try:
    count = 0
    while count < args.iterations:
        availabilities = fetch_availability(start_date)
        process_response(availabilities)
        count += 1
        if count < args.iterations and kill_signal.wait(timeout=30):
            break
except Exception as e:
    if datetime.datetime.utcnow().hour == 20:
        message = f"Campsite Exception: {e}"
        print(message)
        if not args.dry_run:
            client = make_twilio_client()
            client.messages.create(
                to=twilio_phone_to,
                from_=twilio_phone_from,
                body=message,
            )
    else:
        print("Suppressing Error on off-hour")
    raise
