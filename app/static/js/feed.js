const filtersForm = document.getElementById("filters");
const listBox = document.getElementById("feed-list");
const moreBox = document.getElementById("feed-more");
const loadMoreBtn = document.getElementById("load-more");

const PAGE_SIZE = 20;

let offset = 0;
let total = 0;
let loading = false;

const KIND_LABELS = { lost: "Пропала", found: "Найдена" };
const SIZE_LABELS = { small: "мелкая", medium: "средняя", large: "крупная" };

function escapeText(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

function currentFilters() {
    const data = Object.fromEntries(new FormData(filtersForm));
    const params = new URLSearchParams({ limit: String(PAGE_SIZE) });

    for (const [key, value] of Object.entries(data)) {
        if (value) params.set(key, value);
    }
    return params;
}

function listingCard(listing) {
    const photo = listing.photos.find((p) => p.is_primary) ?? listing.photos[0];
    const image = photo
        ? `<img src="${photo.thumb_url ?? photo.url}" alt="">`
        : '<div class="feed-photo empty"></div>';

    const date = new Date(listing.happened_at).toLocaleDateString("ru-RU");

    const details = [listing.breed, listing.color, SIZE_LABELS[listing.size]]
        .filter(Boolean)
        .join(" · ");

    return `
        <a class="feed-card" href="/listings/${listing.id}">
            ${image}
            <div class="feed-body">
                <span class="badge ${listing.kind}">${KIND_LABELS[listing.kind]}</span>
                <div class="feed-title">${escapeText(listing.title)}</div>
                ${details ? `<div class="feed-details">${escapeText(details)}</div>` : ""}
                <div class="feed-meta">${date}</div>
            </div>
        </a>
    `;
}

async function load(reset) {
    if (loading) return;
    loading = true;

    if (reset) {
        offset = 0;
        listBox.innerHTML = '<p class="loading">Загружаем…</p>';
    }

    const params = currentFilters();
    params.set("offset", String(offset));

    const response = await fetch(`/api/listings?${params}`);
    if (!response.ok) {
        listBox.innerHTML = '<p class="card-meta">Не удалось загрузить объявления</p>';
        loading = false;
        return;
    }

    const data = await response.json();
    total = data.total;

    const html = data.items.map(listingCard).join("");
    if (reset) {
        listBox.innerHTML = html || '<p class="card-meta">Ничего не найдено</p>';
    } else {
        listBox.insertAdjacentHTML("beforeend", html);
    }

    offset += data.items.length;
    moreBox.hidden = offset >= total;
    loading = false;
}

let debounceTimer = null;

filtersForm.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => load(true), 300);
});

loadMoreBtn.addEventListener("click", () => load(false));

load(true);
