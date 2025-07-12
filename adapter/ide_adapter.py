from websockets.sync.client import connect

class IDEAdapter:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url

    def send_edits(self, changes: list):
        with connect(self.ws_url) as websocket:
            websocket.send(json.dumps({
                "type": "code_edits",
                "changes": changes
            }))