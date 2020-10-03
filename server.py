#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request
import urllib.parse
import json
import re


app = Flask(__name__)


def parse_request(req):
    """
    Parses application/json request body data into a Python dictionary
    """
    payload = req.get_data()
    payload = urllib.parse.unquote_plus(payload)
    payload = re.sub('payload=', '', payload)
    payload = json.loads(payload)

    return payload


@app.route('/', methods=['GET'])
def index():
    """
    Go to localhost:5000 to see a message
    """
    return ('This is a website.', 200, None)


@app.route('/api/print', methods=['POST'])
def print_test():
    """
    Send a POST request to localhost:5000/api/print with a JSON body with a "p" key
    to print that message in the server console.
    """
    payload = parse_request(request)
    print(payload)
    return ("", 200, None)

if __name__ == '__main__':
    app.run(port=process.env.PORT, use_reloader=True)
