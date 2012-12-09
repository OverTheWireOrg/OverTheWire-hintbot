#!/usr/bin/python

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys

def log(m):
    print m;

class BotIRCComponent(irc.IRCClient):
    def getNickname(self):
        return self.factory.nickname

    def getFullname(self):
        return self.factory.fullname

    def getBaseNickname(self):
        return self.factory.basenickname

    def setNickname(self, nick):
        self.factory.nickname = nick
	self.nickname = nick

    def getTarget(self, channel, nick):
        return nick

    def connectionMade(self): #{{{
    	self.setNickname(self.getNickname())
        irc.IRCClient.connectionMade(self)
#}}}
    def signedOn(self): #{{{
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
#}}}
    def joined(self, channel): #{{{
	self.sendLine("PRIVMSG %s :I am %s. Type !hint <levelname> for a hint or !help for help." % (channel, self.getFullname()))
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

        if channel == self.getNickname():
	    private = True

	msg = msg.strip()
	msgparts = msg.split(" ")
	if len(msgparts) < 1:
	    return

	cmd = msgparts[0]

	if len(msgparts) > 1:
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
                "!goto": self.handle_GOTO,
            }[cmd](user, channel, cmd, msgparts, msg, private)
        except KeyError:
	    pass
#}}}

    def handle_HELP(self, user, channel, cmd, cmdparts, msg, private): #{{{
    	#FIXME
	target = self.getTarget(channel, user)
	self.sendLine("NOTICE %s :I am %s. Available commands:" % (target, self.getFullname()))

	self.sendLine("NOTICE %s :  !help          : this help text" % (target))
	self.sendLine("NOTICE %s :  !goto <chan>   : make me join channel <chan>" % (target))
#}}}
    def handle_GOTO(self, user, channel, cmd, cmdparts, msg, private): #{{{
	target = self.getTarget(channel, user)
	if msg.startswith("#"):
	    self.sendLine("NOTICE %s :joining %s" % (target, msg))
	    self.join(msg)
	
#}}}
    # FIXME extra commands:
    #	addhint
    #	delhint
    #	hint <level>
    #	allhints

class BotIRCComponentFactory(protocol.ClientFactory):
    protocol = BotIRCComponent
    def __init__(self, channel, nick, fullname): #{{{
        self.channel = channel
        self.nickname = nick
        self.basenickname = nick
        self.fullname = fullname
# }}}
    def clientConnectionLost(self, connector, reason): #{{{
        """If we get disconnected, reconnect to server."""
        connector.connect()
#}}}
    def clientConnectionFailed(self, connector, reason): #{{{
        print "connection failed:", reason
        reactor.stop()
#}}}


if __name__ == '__main__':
    # create factory protocol and application
    f = BotIRCComponentFactory("x", "hintbot", "the Wargames Hintbot")

    # connect factory to this host and port
    reactor.connectTCP("localhost", 6667, f)

    # run bot
    reactor.run()


