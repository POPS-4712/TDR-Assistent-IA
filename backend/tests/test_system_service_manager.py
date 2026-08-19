from app.services.system.service_manager import LocalServiceManager


def test_service_controls_are_disabled_by_default(monkeypatch):
    """The backend must not obtain host control unless production opts in."""
    manager = LocalServiceManager()
    monkeypatch.setattr(manager, "enabled", False)

    availability = manager.availability()
    result = manager.control("restart", ["backend"])

    assert availability["enabled"] is False
    assert availability["available"] is False
    assert result == [{
        "service": "backend",
        "action": "restart",
        "success": False,
        "status": "not_managed",
        "message": "Local service controls are disabled in this deployment",
    }]


def test_service_control_rejects_unknown_actions_and_services():
    manager = LocalServiceManager()

    try:
        manager.control("delete", ["backend"])
    except ValueError as exc:
        assert str(exc) == "Unsupported service action"
    else:
        raise AssertionError("Unknown actions must be rejected")

    try:
        manager.control("start", ["unrelated-container"])
    except ValueError as exc:
        assert str(exc) == "Unknown service requested"
    else:
        raise AssertionError("Unknown services must be rejected")


def test_container_state_mapping_is_safe_and_user_facing():
    assert LocalServiceManager._normalize_status("running", {"Health": {"Status": "healthy"}}) == "running"
    assert LocalServiceManager._normalize_status("running", {"Health": {"Status": "unhealthy"}}) == "error"
    assert LocalServiceManager._normalize_status("exited", {}) == "stopped"
    assert LocalServiceManager._normalize_status("restarting", {}) == "starting"
