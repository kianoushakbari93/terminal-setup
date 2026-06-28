"""Behaviour: the bash deep-health parser turns a bash probe run into named
pass/fail probes. Pure logic."""
import ts_bash_health as bh

GOOD = "ble=1\nstarship=1\ncompletion=1\n"
BASHRC = "source ~/.aliases\n[[ -f ~/.bashrc.local ]] && source ~/.bashrc.local\n"
TOML_WITH_GLYPHS = "format='[" + chr(0xE0B0) + "][" + chr(0xE0B2) + "]'\n"  # both triangles
TOML_EMPTY_GLYPHS = "format='[](purple)'\n"  # no glyph


def names(results):
    return {r.name: r for r in results}


def test_all_green_when_everything_loads():
    by = names(bh.parse_bash_health(
        stdout=GOOD, stderr="", elapsed_s=0.4,
        starship_toml=TOML_WITH_GLYPHS, bashrc_text=BASHRC, threshold_s=2.0,
    ))
    assert by["bash clean login"].ok
    assert by["ble.sh loaded"].ok
    assert by["starship active"].ok
    assert by["bash-completion loaded"].ok
    assert by["aliases and .local sourced"].ok
    assert by["prompt glyphs present"].ok
    assert by["startup under threshold"].ok


def test_missing_blesh_fails_its_probe():
    by = names(bh.parse_bash_health(
        stdout="ble=0\nstarship=1\ncompletion=1\n", stderr="",
        elapsed_s=0.4, starship_toml=TOML_WITH_GLYPHS, bashrc_text=BASHRC,
    ))
    assert by["ble.sh loaded"].ok is False


def test_bashrc_not_sourcing_local_fails_its_probe():
    by = names(bh.parse_bash_health(
        stdout=GOOD, stderr="", elapsed_s=0.4,
        starship_toml=TOML_WITH_GLYPHS, bashrc_text="# no aliases, no local\n",
    ))
    assert by["aliases and .local sourced"].ok is False


def test_stderr_fails_clean_login():
    by = names(bh.parse_bash_health(
        stdout=GOOD, stderr="bash: oops: command not found\n",
        elapsed_s=0.4, starship_toml=TOML_WITH_GLYPHS, bashrc_text=BASHRC,
    ))
    assert by["bash clean login"].ok is False


def test_empty_triangles_fail_glyph_probe():
    by = names(bh.parse_bash_health(
        stdout=GOOD, stderr="", elapsed_s=0.4,
        starship_toml=TOML_EMPTY_GLYPHS, bashrc_text=BASHRC,
    ))
    assert by["prompt glyphs present"].ok is False
