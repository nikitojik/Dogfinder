document.querySelectorAll(".thumbs img").forEach((thumb) => {
    thumb.addEventListener("click", () => {
        document.getElementById("main-photo").src = thumb.dataset.full;
    });
});

const mapEl = document.getElementById("mini-map");
if (mapEl) {
    const lat = parseFloat(mapEl.dataset.lat);
    const lon = parseFloat(mapEl.dataset.lon);

    const miniMap = L.map("mini-map", { scrollWheelZoom: false }).setView([lat, lon], 14);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap",
    }).addTo(miniMap);
    L.marker([lat, lon], { icon: markerIcon(mapEl.dataset.kind) }).addTo(miniMap);
}

const respondForm = document.getElementById("respond-form");

respondForm?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const error = document.getElementById("respond-error");
    error.textContent = "";

    const data = Object.fromEntries(new FormData(respondForm));
    if (!data.contact_phone) {
        delete data.contact_phone;
    }

    const listingId = respondForm.dataset.listingId;
    const response = await fetch(`/api/listings/${listingId}/responses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });

    if (response.ok) {
        respondForm.outerHTML =
            '<p class="success">Отклик отправлен, владелец получит ваше сообщение</p>';
        return;
    }

    const body = await response.json();
    error.textContent = typeof body.detail === "string" ? body.detail : "Не удалось отправить";
});
