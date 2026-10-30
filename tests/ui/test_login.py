import re

import pytest
from playwright.sync_api import Page, expect

from tests.ui.pages import BoardPage, LoginPage

pytestmark = pytest.mark.ui


def test_valid_login_opens_the_board(page: Page):
    LoginPage(page).open().sign_in("alice", "alice-demo-pass")
    expect(BoardPage(page).current_user).to_have_text("alice")


def test_wrong_password_shows_an_error_and_stays_on_login(page: Page):
    login = LoginPage(page).open()
    login.sign_in("alice", "wrong")
    expect(login.error).to_have_text("invalid username or password")
    expect(page).to_have_url(re.compile(r"/login$"))


def test_board_redirects_to_login_when_signed_out(page: Page):
    page.goto("/")
    expect(page).to_have_url(re.compile(r"/login$"))


def test_sign_out_returns_to_login_and_protects_the_board(page: Page):
    board = BoardPage(page).open_as("alice", "alice-demo-pass")
    board.sign_out_button.click()
    expect(page).to_have_url(re.compile(r"/login$"))
    page.goto("/")
    expect(page).to_have_url(re.compile(r"/login$"))
