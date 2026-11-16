"""Observable offline backend for pre-dispatch admission controls."""
from tether_engine.agents import ExtractiveBackend


class SpyBackend(ExtractiveBackend):
    def __init__(self):
        self.events = []

    def prepare_request(self, request):
        self.events.append("prepare")
        return request, {}

    def quote(self, request):
        self.events.append("quote")
        return super().quote(request)

    def select(self, request):
        self.events.append("select")
        return super().select(request)
