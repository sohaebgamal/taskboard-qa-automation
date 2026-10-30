document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: document.getElementById("username").value,
      password: document.getElementById("password").value,
    }),
  });
  if (response.ok) {
    window.location.assign("/");
    return;
  }
  const body = await response.json();
  document.getElementById("error").textContent = body.error;
});
