#-*- coding: utf-8 -*-
#

# Load Google App Engine Library
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

# Load necessary library (URL, JSON, log and regex)
import urllib
import urllib2
import json
import logging
import re

# Bot's Token & API Address
TOKEN = '286930880:AAE011jfoZGxNWQ14Dqk548mE-qKf9uiCwc'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

# Message that Bot's going to respond
CMD_START     = '/start'
CMD_STOP      = '/stop'
CMD_HELP      = '/help'
CMD_BROADCAST = '/broadcast'

# How to's for using Bot's & Message
USAGE = u"""[HELP] Please choose from options from the below. 
/start - (Start Bot)
/stop  - (Termintate Bot)
/help  - (Show help message)
"""
MSG_START = u'To begin the chatting bot.'
MSG_STOP  = u'To stop the chatting bot.'

# Custom Keyboard
CUSTOM_KEYBOARD = [
        [CMD_START],
        [CMD_STOP],
        [CMD_HELP],
        ]

# Status of Chatting Bot
# Store the Google App Engine's datastore and read from datastore
# Initiate chatting bots, if user types '/start'
# Terminate chatting bots, if user types '/stop'
class EnableStatus(ndb.Model):
    enabled = ndb.BooleanProperty(required=True, indexed=True, default=False,)

def set_enabled(chat_id, enabled):
    u"""set_enabled: Change the status of start or terminate chatting bot
    chat_id:    (integer) Chat ID that start or terminate chatting bot
    enabled:    (boolean) Indicate the status whether chatting bot is started or terminated
    """
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = enabled
    es.put()

def get_enabled(chat_id):
    u"""get_enabled: Return the value of chatting bot's status
    return: (boolean)
    """
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False

def get_enabled_chats():
    u"""get_enabled: Return the value of chat list of chatting bot's status
    return: (list of EnableStatus)
    """
    query = EnableStatus.query(EnableStatus.enabled == True)
    return query.fetch()

# List of functions that sends and receive message
def send_msg(chat_id, text, reply_to=None, no_preview=True, keyboard=None):
    u"""send_msg: Send message
    chat_id:    (integer) Chat ID that sends message
    text:       (string)  Message contents
    reply_to:   (integer) Reply message contents
    no_preview: (boolean) Turn off the URL preview
    keyboard:   (list)    Custom keyboard
    """
    params = {
        'chat_id': str(chat_id),
        'text': text.encode('utf-8'),
        }
    if reply_to:
        params['reply_to_message_id'] = reply_to
    if no_preview:
        params['disable_web_page_preview'] = no_preview
    if keyboard:
        reply_markup = json.dumps({
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False,
            'selective': (reply_to != None),
            })
        params['reply_markup'] = reply_markup
    try:
        urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode(params)).read()
    except Exception as e: 
        logging.exception(e)

def broadcast(text):
    u"""broadcast: Broadcast the message to users that connected to chatting bots
    text:       (string)  Message contents
    """
    for chat in get_enabled_chats():
        send_msg(chat.key.string_id(), text)

# Lists of chatting bot's commands functions
def cmd_start(chat_id):
    u"""cmd_start: Start chatting bots, and broadcast the message
    chat_id: (integer) Chat ID
    """
    set_enabled(chat_id, True)
    send_msg(chat_id, MSG_START, keyboard=CUSTOM_KEYBOARD)

def cmd_stop(chat_id):
    u"""cmd_stop: Terminate the chatting bot and broadcast the message
    chat_id: (integer) Chat ID
    """
    set_enabled(chat_id, False)
    send_msg(chat_id, MSG_STOP)

def cmd_help(chat_id):
    u"""cmd_help: Broadcast the help message
    chat_id: (integer) Chat ID
    """
    send_msg(chat_id, USAGE, keyboard=CUSTOM_KEYBOARD)

def cmd_broadcast(chat_id, text):
    u"""cmd_broadcast: Broadcast the message to the users that connected to chatting bot
    chat_id: (integer) Chat ID
    text:    (string)  Message contents
    """
    send_msg(chat_id, u'Broadcast the message.', keyboard=CUSTOM_KEYBOARD)
    broadcast(text)

def cmd_echo(chat_id, text, reply_to):
    u"""cmd_echo: Echo users message 
    chat_id:  (integer) Chat ID
    text:     (string)  Message contents that sent by the user
    reply_to: (integer) Reply message id
    """
    send_msg(chat_id, text, reply_to=reply_to)

def process_cmds(msg):
    u"""Process the bot commands by getting users message 
    chat_id: (integer) Chat ID
    text:    (string)  Message contents sent by user
    """
    msg_id = msg['message_id']
    chat_id = msg['chat']['id']
    text = msg.get('text')
    if (not text):
        return
    if CMD_START == text:
        cmd_start(chat_id)
        return
    if (not get_enabled(chat_id)):
        return
    if CMD_STOP == text:
        cmd_stop(chat_id)
        return
    if CMD_HELP == text:
        cmd_help(chat_id)
        return
    cmd_broadcast_match = re.match('^' + CMD_BROADCAST + ' (.*)', text)
    if cmd_broadcast_match:
        cmd_broadcast(chat_id, cmd_broadcast_match.group(1))
        return
    cmd_echo(chat_id, text, reply_to=msg_id)
    return

# Define the handler for Web requests
# If there are requests of /me
class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))

# If there are requests of /updates
class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))

# IF there are requests of /set-wehook
class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))

# If there are requests of /webhook (Telegram Bot API)
class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        self.response.write(json.dumps(body))
        process_cmds(body['message'])

# Set the handler for Google App ENgine's web request
app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set-webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)