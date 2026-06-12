"""Smoke test Pilot della shell: avvio sull'elenco Carriere, uscita con q."""

from textual.widgets import Footer

from fm_tui.app import FormulaManagerApp
from fm_tui.screens import CareerList


async def test_app_starts_on_career_list(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.is_running
        assert isinstance(app.screen, CareerList)
        assert app.screen.name == "career_list"
        assert app.screen.query_one(Footer) is not None


async def test_q_quits_the_app(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
    assert app.return_code == 0


def test_q_binding_visible():
    keys = {binding.key for binding in FormulaManagerApp.BINDINGS}
    assert "q" in keys
