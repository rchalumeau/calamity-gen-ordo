from zope.interface import Interface


class IBackendService(Interface):
    def getPhase(phase):
        """
        return the status for a phase
        """
    def getPhases():
        """
        return the phases
        """
    
class IBackendFactory(Interface):

    def getPhases():
        """
        Return a deferred returning a string.
        """

    def buildProtocol(addr):
        """
        Return a protocol returning a string.
        """


class IPerspectiveBackend(Interface):

    def remote_getPhase(phase):
        """
        Return a user's status.
        """

    def remote_getPhases():
        """
        Return a user's status.
        """
