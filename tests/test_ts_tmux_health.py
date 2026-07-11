"""Behaviour: the tmux deep-health parser turns an isolated tmux server probe
into named pass/fail probes. Pure logic."""
import ts_tmux_health as th

WIN_FMT = "#[fg=x]" + chr(0xE0B6) + " #I " + chr(0xE0B4)  # has rounded caps
STATUS = " 98% 2026-06-28 12:00  probe "                    # battery+date+session
PLUGINS = {"tpm": True, "catppuccin": True, "battery": True}


def names(results):
    return {r.name: r for r in results}


def test_all_green_for_a_healthy_server():
    by = names(th.parse_tmux_health(
        config_ok=True, config_err="", status_right=STATUS,
        window_format=WIN_FMT, plugins_present=PLUGINS,
    ))
    assert by["tmux config parses"].ok
    assert by["status-right modules non-empty"].ok
    assert by["window tabs rounded caps"].ok
    assert by["required plugins present"].ok


def test_config_error_fails_parse_probe():
    by = names(th.parse_tmux_health(
        config_ok=False, config_err="usage: bad option",
        status_right=STATUS, window_format=WIN_FMT, plugins_present=PLUGINS,
    ))
    assert by["tmux config parses"].ok is False
    assert "bad option" in by["tmux config parses"].detail


def test_empty_status_right_fails_its_probe():
    by = names(th.parse_tmux_health(
        config_ok=True, config_err="", status_right="   ",
        window_format=WIN_FMT, plugins_present=PLUGINS,
    ))
    assert by["status-right modules non-empty"].ok is False


def test_window_format_without_caps_fails():
    by = names(th.parse_tmux_health(
        config_ok=True, config_err="", status_right=STATUS,
        window_format="#[fg=x] #I #W ", plugins_present=PLUGINS,
    ))
    assert by["window tabs rounded caps"].ok is False


def test_missing_plugin_fails_probe():
    by = names(th.parse_tmux_health(
        config_ok=True, config_err="", status_right=STATUS,
        window_format=WIN_FMT, plugins_present={"tpm": True, "catppuccin": False, "battery": True},
    ))
    assert by["required plugins present"].ok is False
    assert "catppuccin" in by["required plugins present"].detail


def test_battery_plugin_required_only_when_conf_declares_it():
    assert th.battery_required("set -g @plugin 'tmux-plugins/tmux-battery'") is True
    # Batteryless render: the plugin line is omitted, so it must not be required.
    assert th.battery_required("set -g @plugin 'catppuccin/tmux'") is False
