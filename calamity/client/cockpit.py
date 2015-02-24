from twisted.conch.insults import insults, window
from twisted.spread import pb
from twisted.internet import reactor, defer

from tty import TIOCGWINSZ
from struct import unpack
from fcntl import ioctl

class Cockpit(insults.TerminalProtocol):

    width = 80
    height = 24


    # XXX Should be part of runWithProtocol
    def getWindowSize(self):
        winsz = ioctl(0, TIOCGWINSZ, '12345678')
        winSize = unpack('4H', winsz)
        self.width = winSize[1]
        self.height = winSize[0]
    
    def windowChanged(self, signum, frame):
        self.getWindowSize()
        self.terminalSize(self.width, self.width)

    def _draw(self):
        self.window.redraw(self.width, self.height, self.terminal)

    def _redraw(self):
        self.window.filthy()
        self._draw()

    def _schedule(self, f):
        reactor.callLater(0, f)
    
    @defer.inlineCallbacks
    def connectionMade(self):
        super(Cockpit, self).connectionMade()
        self.terminal.eraseDisplay()
        self.terminal.resetPrivateModes([insults.privateModes.CURSOR_MODE])

        self.getWindowSize()

        # Mise en pace du canvas
        self.window = window.TopWindow(self._draw, self._schedule)
        self.window.reactor = reactor
        # Ligne de commandes
        self.input = window.TextInput(self.width-2, self.parseInputLine)

        self.output = StatusWidget()
        
        # Mise en place des boites serveurs : affichage vertical
        self.servers = window.HBox()
        
        vbox = window.VBox()
        vbox.addChild(self.servers )
        vbox.addChild(window.Border(self.output))
        vbox.addChild(self.input)
        
        self.window.addChild(vbox)
        self.terminalSize(self.width, self.height)
        
        print "Fin de mise en place canvas"
        try:
            # Connection au service
            backend = pb.PBClientFactory()
            reactor.connectTCP("127.0.0.1",8889, backend )
            self.backend = yield backend.getRootObject()
            self.output.addMessage("== Connection to backend established." )
        
        except Exception, e:
            self.output.addMessage("== Ouch !! %s." % e, True)

    def connectionLost(self, reason):
        #self.call.stop()
        #insults.TerminalProtocol.connectionLost(self, reason)
        reactor.stop()

    def cmd_QUIT(self, line):
        #self.connectionLost("QUIT")
        self.terminal.eraseDisplay()
        self.terminal.setPrivateModes([insults.privateModes.CURSOR_MODE])
        self.terminal.loseConnection()

    # Charge un plan de mel
    def cmd_START(self, line):
        self.listener = Listener(self)
        self.backend.callRemote("load", self.listener)#.addCallback(self.displayPending)
        self.cmd_NEXT(None)


    @defer.inlineCallbacks
    def cmd_NEXT(self, line):
        servers = yield self.backend.callRemote("next")
        #self.servers.rebuild(servers)
        self.terminal.eraseDisplay()
        for child in self.servers.children[:]:
            self.servers.remChild(child)
        
        self.widgets = {}
        for server, actions in servers.iteritems() :
            
            serverw = window.VBox()
            # Case server
            svr = window.TextOutput( (None, 1) )
            svr.setText(server + ' ---' )
            self.widgets[server] = svr
            serverw.addChild( svr )
            
            # cases actions
            for a in actions:
                actw = window.TextOutput( (12, 1) )
                actw.setText(a + ' ---' )
                self.widgets["%s-%s" % (server,a) ] = actw
                serverw.addChild( window.Border(actw) )
                #serverw.addChild( actw )
            
            self.servers.addChild( serverw )
        self._redraw()
        
    @defer.inlineCallbacks
    def cmd_GO(self, line):
        phase = yield self.backend.callRemote("go")
        #self.mel = 'Mel phase %s en cours...' % phase
        #self.statusChanged()

    # Parsing de la ligne de commande
    def parseInputLine(self, line):
        if line:
            cmd = line.split()[0].upper()
            special = getattr(self, 'cmd_' + cmd, None)
            if special is not None:
                special(line)
            else:
                self.output.addMessage('== no such command : %s' % cmd)
            self.input.setText('')

    def terminalSize(self, width, height):
        self.width = width
        self.height = height
        self.terminal.eraseDisplay()
        self._redraw()

    def keystrokeReceived(self, keyID, modifier):
        print str(keyID)
        self.window.keystrokeReceived(keyID, modifier)

    def _clear(self):
        self.canvas.clear()

    def _setText(self, text):
        self.input.setText('')
        self.output.addMessage(text)
        
from textwrap import wrap
class StatusWidget(window.TextOutput):
    
    def __init__(self, size=None):
        super(StatusWidget, self).__init__(size)
        self.messages = []

    def formatMessage(self, s, width):
        return wrap(s, width=width, subsequent_indent="  ")

    def sizeHint(self):
        return (None, 10)

    def addMessage(self, message):
        self.messages.append(message)
        self.repaint()

    def render(self, width, height, terminal):
        output = []
        
        for i in xrange(len(self.messages) - 1, -1, -1):
            output[:0] = self.formatMessage(self.messages[i], width - 2)
            if len(output) >= height:
                break
        
        if len(output) < height:
            output[:0] = [''] * (height - len(output))
        
        for n, L in enumerate(output):
            terminal.cursorPosition(0, n)
            terminal.write(L + ' ' * (width - len(L)))

# Listener sur broker : recoit les even du backend (retour de callbacls unitaires)
from twisted.conch.insults.text import flatten, attributes as A
from twisted.conch.insults.helper import CharacterAttribute
#print flatten(
#    A.normal[A.bold[A.fg.red['He'], A.fg.green['ll'], A.fg.magenta['o'], ' ',
#                     A.fg.yellow['Wo'], A.fg.blue['rl'], A.fg.cyan['d!']]],
#     CharacterAttribute())

class Listener(pb.Referenceable):
    
    def __init__(self, console):
        self.console = console
    
    def remote_print(self, arg):
        self.console.output.addMessage( arg )
        print "received %s" % arg

    def remote_report(self, tuple):
        
        (id, msg) = tuple
        
        
        if ' OK' in msg :
            color = '\x1b[32m'
        elif 'NOK' in msg:
            color = '\x1b[31m'
        elif 'RUN' in msg:
            color = "\x1b[34m"
        else:
            color = "\x1b[0m"

        print 'report %s%s\x1b[0m in %s' % (color, msg, id)
        
        if 'server' in msg:
            self.console.widgets[id].setText( "%s%s\x1b[0m" % (color, msg) )
        else:
            self.console.widgets[id].setText( "%s" % msg )
        

