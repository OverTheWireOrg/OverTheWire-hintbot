#!/usr/bin/python

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

# SQLite
import sqlite3

# system imports
import sys, os.path
from time import gmtime, strftime

from GenericIRCBot import GenericIRCBot, GenericIRCBotFactory, log

class HintBot(GenericIRCBot):
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

class HintBotFactory(GenericIRCBotFactory):
    def __init__(self, proto, channel, nick, fullname, url): #{{{
        GenericIRCBotFactory.__init__(self, proto, channel, nick, fullname, url)
	# if the db file doesn't exist, create it
	self.db_init("hints.db")
# }}}
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
    f = HintBotFactory(HintBot, "wargames", "HintBot", "the Wargames Hintbot v0.2", "https://github.com/StevenVanAcker/OverTheWire-hintbot")

    # connect factory to this host and port
    reactor.connectTCP("irc.overthewire.org", 6667, f)

    # run bot
    reactor.run()


