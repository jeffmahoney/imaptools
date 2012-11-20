#!/usr/bin/env python

import os
import email
import sifter.parser

import imaplib
import sys
import re
import email.utils
import datetime
import time

def connect(server, creds):
    conn = imaplib.IMAP4_SSL(server)
    conn.login(creds['u'], creds['p'])
    return conn

# INTERNALDATE "19-Nov-2012 17:37:44 +0100")
def deliver_to(conn, folder, body, flags, timestamp):
    timestamp = imaplib.Time2Internaldate(timestamp)

    conn.append("\"%s\"" % folder, "(%s)" % str.join(" ", flags),
                timestamp, body)

def deliver_message(conn, rules, body):
    msg = email.message_from_string(body)

    timestamp = None
    try:
        timestamp = email.utils.parsedate(msg['Date'])
    except Exception, e:
	pass

    if not timestamp:
        timestamp = datetime.datetime.now().timetuple()

    actions = []

    if rules:
        actions = rules.evaluate(msg)

    fall_through_to_inbox = True
    flags = []
    for action in actions:
        if action[0] == 'keep':
            print ">> %s %s" % ("INBOX", flags)
            deliver_to(conn, "INBOX", body, flags, timestamp)
            fall_through_to_inbox = False
        elif action[0] == 'fileinto':
            fall_through_to_inbox = False
            print ">> %s %s" % (action[1][0], flags)
            deliver_to(conn, action[1][0], body, flags, timestamp)
            pass # Goes into action[1]
        elif action[0] == 'addflag':
            flags += action[1]
            pass # Add flag to list
        elif action[0] == 'setflag':
            flags = action[1]
            pass # Ignore list, set new flags
        elif action[0] == 'removeflag':
            for flag in action[1]:
                if flag in flags:
                    flags.remove(flag)
            pass # Remove flag from list
        elif action[0] == 'stop' or action[0] == 'discard':
            fall_through_to_inbox = False
            break
        else:
            raise Exception("Unknown action %s" % action)

    if fall_through_to_inbox:
        print ">> %s %s" % ("INBOX", flags)
        deliver_to(conn, "INBOX", body, flags, timestamp)
        pass # Goes to inbox


if __name__ == '__main__':

    server = "your-server"
    creds = { 'u' : 'username',
              'p' : 'password' }
    try:
        filter = open('filter.sieve')
    except IOError, e:
        filter = open('/dev/null')

    try:
        rules = sifter.parser.parse_file(filter)
    except Exception, e:
        rules = None

    conn = connect(server, creds)
    body = sys.stdin.read()
    deliver_message(conn, rules, body)
    sys.exit(0)
