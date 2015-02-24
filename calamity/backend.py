from twisted.internet import defer, task, reactor
from twisted.spread import pb
from twisted.python import log, failure
from random import randint

import actions

class SchedulerItem(pb.Referenceable):

    def report(self, status=None):
        if status is not None:
            self.status = status
        self.mel.report( self.id , '%s %s' % (self.name, self.status ) )

    def __str__(self):
        return "%s[%s]" % (str(self.parent), self.name)



class FailedActionException(Exception, failure.Failure  ):
    pass

class Job(object):
    
    def __init__(self, name):
        self.name = name
    
    def run(self):
        sl = randint(1, 10)
        if sl > 7:
            raise FailedActionException()
        else:
            sleep(sl)

class Action(SchedulerItem):
    def __init__(self, name, parentserver, mel):
        self.name = name
        self.parent = parentserver
        self.mel = mel
        self.id = "%s-%s" % (self.parent.name, self.name)
        self.status = '   '

    @defer.inlineCallbacks
    def process(self):
        print '%s Starting action job' % str(self)
        self.status = 'RUN'
        self.report()

        try:
            sl = randint(1, 10)
            d = yield task.deferLater(reactor, sl, lambda: None)

            if sl == 5:
                self.status = 'NOK'
                self.report()
                defer.returnValue(defer.fail(FailedActionException() ))
                
            print '%s Finishing action job' % str(self)
            self.status = ' OK'
            self.report()
            defer.returnValue(d)
        
        except FailedActionException(), e:
            print '%s Failing action job %s' % (str(self), str(e))
            self.status = 'NOK'
            self.report()
            defer.returnValue(defer.fail())
     


class Server(SchedulerItem):
    def __init__(self, name, actions, parentphase, mel):
        self.name = name
        self.id = self.name
        self.parent = parentphase
        self.mel = mel
        # La queue va etre ici une deferredlist de deferredlist (steps) de deferred (actions)
        self.queue = []
        for step in actions:
            # Traitement des steps
            self.queue.append( [ Action(action, self, self.mel) for action in step ] )
        
    @defer.inlineCallbacks
    def process(self):
        print '%s Starting server job' % str(self)
        self.status = 'RUN'
        self.report()
        try:
            
            for s in self.queue:
                step = yield defer.DeferredList( [ action.process() for action in s ],
                                                fireOnOneErrback=1
                                                )
            
            self.status=' OK'
            self.report()
            
            defer.returnValue(step)
        except Exception, e:
            print "FAILURE %s : %s" % (str(self), e)
            self.status = 'NOK'
            self.report()
            
            #raise FailedActionException()
            #log.err
    
    def return_server(self):
        actions = [] 
        for step in self.queue:
            for action in step:
                actions.append(action.name)
        
        return actions

class Phase(SchedulerItem):
    
    def __init__(self, name, servers, maxparallel, mel):
        self.name = name
        self.parent = ''
        self.mel = mel
        self.maxparallel = maxparallel
        print str(servers)
        self.servers = [ Server(server, actions, self, self.mel) for server, actions in servers.iteritems() ]
        self.returned_servers = {}
        
        for server in self.servers : 
            self.returned_servers[server.id] = server.return_server()
    
    @defer.inlineCallbacks
    def process(self):
        startmsg = '%s Starting...' % str(self)
        print startmsg
        self.mel.reportToListener(startmsg)
        try:
            # Lancement des traitements en // des servers limite a self.maxparallel
            if self.maxparallel > 0:
                coop = task.Cooperator()
                work = ( server.process() for server in self.servers )
                d = finished_phase = yield defer.DeferredList( [ coop.coiterate(work) for i in xrange(self.maxparallel) ] )
            else:
                d = finished_phase = yield defer.DeferredList( [ s.process() for s in self.servers ] )
                
        
            endmsg = '%s Finished !' % str(self)
            print endmsg
            self.mel.reportToListener(endmsg)
            defer.returnValue(d)
        except Exception, e:
            endmsg = '%s Finished with errors !' % str(self)
            self.mel.reportToListener(endmsg)

        
        
        
        