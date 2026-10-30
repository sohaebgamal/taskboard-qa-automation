import pytest
from playwright.sync_api import Page, expect

from tests.ui.pages import BoardPage

pytestmark = pytest.mark.ui


@pytest.fixture
def board(page: Page):
    return BoardPage(page).open_as("alice", "alice-demo-pass")


def test_added_task_appears_and_input_clears(board):
    board.add_task("Write test plan")
    expect(board.task("Write test plan")).to_be_visible()
    expect(board.title_input).to_have_value("")


def test_task_is_still_there_after_reload(board, page: Page):
    board.add_task("Survive reload")
    expect(board.task("Survive reload")).to_be_visible()
    page.reload()
    expect(board.task("Survive reload")).to_be_visible()


def test_done_state_is_still_there_after_reload(board, page: Page):
    board.add_task("Finish retest")
    board.mark_done("Finish retest")
    page.reload()
    expect(board.task("Finish retest").get_by_role("checkbox")).to_be_checked()


def test_deleted_task_stays_gone_after_reload(board, page: Page):
    board.add_task("Remove me")
    board.delete("Remove me")
    expect(board.tasks).to_have_count(0)
    page.reload()
    expect(board.current_user).to_have_text("alice")
    expect(board.tasks).to_have_count(0)


def test_blank_title_shows_an_error_and_adds_nothing(board):
    board.add_task("   ")
    expect(board.error).to_have_text("title must not be blank")
    expect(board.tasks).to_have_count(0)


def test_html_in_a_title_is_shown_as_text_not_rendered(board):
    title = '<img src="x" id="injected">'
    board.add_task(title)
    expect(board.task(title).locator(".title")).to_have_text(title)
    expect(board.page.locator("#injected")).to_have_count(0)


def test_one_user_does_not_see_another_users_tasks(board, browser):
    board.add_task("Alice only")
    expect(board.task("Alice only")).to_be_visible()

    context = browser.new_context(base_url=board.page.url.rsplit("/", 1)[0])
    other = BoardPage(context.new_page()).open_as("bob", "bob-demo-pass")
    expect(other.tasks).to_have_count(0)
    context.close()


def test_regular_user_does_not_see_the_admin_panel(board):
    expect(board.admin_panel).to_be_hidden()


def test_admin_sees_the_user_list(page: Page):
    board = BoardPage(page).open_as("admin", "admin-demo-pass")
    expect(board.admin_panel).to_be_visible()
    expect(board.admin_panel.get_by_text("alice (user)")).to_be_visible()
