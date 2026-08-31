let nextPage = 1;
let isLoading = false;
let hasMore = true;
let loadMoreObserver = null;
let categories = ["全部分類"];
let selectedCategory = "全部分類";
let currentKeyword = "";
let isLoggedIn = false;
let currentUser = null;

document.addEventListener("DOMContentLoaded", () => {
  initAuthModal();

  // 檢查是否為 attraction 頁面
  const isAttractionPage = document.querySelector(".hero-profile");

  if (isAttractionPage) {
    loadAttractionDetail();
  } else {
    initCategoryMenu();
    loadCategories();
    initSearch();
    initListBarScroll();
    initLoadMoreObserver();
    loadMrts();
    loadAttractions();
  }
});

function initAuthModal() {
  const loginRegisterLink = document.querySelector("#login-register-link");
  const signupModal = document.querySelector("#section-signup-modal");
  const loginModal = document.querySelector("#section-login-modal");

  if (!loginRegisterLink || !signupModal || !loginModal) return;

  const closeButtons = document.querySelectorAll(".modal-overlay .close-btn");
  const signupForm = signupModal.querySelector(".signup-form");
  const loginForm = loginModal.querySelector(".login-form");

  const openModal = (modal) => {
    modal.classList.add("is-visible");
  };

  const closeModal = (modal) => {
    modal.classList.remove("is-visible");

    if (
      !signupModal.classList.contains("is-visible") &&
      !loginModal.classList.contains("is-visible")
    ) {
    }
  };

  const setMessage = (form, message = "", type = "error") => {
    const messageElement = form.querySelector(".form-message");
    if (messageElement) {
      messageElement.textContent = message;
      messageElement.classList.toggle("success", type === "success");
    }
  };

  loginRegisterLink.addEventListener("click", (event) => {
    event.preventDefault();
    if (isLoggedIn) {
      localStorage.removeItem("token");
      window.location.reload();
      return;
    }
    openModal(loginModal);
  });

  signupModal
    .querySelector(".login-link")
    .addEventListener("click", (event) => {
      event.preventDefault();
      setMessage(signupForm);
      closeModal(signupModal);
      openModal(loginModal);
    });

  loginModal.querySelector(".login-link").addEventListener("click", (event) => {
    event.preventDefault();
    setMessage(loginForm);
    closeModal(loginModal);
    openModal(signupModal);
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      closeModal(button.closest(".modal-overlay"));
    });
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(signupForm);
    const inputs = signupForm.querySelectorAll("input");

    try {
      const response = await fetch("/api/user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: inputs[0].value,
          email: inputs[1].value,
          password: inputs[2].value,
        }),
      });
      const result = await response.json();
      if (!response.ok || result.error) {
        throw new Error(result.message || "註冊失敗");
      }
      setMessage(signupForm, "註冊成功，請登入", "success");
      await new Promise((resolve) => setTimeout(resolve, 5000));
      closeModal(signupModal);
      openModal(loginModal);
    } catch (error) {
      setMessage(signupForm, error.message);
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(loginForm);
    const inputs = loginForm.querySelectorAll("input");

    try {
      const response = await fetch("/api/user/auth", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: inputs[0].value,
          password: inputs[1].value,
        }),
      });
      const result = await response.json();
      if (!response.ok || result.error) {
        throw new Error(result.message || "帳號或密碼錯誤");
      }
      localStorage.setItem("token", result.token);
      window.location.reload();
    } catch (error) {
      setMessage(loginForm, error.message);
    }
  });

  const token = localStorage.getItem("token");
  if (!token) {
    openModal(loginModal);
  }
  checkLoginStatus(loginRegisterLink);
}

function updateAuthLink(link, loggedIn) {
  isLoggedIn = loggedIn;
  link.textContent = loggedIn ? "登出系統" : "登入/註冊";
  link.href = loggedIn ? "#" : "#section-login-modal";
}

async function checkLoginStatus(loginRegisterLink) {
  const token = localStorage.getItem("token");

  try {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const response = await fetch("/api/user/auth", { headers });

    const result = await response.json();

    if (response.ok && result.data) {
      currentUser = result.data;
      updateAuthLink(loginRegisterLink, true);
      return;
    }

    localStorage.removeItem("token");
    currentUser = null;
    updateAuthLink(loginRegisterLink, false);
  } catch (error) {
    console.error("檢查登入狀態失敗:", error);
    currentUser = null;
    updateAuthLink(loginRegisterLink, false);
  }
}

async function loadAttractionDetail() {
  const attractionId = getAttractionIdFromUrl();

  if (!attractionId) {
    console.error("No attraction ID found in URL");
    return;
  }

  try {
    const res = await fetch(`/api/attraction/${attractionId}`);

    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }

    const json = await res.json();
    const attraction = json.data;

    renderAttractionDetail(attraction);
  } catch (error) {
    console.error("Failed to load attraction detail:", error);
    showErrorMessage("無法載入景點資訊，請稍後重試");
  }
}

function getAttractionIdFromUrl() {
  // 從 URL 路徑中提取 ID，例如 /attraction/123
  const pathParts = window.location.pathname.split("/");
  const id = pathParts[pathParts.length - 1];
  return isNaN(id) ? null : parseInt(id, 10);
}

function renderAttractionDetail(attraction) {
  // 更新頁面標題
  document.title = attraction.name;

  // 更新景點名稱
  const profileTitle = document.querySelector(".profile-title");
  if (profileTitle) {
    profileTitle.textContent = attraction.name;
  }

  // 更新分類與MRT訊息
  const profileSubtitle = document.querySelector(".profile-subtitle");
  if (profileSubtitle) {
    const mrtInfo = attraction.mrt ? attraction.mrt : "";
    const category = attraction.category || "景點";
    profileSubtitle.textContent = `${category} at ${mrtInfo}`;
  }

  // 更新hero圖片
  const heroImage = document.querySelector(".hero-main-image");
  if (heroImage && attraction.images && attraction.images.length > 0) {
    heroImage.src = attraction.images[0];
    heroImage.alt = attraction.name;
  }

  // 更新景點描述
  const description = document.querySelector(".description");
  if (description) {
    description.textContent = attraction.description || "暫無描述資訊";
  }

  // 更新景點地址
  const infoBlocks = document.querySelectorAll(".info-block");
  if (infoBlocks.length > 0) {
    const addressBlock = infoBlocks[0];
    const addressText = addressBlock.querySelector("p");
    if (addressText) {
      addressText.textContent = attraction.address || "暫無地址資訊";
    }
  }

  // 更新交通方式
  if (infoBlocks.length > 1) {
    const transportBlock = infoBlocks[1];
    const transportText = transportBlock.querySelector("p");
    if (transportText) {
      transportText.textContent = attraction.transport || "暫無交通資訊";
    }
  }

  // 初始化時間和價格選擇
  initTimePriceHandler();
  initImageCarousel(attraction.images || []);
}

function showErrorMessage(message) {
  const heroProfile = document.querySelector(".hero-profile");
  if (heroProfile) {
    const errorDiv = document.createElement("div");
    errorDiv.style.cssText = "color: red; padding: 20px; text-align: center;";
    errorDiv.textContent = message;
    heroProfile.insertBefore(errorDiv, heroProfile.firstChild);
  }
}

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

    const link = document.createElement("a");
    link.href = `/attraction/${attraction.id}`;
    link.className = "card";
    link.style.cssText =
      "text-decoration: none; color: inherit; cursor: pointer;";

    link.innerHTML = `
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
    grid.appendChild(link);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatPriceWithComma(price) {
  return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function initTimePriceHandler() {
  const radioInputs = document.querySelectorAll('input[name="time"]');
  const priceElement = document.querySelector(".price");

  if (!radioInputs.length || !priceElement) return;

  // 定義價格
  const prices = {
    morning: 2000,
    afternoon: 2500,
  };

  // 更新價格顯示
  function updatePrice() {
    const selectedValue = document.querySelector(
      'input[name="time"]:checked',
    )?.value;
    const price = prices[selectedValue] || 2000;
    const formattedPrice = formatPriceWithComma(price);
    priceElement.textContent = `新台幣 ${formattedPrice} 元`;
  }

  // 為所有單選按鈕添加change事件監聽
  radioInputs.forEach((input) => {
    input.addEventListener("change", updatePrice);
  });

  // 初始化價格顯示
  updatePrice();
}

function initImageCarousel(images = []) {
  const heroImage = document.querySelector(".hero-main-image");
  const leftArrow = document.querySelector(".arrow-left");
  const rightArrow = document.querySelector(".arrow-right");
  const indicatorBar = document.querySelector(".indicator-bar");

  if (!heroImage || !indicatorBar) return;

  const validImages = Array.isArray(images) ? images.filter(Boolean) : [];

  if (validImages.length === 0) {
    indicatorBar.innerHTML = "";
    if (leftArrow) leftArrow.style.display = "none";
    if (rightArrow) rightArrow.style.display = "none";
    return;
  }

  let currentIndex = 0;

  function updateCarousel() {
    heroImage.src = validImages[currentIndex];
    heroImage.alt = `景點圖片 ${currentIndex + 1}`;

    const indicators = indicatorBar.querySelectorAll(".indicator");
    indicators.forEach((indicator, index) => {
      indicator.classList.toggle("active", index === currentIndex);
    });
  }

  indicatorBar.innerHTML = "";

  validImages.forEach((_, index) => {
    const indicator = document.createElement("div");
    indicator.className = "indicator";
    indicator.setAttribute("aria-label", `顯示第 ${index + 1} 張圖片`);

    indicator.addEventListener("click", () => {
      currentIndex = index;
      updateCarousel();
    });

    indicatorBar.appendChild(indicator);
  });

  if (validImages.length <= 1) {
    if (leftArrow) leftArrow.style.display = "none";
    if (rightArrow) rightArrow.style.display = "none";
  } else {
    if (leftArrow) {
      leftArrow.style.display = "block";
      leftArrow.onclick = () => {
        currentIndex =
          (currentIndex - 1 + validImages.length) % validImages.length;
        updateCarousel();
      };
    }

    if (rightArrow) {
      rightArrow.style.display = "block";
      rightArrow.onclick = () => {
        currentIndex = (currentIndex + 1) % validImages.length;
        updateCarousel();
      };
    }
  }

  updateCarousel();
}
