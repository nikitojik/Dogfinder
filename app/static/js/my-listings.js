const container = document.getElementById("listings");

const KIND_LABELS = { lost: window.I18N.lost, found: window.I18N.found };
const STATUS_LABELS = {
    active: window.I18N.statusActive,
    resolved: window.I18N.statusResolved,
    archived: window.I18N.statusArchived,
};
const RESPONSE_LABELS = {
    new: window.I18N.statusNew,
    accepted: window.I18N.statusAccepted,
    rejected: window.I18N.statusRejected,
};

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

function listingCard(listing) {
    const photo = listing.photos.find((p) => p.is_primary) ?? listing.photos[0];
    const thumb = photo
        ? `<img class="card-photo" src="${photo.thumb_url ?? photo.url}" alt="">`
        : '<div class="card-photo empty"></div>';

    const date = new Date(listing.happened_at).toLocaleDateString(window.I18N.localeTag);
    const responses = listing.response_count;

    const buttonLabel = responses > 0
        ? `${window.I18N.responsesCount} (${responses})`
        : window.I18N.noResponsesButton;

    return `
        <article class="my-card" data-id="${listing.id}">
            ${thumb}
            <div class="card-body">
                <div class="card-tags">
                    <span class="badge ${listing.kind}">${KIND_LABELS[listing.kind]}</span>
                    <span class="status">${STATUS_LABELS[listing.status]}</span>
                </div>
                <a class="card-title" href="/listings/${listing.id}">${escapeHtml(listing.title)}</a>
                <div class="card-meta">${date}</div>
                <button type="button" class="toggle-responses" data-id="${listing.id}">
                    ${buttonLabel}
                </button>
                <div class="responses" id="responses-${listing.id}" hidden></div>
            </div>
        </article>
    `;
}

function responseItem(item) {
    const date = new Date(item.created_at).toLocaleDateString(window.I18N.localeTag);
    const isNew = item.status === "new";

    return `
        <div class="response-item" data-id="${item.id}">
            <div class="response-head">
                <strong>${escapeHtml(item.author.name)}</strong>
                <a href="tel:${item.contact_phone ?? item.author.phone}">
                    ${item.contact_phone ?? item.author.phone}
                </a>
                <span class="response-status ${item.status}">${RESPONSE_LABELS[item.status]}</span>
            </div>
            <p class="response-message">${escapeHtml(item.message)}</p>
            <div class="response-foot">
                <span class="card-meta">${date}</span>
                ${isNew ? `
                    <button type="button" class="set-status" data-id="${item.id}" data-status="accepted">${window.I18N.accept}</button>
                    <button type="button" class="set-status secondary" data-id="${item.id}" data-status="rejected">${window.I18N.reject}</button>
                ` : ""}
            </div>
        </div>
    `;
}

async function loadResponses(listingId) {
    const box = document.getElementById(`responses-${listingId}`);

    if (!box.hidden) {
        box.hidden = true;
        return;
    }

    box.hidden = false;
    box.innerHTML = `<p class="loading">${window.I18N.loading}</p>`;

    const response = await fetch(`/api/listings/${listingId}/responses`);
    if (!response.ok) {
        box.innerHTML = `<p class="error">${window.I18N.loadResponsesError}</p>`;
        return;
    }

    const items = await response.json();
    box.innerHTML = items.length
        ? items.map(responseItem).join("")
        : `<p class="card-meta">${window.I18N.noResponses}</p>`;
}

async function setStatus(responseId, status) {
    const result = await fetch(`/api/responses/${responseId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
    });
    if (!result.ok) return;

    const updated = await result.json();
    const node = document.querySelector(`.response-item[data-id="${responseId}"]`);
    node.outerHTML = responseItem(updated);
}

container.addEventListener("click", (event) => {
    const toggle = event.target.closest(".toggle-responses");
    if (toggle) {
        loadResponses(toggle.dataset.id);
        return;
    }

    const statusBtn = event.target.closest(".set-status");
    if (statusBtn) {
        setStatus(statusBtn.dataset.id, statusBtn.dataset.status);
    }
});

(async () => {
    const response = await fetch("/api/listings/mine");
    if (!response.ok) {
        container.innerHTML = `<p class="error">${window.I18N.loadError}</p>`;
        return;
    }

    const items = await response.json();
    container.innerHTML = items.length
        ? items.map(listingCard).join("")
        : `<p class="card-meta">${window.I18N.noListings} <a href="/listings/new">${window.I18N.createOne}</a></p>`;
})();
