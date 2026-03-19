import asyncio

import receiver


class DummyServer:
    async def serve(self):
        return None


class DummyBleHub:
    async def run(self, _state, _hubdb):
        return None


def test_main_wires_dependencies_and_runs_tasks(monkeypatch) -> None:
    calls = {
        "configured": None,
        "gather_args": None,
        "server_cfg": None,
    }

    class DummyDB:
        pass

    class DummyState:
        pass

    def fake_configure(hubdb, state):
        calls["configured"] = (hubdb, state)

    def fake_server(config):
        calls["server_cfg"] = config
        return DummyServer()

    async def fake_gather(*args):
        calls["gather_args"] = args
        for coro in args:
            await coro
        return None

    async def fake_broadcast_state():
        return None

    monkeypatch.setattr(receiver.db, "HubDatabase", DummyDB)
    monkeypatch.setattr(receiver.hike, "ActiveSessionState", DummyState)
    monkeypatch.setattr(receiver.wserver, "configure", fake_configure)
    monkeypatch.setattr(receiver.bt, "HubBluetooth", DummyBleHub)
    monkeypatch.setattr(receiver.wserver, "get_uvicorn_config", lambda: "cfg")
    monkeypatch.setattr(receiver.uvicorn, "Server", fake_server)
    monkeypatch.setattr(receiver.wserver, "broadcast_state", fake_broadcast_state)
    monkeypatch.setattr(receiver.asyncio, "gather", fake_gather)

    asyncio.run(receiver.main())

    assert calls["configured"] is not None
    assert calls["server_cfg"] == "cfg"
    assert len(calls["gather_args"]) == 3
