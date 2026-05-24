const profilePanel = document.querySelector("#profile-panel");
const profileSummaryPanel = document.querySelector("#profile-summary-panel");
const appShell = document.querySelector("#app-shell");
const profileStatus = document.querySelector("#profile-status");
const searchStatus = document.querySelector("#search-status");
const resultList = document.querySelector("#result-list");
const calculationNote = document.querySelector("#calculation-note");
const logStatus = document.querySelector("#log-status");
const historyList = document.querySelector("#history-list");
const profileSummaryCopy = document.querySelector("#profile-summary-copy");

const profileFields = {
  dogName: document.querySelector("#dog-name"),
  dogWeight: document.querySelector("#dog-weight"),
  dogAgeGroup: document.querySelector("#dog-age-group"),
  dogActivity: document.querySelector("#dog-activity"),
};

const intakeFields = {
  productKind: document.querySelector("#product-kind"),
  treatCount: document.querySelector("#treat-count"),
  treatTotalKcal: document.querySelector("#treat-total-kcal"),
  treatPieceCount: document.querySelector("#treat-piece-count"),
  foodGrams: document.querySelector("#food-grams"),
  foodKcalPer100g: document.querySelector("#food-kcal-per-100g"),
};

const outputs = {
  kcalPerPiece: document.querySelector("#kcal-per-piece-output"),
  treatKcal: document.querySelector("#treat-kcal-output"),
  foodKcal: document.querySelector("#food-kcal-output"),
  recommended: document.querySelector("#recommended-output"),
  dailyTotal: document.querySelector("#daily-total-output"),
  rer: document.querySelector("#rer-output"),
  comparison: document.querySelector("#comparison-output"),
};

const selectedLabels = {
  treat: document.querySelector("#selected-treat-name"),
  food: document.querySelector("#selected-food-name"),
};

let currentProfile = null;
let currentSelection = {
  treat: null,
  food: null,
};
let lastCalculation = null;
const searchParams = new URLSearchParams(window.location.search);

function apiUrl(path) {
  return `${window.location.origin}${path}`;
}

function requestJson(url, options = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(options.method || "GET", url, true);
    xhr.responseType = "json";

    const headers = options.headers || {};
    Object.entries(headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });

    xhr.onload = () => {
      const response = xhr.response || {};
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(response);
        return;
      }
      reject(new Error(response.error || `HTTP ${xhr.status}`));
    };

    xhr.onerror = () => reject(new Error("네트워크 요청 실패"));
    xhr.send(options.body || null);
  });
}

function getNumber(input) {
  const value = Number.parseFloat(input.value);
  return Number.isFinite(value) ? value : null;
}

function formatKcal(value) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return `${value.toFixed(2)} kcal`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("ko-KR");
}

function showApp(profile) {
  currentProfile = profile;
  profilePanel.classList.add("hidden");
  profileSummaryPanel.classList.remove("hidden");
  appShell.classList.remove("hidden");
  profileSummaryCopy.textContent =
    `${profile.dog_name} · ${profile.dog_weight}kg · ${profile.dog_age_group} · 활동계수 ${profile.dog_activity}`;
}

function showProfileEditor() {
  profilePanel.classList.remove("hidden");
  profileSummaryPanel.classList.add("hidden");
  appShell.classList.add("hidden");
}

function applyProfileToForm(profile) {
  profileFields.dogName.value = profile?.dog_name || "";
  profileFields.dogWeight.value = profile?.dog_weight ?? "";
  profileFields.dogAgeGroup.value = profile?.dog_age_group || "adult";
  profileFields.dogActivity.value = profile?.dog_activity || "1.6";
}

async function fetchProfile() {
  try {
    const payload = await requestJson(apiUrl("/api/profile"));
    if (payload.profile) {
      applyProfileToForm(payload.profile);
      showApp(payload.profile);
    } else {
      showProfileEditor();
    }
  } catch (error) {
    profileStatus.textContent = "프로필을 불러오지 못했어요.";
    showProfileEditor();
  }
}

function bootstrapProfileFromQuery() {
  if (searchParams.get("profile_error") === "1") {
    profileStatus.textContent = "이름과 체중을 다시 확인해 주세요.";
  }

  if (searchParams.get("profile_saved") !== "1") {
    return false;
  }

  const profile = {
    dog_name: searchParams.get("dog_name") || profileFields.dogName.value.trim(),
    dog_weight: Number(searchParams.get("dog_weight") || profileFields.dogWeight.value || 0),
    dog_age_group: searchParams.get("dog_age_group") || profileFields.dogAgeGroup.value || "adult",
    dog_activity: searchParams.get("dog_activity") || profileFields.dogActivity.value || "1.6",
  };

  applyProfileToForm(profile);
  profileStatus.textContent = "프로필을 저장했어요.";
  showApp(profile);
  window.history.replaceState({}, "", window.location.pathname);
  return true;
}

async function saveProfile() {
  const payload = {
    dog_name: profileFields.dogName.value.trim(),
    dog_weight: getNumber(profileFields.dogWeight),
    dog_age_group: profileFields.dogAgeGroup.value,
    dog_activity: profileFields.dogActivity.value,
  };

  profileStatus.textContent = "프로필을 저장하는 중입니다...";

  try {
    const data = await requestJson(apiUrl("/api/profile"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    profileStatus.textContent = "프로필을 저장했어요.";
    showApp(data.profile);
  } catch (error) {
    profileStatus.textContent = error.message || "프로필 저장에 실패했어요.";
  }
}

function setSelectedProduct(kind, product) {
  currentSelection[kind] = product;
  selectedLabels[kind].textContent = product.name || "선택됨";

  if (kind === "treat") {
    intakeFields.treatTotalKcal.value = product.total_kcal ?? "";
    intakeFields.treatPieceCount.value = "";
  } else {
    intakeFields.foodKcalPer100g.value = product.kcal_per_100g ?? "";
  }

  calculationNote.textContent = `${kind === "treat" ? "간식" : "사료"} 제품을 선택했어요. 오늘 먹인 양만 입력해 보세요.`;
}

function renderResults(results) {
  resultList.innerHTML = "";

  if (!results.length) {
    searchStatus.textContent = "검색 결과가 부족해요. 더 구체적인 제품명이나 브랜드명을 넣어보세요.";
    return;
  }

  searchStatus.textContent =
    "검색 결과를 찾았어요. 같은 제품이 보이면 가장 정확한 후보를 선택해 주세요.";

  const selectedKind = intakeFields.productKind.value;

  results.forEach((product) => {
    const card = document.createElement("article");
    card.className = "result-card";
    const linkHtml = product.product_url
      ? `<a href="${product.product_url}" target="_blank" rel="noreferrer">원본 보기</a>`
      : "<span></span>";

    card.innerHTML = `
      <div>
        <h3>${product.name}</h3>
        <p class="status">${product.brand || "-"}</p>
      </div>
      <div class="result-meta">
        <span class="pill">총중량 ${product.total_weight_g ?? "?"} g</span>
        <span class="pill">총칼로리 ${product.total_kcal ?? "?"} kcal</span>
        <span class="pill">100g당 ${product.kcal_per_100g ?? "?"} kcal</span>
      </div>
      <p class="status">${product.categories || "-"}</p>
      <div class="result-actions">
        <button type="button">${selectedKind === "treat" ? "간식으로 선택" : "사료로 선택"}</button>
        ${linkHtml}
      </div>
    `;

    card.querySelector("button").addEventListener("click", () => {
      setSelectedProduct(selectedKind, product);
    });
    resultList.appendChild(card);
  });
}

async function searchProducts(query) {
  searchStatus.textContent = "검색 소스를 넓혀서 제품을 찾는 중입니다...";
  resultList.innerHTML = "";

  try {
    const payload = await requestJson(`${apiUrl("/api/search")}?q=${encodeURIComponent(query)}`);
    renderResults(payload.results || []);
  } catch (error) {
    searchStatus.textContent = "외부 검색에 실패했어요. 제품명과 브랜드명을 더 길게 입력해 보세요.";
  }
}

function calculateRecommended(profile) {
  const dogWeight = Number(profile.dog_weight);
  const dogActivity = Number(profile.dog_activity);
  const rer = 70 * Math.pow(dogWeight, 0.75);
  const recommended = rer * dogActivity;
  return { rer, recommended };
}

function calculate() {
  if (!currentProfile) {
    calculationNote.textContent = "먼저 강아지 프로필을 저장해 주세요.";
    return;
  }

  const treatCount = getNumber(intakeFields.treatCount) ?? 0;
  const treatTotalKcal = getNumber(intakeFields.treatTotalKcal);
  const treatPieceCount = getNumber(intakeFields.treatPieceCount);
  const foodGrams = getNumber(intakeFields.foodGrams) ?? 0;
  const foodKcalPer100g = getNumber(intakeFields.foodKcalPer100g);

  let kcalPerPiece = null;
  let treatKcal = 0;

  if (Number.isFinite(treatTotalKcal) && Number.isFinite(treatPieceCount) && treatPieceCount > 0) {
    kcalPerPiece = treatTotalKcal / treatPieceCount;
    treatKcal = kcalPerPiece * treatCount;
  }

  let foodKcal = 0;
  if (Number.isFinite(foodKcalPer100g) && foodKcalPer100g > 0) {
    foodKcal = (foodGrams * foodKcalPer100g) / 100;
  }

  const dailyTotal = treatKcal + foodKcal;
  const { rer, recommended } = calculateRecommended(currentProfile);

  let comparisonText = "권장량과 비슷해요";
  const diff = dailyTotal - recommended;
  if (Math.abs(diff) >= recommended * 0.05) {
    comparisonText = diff > 0 ? `${diff.toFixed(2)} kcal 많아요` : `${Math.abs(diff).toFixed(2)} kcal 적어요`;
  }

  outputs.kcalPerPiece.textContent = formatKcal(kcalPerPiece);
  outputs.treatKcal.textContent = formatKcal(treatKcal);
  outputs.foodKcal.textContent = formatKcal(foodKcal);
  outputs.recommended.textContent = formatKcal(recommended);
  outputs.dailyTotal.textContent = formatKcal(dailyTotal);
  outputs.rer.textContent = formatKcal(rer);
  outputs.comparison.textContent = comparisonText;

  lastCalculation = {
    dog_name: currentProfile.dog_name,
    dog_weight: currentProfile.dog_weight,
    dog_activity: currentProfile.dog_activity,
    product_name: [currentSelection.food?.name, currentSelection.treat?.name].filter(Boolean).join(" / ") || "오늘 급여",
    treat_name: currentSelection.treat?.name || "",
    food_name: currentSelection.food?.name || "",
    treat_kcal: treatKcal,
    food_kcal: foodKcal,
    daily_total_kcal: dailyTotal,
    kcal_per_piece: kcalPerPiece,
    rer,
    recommended_kcal: recommended,
    comparison_text: comparisonText,
    saved_at: new Date().toISOString(),
  };

  calculationNote.textContent =
    "기본 입력으로 계산했어요. 값이 다르면 각 카드의 고급 보정 항목만 열어서 수정하면 됩니다.";
}

function renderHistory(logs) {
  historyList.innerHTML = "";

  if (!logs.length) {
    logStatus.textContent = "아직 저장된 기록이 없어요.";
    return;
  }

  logStatus.textContent = `최근 ${logs.length}개의 기록을 불러왔어요.`;

  logs.forEach((log) => {
    const card = document.createElement("article");
    card.className = "history-card";
    card.innerHTML = `
      <div class="history-head">
        <strong>${log.product_name || "이름 없는 기록"}</strong>
        <span class="pill">${formatDateTime(log.saved_at)}</span>
      </div>
      <div class="result-meta">
        <span class="pill">총 ${Number(log.daily_total_kcal || 0).toFixed(2)} kcal</span>
        <span class="pill">간식 ${Number(log.treat_kcal || 0).toFixed(2)} kcal</span>
        <span class="pill">사료 ${Number(log.food_kcal || 0).toFixed(2)} kcal</span>
      </div>
      <p class="status">${log.dog_name || "-"} · ${log.dog_weight ?? "-"}kg · ${log.comparison_text || "-"}</p>
    `;
    historyList.appendChild(card);
  });
}

async function fetchLogs() {
  try {
    const payload = await requestJson(apiUrl("/api/logs"));
    renderHistory(payload.logs || []);
  } catch (error) {
    logStatus.textContent = "기록을 불러오지 못했어요.";
  }
}

async function saveLog() {
  if (!lastCalculation) {
    logStatus.textContent = "먼저 계산을 완료해 주세요.";
    return;
  }

  logStatus.textContent = "기록을 저장하는 중입니다...";

  try {
    const payload = await requestJson(apiUrl("/api/logs"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastCalculation),
    });
    renderHistory(payload.logs || []);
    logStatus.textContent = "오늘 기록을 저장했어요.";
  } catch (error) {
    logStatus.textContent = "기록 저장에 실패했어요.";
  }
}

function resetTodayInputs() {
  Object.values(intakeFields).forEach((field) => {
    if (field.tagName === "SELECT") {
      if (field === intakeFields.productKind) {
        field.value = "treat";
      }
      return;
    }
    field.value = "";
  });

  currentSelection = { treat: null, food: null };
  selectedLabels.treat.textContent = "선택 전";
  selectedLabels.food.textContent = "선택 전";
  Object.values(outputs).forEach((output) => {
    output.textContent = "-";
  });
  lastCalculation = null;
  calculationNote.textContent = "오늘 입력을 초기화했어요. 다시 검색해서 선택해 주세요.";
}

document.querySelector("#edit-profile-button").addEventListener("click", showProfileEditor);
document.querySelector("#calculate-button").addEventListener("click", calculate);
document.querySelector("#reset-button").addEventListener("click", resetTodayInputs);
document.querySelector("#save-log-button").addEventListener("click", saveLog);
document.querySelector("#refresh-log-button").addEventListener("click", fetchLogs);

document.querySelector("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const query = document.querySelector("#search-input").value.trim();
  if (!query) {
    searchStatus.textContent = "검색어를 입력해 주세요.";
    return;
  }
  searchProducts(query);
});

if (!bootstrapProfileFromQuery()) {
  fetchProfile();
}
fetchLogs();
