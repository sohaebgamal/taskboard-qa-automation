const errorBox = document.getElementById("error");
const unsafeRender = document.body.dataset.unsafeRender === "1";

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("signed out");
  }
  return response;
}

function renderTask(task) {
  const item = document.createElement("li");
  item.dataset.testid = "task";
  item.dataset.id = task.id;

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = task.done;
  checkbox.setAttribute("aria-label", "Mark done");
  checkbox.addEventListener("change", async () => {
    await api(`/api/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ done: checkbox.checked }),
    });
    item.dataset.saved = String(checkbox.checked);
  });

  const title = document.createElement("span");
  title.className = "title";
  if (unsafeRender) {
    title.innerHTML = task.title; // Fault "xss": see scripts/fault_check.py.
  } else {
    title.textContent = task.title;
  }

  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "Delete";
  remove.addEventListener("click", async () => {
    const response = await api(`/api/tasks/${task.id}`, { method: "DELETE" });
    if (response.ok) item.remove();
  });

  item.append(checkbox, title, remove);
  document.getElementById("tasks").append(item);
}

async function load() {
  const me = await (await api("/api/me")).json();
  document.getElementById("current-user").textContent = me.username;

  const { tasks } = await (await api("/api/tasks")).json();
  tasks.forEach(renderTask);

  if (me.role === "admin") {
    const { users } = await (await api("/api/admin/users")).json();
    const list = document.getElementById("users");
    users.forEach((user) => {
      const item = document.createElement("li");
      item.textContent = `${user.username} (${user.role})`;
      list.append(item);
    });
    document.getElementById("admin-panel").hidden = false;
  }
}

document.getElementById("task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";
  const input = document.getElementById("task-title");
  const response = await api("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ title: input.value }),
  });
  const body = await response.json();
  if (!response.ok) {
    errorBox.textContent = body.error;
    return;
  }
  renderTask(body);
  input.value = "";
});

document.getElementById("logout").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.assign("/login");
});

load();
