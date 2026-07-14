(function () {
  "use strict";

  /* ── helpers ──────────────────────────────────────────────────────── */

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  /**
   * Format an ISO-8601 date string as MM/dd/yyyy (matching the RDL format).
   * Returns empty string for falsy / unparseable values.
   */
  function formatDate(value) {
    if (!value) return "";
    var d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    var mm = String(d.getMonth() + 1).padStart(2, "0");
    var dd = String(d.getDate()).padStart(2, "0");
    var yyyy = d.getFullYear();
    return mm + "/" + dd + "/" + yyyy;
  }

  function esc(text) {
    var el = document.createElement("span");
    el.textContent = text == null ? "" : String(text);
    return el.innerHTML;
  }

  /* ── per-patient transplant count ────────────────────────────────── */

  /**
   * Build a map { patientName -> count } by grouping rows on patientName.
   * Consistent with the RDL render service logic (RdlRenderer.cs).
   */
  function buildTransplantCounts(rows) {
    var counts = {};
    for (var i = 0; i < rows.length; i++) {
      var name = rows[i].patientName || "";
      counts[name] = (counts[name] || 0) + 1;
    }
    return counts;
  }

  /* ── rendering ───────────────────────────────────────────────────── */

  function renderFiltersEcho(params) {
    var el = document.querySelector("[data-filters]");
    if (!el) return;
    var parts = [];
    if (params.fromDate) parts.push("From: " + formatDate(params.fromDate));
    if (params.toDate) parts.push("To: " + formatDate(params.toDate));
    if (parts.length) {
      el.textContent = "Applied filters — " + parts.join(" | ");
    } else {
      el.style.display = "none";
    }
  }

  function renderSummary(rowCount) {
    var el = document.querySelector("[data-summary]");
    if (!el) return;
    el.textContent = "Total Transplants: " + rowCount;
    el.hidden = false;
  }

  function renderNarrative(text) {
    var el = document.querySelector("[data-narrative]");
    if (!el) return;
    if (text) {
      var sentences = text.split(/(?<=\.)\s+/);
      var paragraphs = [];
      for (var i = 0; i < sentences.length; i += 2) {
        var chunk = sentences.slice(i, i + 2).join(" ");
        paragraphs.push("<p>" + esc(chunk) + "</p>");
      }
      el.innerHTML =
        '<div class="report__narrative-header">' +
          '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 1.5a1 1 0 1 1 0 2 1 1 0 0 1 0-2zM6.5 6.5h2v5h1v1h-3v-1h1v-4h-1v-1z"/></svg>' +
          'AI Summary' +
        '</div>' +
        '<div class="report__narrative-body">' + paragraphs.join("") + '</div>';
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  function renderTable(rows, transplantCounts) {
    var tbody = document.querySelector("[data-rows]");
    var emptyEl = document.querySelector("[data-empty]");
    if (!tbody) return;

    if (!rows.length) {
      if (emptyEl) emptyEl.hidden = false;
      return;
    }

    var html = [];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var total = transplantCounts[r.patientName || ""] || 0;
      html.push(
        "<tr>" +
          "<td>" + esc(r.patientName) + "</td>" +
          "<td>" + esc(formatDate(r.dateOfVisit)) + "</td>" +
          "<td>" + esc(formatDate(r.dateOfPreviousVisit)) + "</td>" +
          "<td>" + esc(formatDate(r.transplantDate)) + "</td>" +
          "<td>" + esc(formatDate(r.infusionDate)) + "</td>" +
          "<td>" + esc(r.eventId) + "</td>" +
          "<td>" + esc(r.transplantNumber) + "</td>" +
          "<td>" + esc(total) + "</td>" +
          "<td>" + esc(r.donorType) + "</td>" +
          "<td>" + esc(r.isInpatient) + "</td>" +
        "</tr>"
      );
    }
    tbody.innerHTML = html.join("");
  }

  function renderFooter(meta) {
    var genEl = document.querySelector("[data-generated]");
    var byEl = document.querySelector("[data-executed-by]");
    if (genEl && meta.generatedAt) {
      genEl.textContent = "Generated: " + formatDate(meta.generatedAt);
    }
    if (byEl && meta.executedBy) {
      byEl.textContent = "Run by: " + meta.executedBy;
    }
  }

  /* ── main ─────────────────────────────────────────────────────────── */

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var rows = Array.isArray(data.rows) ? data.rows : [];
    var params = data.parameters || {};
    var meta = data.meta || {};

    renderFiltersEcho(params);
    renderSummary(rows.length);
    renderNarrative(data.narrative);

    var transplantCounts = buildTransplantCounts(rows);
    renderTable(rows, transplantCounts);

    renderFooter(meta);
  });
})();
