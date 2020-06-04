from __future__ import print_function

import boto3
import hashlib
import hmac
import json
import logging
import os
import re
import requests
import time
import urllib.parse


log = logging.getLogger()
log.setLevel(logging.DEBUG)

# OAuth2 and REST API variables

client_id = os.environ['client_id']
client_secret = os.environ['client_secret']
callback_url = os.environ['callback_url']
auth_url = "https://www.simpleinout.com/oauth/authorize"
token_url = "https://www.simpleinout.com/oauth/token"
base_url = "https://www.simpleinout.com/api/v4"
scope = "write"


# Hook to DynamoDB for the access/refresh tokens

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('soc-inout')
token_data = table.get_item(
    Key={'env': 'prod'}
)
bearer_token = "Bearer " + token_data['Item']['access_token']
token_expires = token_data['Item']['expires']

# If the access token has expired, use refresh token to get a new one

if (time.time() > token_expires):
    log.info("[simple_sign_in] refresh token")

    url = token_url

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_data['Item']['refresh_token']
    }
    headers = { "Content-Type": "application/json" }

    resp = requests.post(url, headers=headers, json=payload)
    resp_json = resp.json()

    log.info("[simple_sign_in] refresh token response: " + format(resp_json))

    try:
        resp_json
    except NameError:
        response = msg_error
    else:
        table.put_item(
            Item={
                'env': 'prod',
                'access_token': resp_json['access_token'],
                'expires': (resp_json['created_at'] + resp_json['expires_in']),
                'refresh_token': resp_json['refresh_token']
            }
        )
        log.info("[simple_sign_in] updated DynamoDB with new token data")
        bearer_token = "Bearer " + resp_json['access_token']
else:
    log.info("[simple_sign_in] using existing token data")


# Messages
msg_error       = "There was an error updating your status."
msg_signed_in   = "You have been signed in."
msg_signed_out  = "You have been signed out."


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
    body = urllib.parse.parse_qs(bot_event['body'])

    msg = 'v0:' + bot_event['headers']['X-Slack-Request-Timestamp'] + ':' + bot_event['body']
    hash = hmac.new(bytes(os.environ['signing_secret'], 'latin-1'), msg.encode(), hashlib.sha256)
    hash_digest = hash.hexdigest()

    log.debug("[slack_handler] Asserted signature:'{0}' Computed signature:'{1}'".format(
        bot_event['headers']['X-Slack-Signature'], hash_digest))

    if ('v0=' + hash_digest) != bot_event['headers']['X-Slack-Signature']:
        resp = "Invalid signature from Slack"

        return resp

    # Initialize variables used in processing the command
    command = ''
    message = ''

    if 'payload' in body.keys():
        payload_args = json.loads(body['payload'][0])
        user_id = payload_args['user']['id']

        log.debug("[slack_handler] user_id:'{0}' payload_args:'{1}'".format(
            user_id, payload_args))

        resp = "Made it through payload"
    else:
        payload_args = ''
        log.debug("[slack_handler] no payload_args")

    if 'text' in body.keys():     # Process slash command
        text_args = body['text'][0].split()

        if len(text_args) >= 1:
            command = text_args[0]

        if command not in commands:
            command = 'help'

        if len(text_args) >= 2:
            message = ' '.join(text_args[1:])

        if len(text_args) >= 1:
            command = text_args[0]

        if command not in commands:
            command = 'help'

        if len(text_args) >= 2:
            message = ' '.join(text_args[1:])

        user_id = urllib.parse.parse_qs(bot_event['body'])['user_id'][0]
    elif 'callback_id' in payload_args.keys():  # Process shortcut
        if payload_args['callback_id'] in ['in', 'out']:
            command = payload_args['callback_id']
            user_id = payload_args['user']['id']

    if command != 'help':
        users = json.loads(os.environ['users'])
        userid = users[user_id]

        log.debug("[slack_handler] user_id:'{0}' translated userid:'{1}' command:'{2}' message:'{3}'".format(
            user_id, userid, command, message))

        resp = commands[command](userid, message)
    else:
        text_args = ''
        log.debug("[slack_handler] no command args")


    return resp


def lambda_handler(event, context):
    assert context
    log.debug(event)

    if (event['httpMethod'] == 'POST') and (event['path'] == '/slack'):
        resp = slack_handler(event)
    else:
        return {
            'statusCode': 400,
            'body': 'invalid handler request'
        }

    return {
        'statusCode': 200,
        'body': "{0}".format(resp)
    }
