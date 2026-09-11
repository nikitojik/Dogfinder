const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

async function submitJson(url, data) {
    return fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
}

function showError(element, body, fallback) {
    element.textContent = typeof body.detail === "string" ? body.detail : fallback;
}

loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("error");
    error.textContent = "";

    const data = Object.fromEntries(new FormData(loginForm));
    const response = await submitJson("/api/auth/login", data);

    if (response.ok) {
        location.href = "/";
        return;
    }
    showError(error, await response.json(), "Не удалось войти");
});

registerForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("error");
    error.textContent = "";

    const data = Object.fromEntries(new FormData(registerForm));
    const response = await submitJson("/api/auth/register", data);

    if (!response.ok) {
        showError(error, await response.json(), "Проверьте правильность заполнения полей");
        return;
    }

    await submitJson("/api/auth/login", { email: data.email, password: data.password });
    location.href = "/";
});
