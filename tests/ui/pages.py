"""Page objects: tests talk about screens, and selectors live only here."""
from playwright.sync_api import Page, expect


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.username = page.get_by_label("Username")
        self.password = page.get_by_label("Password")
        self.submit = page.get_by_role("button", name="Sign in")
        self.error = page.get_by_role("alert")

    def open(self):
        self.page.goto("/login")
        return self

    def sign_in(self, username, password):
        self.username.fill(username)
        self.password.fill(password)
        self.submit.click()


class BoardPage:
    def __init__(self, page: Page):
        self.page = page
        self.current_user = page.locator("#current-user")
        self.title_input = page.get_by_label("New task")
        self.add_button = page.get_by_role("button", name="Add")
        self.sign_out_button = page.get_by_role("button", name="Sign out")
        self.error = page.get_by_role("alert")
        self.tasks = page.locator('[data-testid="task"]')
        self.admin_panel = page.locator("#admin-panel")

    def open_as(self, username, password):
        LoginPage(self.page).open().sign_in(username, password)
        expect(self.current_user).to_have_text(username)
        return self

    def add_task(self, title):
        self.title_input.fill(title)
        self.add_button.click()

    def task(self, title):
        return self.tasks.filter(has_text=title)

    def mark_done(self, title):
        row = self.task(title)
        row.get_by_role("checkbox", name="Mark done").check()
        expect(row).to_have_attribute("data-saved", "true")

    def delete(self, title):
        self.task(title).get_by_role("button", name="Delete").click()
