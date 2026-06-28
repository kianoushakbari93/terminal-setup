"""Behaviour: the zsh deep-health parser turns a zsh probe run (stdout/stderr/
timing + the rendered p10k file) into named pass/fail probes. Pure logic."""
import ts_zsh_health as zh

GOOD_STDOUT = "p10k=1\nautosuggest=1\nhighlight=1\n"
P10K_WITH_GLYPHS = "SEP=''\nCAP=''\n"


def names(results):
    return {r.name: r for r in results}


def test_all_green_when_everything_loads_fast_and_clean():
    results = zh.parse_zsh_health(
        stdout=GOOD_STDOUT, stderr="", elapsed_s=0.3,
        p10k_text=P10K_WITH_GLYPHS, threshold_s=2.0,
    )
    by = names(results)
    assert by["zsh clean login"].ok is True
    assert by["p10k loaded"].ok is True
    assert by["autosuggestions active"].ok is True
    assert by["syntax-highlighting active"].ok is True
    assert by["prompt glyphs present"].ok is True
    assert by["startup under threshold"].ok is True


def test_stderr_output_fails_clean_login():
    results = names(zh.parse_zsh_health(
        stdout=GOOD_STDOUT, stderr="compinit: insecure directories\n",
        elapsed_s=0.3, p10k_text=P10K_WITH_GLYPHS,
    ))
    assert results["zsh clean login"].ok is False
    assert "insecure" in results["zsh clean login"].detail


def test_missing_plugin_fails_its_probe():
    results = names(zh.parse_zsh_health(
        stdout="p10k=1\nautosuggest=0\nhighlight=1\n", stderr="",
        elapsed_s=0.3, p10k_text=P10K_WITH_GLYPHS,
    ))
    assert results["autosuggestions active"].ok is False


def test_empty_glyphs_fail_the_glyph_probe():
    results = names(zh.parse_zsh_health(
        stdout=GOOD_STDOUT, stderr="", elapsed_s=0.3,
        p10k_text="SEP=''\nCAP=''\n",  # glyphs stripped to empty
    ))
    assert results["prompt glyphs present"].ok is False


def test_slow_startup_fails_threshold():
    results = names(zh.parse_zsh_health(
        stdout=GOOD_STDOUT, stderr="", elapsed_s=5.0,
        p10k_text=P10K_WITH_GLYPHS, threshold_s=2.0,
    ))
    assert results["startup under threshold"].ok is False
