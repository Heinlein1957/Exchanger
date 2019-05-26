'''from flask import Flask, redirect

server = Flask(__name__)


@server.route("/ym", methods=['POST', 'GET'])
def get_message():
    return '!!!!!!!!!!!!!!!!1', 200


@server.route("/")
def webhook():
    return redirect('https://google.com')


server.run(host="0.0.0.0", port=80)'''
