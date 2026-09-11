const form = document.getElementById("listing-form");
const errorEl = document.getElementById("error");
const coordsEl = document.getElementById("coords");
const submitBtn = document.getElementById("submit-btn");

let selectedPoint = null;
let marker = null;
const pendingFiles = [];

const pickerMap = createMap("picker-map");

function setPoint(lat, lon, zoom) {
    selectedPoint = { lat, lon };
    if (marker) {
        marker.setLatLng([lat, lon]);
    } else {
        marker = L.marker([lat, lon], { icon: markerIcon("lost") }).addTo(pickerMap);
    }
    if (zoom) {
        pickerMap.setView([lat, lon], zoom);
    }
    coordsEl.textContent = `Выбрано: ${lat.toFixed(5)}, ${lon.toFixed(5)}`;
}

pickerMap.on("click", (event) => {
    setPoint(event.latlng.lat, event.latlng.lng);
});

document.getElementById("find-address").addEventListener("click", async () => {
    const query = document.getElementById("address").value.trim();
    if (query.length < 3) return;

    const response = await fetch(`/api/listings/geocode?q=${encodeURIComponent(query)}`);
    if (!response.ok) {
        coordsEl.textContent = "Адрес не найден, поставьте точку вручную";
        return;
    }
    const data = await response.json();
    setPoint(data.lat, data.lon, 15);
});

const photoInput = document.getElementById("photo-input");
const photoPreview = document.getElementById("photo-preview");

photoInput.addEventListener("change", () => {
    for (const file of photoInput.files) {
        if (pendingFiles.length >= 8) break;
        pendingFiles.push(file);

        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        photoPreview.appendChild(img);
    }
    photoInput.value = "";
});

async function uploadPhoto(listingId, file) {
    const urlResponse = await fetch(`/api/listings/${listingId}/photos/upload-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_type: file.type, size_bytes: file.size }),
    });
    if (!urlResponse.ok) return;

    const { upload_url, object_key } = await urlResponse.json();

    const putResponse = await fetch(upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type },
        body: file,
    });
    if (!putResponse.ok) return;

    await fetch(`/api/listings/${listingId}/photos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ object_key }),
    });
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorEl.textContent = "";
    submitBtn.disabled = true;
    submitBtn.textContent = "Публикуем…";

    const raw = Object.fromEntries(new FormData(form));

    const payload = {
        kind: raw.kind,
        title: raw.title,
        happened_at: new Date(raw.happened_at).toISOString(),
        sex: raw.sex,
    };

    for (const field of ["description", "breed", "color", "size", "size_note", "contact_phone"]) {
        if (raw[field]) payload[field] = raw[field];
    }

    if (selectedPoint) {
        payload.lat = selectedPoint.lat;
        payload.lon = selectedPoint.lon;
    }

    const response = await fetch("/api/listings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const body = await response.json();
        errorEl.textContent =
            typeof body.detail === "string" ? body.detail : "Проверьте заполнение полей";
        submitBtn.disabled = false;
        submitBtn.textContent = "Опубликовать";
        return;
    }

    const listing = await response.json();

    for (const file of pendingFiles) {
        submitBtn.textContent = "Загружаем фото…";
        await uploadPhoto(listing.id, file);
    }

    location.href = `/listings/${listing.id}`;
});
