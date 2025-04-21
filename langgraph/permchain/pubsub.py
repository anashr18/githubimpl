class PubSub:
    def __init__(self, processes, connection):
        self.processes = processes
        self.connection = connection

    def stream(self, input):
        # Stub: will implement streaming logic in next steps
        yield from ()
