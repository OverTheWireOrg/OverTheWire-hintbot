#!/usr/bin/python

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# SQLite
import sqlite3

# system imports
import sys, os.path
from time import gmtime, strftime

def log(m, c=""):
    with open("hints.log", "a") as f:
    	mc = "# logged at " + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " " + c
    	f.write(mc + "\n")
    	f.write(m + "\n")
    print(mc)
    print(m)

class BotIRCComponent(irc.IRCClient):
    def getNickname(self):
        return self.factory.nickname

    def getFullname(self):
        return self.factory.fullname

    def getContributionURL(self):
        return self.factory.contriburl

    def getBaseNickname(self):
        return self.factory.basenickname

    def setNickname(self, nick):
        self.factory.nickname = nick
	self.nickname = nick

    def getTarget(self, channel, nick):
        return channel

    def connectionMade(self): #{{{
    	self.setNickname(self.getNickname())
        irc.IRCClient.connectionMade(self)
#}}}
    def signedOn(self): #{{{
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
#}}}
    def joined(self, channel): #{{{
	self.sendLine("PRIVMSG %s :I am %s. Type !hint <keyword> for a hint or !help for help." % (channel, self.getFullname()))
#}}}
    def alterCollidedNick(self, nickname): #{{{
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
	self.setNickname("%s-%03d" % (self.getBaseNickname(), randint(0, 1000)))
        return self.getNickname()
#}}}
    def privmsg(self, user, channel, msg): #{{{
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        private = False
	prefix = ""
	origmsg = msg

        if channel == self.getNickname():
	    private = True

	msg = msg.strip()
	msgparts = msg.split(" ")
	if not msgparts:
	    return

	cmd = msgparts[0]

	if msgparts:
	    msg = " ".join(msgparts[1:])
	    msgparts = msgparts[1:]
	else:
	    msg = ""
	    msgparts = []

	# private = whether this message was sent to a channel or not
	# cmd = command given
	# msgparts = array of words after the cmd
	# msg = msgparts joined to a string

        try:
            result = {
                "!help": self.handle_HELP,
                #"!goto": self.handle_GOTO,
                "!add": self.handle_ADD,
                "!del": self.handle_DEL,
                "!hint": self.handle_HINT,
                "!list": self.handle_LIST,
            }[cmd](user, channel, cmd, msgparts, msg, private)
	    log(origmsg, "User: %s, Channel: %s" % (user, channel));
        except KeyError:
	    pass
#}}}

    def handle_HELP(self, user, channel, cmd, cmdparts, msg, private): #{{{
	target = self.getTarget(channel, user)
	self.sendLine("NOTICE %s :I am %s from %s. Available commands:" % (target, self.getFullname(), self.getContributionURL()))

	self.sendLine("NOTICE %s :  !help               : this help text" % (target))
	#self.sendLine("NOTICE %s :  !goto <chan>        : make me join channel <chan>" % (target))
	self.sendLine("NOTICE %s :  !add  <hint>        : add a hint" % (target))
	self.sendLine("NOTICE %s :  !del  <id>          : delete hint with given id" % (target))
	self.sendLine("NOTICE %s :  !hint <id|keywords> : show a random hint matching the id or keywords" % (target))
	self.sendLine("NOTICE %s :  !list <keywords>    : list the hints with given keywords" % (target))
#}}}
    def handle_GOTO(self, user, channel, cmd, cmdparts, msg, private): #{{{
	target = self.getTarget(channel, user)
	if msg.startswith("#"):
	    self.sendLine("NOTICE %s :joining %s" % (target, msg))
	    self.join(msg)
	
#}}}
    def handle_ADD(self, user, channel, cmd, cmdparts, msg, private): #{{{
	target = self.getTarget(channel, user)
	if not cmdparts:
	    self.sendLine("NOTICE %s :The add command takes at least 1 argument" % (target))
	else:
	    hint = " ".join(cmdparts)
	    hintid = self.factory.db_addHint(hint)
	    self.sendLine("NOTICE %s :added hint id %d: %s" % (target, hintid, hint))
	
#}}}
    def handle_DEL(self, user, channel, cmd, cmdparts, msg, private): #{{{
	target = self.getTarget(channel, user)
	if not cmdparts or not cmdparts[0].isdigit():
	    self.sendLine("NOTICE %s :The add command takes 1 numeric argument" % (target))
	else:
	    hintid = int(cmdparts[0])
	    (success, hint) = self.factory.db_getHint(hintid)
	    if success:
		self.factory.db_delHint(hintid)
		self.sendLine("NOTICE %s :removed hint %d: %s" % (target, hintid, hint))
	    else:
		self.sendLine("NOTICE %s :hint %d doesn't exist" % (target, hintid))
	
#}}}
    def handle_HINT(self, user, channel, cmd, cmdparts, msg, private): #{{{
	target = self.getTarget(channel, user)
	key = []
	if cmdparts:
	    key = cmdparts

        if len(key) == 1 and key[0].isdigit():
	    hintid = int(key[0])
	    (success, hint) = self.factory.db_getHint(hintid)
	else:
	    (success, hintid, hint) = self.factory.db_getRandomHint(key)

	if success:
	    self.sendLine("NOTICE %s :Hint(%d): %s" % (target, hintid, hint))
	else:
	    self.sendLine("NOTICE %s :no hints found" % (target))
	
#}}}
    def handle_LIST(self, user, channel, cmd, cmdparts, msg, private): #{{{
	target = self.getTarget(channel, user)
	key = []
	if cmdparts:
	    key = cmdparts

	(success, hintids) = self.factory.db_getAllHints(key)
	if success:
	    self.sendLine("NOTICE %s :Hint IDs: %s" % (target, ",".join([str(x) for x in hintids])))
	else:
	    self.sendLine("NOTICE %s :no hints found" % (target))
	
#}}}

class BotIRCComponentFactory(protocol.ClientFactory):
    protocol = BotIRCComponent
    def __init__(self, channel, nick, fullname, url): #{{{
        self.channel = channel
        self.nickname = nick
        self.basenickname = nick
        self.fullname = fullname
        self.contriburl = url
	# if the db file doesn't exist, create it
	self.db_init("hints.db")
# }}}
    def clientConnectionLost(self, connector, reason): #{{{
        """If we get disconnected, reconnect to server."""
        connector.connect()
#}}}
    def clientConnectionFailed(self, connector, reason): #{{{
        print "connection failed:", reason
        reactor.stop()
#}}}
    def db_init(self, fn): #{{{
	if os.path.exists(fn):
	    self.db = sqlite3.connect(fn)
	else:
	    self.db = sqlite3.connect(fn)
	    cu = self.db.cursor()
	    cu.execute("create table hints (hint varchar)")
	    self.db.commit()
    #}}}
    def db_addHint(self, hint): #{{{
	cu = self.db.cursor()
	cu.execute("insert into hints values(?)", (hint,))
	log("# Added hint %d" % cu.lastrowid)
	self.db.commit()
	return cu.lastrowid
    #}}}
    def db_delHint(self, hintid): #{{{
	cu = self.db.cursor()
	cu.execute("delete from hints where rowid=%d" % hintid)
	log("# Deleted hint %d" % hintid)
	self.db.commit()
    #}}}
    def db_getHint(self, hintid): #{{{
	cu = self.db.cursor()
	cu.execute("select hint from hints where rowid=%d" % hintid)
	row = cu.fetchone()
	if row:
	    hint = str(row[0])
	    log("# Getting hint %d: %s" % (hintid, hint))
	    return True, hint
	else:
	    return False, 0
    #}}}
    def db_getAllHints(self, keys=[]): #{{{
	cu = self.db.cursor()
	key = "%" + "%".join(keys) + "%"
	cu.execute("select rowid from hints where hint like ?", (key,))
	rows = cu.fetchall()
	if rows:
	    hintids = [int(x[0]) for x in rows]
	    log("# Getting all hint ids for [%s]: %s" % (key, ",".join([str(x) for x in hintids])))
	    return True, hintids
	else:
	    return False, []
    #}}}
    def db_getRandomHint(self, keys=[]): #{{{
	cu = self.db.cursor()
	key = "%" + "%".join(keys) + "%"
	cu.execute("select rowid, hint from hints where hint like ? order by random() limit 1", (key,))
	row = cu.fetchone()
	if row:
	    hintid = int(row[0])
	    hint = str(row[1])
	    log("# Getting random hint for %s: [%d] %s" % (key, hintid, hint))
	    return True, hintid, hint
	else:
	    return False, 0, 0
    #}}}


if __name__ == '__main__':
    # create factory protocol and application
    f = BotIRCComponentFactory("wargames", "HintBot", "the Wargames Hintbot v0.1", "https://github.com/StevenVanAcker/OverTheWire-hintbot")

    # connect factory to this host and port
    reactor.connectTCP("irc.overthewire.org", 6667, f)

    # run bot
    reactor.run()


