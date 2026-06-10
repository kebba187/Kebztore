// Кебзtore — light client JS: cart actions + 152-ФЗ consent banner.
// No framework. All POSTs send the CSRF token (Django CSRF protection).

(function () {
  const csrftoken = document.querySelector('meta[name="csrf-token"]')?.content;

  function postJSON(url, data) {
    return fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken,
        "Content-Type": "application/json",
      },
      body: data ? JSON.stringify(data) : null,
    });
  }

  function postForm(url, params) {
    const body = new URLSearchParams(params);
    return fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrftoken },
      body,
    }).then((r) => r.json());
  }

  function updateBadge(count) {
    const el = document.getElementById("cart-count");
    if (el) el.textContent = count;
  }

  // ── Add to cart (catalog + product detail) ───────────────────────────────
  document.querySelectorAll(".add-to-cart").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const qtyInput = btn.dataset.qtyInput ? document.getElementById(btn.dataset.qtyInput) : null;
      const qty = qtyInput ? qtyInput.value : 1;
      postForm(`/cart/add/${id}/`, { quantity: qty }).then((data) => {
        if (data.error) { alert(data.error); return; }
        updateBadge(data.count);
        btn.textContent = "✓";
        setTimeout(() => (btn.textContent = btn.dataset.label || "В корзину"), 1200);
      });
    });
  });

  // ── Cart page: update quantity / remove ──────────────────────────────────
  document.querySelectorAll(".cart-qty").forEach((input) => {
    input.addEventListener("change", () => {
      const row = input.closest("tr");
      postForm(`/cart/update/${row.dataset.id}/`, { quantity: input.value }).then((data) => {
        updateBadge(data.count);
        document.getElementById("cart-subtotal").textContent = formatRub(data.subtotal);
        const item = data.items.find((i) => String(i.id) === row.dataset.id);
        if (!item) { row.remove(); } else {
          row.querySelector(".line-total").textContent = formatRub(item.line_total);
        }
      });
    });
  });

  document.querySelectorAll(".cart-remove").forEach((btn) => {
    btn.addEventListener("click", () => {
      const row = btn.closest("tr");
      postForm(`/cart/remove/${row.dataset.id}/`, {}).then((data) => {
        updateBadge(data.count);
        row.remove();
        const sub = document.getElementById("cart-subtotal");
        if (sub) sub.textContent = formatRub(data.subtotal);
      });
    });
  });

  function formatRub(value) {
    return Math.round(parseFloat(value)).toLocaleString("ru-RU") + " ₽";
  }

  // ── 152-ФЗ consent banner ────────────────────────────────────────────────
  const consent = document.getElementById("consent");
  if (consent) {
    function saveConsent(prefs) {
      postJSON("/consent/", prefs).then(() => consent.remove());
    }
    document.getElementById("consent-accept-all").addEventListener("click", () =>
      saveConsent({ analytical: true, advertising: true })
    );
    document.getElementById("consent-accept-selected").addEventListener("click", () =>
      saveConsent({
        analytical: document.getElementById("c-analytical").checked,
        advertising: document.getElementById("c-advertising").checked,
      })
    );
  }
})();
