const DEFAULT_CENTER = [61.0667, 42.1];
const DEFAULT_ZOOM = 12;

const COLORS = { lost: "#d32f2f", found: "#2e7d32" };

function createMap(elementId) {
    const map = L.map(elementId).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(map);
    return map;
}

function markerIcon(kind) {
    const color = COLORS[kind] ?? "#666";
    return L.divIcon({
        className: "pin",
        html: `<span style="background:${color}"></span>`,
        iconSize: [22, 22],
        iconAnchor: [11, 22],
        popupAnchor: [0, -20],
    });
}

function popupHtml(listing) {
    const photo = listing.photos.find((p) => p.is_primary) ?? listing.photos[0];
    const image = photo
        ? `<img src="${photo.thumb_url ?? photo.url}" alt="">`
        : "";
    const label = listing.kind === "lost" ? "Пропала" : "Найдена";
    const date = new Date(listing.happened_at).toLocaleDateString("ru-RU");

    return `
        <div class="popup">
            ${image}
            <div class="popup-label ${listing.kind}">${label}</div>
            <a class="popup-title" href="/listings/${listing.id}">${escapeHtml(listing.title)}</a>
            <div class="popup-meta">${date}</div>
        </div>
    `;
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

async function loadListings(params = {}) {
    const query = new URLSearchParams({ limit: "100", ...params });
    const response = await fetch(`/api/listings?${query}`);
    if (!response.ok) {
        console.error("Не удалось загрузить объявления");
        return [];
    }
    const data = await response.json();
    return data.items.filter((item) => item.lat !== null && item.lon !== null);
}

function renderMarkers(map, listings) {
    const cluster = L.markerClusterGroup({
        maxClusterRadius: 50,
        showCoverageOnHover: false,
    });

    for (const listing of listings) {
        L.marker([listing.lat, listing.lon], { icon: markerIcon(listing.kind) })
            .bindPopup(popupHtml(listing))
            .addTo(cluster);
    }

    map.addLayer(cluster);
    return cluster;
}
