from twisted.spread import pb
from zope.interface import implements
import interfaces

#PerspectiveBroker pour la console (principalement)
class PerspectiveBackend(pb.Root):

    implements(interfaces.IPerspectiveBackend)

    def __init__(self, service):
        self.service = service

    def remote_load(self, listener):
        self.service.registerListener(listener)
        return self.service.load()

    def remote_next(self):
        return self.service.nextPhase()

    def remote_go(self):
        return self.service.launchPhase()

    def remote_pending(self):
        return self.service.pending()
    

