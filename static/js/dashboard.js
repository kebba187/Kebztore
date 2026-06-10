// Кебзtore — dependency-free dual-axis line chart for the admin dashboard.
// Reads data from <script id="chart-data"> (Django json_script) and draws a
// Sales (left axis) + Revenue (right axis) line chart on a <canvas>.

(function () {
  const dataEl = document.getElementById("chart-data");
  const canvas = document.getElementById("sales-chart");
  if (!dataEl || !canvas) return;

  const data = JSON.parse(dataEl.textContent);
  const COLORS = { sales: "#34d399", revenue: "#5e9bff", grid: "rgba(255,255,255,.08)",
                   axis: "#94a39d", text: "#94a39d" };
  const PAD = { top: 20, right: 52, bottom: 30, left: 44 };

  function niceMax(v) {
    if (v <= 0) return 10;
    const pow = Math.pow(10, Math.floor(Math.log10(v)));
    return Math.ceil(v / pow) * pow;
  }

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 800;
    const cssH = canvas.clientHeight || 240;
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    const plotW = cssW - PAD.left - PAD.right;
    const plotH = cssH - PAD.top - PAD.bottom;
    const n = data.labels.length;
    const maxSales = niceMax(Math.max(1, ...data.sales));
    const maxRev = niceMax(Math.max(1, ...data.revenue));
    const xAt = (i) => PAD.left + (n <= 1 ? plotW / 2 : (plotW * i) / (n - 1));

    // ── grid + horizontal ticks (5 rows) ──
    ctx.font = "11px system-ui, sans-serif";
    ctx.textBaseline = "middle";
    const ROWS = 5;
    for (let r = 0; r <= ROWS; r++) {
      const y = PAD.top + (plotH * r) / ROWS;
      ctx.strokeStyle = COLORS.grid;
      ctx.beginPath();
      ctx.moveTo(PAD.left, y);
      ctx.lineTo(PAD.left + plotW, y);
      ctx.stroke();
      const frac = 1 - r / ROWS;
      ctx.fillStyle = COLORS.sales;
      ctx.textAlign = "right";
      ctx.fillText(Math.round(maxSales * frac), PAD.left - 6, y);   // left axis = sales
      ctx.fillStyle = COLORS.revenue;
      ctx.textAlign = "left";
      ctx.fillText(Math.round(maxRev * frac), PAD.left + plotW + 6, y); // right axis = revenue
    }

    // ── x labels ──
    ctx.fillStyle = COLORS.text;
    ctx.textAlign = "center";
    data.labels.forEach((lbl, i) => ctx.fillText(lbl, xAt(i), cssH - PAD.bottom + 14));

    // ── line drawing helper ──
    function line(series, max, color) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      series.forEach((v, i) => {
        const x = xAt(i);
        const y = PAD.top + plotH * (1 - v / max);
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      });
      ctx.stroke();
      // points
      ctx.fillStyle = color;
      series.forEach((v, i) => {
        const x = xAt(i);
        const y = PAD.top + plotH * (1 - v / max);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    line(data.sales, maxSales, COLORS.sales);
    line(data.revenue, maxRev, COLORS.revenue);
  }

  draw();
  window.addEventListener("resize", draw);
})();
