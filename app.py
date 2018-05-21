import os
import sys
import json
from datetime import datetime
import glob
from random import randint
from enum import Enum

import requests
from requests_toolbelt import MultipartEncoder
from flask import Flask, request

app = Flask(__name__)

vowels = ["a", "e", "i", "o", "u", "y"]



@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get(
            "hub.challenge"):
        if not request.args.get(
                "hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message
                    message = messaging_event.get("message")
                    sender_id = messaging_event["sender"]["id"]

                    if len(message.get("attachments", [])) == 1:
                        img_url = message["attachments"][0]["payload"]["url"]
                        img_data = requests.get(img_url, stream=True).raw
                        files = {'image_data': img_data}
                        post_image = requests.post(
                            "https://dog-app-project.appspot.com/predict",
                            files=files)

                        if post_image.status_code == 200:
                            response = post_image.json()
                            breed = response.get('breed')

                            imgs_path = glob.glob(
                                "dog_breed_images/*{}/{}*".format(
                                    breed, breed))

                            returned_img_path = imgs_path[randint(
                                0, (len(imgs_path) - 1))]

                            formatted_breed = breed.replace("_", " ")
                            pronoun = "an" if formatted_breed[
                                0].lower() in vowels else "a"

                            returned_message = "I know! You look like {} {}.".format(
                                pronoun, formatted_breed)
                            send_message(sender_id, returned_message)
                            send_attachment(sender_id, returned_img_path)

                            return "ok", 200
                        else:
                            send_message(
                                sender_id,
                                "Sorry I've encountered an error. Please try again later !"
                            )
                            return "ok", 200

                    elif len(message.get("attachments", [])) > 1:
                        send_message(
                            sender_id,
                            "Sorry, I can not analyze more than one image at a time. Please send me back only one image !"
                        )
                        return "ok", 200
                    else:
                        send_message(
                            sender_id,
                            "Sorry, I can not read text, please send me a picture of your dog or your friend. (Maybe it's the same person)"
                        )
                        return "ok", 200

                if messaging_event.get("delivery"):
                    pass

                if messaging_event.get("optin"):
                    pass

                if messaging_event.get("postback"):
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):
    log("sending message to {recipient}: {text}".format(
        recipient=recipient_id, text=message_text))

    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params,
        headers=headers,
        data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_attachment(recipient_id, img_path):
    payload = {
        'recipient': json.dumps({
            'id': recipient_id
        }),
        'message': json.dumps({
            'attachment': {
                'type': "image",
                'payload': {}
            }
        }),
        'filedata': (os.path.basename(img_path), open(img_path, 'rb'))
    }
    multipart_data = MultipartEncoder(payload)
    multipart_header = {'Content-Type': multipart_data.content_type}
    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    r = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        data=multipart_data,
        params=params,
        headers=multipart_header)
    log(r.json())
    if r.status_code != 200:
        log(r.status_code)
        #log(r.text)


def log(msg, *args,
        **kwargs):  # simple wrapper for logging to stdout on heroku
    try:
        if type(msg) is dict:
            msg = json.dumps(msg)
        else:
            msg = unicode(msg).format(*args, **kwargs)
        print u"{}: {}".format(datetime.now(), msg)
    except UnicodeEncodeError:
        pass  # squash logging errors in case of non-ascii text
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
