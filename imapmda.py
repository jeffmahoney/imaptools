#!/usr/bin/env python
# vim: sw=4 ts=4 et si:
"""
Parse and potentially edit an email message from stdin and deposit it in
an IMAP store.
From Jeff Mahoney
"""

__revision__ = 'Revision: 0.3'
__author__ = 'Jeff Mahoney'

import os
import email
import sifter.parser
import ConfigParser
from optparse import OptionParser

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
    timestamp = imaplib.Time2Internaldate(time.localtime(timestamp))

    if conn:
        conn.append("\"%s\"" % folder, "(%s)" % str.join(" ", flags),
                    timestamp, body)
    else:
        print "flags=%s" % str.join(" ", flags)
        print "timestamp=%s" % timestamp
        print "=== begin message ==="
        print body
        print "=== end message ==="

def deliver_message(conn, rules, body):
    msg = email.message_from_string(body)

    timestamp = None
    try:
        timestamp = email.utils.mktime_tz(email.utils.parsedate_tz(msg['Date']))
    except Exception, e:
        pass

    if not timestamp:
        timestamp = time.time()

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
        elif action[0] == 'rewrite':
            body = re.sub(action[1][0], action[1][1], body, flags=re.I|re.M)
        else:
            raise Exception("Unknown action %s" % action)

    if fall_through_to_inbox:
        print ">> %s %s" % ("INBOX", flags)
        deliver_to(conn, "INBOX", body, flags, timestamp)
        pass # Goes to inbox

if __name__ == '__main__':
    parser = OptionParser(version='%prog' + __revision__,
                          usage='%prog [options] <configfile>')
    parser.add_option('-n', '--dry-run', action='store_true',
                      help="write modified message to stdout instead of executing on IMAP server", default=False)
    (options, args) = parser.parse_args()

    if not args or len(args) != 1:
        parser.error("must supply config file")
        sys.exit(1)

    config = ConfigParser.ConfigParser()
    try:
        cfile = open(args[0])
    except IOError, e:
        print >>sys.stderr, "error: %s: %s" % (e.args[1], e.filename)
        sys.exit(1)
    config.readfp(cfile)

    if not options.dry_run:
        username = config.get('server', 'username')
        password = config.get('server', 'password')
        hostname = config.get('server', 'hostname')
        creds = { 'u' : username, 'p' : password }

    sieve = config.get('filter', 'sieve')

    try:
        filter = open(sieve)
    except IOError, e:
        filter = open('/dev/null')

    try:
        rules = sifter.parser.parse_file(filter)
    except Exception, e:
        rules = None

    conn = None
    if not options.dry_run:
        conn = connect(hostname, creds)

    body = sys.stdin.read()
    try:
        deliver_message(conn, rules, body)
    except Exception, e:
        print >>sys.stderr, "FAILED: %s" % e
        print >>sys.stderr, body
        sys.exit(1);
    sys.exit(0)
