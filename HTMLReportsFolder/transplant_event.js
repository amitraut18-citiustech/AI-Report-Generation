(function () {
  "use strict";

  // Column order matches the thought file's Layout section exactly.
  // Total Transplants is injected separately (it echoes the overall row count).
  var DATE_FIELDS = ["dateOfVisit", "dateOfPreviousVisit", "transplantDate", "infusionDate"];

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  // Match .NET ToShortDateString(): locale short date, no time component.
  // Guard invalid/empty values by rendering them verbatim.
  function toShortDate(value) {
    if (value === null || value === undefined || value === "") return "";
    var d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    return d.toLocaleDateString();
  }

  function textCell(row, value) {
    var td = document.createElement("td");
    td.textContent = value === null || value === undefined ? "" : String(value);
    return td;
  }

  function dateCell(value) {
    var td = document.createElement("td");
    td.textContent = toShortDate(value);
    return td;
  }

  // No parameters for this report; render a neutral placeholder line.
  function renderFilters(el, params) {
    if (!el) return;
    var keys = params && typeof params === "object" ? Object.keys(params) : [];
    if (!keys.length) {
      el.textContent = "No filters applied — all transplant events.";
      return;
    }
    el.textContent = "Filters: " + keys.map(function (k) {
      return k + " = " + params[k];
    }).join("  ·  ");
  }

  // Banner: "Total Transplants: {rows.length}" (mirrors @Model.Count()).
  function renderSummary(el, totalTransplants) {
    if (!el) return;
    el.textContent = "Total Transplants: " + totalTransplants;
    el.hidden = false;
  }

  function renderNarrative(el, text) {
    if (!el) return;
    if (text && String(text).trim()) {
      el.textContent = text;
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  // Build one <tr> per row, in incoming order (rows arrive ordered by dateOfVisit).
  // The "Total Transplants" column repeats the overall count on every row.
  function renderRows(tbody, rows, totalTransplants) {
    if (!tbody) return;
    tbody.textContent = "";
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.appendChild(textCell(row, row.patientName));        // Patient
      tr.appendChild(dateCell(row.dateOfVisit));             // Date of Visit
      tr.appendChild(dateCell(row.dateOfPreviousVisit));     // Date of Previous Visit
      tr.appendChild(dateCell(row.transplantDate));          // Transplant Date
      tr.appendChild(dateCell(row.infusionDate));            // Infusion Date
      tr.appendChild(textCell(row, row.eventId));            // Event ID
      tr.appendChild(textCell(row, row.transplantNumber));   // Transplant Number
      tr.appendChild(textCell(row, totalTransplants));       // Total Transplants (overall count)
      tr.appendChild(textCell(row, row.isInpatient));        // Inpatient ("Yes"/"No", pre-derived)
      tbody.appendChild(tr);
    });
  }

  function renderFooter(data, rowCount) {
    var gen = document.querySelector("[data-generated]");
    var exec = document.querySelector("[data-executed-by]");
    var meta = data.meta || {};
    if (gen) {
      var when = meta.generatedAt ? new Date(meta.generatedAt) : null;
      var whenText = when && !isNaN(when.getTime()) ? when.toLocaleString() : (meta.generatedAt || "");
      gen.textContent = whenText ? "Generated: " + whenText : "";
    }
    if (exec) {
      var parts = [];
      if (meta.executedBy) parts.push("Executed by: " + meta.executedBy);
      parts.push("Rows: " + rowCount);
      exec.textContent = parts.join("  ·  ");
    }
  }

  function renderEmpty(show) {
    var empty = document.querySelector("[data-empty]");
    var table = document.querySelector(".report__table");
    if (empty) empty.hidden = !show;
    if (table) table.style.display = show ? "none" : "";
  }

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var rows = Array.isArray(data.rows) ? data.rows : [];
    var totalTransplants = rows.length; // overall count, echoed in banner and every row

    renderFilters(document.querySelector("[data-filters]"), data.parameters);
    renderSummary(document.querySelector("[data-summary]"), totalTransplants);
    renderNarrative(document.querySelector("[data-narrative]"), data.narrative);

    if (!rows.length) {
      renderEmpty(true);
    } else {
      renderEmpty(false);
      renderRows(document.querySelector("[data-rows]"), rows, totalTransplants);
    }

    renderFooter(data, totalTransplants);
  });
})();
