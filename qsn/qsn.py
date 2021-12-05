import argparse
import os
import requests
from twilio.rest import Client

parser = argparse.ArgumentParser(description="Scrape a url for a value.")
parser.add_argument("url", help="URL to scrape")
parser.add_argument("--notify_if_present")
parser.add_argument("--notify_if_missing")
parser.add_argument("--twilio_sid")
parser.add_argument("--twilio_token")
parser.add_argument("--twilio_phone_to")
parser.add_argument("--twilio_phone_from")

args = parser.parse_args()

twilio_sid = args.twilio_sid or os.environ.get("TWILIO_SID")
twilio_token = args.twilio_token or os.environ.get("TWILIO_TOKEN")
twilio_phone_to = args.twilio_phone_to or os.environ.get("TWILIO_PHONE_TO")
twilio_phone_from = args.twilio_phone_from or os.environ.get("TWILIO_PHONE_FROM")

client = Client(twilio_sid, twilio_token)

response = requests.get(args.url).text
if args.notify_if_present:
    print(f"present is {args.notify_if_present}")
    if args.notify_if_present in response:
        client.messages.create(
            to=twilio_phone_to,
            from_=twilio_phone_from,
            body=f"QSN: {args.notify_if_present} found at {args.url}"
        )
if args.notify_if_missing:
    print(f"missing is {args.notify_if_missing}")
    if args.notify_if_missing not in response:
        client.messages.create(
            to=twilio_phone_to,
            from_=twilio_phone_from,
            body=f"QSN: {args.notify_if_missing} missing from {args.url}"
        )
