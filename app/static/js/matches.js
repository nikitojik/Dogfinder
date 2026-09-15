const matchesBlock = document.querySelector(".matches-block");

function escapeText(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

function formatDistance(meters) {
    if (meters === null) return "расстояние неизвестно";
    if (meters < 1000) return `${meters} м`;
    return `${(meters / 1000).toFixed(1)} км`;
}

function matchCard(match) {
    const listing = match.listing;
    const photo = listing.photos.find((p) => p.is_primary) ?? listing.photos[0];
    const image = photo
        ? `<img src="${photo.thumb_url ?? photo.url}" alt="">`
        : '<div class="match-photo empty"></div>';

    const date = new Date(listing.happened_at).toLocaleDateString("ru-RU");
    const percent = Math.round(match.visual_similarity * 100);

    return `
        <a class="match-card" href="/listings/${listing.id}">
            ${image}
            <div class="match-body">
                <div class="match-title">${escapeText(listing.title)}</div>
                <div class="match-meta">${date} · ${formatDistance(match.distance_m)}</div>
                <div class="match-score">
                    <div class="score-bar"><span style="width:${percent}%"></span></div>
                    <span class="score-value">сходство ${percent}%</span>
                </div>
            </div>
        </a>
    `;
}

(async () => {
    if (!matchesBlock) return;

    const box = document.getElementById("matches");
    const listingId = matchesBlock.dataset.listingId;

    const response = await fetch(`/api/listings/${listingId}/matches`);
    if (!response.ok) {
        box.innerHTML = '<p class="card-meta">Не удалось загрузить совпадения</p>';
        return;
    }

    const matches = await response.json();
    box.innerHTML = matches.length
        ? matches.map(matchCard).join("")
        : '<p class="card-meta">Подходящих объявлений пока не найдено</p>';
})();
