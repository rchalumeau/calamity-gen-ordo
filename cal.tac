# Do everything properly
from twisted.application import internet, service
from twisted.python import components
from twisted.spread import pb

from calamity import interfaces, scheduler, messaging

application = service.Application('MEL Scheduler')
serviceCollection = service.IServiceCollection(application)

# Principal Service
my_backend = scheduler.Mel()

# Declaration de la perspective par adapter
components.registerAdapter(messaging.PerspectiveBackend,
                           interfaces.IBackendService,
                           interfaces.IPerspectiveBackend)

# Ecoute du port de connexion dce la perspective
internet.TCPServer(
    8889,
    pb.PBServerFactory(
                    interfaces.IPerspectiveBackend(my_backend)
    )
).setServiceParent(serviceCollection)


