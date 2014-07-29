imaptools
=========

Scripts for working with IMAP servers

imapmda
=======
imapmda is an MDA that will upload a message to an IMAP server after
processing it through a sieve filter script. It is meant for use with
tools like fetchmail.

It depends on the sifter package, available here:
https://github.com/jeffmahoney/sifter

It is typically used via fetchmail using the following rule:
mda "/home/user/bin/imapmda.py /home/user/.config/imapmda.ini"
