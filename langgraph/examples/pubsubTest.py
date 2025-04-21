
from permchain.topic import Topic, RunnablePublisher, RunnableSubscriber

sports_topic = Topic(name="Sports")
print(sports_topic.name)

store = {}
def send(topic: str, input: str)-> None:
    store[topic] = input
def get(topic: str)-> str:
    return store[topic]
config = {"send": send, "get": get}

pub = RunnablePublisher(sports_topic)
pub.invoke("Here is the sports info", config)

print(f"store: {store}")
def sub_fn(x):
    print("I am a subsriber method");
    return x
sub = RunnableSubscriber(sports_topic, sub_fn)
print(sub.invoke(config))
