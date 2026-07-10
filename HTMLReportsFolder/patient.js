(function () {
  "use strict";

  // Column order and field mapping straight from the thought file / PatientReportViewModel.
  var COLUMNS = [
    { key: "firstName", label: "First Name" },
    { key: "lastName", label: "Last Name" },
    { key: "gender", label: "Gender" },
    { key: "dateOfBirth", label: "Date of Birth", format: formatShortDate },
    { key: "contactNumber", label: "Contact Number" },
    { key: "email", label: "Email" },
    { key: "phoneNumber", label: "Phone Number" }
  ];

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  // Mirrors DateTime.ToShortDateString() default en-US pattern (M/d/yyyy, no leading zeros).
  function formatShortDate(value) {
    if (value === null || value === undefined || value === "") return "";
    var d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    var month = d.getMonth() + 1;
    var day = d.getDate();
    var year = d.getFullYear();
    return month + "/" + day + "/" + year;
  }

  function cellValue(row, column) {
    var raw = row[column.key];
    if (raw === null || raw === undefined) raw = "";
    return column.format ? column.format(raw) : String(raw);
  }

  // Rows arrive already ordered by lastName (ascending) from the data service — preserve order.
  function renderRows(tbody, rows) {
    tbody.textContent = "";
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      COLUMNS.forEach(function (column) {
        var td = document.createElement("td");
        td.textContent = cellValue(row, column);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function renderNarrative(el, text) {
    if (!el) return;
    if (text && String(text).trim() !== "") {
      el.textContent = text;
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  function renderFooter(data) {
    var meta = data.meta || {};
    var generatedEl = document.querySelector("[data-generated]");
    var executedEl = document.querySelector("[data-executed-by]");
    var rowCountEl = document.querySelector("[data-row-count]");

    if (generatedEl && meta.generatedAt) {
      var g = new Date(meta.generatedAt);
      generatedEl.textContent = "Generated: " +
        (isNaN(g.getTime()) ? String(meta.generatedAt) : g.toLocaleString());
    }
    if (executedEl && meta.executedBy) {
      executedEl.textContent = "Executed by: " + meta.executedBy;
    }
    if (rowCountEl) {
      var count = typeof meta.rowCount === "number"
        ? meta.rowCount
        : (Array.isArray(data.rows) ? data.rows.length : 0);
      rowCountEl.textContent = "Patients: " + count;
    }
  }

  function renderEmpty(show) {
    var emptyEl = document.querySelector("[data-empty]");
    var tableEl = document.querySelector("[data-table]");
    if (emptyEl) emptyEl.hidden = !show;
    if (tableEl) tableEl.hidden = show;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var rows = Array.isArray(data.rows) ? data.rows : [];

    renderNarrative(document.querySelector("[data-narrative]"), data.narrative);
    renderFooter(data);

    if (!rows.length) {
      renderEmpty(true);
      return;
    }

    renderEmpty(false);
    renderRows(document.querySelector("[data-rows]"), rows);
  });
})();
