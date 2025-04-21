from permchain.connection_inmemory import InMemoryPubSubConnection
from permchain.pubsub import PubSub
from permchain.topic import Topic

# Minimal process: just echoes the input
class EchoProcess:
    def invoke(self, input):
        return {"echo": input}

# Create a topic (not strictly needed for this minimal test)
test_topic = Topic("test_topic")

# Create the in-memory connection
connection = InMemoryPubSubConnection()

# Create the PubSub system with a single echo process
pubsub = PubSub(processes=(EchoProcess(),), connection=connection)

# Test input
test_input = {"message": "Hello, PubSub!"}

# Run the stream and print outputs
for output in pubsub.stream(test_input):
    print("Output:", output)
