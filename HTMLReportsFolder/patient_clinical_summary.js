/*
 * patient_clinical_summary.js
 *
 * Renders the Patient Clinical Summary Report ENTIRELY from window.REPORT_DATA.
 *
 * IMPORTANT CONTRACT:
 *   - Rows arrive ALREADY FILTERED by the .NET host (visit-date window, age range,
 *     status applied server-side in PatientDataService.GetClinicalFlatRowsAsync).
 *     This script does NOT re-implement any WHERE / parameter filtering. Rows are
 *     rendered as-is.
 *   - The filter form is interactive: it round-trips the 4 filter values through the
 *     page query string (preserving the routing `report=` param) so the host re-queries
 *     and re-injects REPORT_DATA. No client-side row filtering ever happens here.
 */
(function () {
  "use strict";

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  /* ---------------------------------------------------------------- helpers */

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  // Format an ISO date string to MM/dd/yyyy (matches RDL Format(..., "MM/dd/yyyy")).
  function formatDateMDY(iso) {
    if (iso == null || iso === "") return "-";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getMonth() + 1) + "/" + pad2(d.getDate()) + "/" + d.getFullYear();
  }

  // Format an ISO datetime to MM/dd/yyyy HH:mm (footer).
  function formatDateTime(iso) {
    if (iso == null || iso === "") return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getMonth() + 1) + "/" + pad2(d.getDate()) + "/" + d.getFullYear() +
      " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  function num(v) { return (v == null) ? null : Number(v); }

  /* -------------------------------------------- RDL calculated per-row fields */

  // Age = Floor(DateDiff(Day, DateOfBirth, Today()) / 365.25)  (RDL display age).
  function calcAge(dobIso) {
    if (!dobIso) return 0;
    var dob = new Date(dobIso);
    if (isNaN(dob.getTime())) return 0;
    var days = Math.floor((Date.now() - dob.getTime()) / 86400000);
    return Math.floor(days / 365.25);
  }

  // BMI = height>0 ? Round(weight / (h/100)^2, 1) : 0.
  function calcBmi(heightCm, weightKg) {
    var h = num(heightCm), w = num(weightKg);
    if (!h || h <= 0 || w == null) return 0;
    var m = h / 100;
    return Math.round((w / (m * m)) * 10) / 10;
  }

  // DaysSincePreviousVisit = DateDiff(Day, DateOfPreviousVisit, DateOfVisit).
  // Computed per the RDL field, but the RDL never places it in a cell, so it is
  // intentionally not rendered anywhere in this layout.
  function calcDaysSincePreviousVisit(prevIso, visitIso) {
    if (!prevIso || !visitIso) return null;
    var a = new Date(prevIso), b = new Date(visitIso);
    if (isNaN(a.getTime()) || isNaN(b.getTime())) return null;
    return Math.round((b.getTime() - a.getTime()) / 86400000);
  }

  // LabFlag = "" (no lab) | "OUT" (out of ref range) | "OK".
  function calcLabFlag(labValue, refLow, refHigh) {
    var v = num(labValue);
    if (v == null) return "";
    var lo = num(refLow), hi = num(refHigh);
    if ((lo != null && v < lo) || (hi != null && v > hi)) return "OUT";
    return "OK";
  }

  /* ------------------------------------- RDL custom VB <Code> reimplementation */

  function bmiCategory(bmi) {
    if (!bmi || bmi === 0) return "N/A";
    if (bmi < 18.5) return "Underweight";
    if (bmi < 25) return "Normal";
    if (bmi < 30) return "Overweight";
    return "Obese";
  }

  function riskScore(age, inpatient, outOfRangeLabs) {
    var score = 0;
    if (age >= 65) score += 2;
    else if (age >= 45) score += 1;
    if (inpatient) score += 2;
    score += (outOfRangeLabs || 0);
    return score;
  }

  // Enrich each fed row with the RDL calculated fields.
  function enrich(rows) {
    return rows.map(function (r) {
      var e = Object.assign({}, r);
      e._age = calcAge(r.dateOfBirth);
      e._bmi = calcBmi(r.heightCm, r.weightKg);
      e._daysSincePreviousVisit = calcDaysSincePreviousVisit(r.dateOfPreviousVisit, r.dateOfVisit);
      e._labFlag = calcLabFlag(r.labValue, r.refLow, r.refHigh);
      return e;
    });
  }

  /* ----------------------------------------------------------- filter form */

  // Populate the form from applied parameters; on submit merge values into the
  // query string and reload (host re-filters). NEVER filters rows here.
  function wireFilterForm(params) {
    var form = document.querySelector("[data-filter-form]");
    if (!form) return;
    ["fromDate", "toDate", "minAge", "maxAge"].forEach(function (k) {
      var el = form.querySelector('[name="' + k + '"]');
      if (el != null && params[k] != null && params[k] !== "") {
        var v = params[k];
        // date inputs need yyyy-MM-dd; slice ISO datetimes if present.
        if (el.type === "date" && typeof v === "string" && v.length >= 10) v = v.slice(0, 10);
        el.value = v;
      }
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var qs = new URLSearchParams(location.search); // preserves report= and any other routing params
      form.querySelectorAll("[name]").forEach(function (el) { qs.set(el.name, el.value); });
      location.search = qs.toString(); // host re-queries and re-injects REPORT_DATA
    });
  }

  /* --------------------------------------------------------- filters echo */

  function renderFiltersEcho(params) {
    var el = document.querySelector("[data-filters]");
    if (!el) return;
    var from = params.fromDate ? formatDateMDY(params.fromDate) : "-";
    var to = params.toDate ? formatDateMDY(params.toDate) : "-";
    var minA = (params.minAge != null && params.minAge !== "") ? params.minAge : "-";
    var maxA = (params.maxAge != null && params.maxAge !== "") ? params.maxAge : "-";
    var status = params.status || "All";
    el.textContent = "Filters  -  Visit dates: " + from + " to " + to +
      "     |     Age: " + minA + " to " + maxA +
      "     |     Patient status: " + status;
  }

  /* --------------------------------------------------- narrative + footer */

  function renderNarrative(text) {
    var el = document.querySelector("[data-narrative]");
    if (!el) return;
    if (text && String(text).trim() !== "") {
      el.textContent = text;
      el.hidden = false;
    }
  }

  function renderFooter(meta, params) {
    var gen = document.querySelector("[data-generated]");
    var by = document.querySelector("[data-executed-by]");
    var when = formatDateTime(meta.generatedAt);
    var user = meta.executedBy || params.rptUser || "system";
    if (gen) gen.textContent = "Generated: " + (when || "-") + "     |     Run by: " + user;
    if (by) by.textContent = meta.rowCount != null ? ("Rows: " + meta.rowCount) : "";
  }

  /* ---------------------------------------------------- grouping utilities */

  function distinct(arr) {
    var seen = Object.create(null), out = [];
    arr.forEach(function (v) {
      var k = String(v);
      if (!seen[k]) { seen[k] = true; out.push(v); }
    });
    return out;
  }

  function groupBy(rows, keyFn) {
    var map = new Map();
    rows.forEach(function (r) {
      var k = keyFn(r);
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(r);
    });
    return map;
  }

  /* -------------------------------------------------- Facility Summary tablix */

  function td(text, cls) {
    var el = document.createElement("td");
    el.textContent = (text == null ? "" : String(text));
    if (cls) el.className = cls;
    return el;
  }

  function renderFacilitySummary(rows) {
    var section = document.querySelector("[data-summary-section]");
    var tbody = document.querySelector("[data-facility-summary]");
    if (!tbody) return;
    tbody.innerHTML = "";

    // grpFacSummary on FacilityName, sorted by FacilityName.
    var byFacility = groupBy(rows, function (r) { return r.facilityName; });
    var facilities = Array.from(byFacility.keys()).sort(function (a, b) {
      return String(a).localeCompare(String(b));
    });

    facilities.forEach(function (fac) {
      var frows = byFacility.get(fac);
      var patients = distinct(frows.map(function (r) { return r.patientId; })).length;
      var events = distinct(frows.map(function (r) { return r.eventId; })).length;

      // RDL Avg(Age) averages over the facility's detail rows.
      var ageSum = frows.reduce(function (s, r) { return s + (r._age || 0); }, 0);
      var avgAge = frows.length ? Math.round(ageSum / frows.length) : 0;

      // CountDistinct(IIF(IsInpatient, EventId, Nothing)) -> distinct inpatient events.
      var inpatientEvents = distinct(
        frows.filter(function (r) { return r.isInpatient; })
             .map(function (r) { return r.eventId; })
      ).length;

      var oor = frows.reduce(function (s, r) { return s + (r._labFlag === "OUT" ? 1 : 0); }, 0);

      var tr = document.createElement("tr");
      tr.appendChild(td(fac));
      tr.appendChild(td(patients, "num"));
      tr.appendChild(td(events, "num"));
      tr.appendChild(td(avgAge, "num"));
      tr.appendChild(td(inpatientEvents, "num"));
      var oorTd = td(oor, "num");
      if (oor > 0) oorTd.classList.add("oor-cell"); // red + bold when > 0
      tr.appendChild(oorTd);
      tbody.appendChild(tr);
    });

    if (section) section.hidden = facilities.length === 0;
  }

  /* -------------------------------------------- Clinical Detail nested tablix */

  var DETAIL_HEADERS = ["Event", "Visit Date", "Provider", "Donor", "Setting",
    "Test", "Result", "Reference", "Flag"];

  function renderDetail(rows) {
    var section = document.querySelector("[data-detail-section]");
    var host = document.querySelector("[data-detail]");
    if (!host) return;
    host.innerHTML = "";

    // grpFacility -> grpPatient -> grpDetail (event + lab).
    var byFacility = groupBy(rows, function (r) { return r.facilityName; });
    var facilities = Array.from(byFacility.keys()).sort(function (a, b) {
      return String(a).localeCompare(String(b));
    });

    facilities.forEach(function (fac) {
      var frows = byFacility.get(fac);
      var group = document.createElement("div");
      group.className = "facility-group";

      var f0 = frows[0];
      var band = document.createElement("div");
      band.className = "facility-band";
      band.textContent = "Facility:  " + fac + "   -   " +
        (f0.facilityCity || "") + ", " + (f0.facilityState || "");
      group.appendChild(band);

      // grpPatient on PatientId, sorted by PatientName.
      var byPatient = groupBy(frows, function (r) { return r.patientId; });
      var patientIds = Array.from(byPatient.keys()).sort(function (a, b) {
        var na = byPatient.get(a)[0].patientName || "";
        var nb = byPatient.get(b)[0].patientName || "";
        return na.localeCompare(nb);
      });

      patientIds.forEach(function (pid) {
        var prows = byPatient.get(pid);
        group.appendChild(renderPatientBanner(prows));
        group.appendChild(renderDetailTable(prows));
      });

      host.appendChild(group);
    });

    if (section) section.hidden = facilities.length === 0;
  }

  function renderPatientBanner(prows) {
    var p = prows[0];
    // Scoped aggregates over the patient group (First/Sum ,"grpPatient").
    var age = p._age;
    var anyInpatient = prows.some(function (r) { return r.isInpatient; });
    var oorLabs = prows.reduce(function (s, r) { return s + (r._labFlag === "OUT" ? 1 : 0); }, 0);
    var risk = riskScore(age, anyInpatient, oorLabs);
    var highRisk = risk >= 4;

    var div = document.createElement("div");
    div.className = "patient-banner " + (highRisk ? "risk-high" : "risk-low");

    var bmi = p._bmi;
    var items = [
      ["Patient", p.patientName],
      ["MRN", p.mrn],
      ["Age", age],
      ["Sex", p.gender],
      ["BMI", bmi + " (" + bmiCategory(bmi) + ")"],
      ["Risk", risk + (highRisk ? " (HIGH)" : "")],
      ["Primary Dx", p.primaryDiagnosis || "-"],
      ["Active meds", p.activeMedCount]
    ];
    items.forEach(function (pair) {
      var span = document.createElement("span");
      span.className = "pb-item";
      var lbl = document.createElement("span");
      lbl.className = "pb-label";
      lbl.textContent = pair[0] + ": ";
      span.appendChild(lbl);
      span.appendChild(document.createTextNode(pair[1] == null ? "" : String(pair[1])));
      div.appendChild(span);
    });
    return div;
  }

  function renderDetailTable(prows) {
    // grpDetail sort: DateOfVisit then LabTestName.
    var sorted = prows.slice().sort(function (a, b) {
      var da = new Date(a.dateOfVisit).getTime() || 0;
      var db = new Date(b.dateOfVisit).getTime() || 0;
      if (da !== db) return da - db;
      return String(a.labTestName || "").localeCompare(String(b.labTestName || ""));
    });

    var table = document.createElement("table");
    table.className = "detail-table";

    var thead = document.createElement("thead");
    var htr = document.createElement("tr");
    DETAIL_HEADERS.forEach(function (h) {
      var th = document.createElement("th");
      th.scope = "col";
      th.textContent = h;
      htr.appendChild(th);
    });
    thead.appendChild(htr);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    sorted.forEach(function (r, i) {
      var tr = document.createElement("tr");
      if (i % 2 === 0) tr.classList.add("zebra"); // RowNumber Mod 2 = 1 -> shade (1-based)

      tr.appendChild(td(r.eventId));
      tr.appendChild(td(formatDateMDY(r.dateOfVisit)));
      tr.appendChild(td((r.providerName || "-") + " (" + (r.specialty || "") + ")"));
      tr.appendChild(td(r.donorType));

      var settingTd = td(r.isInpatient ? "Inpatient" : "Outpatient");
      if (r.isInpatient) settingTd.classList.add("cell-inpatient"); // yellow highlight
      tr.appendChild(settingTd);

      tr.appendChild(td(r.labTestName == null ? "-" : r.labTestName));
      tr.appendChild(td(r.labValue == null ? "-" : (String(r.labValue) + " " + (r.labUnit || ""))));
      tr.appendChild(td(r.refLow == null ? "-" : (String(r.refLow) + " - " + String(r.refHigh))));

      var flagTd = td(r._labFlag);
      if (r._labFlag === "OUT") flagTd.classList.add("flag-out");      // red + bold
      else if (r._labFlag === "OK") flagTd.classList.add("flag-ok");   // green
      tr.appendChild(flagTd);

      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
  }

  /* --------------------------------------------------------------- bootstrap */

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var params = data.parameters || {};
    var rows = Array.isArray(data.rows) ? data.rows : []; // ALREADY filtered by host

    wireFilterForm(params);
    renderFiltersEcho(params);
    renderNarrative(data.narrative);
    renderFooter(data.meta || {}, params);

    var empty = document.querySelector("[data-empty]");
    if (!rows.length) {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;

    var enriched = enrich(rows);
    renderFacilitySummary(enriched);
    renderDetail(enriched);
  });
})();
