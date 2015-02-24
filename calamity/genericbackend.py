from twisted.internet import defer, task, reactor
from twisted.spread import pb
from twisted.python import log, failure
from random import randint

import exceptions
import backend


# Meta classe
class Step(object):

    def report(self, status=None):
        if status is not None:
            self.status = status
        self.mel.report( self.id , '%s %s' % (self.name, self.status ) )

    def __str__(self):
        return "%s[%s]" % (str(self.parent), self.name)
    
    def process(self):
        raise exceptions.NotImplementedError()

# classe d'action
class Leaf(Step):
    
    def __init__(self,
                 name,
                 parent,
                 service,
                ):
        self.name = name
        self.parent = parent
        self.service = service

    @defer.inlineCallbacks
    def process(self):
        startmsg = '%s Starting...' % str(self)
        print startmsg
        self.report('RUN')
        
        try:
            sl = randint(1, 10)
            d = yield task.deferLater(reactor, sl, lambda: None)

            if sl > 5:
                self.report('NOK')
                defer.returnValue( defer.fail() )
        
            self.report(' OK')
            defer.returnValue(d)

        except Exception, e:
            self.report('NOK')            
            defer.returnValue( defer.fail() )
        
        
class Container(Step):

    def __init__(self,
                 name,
                 parent,
                 children,
                 service,
                 maxparallel,
                 stopOnError=False):
        """
        params:
            name : nom du conteneur
            parent
            children
            stopOnError : s'arrete a la premiere erreur remontee de la queue
            
        """
        self.name = name
        self.parent = parent
        self.service = service
        self.maxparallel = maxparallel

        self.id = "%s-%s" % ( self.parent.id, self.name ) 
        
        self.queue = [ Step(child, child_childdren, self, self.service) for child, child_children in children.iteritems() ]

    @defer.inlineCallbacks
    def process(self):
        startmsg = '%s Starting...' % str(self)
        print startmsg
        self.report('RUN')
        try:
            # Lancement des traitements en // des servers limite a self.maxparallel
            if self.maxparallel > 0:
                coop = task.Cooperator()
                work = ( server.process() for server in self.servers )
                d = finished_phase = yield defer.DeferredList( [ coop.coiterate(work) for i in xrange(self.maxparallel) ] )
            else:
                d = finished_phase = yield defer.DeferredList( [ s.process() for s in self.servers ] )
        
            self.report(' OK')
            defer.returnValue(d)

        except Exception, e:
            self.report('NOK')            
            defer.returnValue( defer.fail() )
