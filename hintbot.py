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
    DontCheckARGC = -1
    commandData = {}
    commands = {}

    def __init__(self):
	self.commandData = {
	    "!help": { 
	    	"fn": self.handle_HELP, 
		"argc": 0, 
		"tillEnd": False,
		"help": "this help text",
	    },
	    "!goto": { 
	    	"fn": self.handle_GOTO, 
		"argc": 1, 
		"tillEnd": False,
		"help": "go to the given channel",
	    },
	    "!add": { 
	    	"fn": self.handle_ADD, 
		"argc": 1, 
		"tillEnd": True,
		"help": "add a hint",
	    },
	    "!del": { 
	    	"fn": self.handle_DEL, 
		"argc": 1, 
		"tillEnd": True,
		"help": "delete a hint by ID",
	    },
	    "!list": { 
	    	"fn": self.handle_LIST, 
		"argc": self.DontCheckARGC, 
		"tillEnd": True,
		"help": "list all hints matching the given keywords",
	    },
	    "!hint": { 
	    	"fn": self.handle_HINT, 
		"argc": self.DontCheckARGC, 
		"tillEnd": True,
		"help": "get a random hint matching the given ID or keywords",
	    },
	}

	self.commands = {
	    # only in direct user message, first word is the command
	    "private": ["!help", "!add", "!del", "!list", "!hint"],
	    # only in channels, first word must be the command
	    "public": ["!help", "!add", "!del", "!list", "!hint"],
	    # only in channels, first word is the name of this bot followed by a colon, second word is the command
	    "directed": ["!help", "!add", "!del", "!list", "!hint"],
	}

    def getCommandRecords(self, msgtype):
        out = {}
	for c in self.commands[msgtype]:
	    out[c] = self.commandData[c]
	return out

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

    def getReplyTarget(self, msgtype, user, channel):
        return {
	    "public": channel,
	    "directed": channel,
	    "private": user
	}[msgtype]

    def sendMessage(self, msgtype, user, channel, msg):
        prefix = user+": " if msgtype == "directed" else ""
	self.sendLine("PRIVMSG %s :%s%s" % (self.getReplyTarget(msgtype, user, channel), prefix, msg))

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
	origmsg = msg
	error = ""

	# determine the type of command, select the correct set of handlers
	# and, in case of a directed message, strip of this bot's nickname
        if channel == self.getNickname(): 
	    # private message
	    msgtype = "private"
	else:
	    # check if directed at this nickname
	    key = self.getNickname() + ":"
	    keylen = len(key)
	    if msg.startswith(key):
	        msgtype = "directed"
	        msg = msg[keylen:]
	    else:
	        msgtype = "public"
	recset = self.getCommandRecords(msgtype)
	    	
	# split into words, words[0] contains the command if it exists
	words = msg.split()

	if len(words):
	    cmd = words[0]
	    if cmd in recset:
		rec = recset[cmd]
		c = rec["argc"]
		if c == self.DontCheckARGC:
		    words = msg.split(None)
		else:
		    if len(words) >= (c+1):
			words = msg.split(None, c if rec["tillEnd"] else c+1)[:(c+1)]
		    else:
			error = "Not enough parameters: expecting %d, received %d" % (c, len(words) - 1)
	    else:
	        if msgtype == "public":
		    return
		error = "Unknown command %s" % (cmd)
	else:
	    if msgtype == "public":
		return
	    error = "What is it? Use !help if you're confused..."

	if error:
	    self.sendMessage(msgtype, user, channel, error)
	    print "Error msgtype=%s: [%s]" % (msgtype, error)
	    return
	    
	rec["fn"](msgtype, user, channel, *(words))
	log(origmsg, "User: %s, Recip: %s, Target: %s" % (user, channel, self.getReplyTarget(msgtype, user, channel)));
#}}}

    def handle_HELP(self, msgtype, user, recip, cmd): #{{{
	self.sendMessage(msgtype, user, recip, "I am %s from %s. Available commands (m=message, c=channel, d=directed):" % (self.getFullname(), self.getContributionURL()))
	cmds = self.commandData.keys()
	cmds.sort()
	for k in cmds:
	    prefix = "["
	    prefix += "m" if k in self.commands["private"] else "-"
	    prefix += "c" if k in self.commands["public"] else "-"
	    prefix += "d" if k in self.commands["directed"] else "-"
	    prefix += "]"

	    helptext = self.commandData[k]["help"]
	    c = self.commandData[k]["argc"]
	    if c == self.DontCheckARGC:
	        args = "..."
	    else:
		args = " ".join(["<%s>" % chr(x+ord('a')) for x in range(0,c)])

	    self.sendMessage(msgtype, user, recip, "  %s %10s %-10s : %s" % (prefix, k,args, helptext))
#}}}
    def handle_GOTO(self, msgtype, user, recip, cmd, newchan): #{{{
	if newchan.startswith("#"):
	    self.sendMessage(msgtype, user, recip, "joining %s" % newchan)
	    self.join(newchan)
#}}}
    def handle_ADD(self, msgtype, user, recip, cmd, hint): #{{{
	    hintid = self.factory.db_addHint(hint)
	    self.sendMessage(msgtype, user, recip, "added hint id %d: %s" % (hintid, hint))
	
#}}}
    def handle_DEL(self, msgtype, user, recip, cmd, hintid): #{{{
	if not hintid.isdigit():
	    self.sendMessage(msgtype, user, recip, "The add command takes 1 numeric argument")
	else:
	    hintid = int(hintid)
	    (success, hint) = self.factory.db_getHint(hintid)
	    if success:
		self.factory.db_delHint(hintid)
		self.sendMessage(msgtype, user, recip, "removed hint %d: %s" % (hintid, hint))
	    else:
		self.sendMessage(msgtype, user, recip, "hint %d doesn't exist" % (hintid))
	
#}}}
    def handle_HINT(self, msgtype, user, recip, cmd, keymsg=""): #{{{
	key = keymsg.split()

        if len(key) == 1 and key[0].isdigit():
	    hintid = int(key[0])
	    (success, hint) = self.factory.db_getHint(hintid)
	else:
	    (success, hintid, hint) = self.factory.db_getRandomHint(key)

	if success:
	    self.sendMessage(msgtype, user, recip, "Hint(%d): %s" % (hintid, hint))
	else:
	    self.sendMessage(msgtype, user, recip, "no hints found")
	
#}}}
    def handle_LIST(self, msgtype, user, recip, cmd, keymsg=""): #{{{
	key = keymsg.split()

	(success, hintids) = self.factory.db_getAllHints(key)
	if success:
	    self.sendMessage(msgtype, user, recip, "Hint IDs: %s" % (",".join([str(x) for x in hintids])))
	else:
	    self.sendMessage(msgtype, user, recip, "no hints found")
	
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
    f = BotIRCComponentFactory("wargames", "HintBot", "the Wargames Hintbot v0.2", "https://github.com/StevenVanAcker/OverTheWire-hintbot")

    # connect factory to this host and port
    reactor.connectTCP("irc.overthewire.org", 6667, f)

    # run bot
    reactor.run()


