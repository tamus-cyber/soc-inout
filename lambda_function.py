from __future__ import print_function
import requests

import re
import json
import logging
import os
import urllib.parse


log = logging.getLogger()
log.setLevel(logging.DEBUG)

# OAuth2 and REST API variables

client_id = os.environ['client_id']
client_secret = os.environ['client_secret']
bearer_token = os.environ['bearer']
callback_url = os.environ['callback_url']
auth_url = "https://www.simpleinout.com/oauth/authorize"
token_url = "https://www.simpleinout.com/oauth/token"
base_url = "https://www.simpleinout.com/api/v4"
scope = "write"


# Messages
msg_error       = "There was an error updating your status."
msg_signed_in   = "You have been signed in."
msg_signed_out  = "You have been signed out."


# TODO: The auth function is still under development; if anyone knows how to make a
# Slack client launch an interactive OAuth2 process, please let me know

def auth(userid, message):
    log.info("[simple_sign_in] auth")

    url = auth_url + "?response_type=code&client_id" + client_id + "&redirect_uri=" + callback_url + "&scope=write"

    headers = { "Content-Type": "application/json" }

    resp = requests.get(url, headers=headers)

    log.info("[simple_sign_in] response: " + resp.text)

    return


def sign_in(userid, message):
    log.info("[sign_in] message: " + message)

    url = (base_url + "/users/%d/statuses") % userid

    payload = { "status": { "status": "in", "comment": message } }
    headers = { "Content-Type": "application/json",
                "Authorization": bearer_token }

    resp = requests.post(url, headers=headers, json=payload)
    resp_json = resp.json()

    log.info("[sign_in] response: " + format(resp_json))

    try:
        resp_json
    except NameError:
        response = msg_error
    else:
        if (resp_json['statuses']['status'] == 'in'):
            response = msg_signed_in

    return response


def sign_out(userid, message):
    log.debug("[sign_out] message: " + message)

    url = (base_url + "/users/%d/statuses") % userid

    payload = { "status": { "status": "out", "comment": message } }
    headers = { "Content-Type": "application/json",
                "Authorization": bearer_token }

    resp = requests.post(url, headers=headers, json=payload)
    resp_json = resp.json()

    log.info("[sign_out] response: " + format(resp_json))

    try:
        resp_json
    except NameError:
        response = msg_error
    else:
        if (resp_json['statuses']['status'] == 'out'):
            response = msg_signed_out

    return response


def bot_help(userid, message):
    log.debug("[bot_help]")
    h = "Usage: `sign <in|out|help> [optional message]`"
    return h


commands = {
    'in': sign_in,
    'out': sign_out,
    'help': bot_help
}


def slack_handler(bot_event):
    user_id = urllib.parse.parse_qs(bot_event['body'])['user_id'][0]

    raw_text = urllib.parse.parse_qs(bot_event['body'])['text'][0]
    args = raw_text.split()

    log.debug("[slack_handler] args:{0}".format(args))

    if len(args) >= 1:
        command = args[0]

    if command not in commands:
        command = 'help'

    message = ""
    if len(args) >= 2:
        message = ' '.join(args[1:])

    log.debug("[slack_handler] user_id:'{0}' command:'{1}' message:'{2}'".format(
        user_id, command, message))

    users = json.loads(os.environ['users'])
    userid = users[user_id]

    log.debug("[slack_handler] translated userid: '{0}' user_id:'{1}'".format(
        userid, user_id))

    resp = commands[command](userid, message)

    return resp


# TODO: This goes with the OAuth2 integration; this is the redirect URL handler

def redirect_handler(bot_event):
    raw_text = bot_event['queryStringParameters']

    log.debug("[redirect_handler] queryStringParameters:'{0}'".format(
        raw_text))
    resp = raw_text['authCode']

    return resp


def lambda_handler(event, context):
    assert context
    log.debug(event)

    if (event['httpMethod'] == 'POST') and (event['path'] == '/slack'):
        resp = slack_handler(event)
    elif (event['httpMethod'] == 'GET') and (event['path'] == '/redirect'):
        resp = redirect_handler(event)
    else:
        return {
            'statusCode': 400,
            'body': 'invalid handler request'
        }

    return {
        'statusCode': 200,
        'body': "{0}".format(resp)
    }