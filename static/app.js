let products = [];
let auditData = [];
let insights = {};
let channelReadiness = null;
let readinessChannel = "amazon";
let selectedProduct = null;
let currentSuggestion = null;
const bulkSelection = new Set();
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function toast(message) {
  const element = $("toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toast.timeout);
  toast.timeout = setTimeout(() => element.classList.remove("show"), 2800);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function money(value) {
  const amount = Number(value || 0);
  return "₹" + amount.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

$("dashboardDate").textContent = new Intl.DateTimeFormat(undefined, {
  weekday: "long",
  month: "long",
  day: "numeric"
}).format(new Date()).toUpperCase();

function productCategory(product) {
  const category = (product.categories || [])[0];
  return typeof category === "object" ? category.name || "Uncategorized" : category || "Uncategorized";
}

function stockState(product) {
  const quantity = Number(product.stock_quantity);
  if (product.stock_status === "outofstock" || (product.manage_stock && quantity <= 0)) return "out";
  if (product.manage_stock && quantity <= 5) return "low";
  return "available";
}

async function loadAll() {
  try {
    const [status, productData, audit, insightData, readiness] = await Promise.all([
      api("/api/status"),
      api("/api/products"),
      api("/api/audit"),
      api("/api/insights"),
      api(`/api/channel-readiness?channel=${encodeURIComponent(readinessChannel)}`)
    ]);
    products = productData;
    auditData = audit.results;
    insights = insightData;
    channelReadiness = readiness;
    $("modeLabel").textContent = status.mode + " mode";
    $("connectionDetail").textContent = status.woocommerce_configured
      ? "WooCommerce connected"
      : "Demo workspace · changes saved in memory";
    $("navProductCount").textContent = products.length;
    renderDashboard(audit, status);
    renderProductFilters();
    renderProducts();
    renderBulkEditor();
    renderInventory();
    renderAudit(audit);
    renderChannelReadiness(channelReadiness);
    renderMargins();
  } catch (error) {
    toast(error.message);
  }
}

function renderDashboard(audit, status) {
  $("totalProducts").textContent = insights.catalog_size ?? products.length;
  $("productStatCaption").textContent = `${products.filter((p) => p.status === "publish").length} published products`;
  $("healthScore").textContent = `${insights.average_health ?? 0}%`;
  $("healthBadge").textContent = `${insights.average_health ?? 0}%`;
  $("stockAlerts").textContent = insights.alerts
    ? insights.alerts.low_stock.length + (insights.alerts.out_of_stock || []).length
    : 0;
  $("issueTotal").textContent = audit.issues_total;
  $("attentionCaption").textContent = `${audit.results.filter((result) => result.issue_count > 0).length} products need attention`;
  $("stockStatCaption").textContent = `${(insights.alerts?.low_stock || []).length} low · ${(insights.alerts?.out_of_stock || []).length} out of stock`;
  $("categoryCount").textContent = insights.category_distribution?.length || 0;
  $("healthyCount").textContent = insights.healthy_products || 0;
  $("missingImages").textContent = insights.alerts?.missing_images?.length || 0;
  $("snapshotNote").textContent = makeSnapshotNote();
  $("channelStatus").textContent = status.woocommerce_configured ? "Credentials configured" : "Demo mode";
  $("channelStatus").className = `connection-status-pill ${status.woocommerce_configured ? "connected" : "demo"}`;
  $("channelDetail").textContent = status.woocommerce_configured
    ? "Store credentials configured · approved edits target WooCommerce"
    : "No store credentials configured · using sample catalog";
  $("channelMode").textContent = status.woocommerce_configured ? "WooCommerce configured" : "Local demo catalog";
  renderCategoryChart();
  renderHealthChart();
  renderPriorityAlerts();
}

function makeSnapshotNote() {
  const lowStock = (insights.alerts?.low_stock || []).length;
  const missingImages = (insights.alerts?.missing_images || []).length;
  if (lowStock && missingImages) return `${lowStock} products are at low stock and ${missingImages} ${missingImages === 1 ? "product is" : "products are"} missing imagery.`;
  if (lowStock) return `${lowStock} products are at or below the 5-unit stock threshold.`;
  if (missingImages) return `${missingImages} ${missingImages === 1 ? "product is" : "products are"} missing product imagery.`;
  return "No low-stock or missing-image alerts are currently flagged.";
}

function renderCategoryChart() {
  const categories = insights.category_distribution || [];
  const largest = Math.max(...categories.map((item) => item.count), 1);
  $("categoryChart").innerHTML = categories.length
    ? categories.map((item, index) => `<div class="category-row">
        <div class="category-label"><span class="category-swatch swatch-${index % 6}"></span><span>${escapeHtml(item.category)}</span><b>${item.count}</b></div>
        <div class="bar-track"><span class="category-bar bar-${index % 6}" style="width:${Math.max(6, item.count / largest * 100)}%"></span></div>
      </div>`).join("")
    : `<div class="empty">No category data available.</div>`;
}

function renderHealthChart() {
  const groups = [
    { label: "Healthy", range: "80–100 score", className: "healthy", count: insights.healthy_products || 0 },
    { label: "Needs work", range: "50–79 score", className: "needs-work", count: products.filter((product) => {
      const score = auditData.find((item) => Number(item.product_id) === Number(product.id))?.score ?? 100;
      return score >= 50 && score < 80;
    }).length },
    { label: "Critical", range: "0–49 score", className: "critical", count: insights.critical_products || 0 }
  ];
  const total = Math.max(products.length, 1);
  $("healthChart").innerHTML = groups.map((group) => `<div class="health-row">
    <div class="health-row-label"><span>${group.label}</span><b>${group.count}<small> / ${products.length}</small></b></div>
    <div class="health-track"><span class="health-fill ${group.className}" style="width:${group.count / total * 100}%"></span></div>
  </div>`).join("");
}

function renderPriorityAlerts() {
  const alerts = [];
  for (const product of insights.alerts?.out_of_stock || []) {
    alerts.push({ type: "stock", title: product.name, detail: "Out of stock", id: product.id });
  }
  for (const product of insights.alerts?.low_stock || []) {
    alerts.push({ type: "stock", title: product.name, detail: `Only ${product.stock_quantity} units left`, id: product.id });
  }
  for (const product of insights.alerts?.missing_descriptions || []) {
    alerts.push({ type: "content", title: product.name, detail: "Full product description is missing", id: product.id });
  }
  for (const product of insights.alerts?.missing_images || []) {
    alerts.push({ type: "image", title: product.name, detail: "Product image is missing", id: product.id });
  }
  const unique = alerts.filter((alert, index) => alerts.findIndex((item) => item.id === alert.id && item.type === alert.type) === index).slice(0, 5);
  $("priorityAlerts").innerHTML = unique.length
    ? unique.map((alert) => `<button class="priority-item" data-edit="${escapeHtml(alert.id)}">
        <span class="alert-icon ${alert.type}">${alert.type === "stock" ? "!" : alert.type === "image" ? "▧" : "✎"}</span>
        <span class="priority-copy"><b>${escapeHtml(alert.title)}</b><small>${escapeHtml(alert.detail)}</small></span>
        <span class="priority-arrow">→</span>
      </button>`).join("")
    : `<div class="empty">You're all caught up. No priority alerts.</div>`;
  document.querySelectorAll("#priorityAlerts [data-edit]").forEach((button) => {
    button.addEventListener("click", () => openEditor(Number(button.dataset.edit)));
  });
}

function renderProductFilters() {
  const categories = [...new Set(products.map(productCategory))].sort((a, b) => a.localeCompare(b));
  const selected = $("categoryFilter").value;
  $("categoryFilter").innerHTML = `<option value="">All categories</option>${categories.map((category) =>
    `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`
  ).join("")}`;
  $("categoryFilter").value = categories.includes(selected) ? selected : "";
  const studioSelection = $("studioProduct").value;
  $("studioProduct").innerHTML = `<option value="">Select a product…</option>${products.map((product) =>
    `<option value="${escapeHtml(product.id)}">${escapeHtml(product.name)}</option>`
  ).join("")}`;
  if (products.some((product) => String(product.id) === studioSelection)) $("studioProduct").value = studioSelection;
}

function renderProducts() {
  const query = $("search").value.trim().toLowerCase();
  const category = $("categoryFilter").value;
  const stock = $("stockFilter").value;
  const filtered = products.filter((product) => {
    const matchesQuery = `${product.name} ${product.sku || ""} ${product.id}`.toLowerCase().includes(query);
    const matchesCategory = !category || productCategory(product) === category;
    const state = stockState(product);
    const matchesStock = !stock || (stock === "low" && state === "low") || (stock === "out" && state === "out");
    return matchesQuery && matchesCategory && matchesStock;
  });
  $("productCount").textContent = `Showing ${filtered.length} of ${products.length} products`;
  $("productRows").innerHTML = filtered.map((product) => {
    const audit = auditData.find((item) => Number(item.product_id) === Number(product.id));
    const score = audit?.score ?? 100;
    const state = stockState(product);
    const quantity = product.stock_quantity;
    const stockLabel = state === "out" ? "Out of stock" : state === "low" ? `${quantity} left` : product.manage_stock ? `${quantity} in stock` : product.stock_status || "In stock";
    return `<tr>
      <td><div class="table-product"><span class="product-avatar avatar-${Number(product.id) % 6}">${escapeHtml(product.name.trim().charAt(0).toUpperCase())}</span><span><b>${escapeHtml(product.name)}</b><small>${escapeHtml(product.sku || "No SKU")} · #${escapeHtml(product.id)}</small></span></div></td>
      <td><span class="category-chip">${escapeHtml(productCategory(product))}</span></td>
      <td class="price-cell">${money(product.regular_price)}</td>
      <td><span class="stock-state ${state}"><i></i>${escapeHtml(stockLabel)}</span></td>
      <td><span class="score-pill ${score >= 80 ? "good" : score >= 50 ? "warn" : "poor"}">${score}%</span></td>
      <td><button class="text-btn" data-edit="${escapeHtml(product.id)}">Review <span>→</span></button></td>
    </tr>`;
  }).join("") || `<tr><td colspan="6" class="empty">No products match these filters. Try changing your search or filters.</td></tr>`;
  document.querySelectorAll("#productRows [data-edit]").forEach((button) => {
    button.addEventListener("click", () => openEditor(Number(button.dataset.edit)));
  });
}

function renderInventory() {
  const inventory = products.filter((product) => product.manage_stock || product.stock_quantity !== undefined)
    .sort((a, b) => {
      const aState = stockState(a);
      const bState = stockState(b);
      const rank = { out: 0, low: 1, available: 2 };
      return rank[aState] - rank[bState] || Number(a.stock_quantity || 0) - Number(b.stock_quantity || 0);
    });
  $("lowStockCount").textContent = insights.alerts?.low_stock?.length || 0;
  $("outStockCount").textContent = insights.alerts?.out_of_stock?.length || 0;
  $("inventoryRows").innerHTML = inventory.map((product) => {
    const state = stockState(product);
    const label = state === "out" ? "Out of stock" : state === "low" ? "Low stock" : "In stock";
    return `<tr>
      <td><div class="table-product"><span class="product-avatar avatar-${Number(product.id) % 6}">${escapeHtml(product.name.trim().charAt(0).toUpperCase())}</span><span><b>${escapeHtml(product.name)}</b><small>Product #${escapeHtml(product.id)}</small></span></div></td>
      <td>${escapeHtml(product.sku || "—")}</td>
      <td><b class="stock-quantity">${escapeHtml(product.stock_quantity ?? "—")}</b></td>
      <td><span class="stock-state ${state}"><i></i>${label}</span></td>
      <td class="price-cell">${money(product.regular_price)}</td>
      <td><button class="text-btn" data-stock-edit="${escapeHtml(product.id)}">Adjust stock <span>→</span></button></td>
    </tr>`;
  }).join("") || `<tr><td colspan="6" class="empty">No inventory quantities are available for this catalog.</td></tr>`;
  document.querySelectorAll("#inventoryRows [data-stock-edit]").forEach((button) => {
    button.addEventListener("click", () => openEditor(Number(button.dataset.stockEdit)));
  });
}

function renderBulkEditor() {
  $("bulkRows").innerHTML = products.map((product) => `<tr data-bulk-product="${escapeHtml(product.id)}">
    <td><input class="bulk-product-check" type="checkbox" data-product-id="${escapeHtml(product.id)}" aria-label="Select ${escapeHtml(product.name)}" ${bulkSelection.has(Number(product.id)) ? "checked" : ""}></td>
    <td><div class="table-product"><span class="product-avatar avatar-${Number(product.id) % 6}">${escapeHtml(product.name.trim().charAt(0).toUpperCase())}</span><span><b>${escapeHtml(product.name)}</b><small>${escapeHtml(product.sku || "No SKU")} · #${escapeHtml(product.id)}</small></span></div></td>
    <td class="bulk-price-preview">${money(product.regular_price)}</td>
    <td class="bulk-stock-preview">${escapeHtml(product.stock_quantity ?? "—")}</td>
  </tr>`).join("") || `<tr><td colspan="4" class="empty">No products are available.</td></tr>`;
  document.querySelectorAll(".bulk-product-check").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const id = Number(checkbox.dataset.productId);
      if (checkbox.checked) bulkSelection.add(id);
      else bulkSelection.delete(id);
      updateBulkSelection();
    });
  });
  updateBulkSelection();
  renderBulkPreview();
}

function updateBulkSelection() {
  $("bulkSelectionCount").textContent = `${bulkSelection.size} selected`;
  $("bulkSelectAll").checked = products.length > 0 && bulkSelection.size === products.length;
  $("bulkSelectAll").indeterminate = bulkSelection.size > 0 && bulkSelection.size < products.length;
}

function renderBulkPreview() {
  const priceValue = $("bulkPricePercent").value.trim();
  const stockValue = $("bulkStockDelta").value.trim();
  const pricePercent = priceValue === "" ? null : Number(priceValue);
  const stockDelta = stockValue === "" ? null : Number(stockValue);
  document.querySelectorAll("[data-bulk-product]").forEach((row) => {
    const product = products.find((item) => Number(item.id) === Number(row.dataset.bulkProduct));
    if (!product) return;
    const originalPrice = Number(product.regular_price);
    const originalStock = Number(product.stock_quantity);
    const adjustedPrice = pricePercent === null ? originalPrice : originalPrice * (1 + pricePercent / 100);
    const adjustedStock = stockDelta === null ? originalStock : originalStock + stockDelta;
    row.querySelector(".bulk-price-preview").textContent = Number.isFinite(adjustedPrice) && adjustedPrice >= 0
      ? `${money(originalPrice)} → ${money(Math.round(adjustedPrice * 100) / 100)}`
      : "Check adjustment";
    row.querySelector(".bulk-stock-preview").textContent = Number.isInteger(adjustedStock) && adjustedStock >= 0
      ? `${product.stock_quantity ?? "—"} → ${adjustedStock}`
      : "Check adjustment";
  });
}

async function applyBulkChanges(event) {
  event.preventDefault();
  if (!bulkSelection.size) return toast("Select at least one product.");
  const priceValue = $("bulkPricePercent").value.trim();
  const stockValue = $("bulkStockDelta").value.trim();
  if (!priceValue && !stockValue) return toast("Enter a price or stock adjustment.");
  const pricePercent = priceValue ? Number(priceValue) : null;
  const stockDelta = stockValue ? Number(stockValue) : null;
  if (pricePercent !== null && !Number.isFinite(pricePercent)) return toast("Enter a valid price percentage.");
  if (stockDelta !== null && (!Number.isInteger(stockDelta) || !Number.isFinite(stockDelta))) {
    return toast("Stock change must be a whole number.");
  }

  const updates = [];
  for (const id of bulkSelection) {
    const product = products.find((item) => Number(item.id) === id);
    if (!product) continue;
    const fields = {};
    if (pricePercent !== null) {
      const price = Number(product.regular_price);
      const adjustedPrice = Math.round(price * (1 + pricePercent / 100) * 100) / 100;
      if (!Number.isFinite(price) || price < 0 || !Number.isFinite(adjustedPrice) || adjustedPrice < 0) {
        return toast(`${product.name}: this price adjustment would be invalid.`);
      }
      fields.regular_price = adjustedPrice.toFixed(2);
    }
    if (stockDelta !== null) {
      const stock = Number(product.stock_quantity);
      const adjustedStock = stock + stockDelta;
      if (!Number.isInteger(stock) || stock < 0 || !Number.isInteger(adjustedStock) || adjustedStock < 0) {
        return toast(`${product.name}: stock must remain a non-negative whole number.`);
      }
      fields.stock_quantity = adjustedStock;
    }
    updates.push({ id, name: product.name, fields });
  }
  if (!updates.length) return toast("No selected products could be updated.");

  const button = $("bulkApplyBtn");
  button.disabled = true;
  button.textContent = "Applying…";
  $("bulkResult").textContent = "";
  try {
    const results = await Promise.allSettled(updates.map(({ id, fields }) => api("/api/update", {
      method: "POST",
      body: JSON.stringify({ product_id: id, fields })
    })));
    const succeededIds = new Set();
    const failures = [];
    results.forEach((result, index) => {
      if (result.status === "fulfilled") succeededIds.add(updates[index].id);
      else failures.push(`${updates[index].name}: ${result.reason.message}`);
    });
    succeededIds.forEach((id) => bulkSelection.delete(id));
    await loadAll();
    const updatedCount = succeededIds.size;
    $("bulkResult").textContent = failures.length
      ? `${updatedCount} product(s) updated. ${failures.length} failed: ${failures.join(" · ")}`
      : `${updatedCount} product(s) updated successfully.`;
    $("bulkResult").classList.toggle("has-errors", failures.length > 0);
  } finally {
    button.disabled = false;
    button.textContent = "Apply to selected";
  }
}

function renderMargins() {
  const rows = insights.margins?.rows || [];
  $("marginRows").innerHTML = rows.slice(0, 6).map((row) => `<tr>
    <td><b>${escapeHtml(row.name)}</b></td>
    <td>${money(row.price)}</td>
    <td>${money(row.cost)}</td>
    <td>${money(row.gross_profit_per_unit)}</td>
    <td><div class="margin-cell"><span class="margin-track"><i style="width:${Math.max(0, Math.min(row.gross_margin_percent, 100))}%"></i></span><b>${row.gross_margin_percent}%</b></div></td>
    <td><span class="margin-status ${row.gross_margin_percent < 20 ? "review" : "healthy"}">${escapeHtml(row.flag)}</span></td>
  </tr>`).join("") || `<tr><td colspan="6" class="empty">Add unit cost data to your products to see gross margin insights.</td></tr>`;
}

function renderAudit(audit) {
  $("auditSummary").innerHTML = `<span class="audit-summary-icon">✓</span><span><b>${audit.products_checked} products checked</b> · ${audit.issues_total} open issues · ${audit.results.filter((result) => result.issue_count === 0).length} products passed all current checks.</span>`;
  const issueCards = [];
  for (const result of audit.results) {
    for (const issue of result.issues) {
      issueCards.push(`<div class="audit-item"><div><strong>${escapeHtml(result.name)}</strong><small>${escapeHtml(issue.message)}</small></div><span class="pill ${issue.severity.toLowerCase()}">${escapeHtml(issue.severity)}</span></div>`);
    }
  }
  $("auditList").innerHTML = issueCards.slice(0, 8).join("") || `<div class="empty">Great! No issues found.</div>`;
  if (issueCards.length > 8) {
    $("auditList").insertAdjacentHTML("beforeend", `<div class="empty audit-more">Showing 8 of ${issueCards.length} issues. Review products for details.</div>`);
  }
}

function renderChannelReadiness(report) {
  if (!report) return;
  $("readinessDescription").textContent = `${report.name}: ${report.description} These checks are guidance only and do not publish listings or guarantee channel approval.`;
  $("readinessAverage").textContent = `${report.average_score}%`;
  $("readinessAverageBar").style.width = `${report.average_score}%`;
  $("readinessReady").textContent = report.ready_count;
  $("readinessNeedsWork").textContent = report.needs_work_count;
  $("readinessChecked").textContent = report.products_checked;
  $("readinessRows").innerHTML = report.results.map((product) => {
    const gaps = product.issues.length
      ? `<ul class="readiness-gaps">${product.issues.map((issue) => `<li><b>${escapeHtml(issue.label)}</b><small>${escapeHtml(issue.guidance)}</small></li>`).join("")}</ul>`
      : `<span class="readiness-clear">All checklist items passed.</span>`;
    return `<tr>
      <td><div class="table-product"><span class="product-avatar avatar-${Number(product.product_id) % 6}">${escapeHtml(product.name.trim().charAt(0).toUpperCase())}</span><span><b>${escapeHtml(product.name)}</b><small>Product #${escapeHtml(product.product_id)}</small></span></div></td>
      <td><div class="readiness-score"><b>${product.score}%</b><span class="readiness-pill ${product.ready ? "ready" : "needs-work"}">${product.ready ? "Ready" : "Needs work"}</span><span class="readiness-track"><i class="${product.ready ? "ready" : ""}" style="width:${product.score}%"></i></span></div></td>
      <td>${gaps}</td>
      <td><button class="text-btn" data-readiness-edit="${escapeHtml(product.product_id)}">Review <span>→</span></button></td>
    </tr>`;
  }).join("") || `<tr><td colspan="4" class="empty">No products found for this channel checklist.</td></tr>`;
  document.querySelectorAll("#readinessRows [data-readiness-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const product = report.results.find((item) => Number(item.product_id) === Number(button.dataset.readinessEdit));
      if (!product) return;
      openEditor(Number(product.product_id));
      $("aiNote").textContent = product.issues.length
        ? `Checklist gaps: ${product.issues.map((issue) => `${issue.label} — ${issue.guidance}`).join(" ")} For description gaps, generate a draft and review it before saving. Category, image, and attribute changes must be made in your catalog source.`
        : "This product meets the current sample checklist. Review the product data before publishing.";
    });
  });
}

function renderCopilot(response) {
  const items = response.items || [];
  const itemMarkup = items.slice(0, 5).map((item) => {
    const title = item.name || item.product || "Catalog item";
    const detail = item.issue_count ? `${item.issue_count} data issues · health ${item.score}%`
      : item.stock_quantity !== undefined ? `Stock: ${item.stock_quantity ?? "unknown"}`
        : item.possible_match ? `Possible match: ${item.possible_match}`
          : item.score !== undefined ? `Health score: ${item.score}%` : "";
    return `<div class="copilot-item"><b>${escapeHtml(title)}</b><small>${escapeHtml(detail)}</small></div>`;
  }).join("");
  $("copilotResult").innerHTML = `<p>${escapeHtml(response.answer)}</p>${items.length > 5 ? `<small class="muted">Showing 5 of ${items.length} results.</small>` : ""}${itemMarkup}`;
  $("copilotResult").classList.add("visible");
}

function openEditor(id) {
  selectedProduct = products.find((product) => Number(product.id) === id);
  if (!selectedProduct) return;
  currentSuggestion = null;
  $("modalTitle").textContent = selectedProduct.name;
  $("description").value = stripHtml(selectedProduct.description || "");
  $("shortDescription").value = stripHtml(selectedProduct.short_description || "");
  $("sku").value = selectedProduct.sku || "";
  $("price").value = selectedProduct.regular_price || "";
  $("stockQuantity").value = selectedProduct.stock_quantity ?? "";
  $("keywords").value = "";
  $("aiNote").textContent = "Generate suggestions to fill the editor. Check all details before saving.";
  $("saveMessage").textContent = "";
  $("modalBackdrop").classList.add("open");
  $("closeModal").focus();
}

function stripHtml(value) {
  return String(value).replace(/<[^>]*>/g, "").trim();
}

function closeEditor() {
  $("modalBackdrop").classList.remove("open");
}

async function generate() {
  if (!selectedProduct) return;
  $("generateBtn").disabled = true;
  $("generateBtn").textContent = "Generating…";
  try {
    const result = await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({ product_id: Number(selectedProduct.id), keywords: $("keywords").value })
    });
    currentSuggestion = result.suggestion;
    $("description").value = currentSuggestion.description || "";
    $("shortDescription").value = currentSuggestion.short_description || "";
    $("aiNote").innerHTML = `<b>${escapeHtml(result.mode)}</b>: Suggestions generated. Suggested category: <b>${escapeHtml(currentSuggestion.suggested_category || "Not specified")}</b>. SEO title: ${escapeHtml(currentSuggestion.seo_title || "—")}. Keywords: ${escapeHtml((currentSuggestion.keywords || []).join(", "))}.`;
    toast("Suggestions generated. Review before saving.");
  } catch (error) {
    toast(error.message);
  } finally {
    $("generateBtn").disabled = false;
    $("generateBtn").innerHTML = "✦ &nbsp; Generate AI suggestions";
  }
}

async function save() {
  if (!selectedProduct) return;
  const fields = {
    description: $("description").value.trim(),
    short_description: $("shortDescription").value.trim(),
    sku: $("sku").value.trim(),
    regular_price: $("price").value.trim()
  };
  if (fields.regular_price && Number(fields.regular_price) < 0) return toast("Price cannot be negative.");
  if (!fields.regular_price) delete fields.regular_price;
  const stockQuantity = $("stockQuantity").value.trim();
  if (stockQuantity) {
    if (!Number.isInteger(Number(stockQuantity)) || Number(stockQuantity) < 0) {
      return toast("Stock quantity must be a non-negative whole number.");
    }
    fields.stock_quantity = Number(stockQuantity);
  }
  $("saveBtn").disabled = true;
  $("saveBtn").textContent = "Saving…";
  try {
    const result = await api("/api/update", {
      method: "POST",
      body: JSON.stringify({ product_id: Number(selectedProduct.id), fields })
    });
    $("saveMessage").textContent = result.message;
    toast(result.message);
    await loadAll();
  } catch (error) {
    toast(error.message);
  } finally {
    $("saveBtn").disabled = false;
    $("saveBtn").textContent = "Approve & save";
  }
}

function exportCatalog() {
  const columns = ["id", "name", "sku", "regular_price", "stock_quantity", "category", "health_score"];
  const lines = [columns.join(","), ...products.map((product) => {
    const audit = auditData.find((item) => Number(item.product_id) === Number(product.id));
    const values = [
      product.id, product.name, product.sku || "", product.regular_price || "",
      product.stock_quantity ?? "", productCategory(product), audit?.score ?? 100
    ];
    return values.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(",");
  })];
  const file = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = "catalogpilot-products.csv";
  link.click();
  URL.revokeObjectURL(url);
  toast("Catalog export downloaded.");
}

$("refreshBtn").addEventListener("click", loadAll);
$("auditBtn").addEventListener("click", async () => {
  $("auditBtn").disabled = true;
  $("auditBtn").textContent = "Auditing…";
  try {
    await loadAll();
    toast("Catalog audit completed.");
  } finally {
    $("auditBtn").disabled = false;
    $("auditBtn").innerHTML = "✦ &nbsp; Run audit";
  }
});
$("search").addEventListener("input", renderProducts);
$("categoryFilter").addEventListener("change", renderProducts);
$("stockFilter").addEventListener("change", renderProducts);
$("clearFilters").addEventListener("click", () => {
  $("search").value = "";
  $("categoryFilter").value = "";
  $("stockFilter").value = "";
  renderProducts();
});
$("exportBtn").addEventListener("click", exportCatalog);
$("bulkForm").addEventListener("submit", applyBulkChanges);
$("bulkPricePercent").addEventListener("input", renderBulkPreview);
$("bulkStockDelta").addEventListener("input", renderBulkPreview);
$("bulkSelectAll").addEventListener("change", () => {
  if ($("bulkSelectAll").checked) products.forEach((product) => bulkSelection.add(Number(product.id)));
  else bulkSelection.clear();
  renderBulkEditor();
});
$("readinessChannel").value = readinessChannel;
$("readinessChannel").addEventListener("change", async () => {
  const select = $("readinessChannel");
  const previousChannel = readinessChannel;
  readinessChannel = select.value;
  select.disabled = true;
  try {
    channelReadiness = await api(`/api/channel-readiness?channel=${encodeURIComponent(readinessChannel)}`);
    renderChannelReadiness(channelReadiness);
  } catch (error) {
    readinessChannel = previousChannel;
    select.value = previousChannel;
    toast(error.message);
  } finally {
    select.disabled = false;
  }
});
$("studioLaunchBtn").addEventListener("click", () => {
  const id = Number($("studioProduct").value);
  if (!id) return toast("Choose a product to open in the content editor.");
  openEditor(id);
  $("keywords").value = $("studioKeywords").value.trim();
});
$("channelRefreshBtn").addEventListener("click", async () => {
  const button = $("channelRefreshBtn");
  button.disabled = true;
  button.textContent = "Checking…";
  try {
    await loadAll();
  } finally {
    button.disabled = false;
    button.innerHTML = "↻ &nbsp; Refresh status";
  }
});
$("generateBtn").addEventListener("click", generate);
$("saveBtn").addEventListener("click", save);
$("closeModal").addEventListener("click", closeEditor);
$("cancelBtn").addEventListener("click", closeEditor);
$("modalBackdrop").addEventListener("click", (event) => {
  if (event.target === $("modalBackdrop")) closeEditor();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeEditor();
});
$("copilotForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = $("copilotInput").value.trim();
  if (!message) return;
  const button = $("copilotForm").querySelector("button");
  button.disabled = true;
  button.textContent = "Thinking…";
  try {
    renderCopilot(await api("/api/copilot", { method: "POST", body: JSON.stringify({ message }) }));
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = "Ask Copilot <span>→</span>";
  }
});

const navLinks = [...document.querySelectorAll("[data-view-link]")];
const viewTitles = {
  overview: "Overview",
  products: "Product catalog",
  "bulk-editor": "Bulk editor",
  inventory: "Inventory",
  "content-studio": "Content studio",
  pricing: "Pricing",
  insights: "Analytics",
  audit: "Data quality",
  "channel-readiness": "Channel readiness",
  copilot: "AI Copilot",
  channels: "Store connection"
};

function showView(view, updateHistory = false) {
  if (!viewTitles[view]) view = "overview";
  document.querySelectorAll("[data-view]").forEach((section) => {
    section.hidden = section.dataset.view !== view;
  });
  navLinks.forEach((link) => {
    const active = link.dataset.viewLink === view;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  $("viewTitle").textContent = viewTitles[view];
  if (updateHistory && location.hash !== `#${view}`) {
    history.pushState(null, "", `#${view}`);
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function viewFromHash() {
  const target = $(decodeURIComponent(location.hash.slice(1)));
  return target?.dataset.view || target?.dataset.viewLink || "overview";
}

document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (!link) return;
  const targetId = decodeURIComponent(link.getAttribute("href").slice(1));
  const target = $(targetId);
  const view = link.dataset.viewLink || target?.dataset.view;
  if (!view) return;
  event.preventDefault();
  showView(view, true);
});

window.addEventListener("popstate", () => showView(viewFromHash()));
showView(viewFromHash());

loadAll();
