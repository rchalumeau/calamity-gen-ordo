from twisted.application import service

from twisted.internet import defer, protocol, task
from twisted.internet.task import cooperate

from zope.interface import implements
import interfaces

from backend import Action, Phase, Server
import sys

#from rdq.rdq import ResizableDispatchQueue
#from rdq.job import Job
from twisted.python import log

from testplan import plan 

STATUS = {}
STATUS[0] = "PENDING"
STATUS[1] = "UNDERWAY"
STATUS[2] = "FINISHED"
STATUS[3] = "FAILED"
STATUS[4] = "CANCELLED"

class Mel(service.Service):

    implements(interfaces.IBackendService)
    
    # Chargement du plan de MEl
    def load(self):
        # Chargement d'un plan de test
        self.plan = plan
        
        # Chargement dans une liste des phases a traiter
        self.queue = defer.DeferredQueue()
        for phase,servers in self.plan.iteritems():
            if 'bridage' in servers:
                maxparallel = servers['bridage']
                del servers['bridage']
            else:
                maxparallel = 0
            self.queue.put( Phase(phase, servers, maxparallel, self) )
        
        print "Chargement de la premiere phase"
        #return self.nextPhase()
        
    # Lancement de la phase suivante
    @defer.inlineCallbacks
    def nextPhase(self):
            
        self.currentphase = yield self.queue.get()

        msg = "Loading the phase %s" % self.currentphase.name
        self.reportToListener(msg)
        print msg
        #ret = [ server.name for server in self.currentphase.servers ]
        # Renvoie la liste des servers a traiter dans cette phase
        defer.returnValue(self.currentphase.returned_servers)

    @defer.inlineCallbacks
    def launchPhase(self):
        print "Lancement de la phase %s" % self.currentphase.name
        yield self.currentphase.process()
        

    # Enregistrement du perspective listener pour piloter la console cliente
    def registerListener(self, listener):
        self.listener = listener

    def reportToListener(self, msg):
        self.listener.callRemote("print", msg)

    def report(self, id, msg):
        tuple = (id, msg)
        self.listener.callRemote("report", tuple )

    # Handle du service
    def startService(self):
        self._read()
        service.Service.startService(self)

    def stopService(self):
        
        self.reportToListener("Service stopping")
        service.Service.stopService(self)
        self.call.cancel()

