let nextPage = 1;
let isLoading = false;
let hasMore = true;
let loadMoreObserver = null;
let categories = ["全部分類"];
let selectedCategory = "全部分類";
let currentKeyword = "";

document.addEventListener("DOMContentLoaded", () => {
  initCategoryMenu();
  loadCategories();
  initSearch();
  initListBarScroll();
  initLoadMoreObserver();
  loadMrts();
  loadAttractions();
});

async function loadMrts() {
  try {
    const res = await fetch("/api/mrts");
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "Failed to load MRTs");
    renderMrts(json.data || []);
  } catch (error) {
    console.error("MRT load error:", error);
  }
}

function renderMrts(mrts) {
  const listBar = document.querySelector(".list-bar");
  if (!listBar) return;
  listBar.innerHTML = "";

  mrts.forEach((mrt) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.textContent = mrt;
    item.addEventListener("click", () => {
      currentKeyword = mrt;
      const input = document.querySelector(".search-input");
      if (input) {
        input.value = mrt;
      }
      searchAttractions();
    });
    listBar.appendChild(item);
  });
}

function initListBarScroll() {
  const listBar = document.querySelector(".list-bar");
  const leftBtn = document.querySelector(".left-btn");
  const rightBtn = document.querySelector(".right-btn");
  if (!listBar || !leftBtn || !rightBtn) return;

  leftBtn.addEventListener("click", () => {
    listBar.scrollBy({ left: -240, behavior: "smooth" });
  });

  rightBtn.addEventListener("click", () => {
    listBar.scrollBy({ left: 240, behavior: "smooth" });
  });
}

function initSearch() {
  const input = document.querySelector(".search-input");
  const button = document.querySelector(".search-btn");
  if (!button || !input) return;

  button.addEventListener("click", () => {
    currentKeyword = input.value.trim();
    searchAttractions();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      button.click();
    }
  });
}

function searchAttractions() {
  nextPage = 1;
  hasMore = true;
  loadAttractions(true);
}

function initCategoryMenu() {
  const categoryToggle = document.querySelector(".search-category");
  const categoryMenu = document.querySelector(".category-menu");
  if (!categoryToggle || !categoryMenu) return;

  categoryToggle.addEventListener("click", () => {
    categoryMenu.classList.toggle("hidden");
  });

  categoryToggle.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      categoryMenu.classList.toggle("hidden");
    }
  });

  document.addEventListener("click", (event) => {
    if (
      !categoryToggle.contains(event.target) &&
      !categoryMenu.contains(event.target)
    ) {
      categoryMenu.classList.add("hidden");
    }
  });
}

async function loadCategories() {
  try {
    const res = await fetch("/api/categories");
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "Failed to load categories");

    categories = ["全部分類", ...(json.data || [])];
    renderCategoryMenu();
  } catch (error) {
    console.error("Category load error:", error);
  }
}

function renderCategoryMenu() {
  const categoryMenu = document.querySelector(".category-menu");
  if (!categoryMenu) return;

  categoryMenu.innerHTML = categories
    .map(
      (category) =>
        `<div class="menu-item" tabindex="0">${escapeHtml(category)}</div>`,
    )
    .join("");

  const items = categoryMenu.querySelectorAll(".menu-item");
  items.forEach((item, index) => {
    const category = categories[index];
    item.addEventListener("click", () => {
      selectedCategory = category;
      const categoryLabel = document.querySelector(".search-category span");
      if (categoryLabel) {
        categoryLabel.textContent = `${category} ▼`;
      }
      categoryMenu.classList.add("hidden");
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        item.click();
      }
    });
  });
}

function initLoadMoreObserver() {
  const container = document.querySelector(".main-section .container");
  if (!container) return;

  const sentinel = document.createElement("div");
  sentinel.className = "load-more-sentinel";
  sentinel.style.cssText = "height: 1px; visibility: hidden;";
  container.appendChild(sentinel);

  loadMoreObserver = new IntersectionObserver(
    (entries) => {
      const entry = entries[0];
      if (entry.isIntersecting && hasMore && !isLoading) {
        loadAttractions();
      }
    },
    {
      root: null,
      rootMargin: "0px",
      threshold: 0.1,
    },
  );

  loadMoreObserver.observe(sentinel);
}

async function loadAttractions(clear = false) {
  if (!hasMore || isLoading || nextPage == null) return;

  isLoading = true;
  try {
    const params = new URLSearchParams();
    params.append("page", nextPage);
    if (selectedCategory && selectedCategory !== "全部分類") {
      params.append("category", selectedCategory);
    }
    if (currentKeyword) {
      params.append("keyword", currentKeyword);
    }

    const res = await fetch(`/api/attractions?${params.toString()}`);
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "Failed to load attractions");

    const shouldClear = clear || nextPage === 1;
    renderAttractions(json.data || [], shouldClear);

    nextPage = json.nextPage;
    hasMore = nextPage != null;
  } catch (error) {
    console.error("Attractions load error:", error);
  } finally {
    isLoading = false;
  }
}

function renderAttractions(attractions, clear = false) {
  const grid = document.querySelector(".attractions-grid");
  if (!grid) return;
  if (clear) {
    grid.innerHTML = "";
  }

  attractions.forEach((attraction) => {
    const imageUrl =
      Array.isArray(attraction.images) && attraction.images.length > 0
        ? attraction.images[0]
        : "";

    const stationText = Array.isArray(attraction.mrt)
      ? attraction.mrt[0] || ""
      : attraction.mrt || "";

    const card = document.createElement("div");
    card.className = "card";

    card.innerHTML = `
      <div class="card-image-wrapper">
        <img src="${imageUrl}" alt="${escapeHtml(attraction.name)}" class="card-image" />
        <div class="card-title-overlay">
          <h3 class="card-title">${escapeHtml(attraction.name)}</h3>
        </div>
      </div>
      <div class="card-info">
        <span class="card-station">${escapeHtml(stationText)}</span>
        <span class="card-category">${escapeHtml(attraction.category || "")}</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

function escapeHtml(text) {
  return text
    ? text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;")
    : "";
}
