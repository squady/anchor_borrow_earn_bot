import weakref


class Observable(object):
    def __init__(self):
        self.observers = weakref.WeakKeyDictionary()

    def set(self, event_name, **kwargs):
        self.notifyObservers(event_name, **kwargs)

    async def async_set(self, event_name, **kwargs):
        await self.async_notifyObservers(event_name, **kwargs)

    def addObserver(self, o, event_name, callback):
        if o not in self.observers:
            self.observers[o] = {}

        self.observers[o][event_name] = callback

    def removeObserver(self, o):
        del self.observers[o]

    def notifyObservers(self, event_name, **kwargs):
        for o in self.observers:
            if self.observers[o][event_name] is not None:
                self.observers[o][event_name](**kwargs)

    async def async_notifyObservers(self, event_name, **kwargs):
        for o in self.observers:
            event_observer = self.observers[o].get(event_name, None)
            if event_observer is not None:
                await event_observer(**kwargs)
