import os
import sys
import json

import requests
from flask import Flask, request

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def webook():

    if request.method == "GET":
        # when endpoint is registered as a webhook, it must
        # return the 'hub.challenge' value in the query arguments
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
            if not request.args.get("verify_token") == os.environ["VERIFY_TOKEN"]:
                return "Verification token mismatch", 403
            return request.args["hub.challenge"], 200

    else:  # POST
        data = request.get_json()
        log(data)

        if data["object"] == "page":

            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:

                    if messaging_event.get("message"):  # someone sent us a message

                        sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                        recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                        message_text = messaging_event["message"]["text"]  # the message's text

                        send_message(sender_id, "got it, thanks!")

                    if messaging_event.get("delivery"):
                        continue  # delivery confirmation

                    if messaging_event.get("optin"):
                        continue  # optin confirmation

                    if messaging_event.get("postback"):
                        continue  # postback

    return "ok"


def send_message(recipient_id, message_text):
    log("--------------------")
    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    log(r.text)
    log(r.status_code)
    log("--------------------")


def log(message):  # simple wrapper for logging on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)