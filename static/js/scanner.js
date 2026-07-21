// scanner.js
// -----------
// Client-side barcode scanning using the free html5-qrcode library (reads
// the camera via getUserMedia, decodes barcodes in-browser — no server
// cost). On a successful scan we POST the barcode to /meals/scanner/lookup,
// which calls the free Open Food Facts API server-side and returns
// normalized product data + a goal-fit assessment.
//
// Manual search (#manual-search) hits /meals/scanner/manual, which
// searches the app's own small food_db as a fallback when a product
// isn't in Open Food Facts or the user prefers not to use the camera.

let html5QrCode;

function startScanner() {
  const readerDiv = document.getElementById("reader");
  if (!readerDiv) return;
  html5QrCode = new Html5Qrcode("reader");
  html5QrCode.start(
    { facingMode: "environment" },
    { fps: 10, qrbox: 250 },
    (decodedText) => {
      html5QrCode.stop();
      document.getElementById("manual-barcode").value = decodedText;
      lookupBarcode(decodedText);
    },
    () => {} // ignore per-frame scan failures
  ).catch((err) => {
    alert("Camera unavailable: " + err);
  });
}

async function lookupBarcode(barcode) {
  const resp = await fetch("/meals/scanner/lookup", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: "barcode=" + encodeURIComponent(barcode),
  });
  const data = await resp.json();
  renderResult(data, barcode);
}

function renderResult(data, barcode) {
  const card = document.getElementById("result-card");
  card.style.display = "block";

  if (!data.found) {
    document.getElementById("result-name").textContent = "Not found";
    document.getElementById("result-brand").textContent =
      "This product isn't in the free database — try manual search below, or add it by hand.";
    document.getElementById("result-fit").innerHTML = "";
    document.getElementById("result-macros").innerHTML = "";
    return;
  }

  document.getElementById("result-name").textContent = data.product_name;
  document.getElementById("result-brand").textContent = data.brand || "";

  const fit = data.fit || { notes_en: [] };
  const notes = fit.notes_en || fit.notes_ro || [];
  document.getElementById("result-fit").innerHTML =
    "<ul>" + notes.map((n) => `<li>${n}</li>`).join("") + "</ul>";

  const p = data.per_100g || {};
  document.getElementById("result-macros").innerHTML = `
    <p class="hint">Per 100g: ${p.kcal ?? "?"} kcal, ${p.protein_g ?? "?"}g protein,
    ${p.carb_g ?? "?"}g carbs, ${p.fat_g ?? "?"}g fat${!data.data_complete ? " (incomplete — estimated)" : ""}</p>`;

  document.getElementById("log-barcode").value = barcode;
  document.getElementById("log-name").value = data.product_name;
  document.getElementById("log-kcal").value = p.kcal ?? 0;
  document.getElementById("log-protein").value = p.protein_g ?? 0;
  document.getElementById("log-carb").value = p.carb_g ?? 0;
  document.getElementById("log-fat").value = p.fat_g ?? 0;
  document.getElementById("log-fiber").value = p.fiber_g ?? 0;
  document.getElementById("log-estimated").value = (!data.data_complete).toString();
  if (data.serving_size_g) {
    document.getElementById("portion-g").value = data.serving_size_g;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("start-scan");
  if (startBtn) startBtn.addEventListener("click", startScanner);

  const lookupBtn = document.getElementById("lookup-barcode");
  if (lookupBtn) {
    lookupBtn.addEventListener("click", () => {
      const val = document.getElementById("manual-barcode").value.trim();
      if (val) lookupBarcode(val);
    });
  }

  const searchInput = document.getElementById("manual-search");
  if (searchInput) {
    let timer;
    searchInput.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const q = searchInput.value.trim();
        if (q.length < 2) return;
        const resp = await fetch("/meals/scanner/manual?q=" + encodeURIComponent(q));
        const results = await resp.json();
        const list = document.getElementById("manual-results");
        list.innerHTML = results
          .map((f) => `<li>${f.name_en} — ${f.kcal} kcal / ${f.per}${f.unit}</li>`)
          .join("");
      }, 300);
    });
  }
});
