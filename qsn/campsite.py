import argparse
import datetime
import dateutil.parser
import os
import time
import requests
import urllib.parse

from twilio.rest import Client

parser = argparse.ArgumentParser(description="Scrape a url for a value.")
parser.add_argument("campsite_id")  # 232447
parser.add_argument("--dry_run", action="store_true")
parser.add_argument("--start_date")  # 2023-05-01T00%3A00%3A00.000Z
# parser.add_argument("--end_date")  # 2023-05-01T00%3A00%3A00.000Z
# parser.add_argument("--site_name")

parser.add_argument("--twilio_sid")
parser.add_argument("--twilio_token")
parser.add_argument("--twilio_phone_to")
parser.add_argument("--twilio_phone_from")

args = parser.parse_args()


def make_twilio_client():
    twilio_sid = args.twilio_sid or os.environ.get("TWILIO_SID")
    twilio_token = args.twilio_token or os.environ.get("TWILIO_TOKEN")
    return Client(twilio_sid, twilio_token)


client = make_twilio_client()
twilio_phone_to = args.twilio_phone_to or os.environ.get("TWILIO_PHONE_TO")
twilio_phone_from = args.twilio_phone_from or os.environ.get("TWILIO_PHONE_FROM")


def process_response(availability):
    open_sites = []
    campsite_name = args.campsite_id

    DATE_FORMAT = "%Y-%m-%dT00:00:00Z"
    for campsite_number, campsite in availability["campsites"].items():
        availability = campsite["availabilities"][start_date.strftime(DATE_FORMAT)]
        if availability == "Available":
            campsite_name = campsite["loop"]
            open_sites.append(campsite["site"])

    if open_sites:
        message = f"{campsite_name} has {len(open_sites)} sites available on {start_date.strftime(DATE_FORMAT)}."
        print(message)
        if not args.dry_run:
            client.messages.create(
                to=twilio_phone_to,
                from_=twilio_phone_from,
                body=message,
            )


def fetch_availability(start_date):
    for i in range(1):
        if not args.start_date:
            raise Exception("--start_date is required")
        start_of_month = start_date.replace(day=1)

        url = f"https://www.recreation.gov/api/camps/availability/campground/{args.campsite_id}/month"
        params = {
            "start_date": start_of_month.strftime("%Y-%m-%dT00:00:00.000Z"),
        }
        url = f"{url}?{urllib.parse.urlencode(params)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"received {response.status_code=}")
        time.sleep(2)
    raise Exception(f"Received [{response.status_code}] from recreation.gov")


start_date = dateutil.parser.parse(args.start_date)
try:
    availability = fetch_availability(start_date)
    process_response(availability)
except Exception as e:
    print(datetime.datetime.utcnow().hour)
    if datetime.datetime.utcnow().hour == 19:
        message = f"Campsite Exception: {e}"
        print(message)
        if not args.dry_run:
            client.messages.create(
                to=twilio_phone_to,
                from_=twilio_phone_from,
                body=message,
            )
    else:
        print("Suppressing Error on off-hour")
