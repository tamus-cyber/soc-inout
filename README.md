# soc-inout
TAMUS SOC Slack Integration for Simple In/Out

![GitHub issues](https://img.shields.io/github/issues/tamuscyber/soc-inout) 
![GitHub](https://img.shields.io/github/license/tamuscyber/soc-inout) 
![GitHub release (latest by date)](https://img.shields.io/github/v/release/tamuscyber/soc-inout) 

## Description
This is a Slack integration that hooks with the [Simple In/Out](https://www.simpleinout.com) service.

## Usage
In Slack:

``/sign [in|out|help] [optional message]``

## Technologies Used
- AWS Lambda
- Slack

## Setup
### AWS
#### Lambda
- Deploy the Lambda function to AWS
- Configure these environment variables in Lambda from the info provided by the Slack app:
  - client_id
  - client_secret
  - signing_secret
- Configure the environment variable `users` as a JSON dictionary of Slack user IDs with the value of each being the Simple In/Out user ID, e.g. 
  ``` { "slackID_1": simpleID_1, "slackID_2": simpleID_2, ... } ```

#### API Gateway
- Create an API gateway
- Add a resource called /slack
- Add a POST method to /slack
- Set the POST method resource to the ARN of the Lambda function
- Configure a method resource for status 200 with an `application/json` content type
- Publish the API gateway and copy the invoke URL

### Slack
- Create a new app in https://api.slack.com/apps
- Set the request URL to the API gateway invoke URL
- Create a shortcut called "Sign In" with a callback ID of `in`
- Create a shortcut called "Sign Out" with a callback ID of `out`
- Create a command called `/sign` with a request URL of the API gateway invoke URL
