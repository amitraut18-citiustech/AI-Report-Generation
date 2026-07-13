(function () {
  "use strict";

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  /**
   * Format an ISO date string or date-like value as MM/dd/yyyy.
   * Returns the original value if parsing fails.
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

  /** Escape HTML special characters to prevent XSS. */
  function esc(value) {
    if (value == null) return "";
    var s = String(value);
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /**
   * Render all patient rows into the table body.
   * Applies alternating row striping (odd rows #F2F2F2, even rows white).
   */
  function renderRows(rows) {
    var tbody = document.querySelector("[data-rows]");
    if (!tbody) return;

    if (!rows.length) {
      tbody.innerHTML = "";
      return;
    }

    var html = [];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var cls = (i % 2 === 0) ? "row-odd" : "row-even"; // first row is odd (1-based)
      html.push(
        '<tr class="' + cls + '">' +
          "<td>" + esc(r.firstName) + "</td>" +
          "<td>" + esc(r.lastName) + "</td>" +
          "<td>" + esc(r.gender) + "</td>" +
          "<td>" + esc(formatDate(r.dateOfBirth)) + "</td>" +
          "<td>" + esc(r.contactNumber) + "</td>" +
          "<td>" + esc(r.email) + "</td>" +
          "<td>" + esc(r.phoneNumber) + "</td>" +
        "</tr>"
      );
    }
    tbody.innerHTML = html.join("");
  }

  /** Show or hide the empty-state message. */
  function toggleEmpty(hasRows) {
    var el = document.querySelector("[data-empty]");
    if (el) {
      el.hidden = hasRows;
    }
  }

  function renderNarrative(narrative) {
    var el = document.querySelector("[data-narrative]");
    if (!el) return;
    if (narrative) {
      var sentences = narrative.split(/(?<=\.)\s+/);
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

  /** Populate the footer with generation metadata. */
  function renderFooter(meta) {
    var genEl = document.querySelector("[data-generated]");
    var byEl = document.querySelector("[data-executed-by]");
    if (genEl && meta.generatedAt) {
      genEl.textContent = "Generated: " + formatDate(meta.generatedAt);
    }
    if (byEl && meta.executedBy) {
      byEl.textContent = "Executed by: " + meta.executedBy;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var rows = Array.isArray(data.rows) ? data.rows : [];
    var meta = data.meta || {};

    renderRows(rows);
    toggleEmpty(rows.length > 0);
    renderNarrative(data.narrative);
    renderFooter(meta);
  });
})();
