from pathlib import Path

BASE_HTML = Path("templates/base.html").read_text(encoding="utf-8")
TOKENS_CSS = Path("blunder_tutor/web/static/css/tokens.css").read_text(encoding="utf-8")


class TestSelfHostedFonts:
    def test_base_html_has_no_google_fonts(self):
        assert "fonts.googleapis.com" not in BASE_HTML
        assert "fonts.gstatic.com" not in BASE_HTML

    def test_tokens_css_declares_self_hosted_faces(self):
        assert "@font-face" in TOKENS_CSS
        assert "/static/fonts/jost-400.woff2" in TOKENS_CSS
        assert "/static/fonts/dm-sans-400.woff2" in TOKENS_CSS
